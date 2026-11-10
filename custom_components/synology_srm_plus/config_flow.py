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
    CONF_SAFE_ACCESS,
    CONF_TRACK_ALL,
    CONF_TRACK_CLIENTS,
    CONF_TRACKED_CLIENTS,
    DEFAULT_PORT,
    DEFAULT_SSL,
    DEFAULT_USERNAME,
    DEFAULT_VERIFY_SSL,
    DOMAIN,
)
from .coordinator import build_client, logout_client, safe_error

_LOGGER = logging.getLogger(__name__)


def _router_model(client: Any) -> str | None:
    """Return the model of the main router node, or None when SRM does not say."""
    try:
        info = client.mesh.get_system_info()
    except Exception:  # noqa: BLE001 - the name is a nicety, never a reason to fail
        return None
    nodes = info.get("nodes") if isinstance(info, dict) else None
    for node in nodes if isinstance(nodes, list) else []:
        if isinstance(node, dict) and node.get("node_id") == 0 and node.get("model"):
            return str(node["model"])
    return None


class SrmOptionsFlow(OptionsFlowWithReload):
    """Handle the options: presence entities and Safe Access."""

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
                vol.Required(CONF_SAFE_ACCESS, default=True): bool,
            }
        )
        suggested = {
            CONF_TRACK_ALL: options.get(
                CONF_TRACK_ALL, options.get(CONF_TRACK_CLIENTS, False)
            ),
            CONF_TRACKED_CLIENTS: options.get(CONF_TRACKED_CLIENTS, []),
            CONF_SAFE_ACCESS: options.get(CONF_SAFE_ACCESS, True),
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

    _model: str | None = None

    async def _async_test(self, data: dict[str, Any]) -> str | None:
        """Try to log in; return an error key, or None when it works.

        On success the router's model is kept in ``self._model`` (None when unknown).
        """
        try:

            def _probe() -> str | None:
                client = build_client(data)
                try:
                    client.core.get_system_utilization()
                    return _router_model(client)
                finally:
                    logout_client(client)

            self._model = await self.hass.async_add_executor_job(_probe)
        except SynologyException:
            return "invalid_auth"
        except Exception as err:  # noqa: BLE001
            # No traceback: the error text can quote the URL, which holds the password.
            _LOGGER.warning("Unable to connect to SRM: %s", safe_error(err))
            return "cannot_connect"
        return None

    def _new_title(self, host: str) -> str:
        """Name a new entry (and so its device) after the router's model, not its address."""
        model = self._model
        if not model:
            return host
        taken = {e.title for e in self._async_current_entries()}
        return model if model not in taken else f"{model} ({host})"

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Change the connection settings without removing the entry."""
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            data = {**entry.data, **user_input}
            if not user_input.get(CONF_PASSWORD):
                data[CONF_PASSWORD] = entry.data[CONF_PASSWORD]
            if data[CONF_HOST] != entry.data[CONF_HOST]:
                self._async_abort_entries_match({CONF_HOST: data[CONF_HOST]})
            if not (error := await self._async_test(data)):
                # An entry still named after its address follows it; a model name stays.
                title = (
                    data[CONF_HOST]
                    if entry.title == entry.data[CONF_HOST]
                    else entry.title
                )
                return self.async_update_reload_and_abort(
                    entry, title=title, data=data
                )
            errors["base"] = error

        current = entry.data
        schema = vol.Schema(
            {
                vol.Required(CONF_HOST, default=current[CONF_HOST]): str,
                vol.Required(CONF_USERNAME, default=current[CONF_USERNAME]): str,
                vol.Optional(CONF_PASSWORD): str,
                vol.Required(CONF_PORT, default=current[CONF_PORT]): int,
                vol.Required(CONF_SSL, default=current[CONF_SSL]): bool,
                vol.Required(CONF_VERIFY_SSL, default=current[CONF_VERIFY_SSL]): bool,
            }
        )
        return self.async_show_form(
            step_id="reconfigure", data_schema=schema, errors=errors
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the user step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            self._async_abort_entries_match({CONF_HOST: user_input[CONF_HOST]})
            if not (error := await self._async_test(user_input)):
                return self.async_create_entry(
                    title=self._new_title(user_input[CONF_HOST]), data=user_input
                )
            errors["base"] = error

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
