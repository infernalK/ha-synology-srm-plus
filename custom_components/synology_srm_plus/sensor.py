"""Sensors for Synology SRM Plus."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
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
        value_fn=lambda d: (_find(d.get("external_ip"), type="WAN") or {}).get("ip") or None,
    ),
    SrmSensorDescription(
        key="external_ipv6",
        translation_key="external_ipv6",
        value_fn=lambda d: (_find(d.get("external_ip"), type="WAN") or {}).get("ipv6")
        or None,
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


def _wifi_clients(d: dict[str, Any], band: str | None) -> list[dict[str, Any]]:
    clients = _dig(d.get("wifi_devices"), "device_list")
    if not isinstance(clients, list):
        return []
    return [
        c
        for c in clients
        if isinstance(c, dict) and (band is None or c.get("radio_type") == band)
    ]


def _wifi_descriptions(data: dict[str, Any]) -> list[SrmSensorDescription]:
    """Channel, client count and signal per Wi-Fi band."""
    out: list[SrmSensorDescription] = []
    bands: set[str] = set()
    for item in _dig(data.get("wifi_radio"), "status_list") or []:
        if isinstance(item, dict) and item.get("radio_type"):
            bands.add(item["radio_type"])
            band = item["radio_type"]
            out.append(
                SrmSensorDescription(
                    key=f"wifi_channel_{band}",
                    translation_key="wifi_channel",
                    placeholders={"band": band},
                    entity_category=EntityCategory.DIAGNOSTIC,
                    value_fn=lambda d, b=band: _num(
                        (
                            _find(_dig(d.get("wifi_radio"), "status_list"), radio_type=b)
                            or {}
                        ).get("channel")
                    ),
                )
            )
    for c in _wifi_clients(data, None):
        if c.get("radio_type"):
            bands.add(c["radio_type"])

    def _avg_signal(d: dict[str, Any], b: str | None) -> float | None:
        signals = [
            c["signal"]
            for c in _wifi_clients(d, b)
            if isinstance(c.get("signal"), (int, float))
        ]
        return round(sum(signals) / len(signals), 1) if signals else None

    if data.get("wifi_devices") is not None:
        out.append(
            SrmSensorDescription(
                key="wifi_clients_total",
                translation_key="wifi_clients",
                placeholders={"band": "Wi-Fi"},
                state_class=SensorStateClass.MEASUREMENT,
                value_fn=lambda d: len(_wifi_clients(d, None)),
            )
        )
        for band in sorted(bands):
            out.append(
                SrmSensorDescription(
                    key=f"wifi_clients_{band}",
                    translation_key="wifi_clients",
                    placeholders={"band": band},
                    state_class=SensorStateClass.MEASUREMENT,
                    value_fn=lambda d, b=band: len(_wifi_clients(d, b)),
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


def _client_group(client: dict[str, Any]) -> str:
    """Return the band of a Wi-Fi client, or 'Wired'."""
    if client.get("is_wireless"):
        return str(client.get("band") or "Wi-Fi")
    return "Wired"


def _client_rate(d: dict[str, Any], field: str, group: str | None) -> float | None:
    clients = d.get("clients")
    if not isinstance(clients, list):
        return None
    return sum(
        c.get(field) or 0
        for c in clients
        if isinstance(c, dict) and (group is None or _client_group(c) == group)
    )


def _client_descriptions(data: dict[str, Any]) -> list[SrmSensorDescription]:
    """Traffic summed over the online clients (total and per band / wired)."""
    clients = data.get("clients")
    if not isinstance(clients, list):
        return []
    groups = sorted({_client_group(c) for c in clients if isinstance(c, dict)})
    out = [
        SrmSensorDescription(
            key="clients_online",
            translation_key="clients_online",
            state_class=SensorStateClass.MEASUREMENT,
            value_fn=lambda d: len(d["clients"]) if d.get("clients") is not None else None,
        )
    ]
    for group in (None, *groups):
        label = "Total" if group is None else group
        for field, tkey in (("transfer_rx_rate", "client_rx"), ("transfer_tx_rate", "client_tx")):
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
                    value_fn=lambda d, f=field, g=group: _client_rate(d, f, g),
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
                )
            )
    if data.get("topology") is not None:
        out.append(
            SrmSensorDescription(
                key="network_mode",
                translation_key="network_mode",
                value_fn=lambda d: _dig(d.get("topology"), "net_topology"),
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


def _dynamic_descriptions(data: dict[str, Any]) -> list[SrmSensorDescription]:
    """Build the per-node / per-interface / per-disk sensors from the first data."""
    out: list[SrmSensorDescription] = [
        *_client_descriptions(data),
        *_wifi_descriptions(data),
        *_network_descriptions(data),
    ]

    for node in _dig(data.get("system_info"), "nodes") or []:
        if isinstance(node, dict) and "node_id" in node:
            out += _node_descriptions(node["node_id"])

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
        """Expose the raw live traffic list on the diagnostic sensor."""
        if self.entity_description.key == "traffic_live":
            return {"data": self.coordinator.data.get("traffic_live")}
        return None

    _unrecorded_attributes = frozenset({"data"})
