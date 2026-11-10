"""Repairs for router settings that weaken it (read only: nothing is changed for you).

A repair stays while its setting is unknown (a failed read must not clear it) and goes once
the setting is safe. You can ignore one in Home Assistant, and it stays ignored.
"""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import issue_registry as ir

from .changes import risks
from .const import DOMAIN
from .coordinator import SrmCoordinator


@callback
def async_update_risk_repairs(
    hass: HomeAssistant, entry: ConfigEntry, coordinator: SrmCoordinator
) -> None:
    """Raise or clear the repairs from the latest router data."""
    for key, risky in risks(coordinator.data or {}).items():
        issue_id = f"{key}_{entry.entry_id}"
        if risky:
            ir.async_create_issue(
                hass,
                DOMAIN,
                issue_id,
                is_fixable=False,
                severity=ir.IssueSeverity.WARNING,
                translation_key=key,
                translation_placeholders={"router": entry.title},
            )
        elif risky is False:
            ir.async_delete_issue(hass, DOMAIN, issue_id)


@callback
def async_watch_risks(
    hass: HomeAssistant, entry: ConfigEntry, coordinator: SrmCoordinator
) -> None:
    """Check after every update until the entry unloads."""
    async_update_risk_repairs(hass, entry, coordinator)
    entry.async_on_unload(
        coordinator.async_add_listener(
            lambda: async_update_risk_repairs(hass, entry, coordinator)
        )
    )
