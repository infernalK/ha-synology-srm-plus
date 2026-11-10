"""Repairs for Synology SRM Plus."""

from __future__ import annotations

from typing import cast

from homeassistant.components.repairs import ConfirmRepairFlow, RepairsFlow
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult

from .certificate import ISSUE_PREFIX
from .const import CONF_CERT_FINGERPRINT


class CertificateChangedFlow(ConfirmRepairFlow):
    """Trust the router's new certificate."""

    def __init__(self, entry_id: str, fingerprint: str) -> None:
        """Initialize."""
        self._entry_id = entry_id
        self._fingerprint = fingerprint

    async def async_step_confirm(
        self, user_input: dict[str, str] | None = None
    ) -> FlowResult:
        """Remember the new certificate, then close the repair."""
        if user_input is not None:
            entry = self.hass.config_entries.async_get_entry(self._entry_id)
            if entry is not None:
                self.hass.config_entries.async_update_entry(
                    entry, data={**entry.data, CONF_CERT_FINGERPRINT: self._fingerprint}
                )
        return await super().async_step_confirm(user_input)


async def async_create_fix_flow(
    hass: HomeAssistant,
    issue_id: str,
    data: dict[str, str | int | float | None] | None,
) -> RepairsFlow:
    """Create the flow that fixes a repair."""
    if issue_id.startswith(ISSUE_PREFIX) and data:
        return CertificateChangedFlow(
            cast(str, data["entry_id"]), cast(str, data["fingerprint"])
        )
    return ConfirmRepairFlow()
