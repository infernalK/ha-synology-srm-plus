"""The Synology SRM Plus integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .coordinator import SrmCoordinator

PLATFORMS = [Platform.SENSOR]

type SrmConfigEntry = ConfigEntry[SrmCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: SrmConfigEntry) -> bool:
    """Set up Synology SRM Plus from a config entry."""
    coordinator = SrmCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: SrmConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
