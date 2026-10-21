"""Diagnostics for Synology SRM Plus."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant

from . import SrmConfigEntry
from .coordinator import redact

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
    "mac_addr",
    "name",
    "ssid",
    "ssids",
    "ddns_hostnames",
    "clientname",
    "from",
    "who",
    "profile",
    "safe_profile",
    "profile_ids",
    "pin",
    "password",
    "sn",
    "serial_number",
    "ip_addr",
    "ip6_addr",
    "wifi_ssid",
    "mesh_node_name",
    "addresses",
    "devices",
    "sessions",
}


def redact_data(data: Any) -> Any:
    """Mask secrets, MAC addresses, IPs and names in a payload (keys and values)."""
    return async_redact_data(redact(data), TO_REDACT)


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: SrmConfigEntry
) -> dict[str, Any]:
    """Return diagnostics: config, offered APIs and the (redacted) payloads."""
    coordinator = entry.runtime_data
    apis = coordinator.available_apis
    return {
        "config": redact_data(dict(entry.data)),
        "api_count": len(apis) if apis is not None else None,
        "apis": sorted(apis) if apis is not None else None,
        "data": redact_data(coordinator.data),
    }
