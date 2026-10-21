"""Data coordinator for Synology SRM Plus."""

from __future__ import annotations

from collections.abc import Callable
import json
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

# key -> call on the synology_srm client
ENDPOINTS: dict[str, Callable[[synology_srm.Client], Any]] = {
    "system_utilization": lambda c: c.core.get_system_utilization(),
    "traffic_live": lambda c: c.core.get_ngfw_traffic("live"),
    "external_ip": lambda c: c.core.list_ddns_extip(),
    "system_info": lambda c: c.mesh.get_system_info(),
    "wan_status": lambda c: c.mesh.get_network_wanstatus(),
    "wifi_devices": lambda c: c.mesh.get_network_wifidevice(),
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

    def _fetch(self) -> dict[str, Any]:
        """Call every endpoint, isolating failures (blocking)."""
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
            else:
                # Discovery phase: log raw payloads so we can see their shape.
                _LOGGER.info(
                    "SRM %s raw: %s", key, json.dumps(results[key], default=str)[:6000]
                )
        if failures == len(ENDPOINTS):
            raise UpdateFailed("All SRM calls failed")
        return results

    async def _async_update_data(self) -> dict[str, Any]:
        """Update data."""
        return await self.hass.async_add_executor_job(self._fetch)
