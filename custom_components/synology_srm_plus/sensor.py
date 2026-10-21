"""Sensors for Synology SRM Plus (discovery version: one raw sensor per endpoint)."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import SrmConfigEntry
from .const import DOMAIN
from .coordinator import ENDPOINTS, SrmCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SrmConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up sensors."""
    coordinator = entry.runtime_data
    async_add_entities(SrmRawSensor(coordinator, key) for key in ENDPOINTS)


class SrmRawSensor(CoordinatorEntity[SrmCoordinator], SensorEntity):
    """Exposes the raw payload of one SRM endpoint as attributes."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _unrecorded_attributes = frozenset({"data"})

    def __init__(self, coordinator: SrmCoordinator, key: str) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self._key = key
        self.entity_description = SensorEntityDescription(key=key, translation_key=key)
        entry_id = coordinator.config_entry.entry_id
        self._attr_unique_id = f"{entry_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry_id)},
            name=coordinator.config_entry.title,
            manufacturer="Synology",
            model="SRM router",
        )

    @property
    def native_value(self) -> str:
        """Return ok / error."""
        data = self.coordinator.data[self._key]
        if isinstance(data, dict) and "error" in data and len(data) == 1:
            return "error"
        return "ok"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the raw payload."""
        return {"data": self.coordinator.data[self._key]}
