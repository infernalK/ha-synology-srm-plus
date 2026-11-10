"""Firewall and DHCP sensors: the rules, who holds an address, how full each pool is."""

from __future__ import annotations

import ipaddress
from typing import Any

from homeassistant.components.sensor import SensorStateClass
from homeassistant.const import PERCENTAGE, EntityCategory

from .changes import default_policy, firewall_rules, rules_hash
from .helpers import SrmSensorDescription

# SRM's usual interface names, as named in its own screens.
NETWORK_NAMES = {"lbr0": "LAN", "gbr0": "guest network"}


def _unwrap(payload: Any, key: str) -> Any:
    """Return payload[key] when SRM nested the answer under a ``key`` field, else the payload."""
    if isinstance(payload, dict) and key in payload and len(payload) == 1:
        return payload[key]
    return payload


def _ipv4_list(payload: Any, outer: str) -> list[dict[str, Any]] | None:
    """The ``ipv4`` rows of an answer shaped ``{outer: {"ipv4": [...]}}``, or None."""
    block = payload.get(outer) if isinstance(payload, dict) else None
    rows = block.get("ipv4") if isinstance(block, dict) else None
    if not isinstance(rows, list):
        return None
    return [r for r in rows if isinstance(r, dict)]


def _servers(d: dict[str, Any]) -> list[dict[str, Any]]:
    """DHCP servers with IPv4 enabled and a valid pool: ifname, begin, end."""
    payload = _unwrap(d.get("dhcp_servers"), "data")
    out = []
    for server in payload if isinstance(payload, list) else []:
        ipv4 = server.get("ipv4") if isinstance(server, dict) else None
        if not isinstance(ipv4, dict) or not ipv4.get("enable") or not server.get("ifname"):
            continue
        try:
            begin = ipaddress.IPv4Address(ipv4["begin"])
            end = ipaddress.IPv4Address(ipv4["end"])
        except (KeyError, ValueError):
            continue
        if end >= begin:
            out.append({"ifname": str(server["ifname"]), "begin": begin, "end": end})
    return out


def _online(d: dict[str, Any]) -> set[str]:
    return {c["mac"] for c in d.get("client_list") or [] if c.get("mac")}


def _in_pool(ip: Any, server: dict[str, Any]) -> bool:
    try:
        return server["begin"] <= ipaddress.IPv4Address(ip) <= server["end"]
    except ValueError:
        return False


def _leases(d: dict[str, Any]) -> list[dict[str, Any]] | None:
    rows = _ipv4_list(d.get("dhcp_clients"), "clientList")
    if rows is None:
        return None
    reserved = {r.get("clid", "").lower() for r in _reservations(d) or []}
    online = _online(d)
    out = []
    for row in rows:
        mac = str(row.get("clid", "")).lower()
        out.append(
            {
                "name": row.get("hostname") or mac,
                "ip": row.get("ip"),
                "mac": mac,
                "online": mac in online,
                "reserved": mac in reserved,
                "expires": row.get("expire"),
            }
        )
    out.sort(key=lambda r: (not r["online"], str(r["name"]).lower()))
    return out


def _reservations(d: dict[str, Any]) -> list[dict[str, Any]] | None:
    return _ipv4_list(d.get("dhcp_reservations"), "reservationList")


def _reservation_rows(d: dict[str, Any]) -> list[dict[str, Any]]:
    servers = _servers(d)
    online = _online(d)
    rows = []
    for row in _reservations(d) or []:
        mac = str(row.get("clid", "")).lower()
        rows.append(
            {
                "name": row.get("hostname") or mac,
                "ip": row.get("ip"),
                "mac": mac,
                "online": mac in online,
                "in_pool": any(_in_pool(row.get("ip"), s) for s in servers),
            }
        )
    rows.sort(key=lambda r: (not r["online"], str(r["name"]).lower()))
    return rows


