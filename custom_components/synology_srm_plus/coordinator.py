"""Data coordinator for Synology SRM Plus."""

from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
import ipaddress
import json
import logging
import re
import time
from typing import Any

import synology_srm
from synology_srm.http import SynologyException

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_SSL,
    CONF_USERNAME,
    CONF_VERIFY_SSL,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .clients import normalize_clients
from .const import CONF_SAFE_ACCESS, DOMAIN, SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)

STORAGE_VERSION = 1
# Calls with answers that look different, used by check_parallel.
CHECK_CALLS = (
    ("SYNO.Core.DDNS.ExtIP", "list"),
    ("SYNO.Core.DDNS.Record", "list"),
    ("SYNO.Mesh.System.Info", "get"),
)
PARALLEL_CALLS = 3  # simultaneous requests to the router


# Answers that must hold this key; if one doesn't, the call is probed (see _verify_answer).
EXPECTED_KEYS = {"tps_trends": "trends"}


def _raw(
    api: str, method: str = "get", version: int = 1
) -> Callable[[synology_srm.Client], Any]:
    """Call an SRM API the library has no wrapper for.

    The endpoint (entry.cgi, or another .cgi for some DSM APIs) is passed in by the
    coordinator, from the API list the router returns.
    """

    def call(c: synology_srm.Client, endpoint: str = "entry.cgi") -> Any:
        return c.http.call(endpoint=endpoint, api=api, method=method, version=version)

    call.raw = True  # type: ignore[attr-defined]
    return call


def reduce_wifi_networks(payload: Any) -> dict[str, Any]:
    """Keep only the harmless fields of the Wi-Fi network settings.

    The raw payload also holds the Wi-Fi passwords: they must never reach the
    coordinator data (which ends up in diagnostics).
    """
    profiles = payload.get("profiles") if isinstance(payload, dict) else None
    networks: list[dict[str, Any]] = []
    for profile in profiles if isinstance(profiles, list) else []:
        if not isinstance(profile, dict):
            continue
        radios = []
        for radio in profile.get("radio_list") or []:
            if not isinstance(radio, dict):
                continue
            item = {
                k: radio[k]
                for k in ("radio_type", "enable", "hide_ssid", "ssid", "max_connection", "enable_client_isolation")
                if k in radio
            }
            mac_filter = radio.get("mac_filter")
            item["mac_filter_profile_id"] = (
                mac_filter.get("profile_id") if isinstance(mac_filter, dict) else None
            )
            radios.append(item)
        networks.append(
            {
                "id": profile.get("id"),
                "name": profile.get("name"),
                "network_type": profile.get("network_type"),
                "enable_smart_connect": profile.get("enable_smart_connect"),
                "radios": radios,
            }
        )
    return {"networks": networks}


def _wifi_networks_call(c: synology_srm.Client, endpoint: str = "entry.cgi") -> Any:
    return reduce_wifi_networks(
        c.http.call(
            endpoint=endpoint, api="SYNO.Wifi.Network.Setting", method="get", version=1
        )
    )


_wifi_networks_call.raw = True  # type: ignore[attr-defined]


