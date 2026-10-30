"""Sensors for Synology SRM Plus."""

from __future__ import annotations

import ipaddress
import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    EntityCategory,
    UnitOfDataRate,
    UnitOfInformation,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import SrmConfigEntry
from .const import DOMAIN
from .clients import GROUP_OFFLINE, GROUP_WIRED, group_label
from .coordinator import SrmCoordinator


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
    if addr.version != version or addr.is_unspecified or addr.is_loopback or addr.is_link_local or addr.is_multicast:
        return None
    if version == 6 and not addr.is_global:
        return None
    return str(value).strip()


def _external(d: dict[str, Any], field: str) -> Any:
    """External address: the WAN entry, else any entry that has one, else the WAN connection's."""
    version = 6 if field == "ipv6" else 4
    items = d.get("external_ip")
    if isinstance(items, dict):  # some routers wrap the list: {"next_update_time": ..., "records": [...]}
        items = items.get("records")
    wan = _find(items, type="WAN") or {}
    found = _address(wan.get(field), version)
    if found is None and isinstance(items, list):
        found = next((a for i in items if isinstance(i, dict) and (a := _address(i.get(field), version))), None)
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
        (_find(_dig(d.get("system_utilization"), *list_path), **{key: value}) or {}).get(
            field
        )
    )


STATIC_SENSORS: tuple[SrmSensorDescription, ...] = (
    SrmSensorDescription(
        key="cpu_usage",
        translation_key="cpu_usage",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_cpu_total,
    ),
    SrmSensorDescription(
        key="cpu_user",
        translation_key="cpu_user",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=_util_num("cpu", "user_load"),
    ),
    SrmSensorDescription(
        key="cpu_system",
        translation_key="cpu_system",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=_util_num("cpu", "system_load"),
    ),
    # SRM reports load averages multiplied by 100.
    SrmSensorDescription(
        key="load_1min",
        translation_key="load_1min",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        value_fn=_util_num("cpu", "1min_load", scale=0.01),
    ),
    SrmSensorDescription(
        key="load_5min",
        translation_key="load_5min",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        value_fn=_util_num("cpu", "5min_load", scale=0.01),
    ),
    SrmSensorDescription(
        key="load_15min",
        translation_key="load_15min",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        value_fn=_util_num("cpu", "15min_load", scale=0.01),
    ),
    SrmSensorDescription(
        key="memory_usage",
        translation_key="memory_usage",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_util_num("memory", "real_usage"),
    ),
    SrmSensorDescription(
        key="swap_usage",
        translation_key="swap_usage",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_util_num("memory", "swap_usage"),
    ),
    # Memory values are reported in KiB.
    *(
        SrmSensorDescription(
            key=f"memory_{field}",
            translation_key=f"memory_{field}",
            device_class=SensorDeviceClass.DATA_SIZE,
            native_unit_of_measurement=UnitOfInformation.KIBIBYTES,
            suggested_unit_of_measurement=UnitOfInformation.MEBIBYTES,
            suggested_display_precision=0,
            state_class=SensorStateClass.MEASUREMENT,
            entity_category=EntityCategory.DIAGNOSTIC,
            value_fn=_util_num("memory", field),
        )
        for field in ("total_real", "avail_real", "cached", "buffer", "total_swap", "avail_swap")
    ),
    SrmSensorDescription(
        key="external_ipv4",
        translation_key="external_ipv4",
        value_fn=lambda d: _external(d, "ip"),
        attrs_fn=lambda d: {
            "ddns_hostnames": [
                r["hostname"]
                for r in (_dig(d.get("ddns"), "records") or [])
                if isinstance(r, dict) and r.get("hostname")
            ]
        }
        or None,
    ),
    SrmSensorDescription(
        key="external_ipv6",
        translation_key="external_ipv6",
        value_fn=lambda d: _external(d, "ipv6"),
    ),
    SrmSensorDescription(
        key="traffic_live",
        translation_key="traffic_live",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: (
            len(d["traffic_live"]) if isinstance(d.get("traffic_live"), list) else None
        ),
    ),
)


# Data key a static sensor needs (default: system_utilization).
STATIC_REQUIRES = {
    "external_ipv4": "external_ip",
    "external_ipv6": "external_ip",
    "traffic_live": "traffic_live",
}


def _node_memory(d: dict[str, Any], node_id: Any) -> float | None:
    node = _node(d, "mesh_utilization", node_id)
    used, total = _num(node.get("mem_used")), _num(node.get("mem_total"))
    return round(used / total * 100, 1) if used is not None and total else None


