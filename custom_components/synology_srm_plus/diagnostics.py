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
from .sensor import _dig, _external, _find, _nodes, _volumes, port_label

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


def _port_line(node: dict[str, Any]) -> str:
    ports = []
    for port in node.get("eth_port_info") or []:
        if isinstance(port, dict) and port.get("port"):
            speed = port.get("link_speed") if port.get("has_link") else None
            ports.append(f"{port_label(port['port'])} {speed if speed else '-'}")
    return ", ".join(ports) or "no port data"


def build_report(
    data: dict[str, Any],
    probes: dict[str, Any],
    counts: dict[str, int],
    unknown: dict[str, int],
    ha_version: str,
) -> str:
    """Short text with what is needed to debug the cards and sensors (no names, addresses or MACs)."""
    lines = [f"Synology SRM Plus {VERSION} - Home Assistant {ha_version}"]
    info = {n.get("node_id"): n for n in _nodes(data, "system_info")}
    nodes = _nodes(data, "eth_ports") or _nodes(data, "system_info")
    lines.append(f"Routers: {len(nodes)}")
    for node in nodes:
        nid = node.get("node_id")
        sys_node = info.get(nid, {})
        lines.append(
            f"  node {nid}: {sys_node.get('model', '?')} {sys_node.get('firmware_ver', '')}"
            f"{' (repeater)' if sys_node.get('is_re') else ''} | ports: {_port_line(node)}"
        )
    records = data.get("external_ip")
    shape = type(records).__name__
    if isinstance(records, dict):
        records = records.get("records")
    via_service = _external({"external_ip": records}, "ip") is not None
    via_wan = bool(_dig(data.get("connection_status"), "ipv4", "ip"))
    lines.append(
        "External IPv4: "
        + ("from the external-IP service" if via_service else "from the WAN connection" if via_wan else "UNKNOWN")
        + f" | service answer: {shape}, {len(records) if isinstance(records, list) else 'no'} records"
    )
    trends = _dig(data.get("tps_trends"), "trends")
    if isinstance(trends, list):
        lines.append(f"Threat statistics: {len(trends)} periods")
    else:
        got = sorted(data["tps_trends"]) if isinstance(data.get("tps_trends"), dict) else data.get("tps_trends")
        lines.append(f"Threat statistics: NO 'trends' in the answer (keys: {got})")
    for key, probe in probes.items():
        lines.append(f"  probe {key}: works with v{probe['version']}" if probe.get("version") else f"  probe {key}: nothing worked, tried {probe.get('tried')}")
    vols = [f"{v.get('id')} {round(100 * v['used'] / v['total'], 1)}%" for v in _volumes(data) if v.get("total")]
    lines.append(f"USB storage: {', '.join(vols) or 'none'}")
    profiles = _dig(data.get("safe_profiles"), "profiles")
    if isinstance(profiles, list):
        raw = [p for p in profiles if isinstance(p, dict) and str(p.get("name", "")).startswith("$")]
        lines.append(f"Safe Access: {len(profiles)} profiles, {len(raw)} still named like $lbrN$")
    clients = data.get("clients") if isinstance(data.get("clients"), list) else []
    wired = [c for c in clients if isinstance(c, dict) and c.get("connection") == "ethernet" and c.get("is_online")]
    lines.append(
        f"Wired clients online: {len(wired)}, with a link rate: {sum(1 for c in wired if c.get('current_rate'))}"
    )
    lines.append("Entities per key: " + ", ".join(f"{k}={v}" for k, v in sorted(counts.items()) if k in WATCHED_KEYS or v > 3))
    lines.append("Unknown/unavailable: " + (", ".join(f"{k}={v}" for k, v in sorted(unknown.items())) or "none"))
    return chr(10).join(lines)


def _entity_summary(
    hass: HomeAssistant, entry: SrmConfigEntry
) -> tuple[Counter[str], dict[str, int], dict[str, Any]]:
    """Count the entities per key, those without a value, and the watched ones."""
    registry = er.async_get(hass)
    counts: Counter[str] = Counter()
    unknown: Counter[str] = Counter()
    watched: dict[str, Any] = {}
    for ent in er.async_entries_for_config_entry(registry, entry.entry_id):
        key = ent.translation_key or ent.domain
        counts[key] += 1
        state = hass.states.get(ent.entity_id)
        if state is None or state.state in ("unknown", "unavailable"):
            unknown[key] += 1
        if key in WATCHED_KEYS and state is not None:
            value = state.state
            if key in ADDRESS_KEYS and value not in ("unknown", "unavailable"):
                value = "set"
            # Entity ids embed the router's address: key by type and index instead.
            watched[f"{key}#{counts[key]}"] = {
                "state": value,
                **{a: state.attributes[a] for a in WATCHED_ATTRS if a in state.attributes},
            }
    return counts, dict(unknown), watched


async def async_build_report(hass: HomeAssistant, entry: SrmConfigEntry) -> str:
    """Return the short text report of one entry."""
    coordinator = entry.runtime_data
    counts, unknown, _ = _entity_summary(hass, entry)
    return build_report(coordinator.data or {}, coordinator.probes, counts, unknown, hass.config.version if hasattr(hass.config, "version") else "?")


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: SrmConfigEntry
) -> dict[str, Any]:
    """Return diagnostics: config, offered APIs and the (redacted) payloads."""
    coordinator = entry.runtime_data
    apis = coordinator.available_apis
    counts, _unknown, watched = _entity_summary(hass, entry)
    return {
        "version": VERSION,
        "report": (await async_build_report(hass, entry)).splitlines(),
        "probes": coordinator.probes,
        "entities_by_key": dict(sorted(counts.items())),
        "watched_entities": watched,
        "config": redact_data(dict(entry.data)),
        "api_count": len(apis) if apis is not None else None,
        "apis": sorted(apis) if apis is not None else None,
        "data": redact_data(coordinator.data),
    }
