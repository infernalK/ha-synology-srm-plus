"""Data coordinator for Synology SRM Plus."""

from __future__ import annotations

from collections.abc import Callable
import logging
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
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)


def _raw(api: str, method: str = "get") -> Callable[[synology_srm.Client], Any]:
    """Call an SRM API the library has no wrapper for."""
    return lambda c: c.http.call(endpoint="entry.cgi", api=api, method=method, version=1)


# key -> (API name, call on the synology_srm client)
# The API name is checked against the router's API list: an API the router does
# not offer is skipped silently (SRM models and firmwares differ).
ENDPOINTS: dict[str, tuple[str, Callable[[synology_srm.Client], Any]]] = {
    "system_utilization": (
        "SYNO.Core.System.Utilization",
        lambda c: c.core.get_system_utilization(),
    ),
    "traffic_live": (
        "SYNO.Core.NGFW.Traffic",
        lambda c: c.core.get_ngfw_traffic("live"),
    ),
    "external_ip": ("SYNO.Core.DDNS.ExtIP", lambda c: c.core.list_ddns_extip()),
    "system_info": ("SYNO.Mesh.System.Info", lambda c: c.mesh.get_system_info()),
    "connection_status": (
        "SYNO.Core.Network.Router.ConnectionStatus",
        _raw("SYNO.Core.Network.Router.ConnectionStatus"),
    ),
    "topology": (
        "SYNO.Core.Network.Router.Topology",
        _raw("SYNO.Core.Network.Router.Topology"),
    ),
    "ethernet": (
        "SYNO.Core.Network.Ethernet",
        _raw("SYNO.Core.Network.Ethernet", "list"),
    ),
    "clients": (
        "SYNO.Core.Network.NSM.Device",
        lambda c: c.core.get_network_nsm_device({"is_online": True}),
    ),
    "wifi_radio": ("SYNO.Wifi.Radio.Status", _raw("SYNO.Wifi.Radio.Status")),
    "wifi_devices": ("SYNO.Wifi.Device", _raw("SYNO.Wifi.Device")),
}


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
    return client


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
        self._apis_loaded = False

    @property
    def available_apis(self) -> set[str] | None:
        """Return the API names offered by the router, if known."""
        return self._available_apis

    def _load_available_apis(self) -> None:
        """Read (once) the API names offered by the router."""
        self._apis_loaded = True
        try:
            apis = self.client.base.query_info()
        except Exception as err:  # noqa: BLE001
            _LOGGER.warning("SRM query_info failed, assuming all APIs exist: %r", err)
            return
        if isinstance(apis, dict):
            self._available_apis = set(apis)
            _LOGGER.debug("SRM exposes %d APIs", len(apis))

    def _fetch(self) -> dict[str, Any]:
        """Call every endpoint the router offers, isolating failures (blocking)."""
        if not self._apis_loaded:
            self._load_available_apis()
        results: dict[str, Any] = {}
        failures = 0
        called = 0
        for key, (api, call) in ENDPOINTS.items():
            if self._available_apis is not None and api not in self._available_apis:
                _LOGGER.debug("SRM API %s not offered by this router, skipping", api)
                results[key] = None
                continue
            called += 1
            try:
                results[key] = call(self.client)
            except SynologyException as err:
                failures += 1
                results[key] = None
                _LOGGER.warning("SRM call %s (%s) failed: %s", key, api, err)
            except Exception as err:  # noqa: BLE001 - unknown payload/lib errors
                failures += 1
                results[key] = None
                _LOGGER.warning("SRM call %s (%s) crashed: %r", key, api, err)
        if called and failures == called:
            raise UpdateFailed("All SRM calls failed")
        return results

    async def _async_update_data(self) -> dict[str, Any]:
        """Update data."""
        return await self.hass.async_add_executor_job(self._fetch)
