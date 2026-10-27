"""The Synology SRM Plus integration."""

from __future__ import annotations

import logging
from pathlib import Path

import voluptuous as vol

from homeassistant.components import persistent_notification
from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.typing import ConfigType

from .const import CARD_URL, CONF_SAFE_ACCESS, LOADER_URL, DOMAIN, VERSION
from .coordinator import SrmCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR, Platform.DEVICE_TRACKER]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

SERVICE_EXPLORE_API = "explore_api"
SERVICE_DEBUG_REPORT = "debug_report"
EXPLORE_SCHEMA = vol.Schema({vol.Optional("filter"): cv.string})

type SrmConfigEntry = ConfigEntry[SrmCoordinator]


async def _async_register_card_resource(
    hass: HomeAssistant, url: str
) -> tuple[bool, bool]:
    """Register the card as a Lovelace resource (storage mode dashboards).

    A Lovelace resource is loaded before the dashboard renders, which avoids the
    "Custom element doesn't exist" errors that a late-loaded script causes.
    Returns (registered, created): registered is False when resources cannot be
    managed (YAML mode), created is True the first time the resource is added.
    """
    try:
        from homeassistant.components.lovelace.const import LOVELACE_DATA  # noqa: PLC0415
        from homeassistant.components.lovelace.resources import (  # noqa: PLC0415
            ResourceStorageCollection,
        )

        lovelace = hass.data.get(LOVELACE_DATA)
        resources = getattr(lovelace, "resources", None)
        if not isinstance(resources, ResourceStorageCollection):
            return False, False
        if not resources.loaded:
            await resources.async_load()
        for item in resources.async_items():
            # Older versions registered the cards file directly: migrate that entry.
            if str(item["url"]).split("?")[0] in (LOADER_URL, CARD_URL):
                if item["url"] != url:
                    await resources.async_update_item(
                        item["id"], {"res_type": "module", "url": url}
                    )
                return True, False
        await resources.async_create_item({"res_type": "module", "url": url})
    except Exception:  # noqa: BLE001 - frontend internals differ between versions
        _LOGGER.debug("Could not register the card as a Lovelace resource", exc_info=True)
        return False, False
    return True, True


def _async_notify_reload(hass: HomeAssistant) -> None:
    """Invite the user to reload without cache once, after the first install."""
    if hass.config.language.startswith("fr"):
        title = "Synology SRM Plus : cartes installées"
        message = (
            "Les cartes du tableau de bord viennent d'être ajoutées. Rechargez la "
            "page **sans cache** (Ctrl+Maj+R, ou Cmd+Maj+R sur Mac ; dans "
            "l'application mobile, *Paramètres → Application → Réinitialiser le "
            "cache du frontend*) pour les voir apparaître."
        )
    else:
        title = "Synology SRM Plus: cards installed"
        message = (
            "The dashboard cards have just been added. Reload the page **without "
            "cache** (Ctrl+Shift+R, or Cmd+Shift+R on Mac; in the mobile app, "
            "*Settings → Companion app → Reset frontend cache*) for them to show up."
        )
    persistent_notification.async_create(
        hass, message, title=title, notification_id=f"{DOMAIN}_reload_cards"
    )


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Serve the dashboard cards and make sure the frontend loads them."""
    www = Path(__file__).parent / "www"
    await hass.http.async_register_static_paths(
        [
            StaticPathConfig(CARD_URL, str(www / "synology-srm-card.js"), cache_headers=False),
            StaticPathConfig(LOADER_URL, str(www / "synology-srm-loader.js"), cache_headers=False),
        ]
    )
    # The loader is what the frontend loads; it imports the cards itself.
    url = f"{LOADER_URL}?v={VERSION}"
    registered, created = await _async_register_card_resource(hass, url)
    if not registered:
        add_extra_js_url(hass, url)
    elif created:
        _async_notify_reload(hass)

    running: set[str] = set()

    async def _async_explore(call: ServiceCall) -> None:
        """Run the read-only API exploration in the background (results in the log)."""
        for entry in hass.config_entries.async_loaded_entries(DOMAIN):
            if entry.entry_id in running:
                continue
            running.add(entry.entry_id)

            async def _run(entry=entry) -> None:
                try:
                    await hass.async_add_executor_job(
                        entry.runtime_data.explore, call.data.get("filter")
                    )
                finally:
                    running.discard(entry.entry_id)

            hass.async_create_background_task(_run(), f"{DOMAIN}_explore")

    async def _async_report(call: ServiceCall) -> dict[str, str]:
        """Return a short text report (no names, addresses or MACs) to paste when asking for help."""
        from .diagnostics import async_build_report  # noqa: PLC0415 - avoids an import cycle

        reports = [
            await async_build_report(hass, entry)
            for entry in hass.config_entries.async_loaded_entries(DOMAIN)
        ]
        return {"report": (chr(10) * 2).join(reports)}

    hass.services.async_register(
        DOMAIN, SERVICE_EXPLORE_API, _async_explore, schema=EXPLORE_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_DEBUG_REPORT, _async_report, supports_response=SupportsResponse.ONLY
    )
    return True


def _remove_safe_access_entities(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Delete the Safe Access entities left over from when the option was on."""
    registry = er.async_get(hass)
    prefix = f"{entry.entry_id}_safe_"
    for entity in er.async_entries_for_config_entry(registry, entry.entry_id):
        if entity.unique_id.startswith(prefix):
            registry.async_remove(entity.entity_id)


async def async_setup_entry(hass: HomeAssistant, entry: SrmConfigEntry) -> bool:
    """Set up Synology SRM Plus from a config entry."""
    coordinator = SrmCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    if not entry.options.get(CONF_SAFE_ACCESS, True):
        _remove_safe_access_entities(hass, entry)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: SrmConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
