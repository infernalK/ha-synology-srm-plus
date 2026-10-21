"""Diagnostics for Synology SRM Plus."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant

from . import SrmConfigEntry

TO_REDACT = {
    CONF_HOST,
    CONF_PASSWORD,
    CONF_USERNAME,
    "bssid",
    "dns",
    "gateway",
    "hostname",
    "ip",
    "ipv6",
    "mac",
    "mac_address",
    "name",
    "ssid",
    "ssids",
    "ddns_hostnames",
    "sn",
    "serial_number",
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: SrmConfigEntry
) -> dict[str, Any]:
    """Return diagnostics: config, offered APIs and the (redacted) payloads."""
    coordinator = entry.runtime_data
    apis = coordinator.available_apis
    return {
        "config": async_redact_data(dict(entry.data), TO_REDACT),
        "api_count": len(apis) if apis is not None else None,
        "apis": sorted(apis) if apis is not None else None,
        "data": async_redact_data(coordinator.data, TO_REDACT),
    }