# key -> (API name, call on the synology_srm client, poll every N updates)
# The API name is checked against the router's API list: an API the router does
# not offer is skipped silently (SRM models and firmwares differ). Slow-changing
# data is read less often to spare the router.
ENDPOINTS: dict[str, tuple[str, Callable[[synology_srm.Client], Any], int]] = {
    "system_utilization": (
        "SYNO.Core.System.Utilization",
        lambda c: c.core.get_system_utilization(),
        1,
    ),
    "traffic_live": (
        "SYNO.Core.NGFW.Traffic",
        lambda c: c.core.get_ngfw_traffic("live"),
        1,
    ),
    "external_ip": ("SYNO.Core.DDNS.ExtIP", lambda c: c.core.list_ddns_extip(), 5),
    "ddns": ("SYNO.Core.DDNS.Record", lambda c: c.core.list_ddns_record(), 10),
    "system_info": ("SYNO.Mesh.System.Info", lambda c: c.mesh.get_system_info(), 10),
    "connection_status": (
        "SYNO.Core.Network.Router.ConnectionStatus",
        _raw("SYNO.Core.Network.Router.ConnectionStatus"),
        2,
    ),
    "topology": (
        "SYNO.Core.Network.Router.Topology",
        _raw("SYNO.Core.Network.Router.Topology"),
        10,
    ),
    "ethernet": (
        "SYNO.Core.Network.Ethernet",
        _raw("SYNO.Core.Network.Ethernet", "list"),
        5,
    ),
    # No filter: devices that are known but offline are returned too.
    "clients": (
        "SYNO.Core.Network.NSM.Device",
        lambda c: c.core.get_network_nsm_device(),
        1,
    ),
    "wifi_radio": ("SYNO.Wifi.Radio.Status", _raw("SYNO.Wifi.Radio.Status"), 5),
    "radio_setting": ("SYNO.Wifi.Radio.Setting", _raw("SYNO.Wifi.Radio.Setting"), 10),
    "wifi_devices": ("SYNO.Wifi.Device", _raw("SYNO.Wifi.Device"), 1),
    # Router throughput, per-band throughput, ports (these see offloaded traffic).
    "mesh_nodes": ("SYNO.Mesh.Node.List", _raw("SYNO.Mesh.Node.List", version=4), 1),
    "mesh_network": (
        "SYNO.Mesh.Network.Info",
        _raw("SYNO.Mesh.Network.Info", version=3),
        1,
    ),
    "mesh_status": ("SYNO.Mesh.Status", _raw("SYNO.Mesh.Status"), 2),
    # CPU and memory of every node (the satellites too).
    "mesh_utilization": ("SYNO.Mesh.System.Utilization", _raw("SYNO.Mesh.System.Utilization"), 1),
    "eth_ports": (
        "SYNO.Mesh.Network.EthPortInfo",
        _raw("SYNO.Mesh.Network.EthPortInfo"),
        3,
    ),
    # USB storage
    "usb_volumes": ("SYNO.DSM.Volume", _raw("SYNO.DSM.Volume", "list"), 5),
    # Security
    "tps_trends": (
        "SYNO.TPS.Statistic.Trends",
        _raw("SYNO.TPS.Statistic.Trends"),
        10,
    ),
    "tps_sensor": ("SYNO.TPS.Sensor", _raw("SYNO.TPS.Sensor"), 10),
    "new_devices": (
        "SYNO.Core.Network.NSM.Device.Notification",
        _raw("SYNO.Core.Network.NSM.Device.Notification"),
        2,
    ),
    "admin_sessions": (
        "SYNO.Core.CurrentConnection",
        _raw("SYNO.Core.CurrentConnection", "list"),
        3,
    ),
    "autoblock": ("SYNO.DSM.AutoBlock", _raw("SYNO.DSM.AutoBlock", "list"), 5),
    "autoblock_settings": ("SYNO.Core.Security.AutoBlock", _raw("SYNO.Core.Security.AutoBlock"), 10),
    "allow_wan": (
        "SYNO.Core.Security.Firewall.AllowSrmFromWan",
        _raw("SYNO.Core.Security.Firewall.AllowSrmFromWan"),
        10,
    ),
    "port_forward": (
        "SYNO.Core.Network.Router.PortForward",
        _raw("SYNO.Core.Network.Router.PortForward"),
        10,
    ),
    # Safe Access (parental control)
    "safe_profiles": (
        "SYNO.SafeAccess.AccessControl.Profile",
        _raw("SYNO.SafeAccess.AccessControl.Profile"),
        10,
    ),
    # Names of the local networks: SRM calls the profile of a network "$lbr0$".
    "local_networks": (
        "SYNO.Core.Network.LocalNetwork",
        _raw("SYNO.Core.Network.LocalNetwork", "list"),
        10,
    ),
    "safe_interfaces": (
        "SYNO.SafeAccess.AccessControl.ConfigGroup.Interface",
        _raw("SYNO.SafeAccess.AccessControl.ConfigGroup.Interface"),
        10,
    ),
    "safe_stats": (
        "SYNO.SafeAccess.Overview.Statistics",
        _raw("SYNO.SafeAccess.Overview.Statistics"),
        5,
    ),
    "macfilter_devices": ("SYNO.Wifi.MACFilter.Global", _raw("SYNO.Wifi.MACFilter.Global"), 10),
    "macfilter_profiles": ("SYNO.Wifi.MACFilter.Profile", _raw("SYNO.Wifi.MACFilter.Profile"), 10),
    "wifi_networks": ("SYNO.Wifi.Network.Setting", _wifi_networks_call, 10),
    "safe_devices": (
        "SYNO.SafeAccess.AccessControl.ConfigGroup.Device",
        _raw("SYNO.SafeAccess.AccessControl.ConfigGroup.Device"),
        5,
    ),
    "safe_device_time": (
        "SYNO.SafeAccess.AccessControl.ConfigGroup.Device.TimeSpent",
        _raw("SYNO.SafeAccess.AccessControl.ConfigGroup.Device.TimeSpent"),
        10,
    ),
    "safe_schedule": (
        "SYNO.SafeAccess.AccessControl.Profile.Schedule",
        _raw("SYNO.SafeAccess.AccessControl.Profile.Schedule"),
        5,
    ),
}

