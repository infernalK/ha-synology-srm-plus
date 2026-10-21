"""Data coordinator for Synology SRM Plus."""

from __future__ import annotations

from collections.abc import Callable
import json
import logging
import re
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

# key -> call on the synology_srm client
ENDPOINTS: dict[str, Callable[[synology_srm.Client], Any]] = {
    "system_utilization": lambda c: c.core.get_system_utilization(),
    "traffic_live": lambda c: c.core.get_ngfw_traffic("live"),
    "external_ip": lambda c: c.core.list_ddns_extip(),
    "system_info": lambda c: c.mesh.get_system_info(),
}

# Candidate APIs found in the router's API list, probed once to see their payloads.
EXTRA_PROBES: tuple[tuple[str, str], ...] = (
    ("SYNO.Core.Network.Router.ConnectionStatus", "get"),
    ("SYNO.Core.Network.Router.Gateway.List", "get"),
    ("SYNO.Core.Network.Interface", "get"),
    ("SYNO.Core.Network.Ethernet", "list"),
    ("SYNO.Wifi.Radio.Status", "get"),
    ("SYNO.Wifi.Device", "get"),
    ("SYNO.Mesh.System.Utilization", "get"),
    ("SYNO.Mesh.Network.Info", "get"),
    ("SYNO.Core.Network.Router.Topology", "get"),
)

# Only used to log which APIs the router offers (to find WAN / Wi-Fi ones).
_API_NAME_FILTER = re.compile(r"mesh|wan|wifi|wireless|internet|network|system\.info", re.I)


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
        self._apis_logged = False

    def _log_available_apis(self) -> None:
        """Log (once) the API names offered by the router."""
        self._apis_logged = True
        try:
            apis = self.client.base.query_info()
        except Exception as err:  # noqa: BLE001
            _LOGGER.warning("SRM query_info failed: %r", err)
            return
        if not isinstance(apis, dict):
            _LOGGER.info("SRM query_info raw: %s", json.dumps(apis, default=str)[:3000])
            return
        names = sorted(apis)
        _LOGGER.info("SRM exposes %d APIs", len(names))
        _LOGGER.info(
            "SRM APIs of interest: %s",
            ", ".join(n for n in names if _API_NAME_FILTER.search(n)),
        )

    def _log_extra_apis(self) -> None:
        """Probe candidate WAN / Wi-Fi APIs once and log their raw payloads."""
        for api, method in EXTRA_PROBES:
            try:
                result = self.client.http.call(
                    endpoint="entry.cgi", api=api, method=method, version=1
                )
            except Exception as err:  # noqa: BLE001
                _LOGGER.info("SRM probe %s.%s failed: %r", api, method, err)
            else:
                _LOGGER.info(
                    "SRM probe %s.%s raw: %s",
                    api,
                    method,
                    json.dumps(result, default=str)[:4000],
                )

    def _fetch(self) -> dict[str, Any]:
        """Call every endpoint, isolating failures (blocking)."""
        if not self._apis_logged:
            self._log_available_apis()
            self._log_extra_apis()
        results: dict[str, Any] = {}
        failures = 0
        for key, call in ENDPOINTS.items():
            try:
                results[key] = call(self.client)
            except SynologyException as err:
                failures += 1
                results[key] = {"error": f"{type(err).__name__}: {err}"}
                _LOGGER.warning("SRM call %s failed: %s", key, err)
            except Exception as err:  # noqa: BLE001 - unknown payload/lib errors
                failures += 1
                results[key] = {"error": f"{type(err).__name__}: {err}"}
                _LOGGER.warning("SRM call %s crashed: %r", key, err)
        if failures == len(ENDPOINTS):
            raise UpdateFailed("All SRM calls failed")
        return results

    async def _async_update_data(self) -> dict[str, Any]:
        """Update data."""
        return await self.hass.async_add_executor_job(self._fetch)
