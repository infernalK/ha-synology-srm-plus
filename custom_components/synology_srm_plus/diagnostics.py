"""Diagnostics for Synology SRM Plus."""

from __future__ import annotations

from collections import Counter
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from . import SrmConfigEntry
from .const import VERSION
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


# Entities whose state the cards rely on: their values and node/port attributes go in the report.
WATCHED_KEYS = {
    "external_ipv4",
    "external_ipv6",
    "port_speed",
    "storage_utilization",
    "node_status",
    "threat_events_24h",
    "threat_events_7d",
}
WATCHED_ATTRS = ("node", "port", "kind", "device", "volume", "link")
# Keys whose state is an address: report only whether it is known.
ADDRESS_KEYS = {"external_ipv4", "external_ipv6"}


def redact_data(data: Any) -> Any:
    """Mask secrets, MAC addresses, IPs and names in a payload (keys and values)."""
    return async_redact_data(redact(data), TO_REDACT)


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: SrmConfigEntry
) -> dict[str, Any]:
    """Return diagnostics: config, offered APIs and the (redacted) payloads."""
    coordinator = entry.runtime_data
    apis = coordinator.available_apis
    registry = er.async_get(hass)
    counts: Counter[str] = Counter()
    watched: dict[str, Any] = {}
    for ent in er.async_entries_for_config_entry(registry, entry.entry_id):
        key = ent.translation_key or ent.domain
        counts[key] += 1
        if key in WATCHED_KEYS and (state := hass.states.get(ent.entity_id)) is not None:
            value = state.state
            if key in ADDRESS_KEYS and value not in ("unknown", "unavailable"):
                value = "set"
            # Entity ids embed the router's address: key by type and index instead.
            watched[f"{key}#{counts[key]}"] = {
                "state": value,
                **{a: state.attributes[a] for a in WATCHED_ATTRS if a in state.attributes},
            }
    return {
        "version": VERSION,
        "probes": coordinator.probes,
        "entities_by_key": dict(sorted(counts.items())),
        "watched_entities": watched,
        "config": redact_data(dict(entry.data)),
        "api_count": len(apis) if apis is not None else None,
        "apis": sorted(apis) if apis is not None else None,
        "data": redact_data(coordinator.data),
    }