def _node_utilization_descriptions(node_id: Any) -> list[SrmSensorDescription]:
    """CPU and memory of a satellite (the main router has its own, fuller sensors)."""
    ph = {"node": str(node_id)}
    return [
        SrmSensorDescription(
            key=f"node_cpu_usage_{node_id}",
            translation_key="node_cpu_usage",
            placeholders=ph,
            native_unit_of_measurement=PERCENTAGE,
            state_class=SensorStateClass.MEASUREMENT,
            value_fn=lambda d, n=node_id: _num(_node(d, "mesh_utilization", n).get("cpu_usage")),
        ),
        SrmSensorDescription(
            key=f"node_memory_usage_{node_id}",
            translation_key="node_memory_usage",
            placeholders=ph,
            native_unit_of_measurement=PERCENTAGE,
            state_class=SensorStateClass.MEASUREMENT,
            value_fn=lambda d, n=node_id: _node_memory(d, n),
        ),
    ]


def _node_descriptions(node_id: Any) -> list[SrmSensorDescription]:
    """Sensors for one router node."""
    return [
        SrmSensorDescription(
            key=f"uptime_{node_id}",
            translation_key="uptime",
            placeholders={"node": str(node_id)},
            device_class=SensorDeviceClass.DURATION,
            native_unit_of_measurement=UnitOfTime.SECONDS,
            suggested_unit_of_measurement=UnitOfTime.HOURS,
            suggested_display_precision=1,
            state_class=SensorStateClass.MEASUREMENT,
            value_fn=lambda d, n=node_id: _num(
                (_find(_dig(d.get("system_info"), "nodes"), node_id=n) or {}).get("uptime")
            ),
        ),
        SrmSensorDescription(
            key=f"firmware_{node_id}",
            translation_key="firmware",
            placeholders={"node": str(node_id)},
            entity_category=EntityCategory.DIAGNOSTIC,
            value_fn=lambda d, n=node_id: (
                _find(_dig(d.get("system_info"), "nodes"), node_id=n) or {}
            ).get("firmware_ver"),
        ),
        SrmSensorDescription(
            key=f"model_{node_id}",
            translation_key="model",
            placeholders={"node": str(node_id)},
            entity_category=EntityCategory.DIAGNOSTIC,
            value_fn=lambda d, n=node_id: (
                _find(_dig(d.get("system_info"), "nodes"), node_id=n) or {}
            ).get("model"),
        ),
    ]


def _interface_descriptions(name: str) -> list[SrmSensorDescription]:
    """Download / upload rate of one network interface (or the total)."""
    common = {
        "device_class": SensorDeviceClass.DATA_RATE,
        "native_unit_of_measurement": UnitOfDataRate.BYTES_PER_SECOND,
        "suggested_unit_of_measurement": UnitOfDataRate.KILOBYTES_PER_SECOND,
        "suggested_display_precision": 1,
        "state_class": SensorStateClass.MEASUREMENT,
        "placeholders": {"interface": name},
        # These counters do not seem to include hardware-accelerated forwarding:
        # prefer the client traffic sensors.
        "entity_registry_enabled_default": False,
    }
    return [
        SrmSensorDescription(
            key=f"net_{name}_{direction}",
            translation_key=f"net_{direction}",
            value_fn=_list_item_value(("network",), "device", name, direction),
            **common,
        )
        for direction in ("rx", "tx")
    ]


def _storage_descriptions(
    list_path: tuple[str, ...], kind: str, name: str
) -> list[SrmSensorDescription]:
    """Utilization and throughput of one disk / volume."""
    base = {"placeholders": {"kind": kind, "device": name}}
    out = [
        SrmSensorDescription(
            key=f"{kind}_{name}_utilization",
            translation_key="storage_utilization",
            native_unit_of_measurement=PERCENTAGE,
            state_class=SensorStateClass.MEASUREMENT,
            value_fn=_list_item_value(list_path, "device", name, "utilization"),
            **base,
        )
    ]
    for field, tkey in (("read_byte", "storage_read"), ("write_byte", "storage_write")):
        out.append(
            SrmSensorDescription(
                key=f"{kind}_{name}_{field}",
                translation_key=tkey,
                device_class=SensorDeviceClass.DATA_RATE,
                native_unit_of_measurement=UnitOfDataRate.BYTES_PER_SECOND,
                suggested_unit_of_measurement=UnitOfDataRate.KILOBYTES_PER_SECOND,
                suggested_display_precision=1,
                state_class=SensorStateClass.MEASUREMENT,
                entity_category=EntityCategory.DIAGNOSTIC,
                value_fn=_list_item_value(list_path, "device", name, field),
                **base,
            )
        )
    return out


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


def _sum_network_rate(d: dict[str, Any], field: str, network: str) -> float:
    return sum(
        c[field]
        for c in _network_clients(d, network)
        if isinstance(c.get(field), (int, float)) and not isinstance(c.get(field), bool)
    )


def _network_attrs(d: dict[str, Any], network: str) -> dict[str, Any]:
    clients = _network_clients(d, network)
    # No "integration" nor client list: the clients card takes sensors that carry both
    # for connection groups and would list these clients a second time.
    return {
        "network": network,
        "bands": sorted({c["band"] for c in clients if c.get("band")}),
        "ssids": sorted({c["ssid"] for c in clients if c.get("ssid")}),
        "download": _sum_network_rate(d, "download", network),
        "upload": _sum_network_rate(d, "upload", network),
        "by_band": _network_by_band(clients),
    }


