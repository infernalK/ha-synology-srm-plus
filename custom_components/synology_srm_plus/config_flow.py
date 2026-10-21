"""Config flow for Synology SRM Plus."""

from __future__ import annotations

import logging
from typing import Any

from synology_srm.http import SynologyException
import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlowWithReload,
)
from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_SSL,
    CONF_USERNAME,
    CONF_VERIFY_SSL,
)
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .const import (
    CONF_TRACK_ALL,
    CONF_TRACK_CLIENTS,
    CONF_TRACKED_CLIENTS,
    DEFAULT_PORT,
    DEFAULT_SSL,
    DEFAULT_USERNAME,
    DEFAULT_VERIFY_SSL,
    DOMAIN,
)
from .coordinator import build_client

_LOGGER = logging.getLogger(__name__)


class SrmOptionsFlow(OptionsFlowWithReload):
    """Handle the options: which clients get a presence entity."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        options = self.config_entry.options
        coordinator = getattr(self.config_entry, "runtime_data", None)
        data = coordinator.data if coordinator else {}
        clients = (data.get("client_list") or []) + (data.get("offline_list") or [])
        choices = [
            SelectOptionDict(
                value=c["mac"], label=f"{c['name']} ({c.get('ip') or c['mac']})"
            )
            for c in sorted(clients, key=lambda c: str(c["name"]).lower())
            if c.get("mac")
        ]
        known = {c["value"] for c in choices}
        choices += [
            SelectOptionDict(value=mac, label=mac)
            for mac in options.get(CONF_TRACKED_CLIENTS, [])
            if mac not in known
        ]
        schema = vol.Schema(
            {
                vol.Required(CONF_TRACK_ALL, default=False): bool,
                vol.Optional(CONF_TRACKED_CLIENTS, default=[]): SelectSelector(
                    SelectSelectorConfig(
                        options=choices,
                        multiple=True,
                        mode=SelectSelectorMode.DROPDOWN,
                    )
                ),
            }
        )
        suggested = {
            CONF_TRACK_ALL: options.get(
                CONF_TRACK_ALL, options.get(CONF_TRACK_CLIENTS, False)
            ),
            CONF_TRACKED_CLIENTS: options.get(CONF_TRACKED_CLIENTS, []),
        }
        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(schema, suggested),
        )


class SrmConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> SrmOptionsFlow:
        """Return the options flow."""
        return SrmOptionsFlow()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the user step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            self._async_abort_entries_match({CONF_HOST: user_input[CONF_HOST]})
            try:
                await self.hass.async_add_executor_job(
                    lambda: build_client(user_input).core.get_system_utilization()
                )
            except SynologyException:
                errors["base"] = "invalid_auth"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Unable to connect to SRM")
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(
                    title=user_input[CONF_HOST], data=user_input
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_HOST): str,
                vol.Required(CONF_USERNAME, default=DEFAULT_USERNAME): str,
                vol.Required(CONF_PASSWORD): str,
                vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
                vol.Required(CONF_SSL, default=DEFAULT_SSL): bool,
                vol.Required(CONF_VERIFY_SSL, default=DEFAULT_VERIFY_SSL): bool,
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)