# API names the explore service never calls (side effects, files, secrets, heavy).
_EXPLORE_SKIP = re.compile(
    r"restart|reboot|shutdown|reset|upgrade|install|setup|scan|download|export|delete|"
    r"remove|blink|factory|format|backup|restore|login|logout|auth|encryption|purchase|"
    r"mydscenter|token|credential|otp|supportform|datacollect|upload|stream|filestation|"
    r"foldersharing|audioplayer|personmail|socialaccount|crypto|terminal|password|ldap|"
    r"directory|ntp|region|theme|desktop|appportal|apppriv|entry\.request|polling|"
    r"migration|snapshot|certificate\.(csr|crt|letsencrypt)|syslogclient\.(ca|filetransfer)|"
    r"core\.user|core\.group|core\.share|core\.file|core\.acl|core\.cms|"
    r"core\.package|dsm\.package|synology\.package|\.thumb",
    re.I,
)

# --- redaction of what the explore service writes to the log ---------------------
_SECRET_KEY = re.compile(
    r"pass|pwd|psk|secret|token|community|serial|private|credential|(^|_)pin($|_)|"
    r"(^|_)key($|_)|(^|_)sn$|auth_key|wpa",
    re.I,
)
_IDENTITY_KEY = re.compile(
    r"^(account|username|user|who|email|hostname|clientname|ssid|essid|wifi_ssid)$", re.I
)
_MAC = re.compile(r"\b(?:[0-9a-f]{2}[:-]){5}[0-9a-f]{2}\b", re.I)
_IPV4 = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
_IPV6 = re.compile(r"\b(?:[0-9a-f]{1,4}:){2,7}[0-9a-f]{0,4}\b", re.I)


# The synology-srm library sends the account, password and session id as URL query
# parameters, and requests / urllib3 quote the URL in their error messages and in
# their debug logs: scrub them before anything reaches a log.
_URL_SECRETS = re.compile(
    r"(?i)\b(passwd|password|pwd|_sid|sid|synotoken|token|otp_code|account)=[^&\s'\")]*"
)


def scrub_secrets(text: str) -> str:
    """Mask credentials and session ids that appear as URL query parameters."""
    return _URL_SECRETS.sub(lambda m: f"{m.group(1)}=***", text)


def safe_error(err: BaseException) -> str:
    """Return an error message that cannot hold the password or the session id."""
    return scrub_secrets(f"{type(err).__name__}: {err}")


class _ScrubFilter(logging.Filter):
    """Logging filter that masks URL credentials in a record."""

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            message = record.getMessage()
        except Exception:  # noqa: BLE001
            return True
        scrubbed = scrub_secrets(message)
        if scrubbed != message:
            record.msg, record.args = scrubbed, ()
        return True


