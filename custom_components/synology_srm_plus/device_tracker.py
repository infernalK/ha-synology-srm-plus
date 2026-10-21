"""Optional per-client device trackers for Synology SRM Plus."""

from __future__ import annotations

from typing import Any

from homeassistant.components.device_tracker import ScannerEntity, SourceType
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import SrmConfigEntry
from .const import CONF_TRACK_ALL, CONF_TRACK_CLIENTS, CONF_TRACKED_CLIENTS, DOMAIN
from .coordinator import SrmCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SrmConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Create one tracker per client, when enabled in the options."""
    track_all = entry.options.get(
        CONF_TRACK_ALL, entry.options.get(CONF_TRACK_CLIENTS, False)
    )
    selected = set(entry.options.get(CONF_TRACKED_CLIENTS) or [])

    # Options changed: forget the trackers that are no longer wanted (no ghost entities).
    if not track_all:
        registry = er.async_get(hass)
        prefix = f"{entry.entry_id}_client_"
        for entity in er.async_entries_for_config_entry(registry, entry.entry_id):
            unique_id = entity.unique_id
            if (
                entity.domain == "device_tracker"
                and unique_id.startswith(prefix)
                and unique_id[len(prefix) :] not in selected
            ):
                registry.async_remove(entity.entity_id)

    if not track_all and not selected:
        return
    coordinator = entry.runtime_data
    known: set[str] = set()

    @callback
    def _add_new_clients() -> None:
        new = []
        everyone = (coordinator.data.get("client_list") or []) + (
            coordinator.data.get("offline_list") or []
        )
        for client in everyone:
            mac = client.get("mac")
            if mac and mac not in known and (track_all or mac in selected):
                known.add(mac)
                new.append(SrmClientTracker(coordinator, mac, client["name"]))
        if new:
            async_add_entities(new)

    _add_new_clients()
    entry.async_on_unload(coordinator.async_add_listener(_add_new_clients))


class SrmClientTracker(CoordinatorEntity[SrmCoordinator], ScannerEntity):
    """A device connected to the router."""

    _attr_has_entity_name = True
    _attr_source_type = SourceType.ROUTER

    def __init__(self, coordinator: SrmCoordinator, mac: str, name: str) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self._mac = mac
        self._attr_name = name
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_client_{mac}"

    @property
    def entity_registry_enabled_default(self) -> bool:
        """Enabled: the user opted in to client trackers."""
        return True

    def _client(self) -> dict[str, Any] | None:
        for client in self.coordinator.data.get("client_list") or []:
            if client.get("mac") == self._mac:
                return client
        return None

    @property
    def mac_address(self) -> str:
        """Return the MAC address."""
        return self._mac

    @property
    def is_connected(self) -> bool:
        """Return whether the client is online."""
        return self._client() is not None

    @property
    def ip_address(self) -> str | None:
        """Return the IP address."""
        return (self._client() or {}).get("ip")

    @property
    def hostname(self) -> str | None:
        """Return the host name."""
        return (self._client() or {}).get("name")

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return the details SRM reports for this client."""
        client = self._client()
        if client is None:
            return None
        skip = {"mac", "ip", "name"}
        return {k: v for k, v in client.items() if k not in skip}

    _unrecorded_attributes = frozenset({"wifi_bytes_rx", "wifi_bytes_tx"})