def _pool_usage(d: dict[str, Any], server: dict[str, Any]) -> float | None:
    """Share of a pool's addresses that are leased or reserved."""
    leases = _leases(d)
    if leases is None:
        return None
    size = int(server["end"]) - int(server["begin"]) + 1
    used = {r["ip"] for r in leases if _in_pool(r["ip"], server)}
    used |= {r["ip"] for r in _reservation_rows(d) if _in_pool(r["ip"], server)}
    return round(100 * len(used) / size, 1)


def _rule_rows(rules: list[dict[str, Any]]) -> list[dict[str, Any]]:
    def where(rule: dict[str, Any], side: str) -> str:
        kind, value = rule.get(f"{side}_ip_type"), rule.get(f"{side}_ip_value")
        return str(value) if value else str(kind or "all")

    def ports(rule: dict[str, Any], side: str) -> str:
        value = rule.get(f"{side}_port_value")
        return str(value) if value else str(rule.get(f"{side}_port_type") or "all")

    return [
        {
            "name": r.get("name"),
            "enabled": r.get("enabled"),
            "action": r.get("action"),
            "ip_version": r.get("ip_version"),
            "protocol": r.get("protocol"),
            "chain": r.get("chain"),
            "in_interfaces": r.get("in_interface_value"),
            "out_interfaces": r.get("out_interface_value"),
            "source": where(r, "src"),
            "destination": where(r, "dst"),
            "source_ports": ports(r, "src"),
            "destination_ports": ports(r, "dst"),
        }
        for r in rules
    ]


def _lan_descriptions(data: dict[str, Any]) -> list[SrmSensorDescription]:
    """Firewall rules, DHCP leases and reservations, and one pool-usage sensor per network."""
    out: list[SrmSensorDescription] = []
    if firewall_rules(data) is not None:
        out.append(
            SrmSensorDescription(
                key="firewall_rules",
                translation_key="firewall_rules",
                state_class=SensorStateClass.MEASUREMENT,
                entity_category=EntityCategory.DIAGNOSTIC,
                # The rule table lists addresses and names: enable it when you want it.
                entity_registry_enabled_default=False,
                value_fn=lambda d: len(firewall_rules(d) or []),
                attrs_fn=lambda d: {
                    "config_hash": rules_hash(firewall_rules(d) or []),
                    "default_policy": default_policy(d),
                    "rules": _rule_rows(firewall_rules(d) or []),
                },
            )
        )
    if _leases(data) is not None:
        out.append(
            SrmSensorDescription(
                key="dhcp_leases",
                translation_key="dhcp_leases",
                state_class=SensorStateClass.MEASUREMENT,
                entity_registry_enabled_default=False,
                value_fn=lambda d: len(_leases(d) or []),
                attrs_fn=lambda d: {"leases": _leases(d)},
            )
        )
        for server in _servers(data):
            ifname = server["ifname"]
            out.append(
                SrmSensorDescription(
                    key=f"dhcp_pool_{ifname}",
                    translation_key="dhcp_pool",
                    placeholders={"network": NETWORK_NAMES.get(ifname, ifname)},
                    native_unit_of_measurement=PERCENTAGE,
                    suggested_display_precision=1,
                    state_class=SensorStateClass.MEASUREMENT,
                    value_fn=lambda d, i=ifname: next(
                        (_pool_usage(d, s) for s in _servers(d) if s["ifname"] == i), None
                    ),
                    attrs_fn=lambda d, s=server: {
                        "begin": str(s["begin"]),
                        "end": str(s["end"]),
                        "size": int(s["end"]) - int(s["begin"]) + 1,
                    },
                )
            )
    if _reservations(data) is not None:
        out.append(
            SrmSensorDescription(
                key="dhcp_reservations",
                translation_key="dhcp_reservations",
                state_class=SensorStateClass.MEASUREMENT,
                entity_category=EntityCategory.DIAGNOSTIC,
                entity_registry_enabled_default=False,
                value_fn=lambda d: len(_reservations(d) or []),
                attrs_fn=lambda d: {"reservations": _reservation_rows(d)},
            )
        )
    return out