def _install_log_scrubber() -> None:
    """Scrub the HTTP libraries' loggers (idempotent)."""
    for name in ("urllib3.connectionpool", "urllib3.util.retry", "urllib3.poolmanager"):
        logger = logging.getLogger(name)
        if not any(isinstance(f, _ScrubFilter) for f in logger.filters):
            logger.addFilter(_ScrubFilter())


_install_log_scrubber()


def _mask_ip(match: re.Match[str]) -> str:
    text = match.group(0)
    try:
        addr = ipaddress.ip_address(text)
    except ValueError:
        return text
    if addr.version == 4:
        parts = text.split(".")
        return f"{parts[0]}.{parts[1]}.x.x" if addr.is_private else "x.x.x.x"
    return "xxxx:xxxx::" if addr.is_global else text


def redact(value: Any) -> Any:
    """Return value with secrets, MAC addresses and public IPs masked."""
    if isinstance(value, dict):
        return {
            (_MAC.sub("xx:xx:xx:xx:xx:xx", k) if isinstance(k, str) else k): (
                "**redacted**"
                if (_SECRET_KEY.search(str(k)) or _IDENTITY_KEY.match(str(k))) and v
                else redact(v)
            )
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [redact(v) for v in value]
    if isinstance(value, str):
        value = _MAC.sub("xx:xx:xx:xx:xx:xx", value)
        value = _IPV4.sub(_mask_ip, value)
        return _IPV6.sub(_mask_ip, value)
    return value


def build_client(data: dict[str, Any]) -> synology_srm.Client:
    """Create a (blocking) SRM client from config entry data."""
    client = synology_srm.Client(
        host=data[CONF_HOST],
        port=data[CONF_PORT],
        username=data[CONF_USERNAME],
        password=data[CONF_PASSWORD],
        https=data[CONF_SSL],
    )
    if not data[CONF_VERIFY_SSL]:
        client.http.disable_https_verify()
    _isolate_call_params(client.http)
    return client


def _isolate_call_params(http: Any) -> None:
    """Give every call its own parameters dict.

    synology-srm's Http.call has `params: dict = {}` as default and writes the api,
    method and version into it: that one dict is shared by every call, so calls made
    at the same time (we run a few in parallel) send each other's api/method/version
    and the router answers with the wrong payload (a threat-statistics call returning
    the sensor settings, the external IP returning the DDNS record...).
    """
    original = http.call

    def call(endpoint: str, api: str, method: str, version: int = 1, params: dict | None = None, **kwargs: Any) -> Any:
        return original(endpoint, api, method, version, params=dict(params or {}), **kwargs)

    http.original_call = original  # kept for check_parallel, which shows what the library does on its own
    http.call = call


class SrmCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Fetch router data from SRM."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=SCAN_INTERVAL,
        )
        self.client = build_client(entry.data)
        # None until the API list has been read; then the set of API names.
        self._available_apis: set[str] | None = None
        self._api_info: dict[str, Any] | None = None
        self._apis_loaded = False
        self._poll = 0
        self._warned: set[str] = set()
        self._cache: dict[str, Any] = {}
        # Endpoints whose answer lacked its key: what was tried, and the version that worked.
        self.probes: dict[str, Any] = {}
        self._versions: dict[str, int] = {}
        # Last time each client was seen online (kept across restarts).
        self._store: Store[dict[str, str]] = Store(
            hass, STORAGE_VERSION, f"{DOMAIN}_{entry.entry_id}_last_seen"
        )
        self._last_seen: dict[str, str] = {}
        self._seen_now: dict[str, str] = {}
        self._online_prev: set[str] = set()

    @property
    def available_apis(self) -> set[str] | None:
        """Return the API names offered by the router, if known."""
        return self._available_apis

    def check_parallel(self, rounds: int = 10) -> list[str]:
        """Ask three different questions at the same time, with and without the per-call fix.

        Read-only. Compares each answer with the one given when asked alone and counts
        the answers that are another call's: that proves, on this very router, whether
        the library mixes up calls made together.
        """
        http = self.client.http
        original = getattr(http, "original_call", None)
        offered = self._available_apis
        calls = [c for c in CHECK_CALLS if offered is None or c[0] in offered]
        if original is None or len(calls) < 2:
            return ["Parallel check: not available on this router"]

        def shape(answer: Any) -> Any:
            return "list" if isinstance(answer, list) else tuple(sorted(answer)) if isinstance(answer, dict) else type(answer).__name__

        baseline: dict[str, Any] = {}
        for api, method in calls:
            try:
                baseline[api] = shape(http.call(endpoint=self._endpoint(api), api=api, method=method, version=1))
            except Exception as err:  # noqa: BLE001
                return [f"Parallel check: {api} failed alone: {safe_error(err)}"]
        if len(set(baseline.values())) < len(baseline):
            return ["Parallel check: the questions have answers too alike to tell apart"]

        def run(ask: Any) -> tuple[int, int, int]:
            wrong = errors = total = 0

            def one(item: tuple[str, str]) -> tuple[str, Any]:
                api, method = item
                try:
                    return api, shape(ask(self._endpoint(api), api, method, 1))
                except Exception:  # noqa: BLE001
                    return api, None

            with ThreadPoolExecutor(max_workers=len(calls)) as pool:
                for _ in range(rounds):
                    for api, got in pool.map(one, calls):
                        total += 1
                        if got is None:
                            errors += 1
                        elif got != baseline[api]:
                            wrong += 1
            return wrong, errors, total

        lines = [f"Parallel check: {len(calls)} different calls at the same time, {rounds} rounds"]
        for label, ask in (("library alone (no fix)", original), ("with the fix", http.call)):
            wrong, errors, total = run(ask)
            lines.append(f"  {label}: {wrong} of {total} answers were another call's answer, {errors} errors")
        return lines

    @property
    def api_versions(self) -> dict[str, str]:
        """Versions the router lists (min-max) for every API this integration calls."""
        info = self._api_info if isinstance(self._api_info, dict) else {}
        out: dict[str, str] = {}
        for api, _call, _every in ENDPOINTS.values():
            entry = info.get(api)
            if isinstance(entry, dict):
                out[api] = f"{entry.get('minVersion', '?')}-{entry.get('maxVersion', '?')}"
            else:
                out[api] = "not offered" if info else "unknown"
        return dict(sorted(out.items()))

    async def _async_setup(self) -> None:
        """Load the persisted last-seen times."""
        self._last_seen = await self._store.async_load() or {}

    def _endpoint(self, api: str) -> str:
        """Return the .cgi endpoint the router lists for an API."""
        info = self._api_info.get(api) if isinstance(self._api_info, dict) else None
        return str(info.get("path") or "entry.cgi") if isinstance(info, dict) else "entry.cgi"

    def _warn_once(self, key: str, message: str, *args: Any) -> None:
        """Warn the first time a call fails, then only log at debug level."""
        if key in self._warned:
            _LOGGER.debug(message, *args)
        else:
            self._warned.add(key)
            _LOGGER.warning(message, *args)

    def _load_available_apis(self) -> None:
        """Read (once) the API names offered by the router."""
        self._apis_loaded = True
        try:
            apis = self.client.base.query_info()
        except Exception as err:  # noqa: BLE001
            _LOGGER.warning(
                "SRM query_info failed, assuming all APIs exist: %s", safe_error(err)
            )
            return
        if isinstance(apis, dict):
            self._api_info = apis
            self._available_apis = set(apis)
            _LOGGER.debug("SRM exposes %d APIs", len(apis))

    def explore(self, name_filter: str | None = None) -> None:
        """Call get / list on every safe API and log what answers (blocking).

        Discovery tool: it never calls a method that writes, skips APIs whose name
        suggests a side effect, and masks secrets, MAC addresses and public IPs in
        the log. Please still skim the output before sharing it.
        """
        if not self._apis_loaded:
            self._load_available_apis()
        names = sorted(self._available_apis or [])
        wanted = [
            n
            for n in names
            if not _EXPLORE_SKIP.search(n)
            and (not name_filter or name_filter.lower() in n.lower())
        ]
        _LOGGER.info(
            "SRM explore: %d of %d APIs selected (filter=%r)",
            len(wanted),
            len(names),
            name_filter,
        )
        ok = 0
        for api in wanted:
            info = self._api_info.get(api) if isinstance(self._api_info, dict) else None
            info = info if isinstance(info, dict) else {}
            endpoint = str(info.get("path") or "entry.cgi")
            versions = sorted({1, int(info.get("maxVersion") or 1)})
            done = False
            for method in ("get", "list"):
                for version in versions:
                    try:
                        result = self.client.http.call(
                            endpoint=endpoint, api=api, method=method, version=version
                        )
                    except Exception:  # noqa: BLE001 - unknown method / params / version
                        continue
                    finally:
                        time.sleep(0.15)
                    ok += 1
                    done = True
                    _LOGGER.info(
                        "SRM explore OK %s.%s v%s: %s",
                        api,
                        method,
                        version,
                        json.dumps(redact(result), default=str)[:900],
                    )
                    break
                if done:
                    break
        _LOGGER.info("SRM explore finished: %d answered out of %d APIs", ok, len(wanted))
        if name_filter and "traffic" in name_filter.lower():
            self._explore_traffic_probes()

    def _explore_traffic_probes(self) -> None:
        """Try per-device traffic calls with parameters (read only, results logged)."""
        probes = [
            ("SYNO.Core.NGFW.Traffic", {"mode": mode, "interval": "live"})
            for mode in ("net", "net_l7", "dev", "device", "net_dev", "mac")
        ] + [
            ("SYNO.Core.NGFW.Traffic.Device", {"interval": "live"}),
            ("SYNO.Core.NGFW.Traffic.Device", {"mode": "net", "interval": "live"}),
            ("SYNO.Core.NGFW.Traffic.Device", {"mode": "dev", "interval": "live"}),
            ("SYNO.Core.Network.NSM.Device", {"conntype": "ethernet"}),
        ]
        for api, params in probes:
            if api not in (self._available_apis or ()):
                continue
            try:
                result = self.client.http.call(
                    endpoint=self._endpoint(api),
                    api=api,
                    method="get",
                    version=1,
                    params=params,
                )
            except Exception as err:  # noqa: BLE001 - probing unknown parameters
                _LOGGER.info("SRM probe %s %s: %s", api, params, safe_error(err))
            else:
                _LOGGER.info(
                    "SRM probe OK %s %s: %s",
                    api,
                    params,
                    json.dumps(redact(result), default=str)[:1500],
                )
            time.sleep(0.15)
        self._explore_traffic_by_client()

    def _explore_traffic_by_client(self) -> None:
        """Log the live per-device traffic of each client, by name (read only)."""
        names = {
            str(c.get("mac")): f"{c.get('name')} [{c.get('group')}]"
            for c in (getattr(self, "data", None) or {}).get("client_list") or []
        }
        for attempt in range(3):
            try:
                rows = self.client.http.call(
                    endpoint=self._endpoint("SYNO.Core.NGFW.Traffic"),
                    api="SYNO.Core.NGFW.Traffic",
                    method="get",
                    version=1,
                    params={"mode": "net_l7", "interval": "live"},
                )
            except Exception as err:  # noqa: BLE001
                _LOGGER.info("SRM live traffic: %s", safe_error(err))
                return
            summary = {}
            for row in rows or []:
                if not isinstance(row, dict):
                    continue
                mac = str(row.get("deviceID")).lower()
                label = names.get(mac) or f"other ...{mac[-5:]}"
                times = [rec.get("time") for rec in (row.get("recs") or [])]
                summary[label] = [row.get("download"), row.get("upload"), times[-2:]]
            _LOGGER.info(
                "SRM live traffic #%d (%d rows): %s", attempt, len(rows or []), summary
            )
            time.sleep(3)

    def _call_endpoint(
        self, key: str, api: str, call: Any, warn: bool = True
    ) -> tuple[str, Any, bool]:
        """Call one endpoint; return (key, result, ok). Never raises."""
        try:
            if getattr(call, "raw", False):
                result = call(self.client, endpoint=self._endpoint(api))
            else:
                result = call(self.client)
            if key == "traffic_live" and result == []:
                # The router only fills its live traffic list while it is being asked
                # for it: the first call wakes it up and comes back empty.
                time.sleep(2)
                result = call(self.client)
        except SynologyException as err:
            if warn:
                self._warn_once(
                    key, "SRM call %s (%s) failed: %s", key, api, safe_error(err)
                )
            return key, self._cache.get(key), False
        except Exception as err:  # noqa: BLE001 - unknown payload/lib errors
            if warn:
                self._warn_once(
                    key, "SRM call %s (%s) crashed: %s", key, api, safe_error(err)
                )
            return key, self._cache.get(key), False
        return key, result, True

    def _verify_answer(self, key: str, api: str, result: Any) -> Any:
        """Make sure an answer holds the key it must; else probe other ways to ask.

        Some routers answer a call with another API's payload. Ask again alone, then
        with each version the router lists, keep the one that works and report what
        was tried once (in the log and in diagnostics).
        """
        expect = EXPECTED_KEYS.get(key)
        if expect is None:
            return result
        known = self._versions.get(key)
        if known is None and isinstance(result, dict) and expect in result:
            return result
        if known is None and key in self.probes:
            return result  # already probed, nothing worked: do not repeat every poll
        info = self._api_info.get(api) if isinstance(self._api_info, dict) else None
        newest = int(info.get("maxVersion") or 1) if isinstance(info, dict) else 1
        tried: dict[str, Any] = {}
        for version in [known] if known else [1, *range(2, newest + 1)]:
            try:
                answer = self.client.http.call(
                    endpoint=self._endpoint(api), api=api, method="get", version=version
                )
            except Exception as err:  # noqa: BLE001
                tried[f"v{version}"] = f"error: {safe_error(err)}"
                continue
            tried[f"v{version}"] = sorted(answer) if isinstance(answer, dict) else type(answer).__name__
            if isinstance(answer, dict) and expect in answer:
                if known is None:
                    self._versions[key] = version
                    self.probes[key] = {"version": version, "newest": newest, "tried": tried}
                    _LOGGER.info(
                        "SRM %s (%s): the first answer had no %r; version %d, asked alone, works",
                        key, api, expect, version,
                    )
                return answer
        if known is None:
            self.probes[key] = {"version": None, "newest": newest, "tried": tried}
            _LOGGER.info("SRM %s (%s) never answered with %r: %s", key, api, expect, tried)
        return result

    def _fetch(self) -> dict[str, Any]:
        """Call every endpoint that is due and the router offers (blocking).

        The router is slow (about half a second per call), so the due calls run on a
        few threads. The first call is made alone: it logs in, and the session id is
        then shared by the other calls.
        """
        started = time.monotonic()
        if not self._apis_loaded:
            self._load_available_apis()
        results: dict[str, Any] = {}
        due: list[tuple[str, str, Any]] = []
        safe_access = self.config_entry.options.get(CONF_SAFE_ACCESS, True)
        for key, (api, call, every) in ENDPOINTS.items():
            if key.startswith("safe_") and not safe_access:
                results[key] = None
            elif self._available_apis is not None and api not in self._available_apis:
                _LOGGER.debug("SRM API %s not offered by this router, skipping", api)
                results[key] = None
            elif self._poll % every and key in self._cache:
                results[key] = self._cache[key]
            else:
                due.append((key, api, call))

        outcomes: list[tuple[str, Any, bool]] = []
        if due:
            outcomes.append(self._call_endpoint(*due[0], warn=False))
            rest = due[1:]
            if rest:
                with ThreadPoolExecutor(max_workers=PARALLEL_CALLS) as pool:
                    outcomes.extend(
                        pool.map(lambda item: self._call_endpoint(*item, warn=False), rest)
                    )
            # A call that fails while others run (the router can answer a busy request
            # with an incomplete payload) is retried once, alone, before it is reported.
            by_key = {item[0]: item for item in due}
            outcomes = [
                o if o[2] else self._call_endpoint(*by_key[o[0]]) for o in outcomes
            ]
        apis = {k: a for k, a, _ in due}
        outcomes = [
            (k, self._verify_answer(k, apis[k], r) if ok else r, ok) for k, r, ok in outcomes
        ]
        failures = 0
        for key, result, ok in outcomes:
            results[key] = result
            if ok:
                self._cache[key] = result
            else:
                failures += 1
        if outcomes and failures == len(outcomes):
            raise UpdateFailed("All SRM calls failed")
        self._poll += 1
        normalized = normalize_clients(
            results.get("clients"), results.get("wifi_devices"), results.get("traffic_live")
        )
        results["client_list"], results["offline_list"] = normalized or (None, None)
        self._name_network_profiles(results)
        self._annotate_safe_profiles(results)
        _LOGGER.debug(
            "SRM update: %d calls in %.1f s (%d failed)",
            len(outcomes),
            time.monotonic() - started,
            failures,
        )
        return results

    @staticmethod
    def _name_network_profiles(results: dict[str, Any]) -> None:
        """Give the Safe Access profile of a network ("$lbr0$") the network's name."""
        payload = results.get("safe_profiles")
        profiles = payload.get("profiles") if isinstance(payload, dict) else None
        if not isinstance(profiles, list):
            return
        lans = (results.get("local_networks") or {}).get("lans")
        groups = (results.get("safe_interfaces") or {}).get("config_groups")
        lan_names = {
            lan.get("id"): lan.get("name") for lan in lans or [] if isinstance(lan, dict) and lan.get("name")
        }
        interfaces = {
            g.get("config_group_id"): g.get("interfaces") or []
            for g in groups or []
            if isinstance(g, dict)
        }
        renamed: list[Any] = []
        for profile in profiles:
            name = profile.get("name") if isinstance(profile, dict) else None
            if isinstance(name, str) and len(name) > 2 and name[0] == name[-1] == "$":
                found = next(
                    (lan_names[i] for i in interfaces.get(profile.get("profile_id"), []) if i in lan_names),
                    None,
                )
                profile = {**profile, "name": found or name.strip("$")}
            renamed.append(profile)
        results["safe_profiles"] = {**payload, "profiles": renamed}

    @staticmethod
    def _annotate_safe_profiles(results: dict[str, Any]) -> None:
        """Add the Safe Access profile of each client (from the group -> devices map)."""
        groups = (results.get("safe_devices") or {}).get("config_groups")
        profiles = (results.get("safe_profiles") or {}).get("profiles")
        if not isinstance(groups, list) or not isinstance(profiles, list):
            return
        names = {p.get("profile_id"): p.get("name") for p in profiles if isinstance(p, dict)}
        by_mac: dict[str, str] = {}  # a device belongs to a single profile
        for group in groups:
            name = names.get(group.get("config_group_id")) if isinstance(group, dict) else None
            for mac in (group.get("devices") or []) if name else []:
                by_mac[str(mac).lower()] = str(name)
        for key in ("client_list", "offline_list"):
            for client in results.get(key) or []:
                profile = by_mac.get(client.get("mac", ""))
                if profile:
                    client["safe_profile"] = profile

    def _track_last_seen(self, data: dict[str, Any]) -> None:
        """Remember when each client was last online; fill it in for offline ones."""
        online = data.get("client_list")
        offline = data.get("offline_list")
        if not isinstance(online, list):
            return
        now = dt_util.utcnow().isoformat(timespec="seconds")
        online_now = {c["mac"] for c in online if c.get("mac")}
        for mac in online_now:
            self._seen_now[mac] = now
        changed = False
        for mac in self._online_prev - online_now:
            self._last_seen[mac] = self._seen_now.get(mac, now)
            changed = True
        self._online_prev = online_now
        if changed:
            self._store.async_delay_save(lambda: self._last_seen, 30)
        for client in offline or []:
            seen = self._last_seen.get(client.get("mac", ""))
            if seen:
                client["last_seen"] = seen

    async def _async_update_data(self) -> dict[str, Any]:
        """Update data."""
        data = await self.hass.async_add_executor_job(self._fetch)
        self._track_last_seen(data)
        return data
