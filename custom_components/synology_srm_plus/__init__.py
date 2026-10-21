"""The Synology SRM Plus integration."""

from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .const import CARD_URL, DOMAIN, VERSION
from .coordinator import SrmCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.SENSOR, Platform.DEVICE_TRACKER]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

type SrmConfigEntry = ConfigEntry[SrmCoordinator]


async def _async_register_card_resource(hass: HomeAssistant, url: str) -> bool:
    """Register the card as a Lovelace resource (storage mode dashboards).

    A Lovelace resource is loaded before the dashboard renders, which avoids the
    "Custom element doesn't exist" errors that a late-loaded script causes.
    Returns False when resources cannot be managed (YAML mode).
    """
    try:
        from homeassistant.components.lovelace.const import LOVELACE_DATA  # noqa: PLC0415
        from homeassistant.components.lovelace.resources import (  # noqa: PLC0415
            ResourceStorageCollection,
        )

        lovelace = hass.data.get(LOVELACE_DATA)
        resources = getattr(lovelace, "resources", None)
        if not isinstance(resources, ResourceStorageCollection):
            return False
        if not resources.loaded:
            await resources.async_load()
        for item in resources.async_items():
            if str(item["url"]).split("?")[0] == CARD_URL:
                if item["url"] != url:
                    await resources.async_update_item(
                        item["id"], {"res_type": "module", "url": url}
                    )
                return True
        await resources.async_create_item({"res_type": "module", "url": url})
    except Exception:  # noqa: BLE001 - frontend internals differ between versions
        _LOGGER.debug("Could not register the card as a Lovelace resource", exc_info=True)
        return False
    return True


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Serve the dashboard cards and make sure the frontend loads them."""
    card = Path(__file__).parent / "www" / "synology-srm-card.js"
    await hass.http.async_register_static_paths(
        [StaticPathConfig(CARD_URL, str(card), cache_headers=False)]
    )
    url = f"{CARD_URL}?v={VERSION}"
    if not await _async_register_card_resource(hass, url):
        add_extra_js_url(hass, url)
    return True


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