def _network_by_band(clients: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Clients and rates of one Wi-Fi network, split per band (2.4G, 5G...)."""
    out: dict[str, dict[str, Any]] = {}
    for c in clients:
        band = c.get("band")
        if not band:
            continue
        item = out.setdefault(str(band), {"clients": 0, "download": 0, "upload": 0})
        item["clients"] += 1
        for field in ("download", "upload"):
            value = c.get(field)
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                item[field] += value
    return dict(sorted(out.items()))


def _sum_rate(d: dict[str, Any], field: str, group: str | None) -> float:
    return sum(
        c[field]
        for c in _clients(d, group)
        if isinstance(c.get(field), (int, float)) and not isinstance(c.get(field), bool)
    )


def _avg_signal(d: dict[str, Any], group: str) -> float | None:
    signals = [
        c["signal"] for c in _clients(d, group) if isinstance(c.get("signal"), (int, float))
    ]
    return round(sum(signals) / len(signals), 1) if signals else None


def _radio(d: dict[str, Any], band: str) -> dict[str, Any]:
    return _find(_dig(d.get("wifi_radio"), "status_list"), radio_type=band) or {}


def _group_attrs(d: dict[str, Any], group: str) -> dict[str, Any]:
    """Attributes of a connection group: who is attached, and how."""
    clients = _clients(d, group)
    attrs: dict[str, Any] = {"integration": DOMAIN, "group": group, "clients": clients}
    if group != GROUP_WIRED:
        radio = _radio(d, group)
        attrs["channel"] = radio.get("channel")
        attrs["bssid"] = radio.get("bssid")
        attrs["ssids"] = sorted({c["ssid"] for c in clients if c.get("ssid")})
        attrs["average_signal"] = _avg_signal(d, group)
    attrs["download"] = _sum_rate(d, "download", group)
    attrs["upload"] = _sum_rate(d, "upload", group)
    return {k: v for k, v in attrs.items() if v is not None}


def _wifi_descriptions(data: dict[str, Any]) -> list[SrmSensorDescription]:
    """Channel and average signal per Wi-Fi band."""
    out: list[SrmSensorDescription] = []
    bands = {
        item["radio_type"]
        for item in _dig(data.get("wifi_radio"), "status_list") or []
        if isinstance(item, dict) and item.get("radio_type")
    } | {c["group"] for c in _clients(data) if c.get("group") != GROUP_WIRED}
    for band in sorted(bands):
        if _radio(data, band):
            out.append(
                SrmSensorDescription(
                    key=f"wifi_channel_{band}",
                    translation_key="wifi_channel",
                    placeholders={"band": band},
                    entity_category=EntityCategory.DIAGNOSTIC,
                    value_fn=lambda d, b=band: _num(_radio(d, b).get("channel")),
                    attrs_fn=lambda d, b=band: {
                        "bssid": _radio(d, b).get("bssid"),
                        **{
                            k: v
                            for k, v in (
                                _find(
                                    _dig(d.get("radio_setting"), "radio_list"), radio_type=b
                                )
                                or {}
                            ).items()
                            if k in ("channel_width", "transmit_power", "wireless_mode")
                        },
                    },
                )
            )
        out.append(
            SrmSensorDescription(
                key=f"wifi_signal_{band}",
                translation_key="wifi_signal",
                placeholders={"band": band},
                native_unit_of_measurement=PERCENTAGE,
                state_class=SensorStateClass.MEASUREMENT,
                entity_category=EntityCategory.DIAGNOSTIC,
                value_fn=lambda d, b=band: _avg_signal(d, b),
            )
        )
    return out


def _client_descriptions(data: dict[str, Any]) -> list[SrmSensorDescription]:
    """Client counts (with the client list as attributes) and traffic, per group."""
    if not isinstance(data.get("client_list"), list):
        return []
    groups = sorted({c["group"] for c in _clients(data)})
    out = [
        SrmSensorDescription(
            key="clients_online",
            translation_key="clients_online",
            state_class=SensorStateClass.MEASUREMENT,
            value_fn=lambda d: len(_clients(d)),
        )
    ]
    for group in groups:
        out.append(
            SrmSensorDescription(
                key=f"clients_group_{group}",
                translation_key="clients_group",
                placeholders={"group": group_label(group)},
                state_class=SensorStateClass.MEASUREMENT,
                value_fn=lambda d, g=group: len(_clients(d, g)),
                attrs_fn=lambda d, g=group: _group_attrs(d, g),
            )
        )
    for network in _wifi_network_names(data):
        slug = re.sub(r"\W+", "_", network).strip("_").lower() or "network"
        out.append(
            SrmSensorDescription(
                key=f"clients_network_{slug}",
                translation_key="clients_network",
                placeholders={"network": network},
                state_class=SensorStateClass.MEASUREMENT,
                value_fn=lambda d, n=network: len(_network_clients(d, n)),
                attrs_fn=lambda d, n=network: _network_attrs(d, n),
            )
        )
        for field, tkey in (("download", "network_rx"), ("upload", "network_tx")):
            out.append(
                SrmSensorDescription(
                    key=f"{tkey}_{slug}",
                    translation_key=tkey,
                    placeholders={"network": network},
                    device_class=SensorDeviceClass.DATA_RATE,
                    native_unit_of_measurement=UnitOfDataRate.BYTES_PER_SECOND,
                    suggested_unit_of_measurement=UnitOfDataRate.MEGABITS_PER_SECOND,
                    suggested_display_precision=1,
                    state_class=SensorStateClass.MEASUREMENT,
                    value_fn=lambda d, f=field, n=network: _sum_network_rate(d, f, n),
                    attrs_fn=lambda d, n=network: {"network": n},
                )
            )
    if isinstance(data.get("offline_list"), list):
        out.append(
            SrmSensorDescription(
                key="clients_offline",
                translation_key="clients_offline",
                value_fn=lambda d: len(d.get("offline_list") or []),
                attrs_fn=lambda d: {
                    "integration": DOMAIN,
                    "group": GROUP_OFFLINE,
                    "clients": d.get("offline_list") or [],
                },
            )
        )
    for group in (None, *groups):
        label = "Total" if group is None else group
        for field, tkey in (("download", "client_rx"), ("upload", "client_tx")):
            out.append(
                SrmSensorDescription(
                    key=f"{tkey}_{label}",
                    translation_key=tkey,
                    placeholders={"group": label},
                    device_class=SensorDeviceClass.DATA_RATE,
                    native_unit_of_measurement=UnitOfDataRate.BYTES_PER_SECOND,
                    suggested_unit_of_measurement=UnitOfDataRate.MEGABITS_PER_SECOND,
                    suggested_display_precision=1,
                    state_class=SensorStateClass.MEASUREMENT,
                    value_fn=lambda d, f=field, g=group: _sum_rate(d, f, g),
                )
            )
    return out


def _network_descriptions(data: dict[str, Any]) -> list[SrmSensorDescription]:
    """Connection status, network mode and Ethernet links."""
    out: list[SrmSensorDescription] = []
    if data.get("connection_status") is not None:
        for family in ("ipv4", "ipv6"):
            out.append(
                SrmSensorDescription(
                    key=f"connection_{family}",
                    translation_key="connection_status",
                    placeholders={"family": family.upper()},
                    value_fn=lambda d, f=family: _dig(
                        d.get("connection_status"), f, "conn_status"
                    ),
                    attrs_fn=lambda d, f=family: {
                        k: v
                        for k, v in (_dig(d.get("connection_status"), f) or {}).items()
                        if k != "conn_status" and v not in ("", None)
                    },
                )
            )
    if data.get("topology") is not None:
        out.append(
            SrmSensorDescription(
                key="network_mode",
                translation_key="network_mode",
                value_fn=lambda d: _dig(d.get("topology"), "net_topology"),
                attrs_fn=lambda d: {
                    k: v
                    for k, v in (d.get("topology") or {}).items()
                    if k != "net_topology"
                },
            )
        )
    for link in data.get("ethernet") or []:
        if not isinstance(link, dict) or not link.get("ifname"):
            continue
        if not (link.get("ip") or link.get("speed")):
            continue  # skip idle virtual interfaces (bwlan0 / bwlan1)
        name = link["ifname"]
        ph = {"interface": name}
        out += [
            SrmSensorDescription(
                key=f"link_{name}_status",
                translation_key="link_status",
                placeholders=ph,
                entity_category=EntityCategory.DIAGNOSTIC,
                value_fn=lambda d, n=name: (
                    _find(d.get("ethernet"), ifname=n) or {}
                ).get("status"),
                attrs_fn=lambda d, n=name: {
                    k: v
                    for k, v in (_find(d.get("ethernet"), ifname=n) or {}).items()
                    if k not in ("status", "ifname", "speed") and v not in ("", None, [])
                },
            ),
            SrmSensorDescription(
                key=f"link_{name}_speed",
                translation_key="link_speed",
                placeholders=ph,
                device_class=SensorDeviceClass.DATA_RATE,
                native_unit_of_measurement=UnitOfDataRate.MEGABITS_PER_SECOND,
                state_class=SensorStateClass.MEASUREMENT,
                entity_category=EntityCategory.DIAGNOSTIC,
                value_fn=lambda d, n=name: _num(
                    (_find(d.get("ethernet"), ifname=n) or {}).get("speed")
                ),
            ),
            SrmSensorDescription(
                key=f"link_{name}_ip",
                translation_key="link_ip",
                placeholders=ph,
                entity_category=EntityCategory.DIAGNOSTIC,
                value_fn=lambda d, n=name: (
                    (_find(d.get("ethernet"), ifname=n) or {}).get("ip") or None
                ),
            ),
        ]
    return out


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


def _router_descriptions(data: dict[str, Any]) -> list[SrmSensorDescription]:
    """Router throughput (sees offloaded traffic), devices, status, per-band rates."""
    out: list[SrmSensorDescription] = []
    for node in _nodes(data, "mesh_nodes"):
        nid = node.get("node_id")
        ph = {"node": str(nid)}
        for field, tkey in (("current_rate_rx", "router_rx"), ("current_rate_tx", "router_tx")):
            out.append(
                SrmSensorDescription(
                    key=f"{tkey}_{nid}",
                    translation_key=tkey,
                    placeholders=ph,
                    value_fn=lambda d, n=nid, f=field: _num(_node(d, "mesh_nodes", n).get(f)),
                    **_rate_kwargs(),
                )
            )
        out.append(
            SrmSensorDescription(
                key=f"connected_devices_{nid}",
                translation_key="connected_devices",
                placeholders=ph,
                state_class=SensorStateClass.MEASUREMENT,
                value_fn=lambda d, n=nid: _num(_node(d, "mesh_nodes", n).get("connected_devices")),
            )
        )
        out.append(
            SrmSensorDescription(
                key=f"node_status_{nid}",
                translation_key="node_status",
                placeholders=ph,
                entity_category=EntityCategory.DIAGNOSTIC,
                value_fn=lambda d, n=nid: _node(d, "mesh_nodes", n).get("node_status"),
                attrs_fn=lambda d, n=nid: {
                    k: v
                    for k, v in _node(d, "mesh_nodes", n).items()
                    if k in ("name", "network_status", "node_status_msg", "led_mode", "is_wireless", "parent_node_id")
                },
            )
        )
    for node in _nodes(data, "mesh_network"):
        nid = node.get("node_id")
        for radio in node.get("wifi_radios") or []:
            band = radio.get("band")
            if not band:
                continue
            ph = {"node": str(nid), "band": band}
            for field, tkey in (("current_rate_rx", "band_rx"), ("current_rate_tx", "band_tx")):
                out.append(
                    SrmSensorDescription(
                        key=f"{tkey}_{nid}_{band}",
                        translation_key=tkey,
                        placeholders=ph,
                        value_fn=lambda d, n=nid, b=band, f=field: _num(_radio_net(d, n, b).get(f)),
                        **_rate_kwargs(),
                    )
                )
    if _dig(data.get("mesh_status"), "overall_status") is not None:
        out.append(
            SrmSensorDescription(
                key="router_status",
                translation_key="router_status",
                value_fn=lambda d: _dig(d.get("mesh_status"), "overall_status"),
                attrs_fn=lambda d: {"message": _dig(d.get("mesh_status"), "overall_status_msg")},
            )
        )
    # Ethernet ports
    for node in _nodes(data, "eth_ports"):
        nid = node.get("node_id")
        for port in node.get("eth_port_info") or []:
            name = port.get("port")
            if not name:
                continue
            out.append(
                SrmSensorDescription(
                    key=f"port_speed_{nid}_{name}",
                    translation_key="port_speed",
                    placeholders={"node": str(nid), "port": port_label(name)},
                    device_class=SensorDeviceClass.DATA_RATE,
                    native_unit_of_measurement=UnitOfDataRate.MEGABITS_PER_SECOND,
                    state_class=SensorStateClass.MEASUREMENT,
                    entity_category=EntityCategory.DIAGNOSTIC,
                    value_fn=lambda d, n=nid, p=name: _port_speed(d, n, p),
                    attrs_fn=lambda d, n=nid, p=name: {
                        "port_id": p,
                        "link": bool((_port(d, n, p) or {}).get("has_link")),
                    },
                )
            )
    return out


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


def _usb_descriptions(data: dict[str, Any]) -> list[SrmSensorDescription]:
    """Space used on the USB storage. SRM reports sizes in MiB (a 32 GB key shows ~29000)."""
    out: list[SrmSensorDescription] = []
    for vol in _volumes(data):
        vid = vol.get("id")
        if not vid:
            continue
        slug = "".join(ch if ch.isalnum() else "_" for ch in vid)
        ph = {"volume": vid}

        def _usage(d: dict[str, Any], v: str = vid) -> float | None:
            volume = _volume(d, v)
            total, used = volume.get("total"), volume.get("used")
            if not isinstance(total, (int, float)) or not total or not isinstance(used, (int, float)):
                return None
            return round(used / total * 100, 1)

        out.append(
            SrmSensorDescription(
                key=f"usb_usage_{slug}",
                translation_key="usb_usage",
                placeholders=ph,
                native_unit_of_measurement=PERCENTAGE,
                state_class=SensorStateClass.MEASUREMENT,
                value_fn=_usage,
                attrs_fn=lambda d, v=vid: {"status": _volume(d, v).get("status")},
            )
        )
        for field, tkey in (("used", "usb_used"), ("total", "usb_total")):
            out.append(
                SrmSensorDescription(
                    key=f"{tkey}_{slug}",
                    translation_key=tkey,
                    placeholders=ph,
                    device_class=SensorDeviceClass.DATA_SIZE,
                    native_unit_of_measurement=UnitOfInformation.MEBIBYTES,
                    suggested_unit_of_measurement=UnitOfInformation.GIBIBYTES,
                    suggested_display_precision=1,
                    state_class=SensorStateClass.MEASUREMENT,
                    entity_category=EntityCategory.DIAGNOSTIC,
                    value_fn=lambda d, v=vid, f=field: _num(_volume(d, v).get(f)),
                )
            )
    return out


def _parse_time(value: Any) -> datetime | None:
    try:
        return datetime.strptime(str(value), "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None


def _threat_events(d: dict[str, Any], hours: int | None) -> int | None:
    trends = _dig(d.get("tps_trends"), "trends")
    if not isinstance(trends, list):
        return None
    end = _parse_time(_dig(d.get("tps_trends"), "end"))
    total = 0
    for bucket in trends:
        if not isinstance(bucket, dict):
            continue
        if hours is not None:
            bucket_end = _parse_time(bucket.get("end"))
            if end is None or bucket_end is None or bucket_end <= end - timedelta(hours=hours):
                continue
        total += int(bucket.get("total") or 0)
    return total


def _threat_levels(d: dict[str, Any]) -> dict[str, Any]:
    trends = _dig(d.get("tps_trends"), "trends")
    if not isinstance(trends, list):
        return {}
    levels = {k: sum(int(b.get(k) or 0) for b in trends if isinstance(b, dict)) for k in ("high", "medium", "low")}
    return {**levels, "since": _dig(d.get("tps_trends"), "begin"), "until": _dig(d.get("tps_trends"), "end")}


def _sessions(d: dict[str, Any]) -> list[dict[str, Any]]:
    """Sign-in records of the admin interface (SRM keeps a history, not the open sessions).

    Entries dated 1970 are unset records: they are dropped.
    """
    items = _dig(d.get("admin_sessions"), "items")
    if not isinstance(items, list):
        return []
    return [i for i in items if isinstance(i, dict) and not str(i.get("time", "")).startswith("1970")]


def _blocked_clients(d: dict[str, Any]) -> list[dict[str, Any]]:
    """Clients (online or not) that the router blocks."""
    everyone = (d.get("client_list") or []) + (d.get("offline_list") or [])
    return [c for c in everyone if c.get("blocked") is True]


def _security_descriptions(data: dict[str, Any]) -> list[SrmSensorDescription]:
    """Threat events, new devices, admin sessions, blocked IPs, forwarded ports."""
    out: list[SrmSensorDescription] = []
    if isinstance(_dig(data.get("tps_trends"), "trends"), list):
        out.append(
            SrmSensorDescription(
                key="threat_events_24h",
                translation_key="threat_events_24h",
                state_class=SensorStateClass.MEASUREMENT,
                value_fn=lambda d: _threat_events(d, 24),
            )
        )
        out.append(
            SrmSensorDescription(
                key="threat_events_7d",
                translation_key="threat_events_7d",
                state_class=SensorStateClass.MEASUREMENT,
                value_fn=lambda d: _threat_events(d, None),
                attrs_fn=_threat_levels,
            )
        )
    if isinstance(_dig(data.get("new_devices"), "new_devices"), list):
        out.append(
            SrmSensorDescription(
                key="new_devices",
                translation_key="new_devices",
                state_class=SensorStateClass.MEASUREMENT,
                value_fn=lambda d: len(_dig(d.get("new_devices"), "new_devices") or []),
                attrs_fn=lambda d: {"devices": _dig(d.get("new_devices"), "new_devices") or []},
            )
        )
    if isinstance(_dig(data.get("admin_sessions"), "items"), list):
        out.append(
            SrmSensorDescription(
                key="admin_sessions",
                translation_key="admin_sessions",
                state_class=SensorStateClass.MEASUREMENT,
                value_fn=lambda d: len(_sessions(d)),
                attrs_fn=lambda d: {
                    "sessions": [
                        {k: s.get(k) for k in ("who", "from", "type", "time", "descr")}
                        for s in _sessions(d)
                    ]
                },
            )
        )
    if _num(_dig(data.get("autoblock"), "total")) is not None:
        out.append(
            SrmSensorDescription(
                key="blocked_ips",
                translation_key="blocked_ips",
                state_class=SensorStateClass.MEASUREMENT,
                value_fn=lambda d: _num(_dig(d.get("autoblock"), "total")),
                attrs_fn=lambda d: {
                    k: v
                    for k, v in {
                        "auto_block_enabled": _dig(d.get("autoblock_settings"), "enable"),
                        "failed_attempts": _dig(d.get("autoblock_settings"), "attempts"),
                        "within_minutes": _dig(d.get("autoblock_settings"), "within_mins"),
                        "expire_days": _dig(d.get("autoblock_settings"), "expire_day"),
                        "addresses": _dig(d.get("autoblock"), "addresses") or None,
                    }.items()
                    if v is not None
                },
            )
        )
    if isinstance(_dig(data.get("macfilter_profiles"), "profiles"), list):
        out.append(
            SrmSensorDescription(
                key="mac_filter_profiles",
                translation_key="mac_filter_profiles",
                state_class=SensorStateClass.MEASUREMENT,
                entity_category=EntityCategory.DIAGNOSTIC,
                value_fn=lambda d: len(_dig(d.get("macfilter_profiles"), "profiles") or []),
                attrs_fn=lambda d: {
                    "profiles": [
                        {k: v for k, v in p.items() if k != "password"}
                        for p in _dig(d.get("macfilter_profiles"), "profiles") or []
                        if isinstance(p, dict)
                    ]
                },
            )
        )
    if isinstance(_dig(data.get("macfilter_devices"), "devices"), list):
        out.append(
            SrmSensorDescription(
                key="mac_filter_devices",
                translation_key="mac_filter_devices",
                state_class=SensorStateClass.MEASUREMENT,
                entity_category=EntityCategory.DIAGNOSTIC,
                value_fn=lambda d: len(_dig(d.get("macfilter_devices"), "devices") or []),
                attrs_fn=lambda d: {
                    "devices": [
                        {"name": x.get("name"), "mac": str(x.get("mac_addr", "")).lower()}
                        for x in _dig(d.get("macfilter_devices"), "devices") or []
                        if isinstance(x, dict)
                    ],
                    "broadcast_storm_prevention": _dig(d.get("macfilter_devices"), "enable_prevent_broadcast"),
                    "max_broadcast_packets_per_second": _dig(d.get("macfilter_devices"), "maximum_broadcast"),
                },
            )
        )
    if isinstance(data.get("client_list"), list):
        out.append(
            SrmSensorDescription(
                key="blocked_devices",
                translation_key="blocked_devices",
                state_class=SensorStateClass.MEASUREMENT,
                value_fn=lambda d: len(_blocked_clients(d)),
                attrs_fn=lambda d: {
                    "devices": [
                        {k: c.get(k) for k in ("name", "mac", "ip") if c.get(k)}
                        for c in _blocked_clients(d)
                    ]
                },
            )
        )
    if isinstance(_dig(data.get("port_forward"), "rules"), list):
        out.append(
            SrmSensorDescription(
                key="port_forward_rules",
                translation_key="port_forward_rules",
                state_class=SensorStateClass.MEASUREMENT,
                entity_category=EntityCategory.DIAGNOSTIC,
                value_fn=lambda d: len(_dig(d.get("port_forward"), "rules") or []),
            )
        )
    return out


def safe_profiles(d: dict[str, Any]) -> list[dict[str, Any]]:
    """Return the Safe Access (parental control) profiles."""
    profiles = _dig(d.get("safe_profiles"), "profiles")
    return [p for p in profiles if isinstance(p, dict)] if isinstance(profiles, list) else []


def safe_stat(d: dict[str, Any], pid: Any) -> dict[str, Any]:
    """Return the Safe Access statistics of one profile."""
    return _find(_dig(d.get("safe_stats"), "config_groups"), id=pid) or {}


def safe_schedule(d: dict[str, Any], pid: Any) -> dict[str, Any]:
    """Return the Safe Access schedules (block time, quota) of one profile."""
    found = _find(_dig(d.get("safe_schedule"), "profiles"), profile_id=pid) or {}
    return found.get("schedules") or {}


def _safe_devices(d: dict[str, Any], pid: Any) -> list[dict[str, Any]]:
    """Devices of a Safe Access profile, with their name, state and internet time."""
    group = _find(_dig(d.get("safe_devices"), "config_groups"), config_group_id=pid) or {}
    spent_group = _find(_dig(d.get("safe_device_time"), "config_groups"), config_group_id=pid) or {}
    times = spent_group.get("device_timespent")
    times = {str(k).lower(): v for k, v in times.items()} if isinstance(times, dict) else {}
    online = {c.get("mac"): c for c in d.get("client_list") or [] if c.get("mac")}
    offline = {c.get("mac"): c for c in d.get("offline_list") or [] if c.get("mac")}
    out: list[dict[str, Any]] = []
    for raw in group.get("devices") or []:
        mac = str(raw).lower()
        client = online.get(mac) or offline.get(mac) or {}
        entry: dict[str, Any] = {
            "name": client.get("name") or mac,
            "mac": mac,
            "online": mac in online,
        }
        if client.get("ip"):
            entry["ip"] = client["ip"]
        minutes = _dig(times.get(mac), "total_spent", "normal")
        if isinstance(minutes, (int, float)):
            entry["internet_minutes"] = minutes
        out.append(entry)
    out.sort(key=lambda e: (not e["online"], str(e["name"]).lower()))
    return out


def _safe_attrs(d: dict[str, Any], pid: Any) -> dict[str, Any]:
    profile = _find(safe_profiles(d), profile_id=pid) or {}
    stat = safe_stat(d, pid)
    hits = stat.get("inappropriate_website_hit")
    quotas = safe_schedule(d, pid).get("timequotas")
    return {
        "profile": profile.get("name"),
        "devices": _safe_devices(d, pid) or None,
        "concerned_status": stat.get("concerned_status"),
        "web_filter": profile.get("enable_filter"),
        "safe_search": profile.get("enable_safe_search"),
        "time_quota": profile.get("enable_timequota"),
        "block_time": profile.get("enable_blocktime"),
        "quota_minutes_by_weekday": (
            {q["weekday"]: q["quota"] for q in quotas if isinstance(q, dict) and "weekday" in q}
            if isinstance(quotas, list) and quotas
            else None
        ),
        "inappropriate_websites": (
            {site: v.get("total") for site, v in hits.items() if isinstance(v, dict)}
            if isinstance(hits, dict) and hits
            else None
        ),
    }


def _safe_descriptions(data: dict[str, Any]) -> list[SrmSensorDescription]:
    """Safe Access (parental control): internet time and status per profile."""
    out: list[SrmSensorDescription] = []
    for profile in safe_profiles(data):
        pid = profile.get("profile_id")
        name = profile.get("name")
        if pid is None or not name:
            continue
        ph = {"profile": str(name)}
        out.append(
            SrmSensorDescription(
                key=f"safe_time_{pid}",
                translation_key="safe_time",
                placeholders=ph,
                device_class=SensorDeviceClass.DURATION,
                native_unit_of_measurement=UnitOfTime.MINUTES,
                suggested_unit_of_measurement=UnitOfTime.HOURS,
                suggested_display_precision=1,
                state_class=SensorStateClass.MEASUREMENT,
                value_fn=lambda d, p=pid: _num(safe_stat(d, p).get("time_spent_on_internet")),
                attrs_fn=lambda d, p=pid: {k: v for k, v in _safe_attrs(d, p).items() if v is not None},
            )
        )
        out.append(
            SrmSensorDescription(
                key=f"safe_status_{pid}",
                translation_key="safe_status",
                placeholders=ph,
                entity_category=EntityCategory.DIAGNOSTIC,
                value_fn=lambda d, p=pid: safe_stat(d, p).get("concerned_status"),
            )
        )
    return out


def _dynamic_descriptions(data: dict[str, Any]) -> list[SrmSensorDescription]:
    """Build the per-node / per-interface / per-disk sensors from the first data."""
    out: list[SrmSensorDescription] = [
        *_client_descriptions(data),
        *_router_descriptions(data),
        *_usb_descriptions(data),
        *_security_descriptions(data),
        *_safe_descriptions(data),
        *_wifi_descriptions(data),
        *_network_descriptions(data),
    ]

    for node in _dig(data.get("system_info"), "nodes") or []:
        if isinstance(node, dict) and "node_id" in node:
            out += _node_descriptions(node["node_id"])
            if node["node_id"] != 0 and _find(_nodes(data, "mesh_utilization"), node_id=node["node_id"]):
                out += _node_utilization_descriptions(node["node_id"])

    for iface in _dig(data.get("system_utilization"), "network") or []:
        if isinstance(iface, dict) and iface.get("device"):
            out += _interface_descriptions(iface["device"])

    util = data.get("system_utilization")
    for path, kind in ((("disk", "disk"), "disk"), (("space", "volume"), "volume")):
        for item in _dig(util, *path) or []:
            if isinstance(item, dict) and item.get("device"):
                out += _storage_descriptions(path, kind, item["device"])
    return out


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SrmConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up sensors."""
    coordinator = entry.runtime_data
    data = coordinator.data
    # Skip sensors whose API this router does not offer.
    descriptions = [
        desc
        for desc in STATIC_SENSORS
        if data.get(STATIC_REQUIRES.get(desc.key, "system_utilization")) is not None
    ] + _dynamic_descriptions(data)
    async_add_entities(SrmSensor(coordinator, desc) for desc in descriptions)


class SrmSensor(CoordinatorEntity[SrmCoordinator], SensorEntity):
    """A sensor reading from the shared SRM coordinator."""

    _attr_has_entity_name = True
    entity_description: SrmSensorDescription

    def __init__(self, coordinator: SrmCoordinator, description: SrmSensorDescription) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self.entity_description = description
        entry = coordinator.config_entry
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_translation_placeholders = description.placeholders or {}
        node0 = _find(_dig(coordinator.data.get("system_info"), "nodes"), node_id=0) or {}
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="Synology",
            model=node0.get("model", "SRM router"),
            sw_version=node0.get("firmware_ver"),
            serial_number=node0.get("sn"),
        )

    @property
    def native_value(self) -> Any:
        """Return the value."""
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return the description's attributes (and the raw live traffic list)."""
        if self.entity_description.key == "traffic_live":
            return {"data": self.coordinator.data.get("traffic_live")}
        # The placeholders (interface, group, band...) identify the sensor for the cards.
        attrs: dict[str, Any] = dict(self.entity_description.placeholders or {})
        if self.entity_description.attrs_fn:
            attrs.update(self.entity_description.attrs_fn(self.coordinator.data) or {})
        return attrs or None

    # Large payloads: keep them out of the database.
    _unrecorded_attributes = frozenset({"data", "clients", "sessions", "devices", "addresses"})
