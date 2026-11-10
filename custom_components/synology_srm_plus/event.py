"""Event entities: a client joined the network, the firewall changed."""

from __future__ import annotations

from typing import Any

from homeassistant.components.event import EventEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import SrmConfigEntry
from .changes import firewall_rules
from .const import DOMAIN
from .coordinator import SrmCoordinator

EVENT_TYPES = {
    "new_client": ["new_client"],
    "router_changes": ["firewall_rules_changed", "firewall_policy_changed"],
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SrmConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the event entities the router can feed."""
    coordinator = entry.runtime_data
    keys = []
    if isinstance(coordinator.data.get("client_list"), list):
        keys.append("new_client")
    if firewall_rules(coordinator.data) is not None:
        keys.append("router_changes")
    async_add_entities(SrmEvent(coordinator, key) for key in keys)


class SrmEvent(CoordinatorEntity[SrmCoordinator], EventEntity):
    """Fires when the coordinator finds a change of its kind."""

    _attr_has_entity_name = True
    # Who joined, which rules changed: shown on the event, kept out of the history.
    _unrecorded_attributes = frozenset(
        {
            "name",
            "mac",
            "ip",
            "connection",
            "band",
            "ssid",
            "private_mac",
            "added",
            "removed",
            "modified_or_moved",
            "rule_count",
            "changed",
        }
    )

    def __init__(self, coordinator: SrmCoordinator, key: str) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self._key = key
        entry = coordinator.config_entry
        self._attr_translation_key = key
        self._attr_event_types = EVENT_TYPES[key]
        self._attr_unique_id = f"{entry.entry_id}_event_{key}"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, entry.entry_id)})

    _handled: list[dict[str, Any]] | None = None

    def _fire(self, events: list[dict[str, Any]]) -> None:
        # A failed update notifies the listeners again with the same list: fire it once.
        if events is self._handled:
            return
        self._handled = events
        fired = False
        for event in events:
            if event["entity"] == self._key and event["type"] in self.event_types:
                self._trigger_event(event["type"], event["data"])
                fired = True
        if fired:
            self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """Report what the first update found (for example a change made while we were off)."""
        await super().async_added_to_hass()
        self._fire(self.coordinator.events)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Fire the events of this update."""
        self._fire(self.coordinator.events)
        super()._handle_coordinator_update()
