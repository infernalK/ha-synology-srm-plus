"""Helpers shared by the Synology SRM Plus entity modules: reading the SRM payloads."""

from __future__ import annotations

import ipaddress
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    UnitOfDataRate,
)


def _dig(data: Any, *path: str | int) -> Any:
    """Return a nested value, or None if anything on the way is missing."""
    for part in path:
        try:
            data = data[part]
        except (KeyError, IndexError, TypeError):
            return None
    return data


def _num(value: Any, scale: float = 1) -> float | int | None:
    """Return a numeric value scaled, or None."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return round(value * scale, 2) if scale != 1 else value


def _address(value: Any, version: int) -> str | None:
    """Return value if it is a usable address of this IP version, else None.

    Rejects what is not an address (a MAC), "0:0:0:0:0:0:0:0", loopback and link-local
    addresses, and a private or unique-local IPv6 as an external address.
    """
    try:
        addr = ipaddress.ip_address(str(value).strip())
    except ValueError:
        return None
    if (
        addr.version != version
        or addr.is_unspecified
        or addr.is_loopback
        or addr.is_link_local
        or addr.is_multicast
    ):
        return None
    if version == 6 and not addr.is_global:
        return None
    return str(value).strip()


def _external(d: dict[str, Any], field: str) -> Any:
    """External address: the WAN entry, else any entry that has one, else the WAN connection's."""
    version = 6 if field == "ipv6" else 4
    items = d.get("external_ip")
    if isinstance(
        items, dict
    ):  # some routers wrap the list: {"next_update_time": ..., "records": [...]}
        items = items.get("records")
    wan = _find(items, type="WAN") or {}
    found = _address(wan.get(field), version)
    if found is None and isinstance(items, list):
        found = next(
            (
                a
                for i in items
                if isinstance(i, dict) and (a := _address(i.get(field), version))
            ),
            None,
        )
    if found is None and version == 4:
        # The external-IP service sometimes answers nothing: use the WAN connection's address.
        found = _address(_dig(d.get("connection_status"), "ipv4", "ip"), 4)
    return found


def _find(items: Any, **match: Any) -> dict[str, Any] | None:
    """Find the first dict in a list whose items match."""
    if not isinstance(items, list):
        return None
    for item in items:
        if isinstance(item, dict) and all(item.get(k) == v for k, v in match.items()):
            return item
    return None


@dataclass(frozen=True, kw_only=True)
class SrmSensorDescription(SensorEntityDescription):
    """Sensor description with a value function over the coordinator data."""

    value_fn: Callable[[dict[str, Any]], Any]
    placeholders: dict[str, str] | None = None
    attrs_fn: Callable[[dict[str, Any]], dict[str, Any] | None] | None = None


def _util(*path: str | int) -> Callable[[dict[str, Any]], Any]:
    return lambda d: _dig(d.get("system_utilization"), *path)


def _util_num(*path: str | int, scale: float = 1) -> Callable[[dict[str, Any]], Any]:
    return lambda d: _num(_dig(d.get("system_utilization"), *path), scale)


def _cpu_total(d: dict[str, Any]) -> float | None:
    cpu = _dig(d.get("system_utilization"), "cpu")
    if not isinstance(cpu, dict):
        return None
    parts = [cpu.get(k) for k in ("user_load", "system_load", "other_load")]
    if not all(isinstance(p, (int, float)) for p in parts):
        return None
    return sum(parts)


def _list_item_value(
    list_path: tuple[str | int, ...], key: str, value: str, field: str
) -> Callable[[dict[str, Any]], Any]:
    return lambda d: _num(
        (
            _find(_dig(d.get("system_utilization"), *list_path), **{key: value}) or {}
        ).get(field)
    )


def _clients(d: dict[str, Any], group: str | None = None) -> list[dict[str, Any]]:
    """Return the normalised client list, optionally for one group."""
    clients = d.get("client_list")
    if not isinstance(clients, list):
        return []
    return [c for c in clients if group is None or c.get("group") == group]


def _network_clients(d: dict[str, Any], network: str) -> list[dict[str, Any]]:
    """Clients attached to one Wi-Fi network (SRM calls it a profile, for example "IOT")."""
    return [c for c in _clients(d) if c.get("wifi_profile") == network]


def _wifi_network_names(data: dict[str, Any]) -> list[str]:
    """Names of the Wi-Fi networks: those the router lists and those clients are on."""
    names = {
        str(n["name"])
        for n in _dig(data.get("wifi_networks"), "networks") or []
        if isinstance(n, dict) and n.get("name")
    }
    names |= {str(c["wifi_profile"]) for c in _clients(data) if c.get("wifi_profile")}
    return sorted(names)


def _nodes(d: dict[str, Any], key: str) -> list[dict[str, Any]]:
    nodes = _dig(d.get(key), "nodes")
    return [n for n in nodes if isinstance(n, dict)] if isinstance(nodes, list) else []


def _node(d: dict[str, Any], key: str, node_id: Any) -> dict[str, Any]:
    return _find(_nodes(d, key), node_id=node_id) or {}


def _rate_kwargs() -> dict[str, Any]:
    return {
        "device_class": SensorDeviceClass.DATA_RATE,
        "native_unit_of_measurement": UnitOfDataRate.BYTES_PER_SECOND,
        "suggested_unit_of_measurement": UnitOfDataRate.MEGABITS_PER_SECOND,
        "suggested_display_precision": 1,
        "state_class": SensorStateClass.MEASUREMENT,
    }


def port_label(port: str) -> str:
    """Return a readable name for an Ethernet port id (wp1 -> WAN, lp2 -> LAN 2)."""
    if port.startswith("wp"):
        return "WAN"
    digits = "".join(ch for ch in port if ch.isdigit())
    return f"LAN {digits}" if port.startswith("lp") and digits else port


def _radio_net(d: dict[str, Any], node_id: Any, band: str) -> dict[str, Any]:
    return _find(_node(d, "mesh_network", node_id).get("wifi_radios"), band=band) or {}


def _port(d: dict[str, Any], node_id: Any, port: str) -> dict[str, Any] | None:
    return _find(_node(d, "eth_ports", node_id).get("eth_port_info"), port=port)


def _port_speed(d: dict[str, Any], node_id: Any, port: str) -> float | int | None:
    info = _port(d, node_id, port)
    if info is None:
        return None
    return _num(info.get("link_speed")) if info.get("has_link") else 0


def _volumes(d: dict[str, Any]) -> list[dict[str, Any]]:
    vols = _dig(d.get("usb_volumes"), "volumes")
    return [v for v in vols if isinstance(v, dict)] if isinstance(vols, list) else []


def _volume(d: dict[str, Any], vid: str) -> dict[str, Any]:
    return _find(_volumes(d), id=vid) or {}
