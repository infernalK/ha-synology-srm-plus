"""System sensors: CPU, memory, traffic, router nodes, ports, USB storage, network."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    EntityCategory,
    UnitOfDataRate,
    UnitOfInformation,
    UnitOfTime,
)

from .helpers import (
    SrmSensorDescription,
    _cpu_total,
    _dig,
    _external,
    _find,
    _list_item_value,
    _node,
    _nodes,
    _num,
    _port,
    _port_speed,
    _radio_net,
    _rate_kwargs,
    _util_num,
    _volume,
    _volumes,
    port_label,
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
        for field in (
            "total_real",
            "avail_real",
            "cached",
            "buffer",
            "total_swap",
            "avail_swap",
        )
    ),
    SrmSensorDescription(
        key="external_ipv4",
        translation_key="external_ipv4",
        value_fn=lambda d: _external(d, "ip"),
        attrs_fn=lambda d: (
            {
                "ddns_hostnames": [
                    r["hostname"]
                    for r in (_dig(d.get("ddns"), "records") or [])
                    if isinstance(r, dict) and r.get("hostname")
                ]
            }
            or None
        ),
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
            value_fn=lambda d, n=node_id: _num(
                _node(d, "mesh_utilization", n).get("cpu_usage")
            ),
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
                (_find(_dig(d.get("system_info"), "nodes"), node_id=n) or {}).get(
                    "uptime"
                )
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
                    if k not in ("status", "ifname", "speed")
                    and v not in ("", None, [])
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


def _router_descriptions(data: dict[str, Any]) -> list[SrmSensorDescription]:
    """Router throughput (sees offloaded traffic), devices, status, per-band rates."""
    out: list[SrmSensorDescription] = []
    for node in _nodes(data, "mesh_nodes"):
        nid = node.get("node_id")
        ph = {"node": str(nid)}
        for field, tkey in (
            ("current_rate_rx", "router_rx"),
            ("current_rate_tx", "router_tx"),
        ):
            out.append(
                SrmSensorDescription(
                    key=f"{tkey}_{nid}",
                    translation_key=tkey,
                    placeholders=ph,
                    value_fn=lambda d, n=nid, f=field: _num(
                        _node(d, "mesh_nodes", n).get(f)
                    ),
                    **_rate_kwargs(),
                )
            )
        out.append(
            SrmSensorDescription(
                key=f"connected_devices_{nid}",
                translation_key="connected_devices",
                placeholders=ph,
                state_class=SensorStateClass.MEASUREMENT,
                value_fn=lambda d, n=nid: _num(
                    _node(d, "mesh_nodes", n).get("connected_devices")
                ),
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
                    if k
                    in (
                        "name",
                        "network_status",
                        "node_status_msg",
                        "led_mode",
                        "is_wireless",
                        "parent_node_id",
                    )
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
            for field, tkey in (
                ("current_rate_rx", "band_rx"),
                ("current_rate_tx", "band_tx"),
            ):
                out.append(
                    SrmSensorDescription(
                        key=f"{tkey}_{nid}_{band}",
                        translation_key=tkey,
                        placeholders=ph,
                        value_fn=lambda d, n=nid, b=band, f=field: _num(
                            _radio_net(d, n, b).get(f)
                        ),
                        **_rate_kwargs(),
                    )
                )
    if _dig(data.get("mesh_status"), "overall_status") is not None:
        out.append(
            SrmSensorDescription(
                key="router_status",
                translation_key="router_status",
                value_fn=lambda d: _dig(d.get("mesh_status"), "overall_status"),
                attrs_fn=lambda d: {
                    "message": _dig(d.get("mesh_status"), "overall_status_msg")
                },
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
            if (
                not isinstance(total, (int, float))
                or not total
                or not isinstance(used, (int, float))
            ):
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
