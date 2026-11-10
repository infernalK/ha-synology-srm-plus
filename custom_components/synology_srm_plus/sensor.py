"""Sensors for Synology SRM Plus: the platform, built from the sensor modules."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import (
    SensorEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import SrmConfigEntry
from .const import DOMAIN
from .coordinator import SrmCoordinator
from .helpers import SrmSensorDescription, _dig, _find, _nodes
from .sensors_clients import _client_descriptions, _wifi_descriptions
from .sensors_lan import _lan_descriptions
from .sensors_safe import _safe_descriptions
from .sensors_security import _security_descriptions
from .sensors_system import (
    STATIC_REQUIRES,
    STATIC_SENSORS,
    _interface_descriptions,
    _network_descriptions,
    _node_descriptions,
    _node_utilization_descriptions,
    _router_descriptions,
    _storage_descriptions,
    _usb_descriptions,
)


def _dynamic_descriptions(data: dict[str, Any]) -> list[SrmSensorDescription]:
    """Build the per-node / per-interface / per-disk sensors from the first data."""
    out: list[SrmSensorDescription] = [
        *_client_descriptions(data),
        *_router_descriptions(data),
        *_usb_descriptions(data),
        *_security_descriptions(data),
        *_safe_descriptions(data),
        *_lan_descriptions(data),
        *_wifi_descriptions(data),
        *_network_descriptions(data),
    ]

    for node in _dig(data.get("system_info"), "nodes") or []:
        if isinstance(node, dict) and "node_id" in node:
            out += _node_descriptions(node["node_id"])
            if node["node_id"] != 0 and _find(
                _nodes(data, "mesh_utilization"), node_id=node["node_id"]
            ):
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


UNRECORDED_ATTRIBUTES = frozenset(
    {
        "data",
        "clients",
        "sessions",
        "devices",
        "addresses",
        "profiles",  # MAC filter profiles
        "inappropriate_websites",  # sites flagged by Safe Access, per profile
        "bssid",
        "ssids",
        "ddns_hostnames",  # the router's public DDNS names
        "leases",  # DHCP leases: names, MAC and IP addresses
        "reservations",
        "rules",  # firewall rule table
    }
)


class SrmSensor(CoordinatorEntity[SrmCoordinator], SensorEntity):
    """A sensor reading from the shared SRM coordinator."""

    _attr_has_entity_name = True
    entity_description: SrmSensorDescription

    def __init__(
        self, coordinator: SrmCoordinator, description: SrmSensorDescription
    ) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self.entity_description = description
        entry = coordinator.config_entry
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_translation_placeholders = description.placeholders or {}
        node0 = (
            _find(_dig(coordinator.data.get("system_info"), "nodes"), node_id=0) or {}
        )
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

    # Large or personal payloads (who is on the network, which sites a child hit, who is
    # blocked, Wi-Fi identifiers): they stay readable as live state but never reach the
    # history database. tests/test_privacy.py fails if a new list attribute is not listed.
    _unrecorded_attributes = UNRECORDED_ATTRIBUTES
