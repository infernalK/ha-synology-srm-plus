"""Set the integration up in a real Home Assistant (the router replaced by sample data)."""

from __future__ import annotations

import copy
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er, issue_registry as ir
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.synology_srm_plus import certificate, config_flow, repairs
from custom_components.synology_srm_plus.const import CONF_CERT_FINGERPRINT, DOMAIN


async def _setup(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED


def _entity(hass: HomeAssistant, entry: MockConfigEntry, domain: str, key: str) -> str | None:
    suffix = f"event_{key}" if domain == "event" else key
    return er.async_get(hass).async_get_entity_id(domain, DOMAIN, f"{entry.entry_id}_{suffix}")


async def _refresh(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    await entry.runtime_data.async_refresh()
    await hass.async_block_till_done()


async def test_setup_creates_the_new_entities(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    """Pool usage is on; the lists of names and addresses start disabled."""
    await _setup(hass, entry)
    registry = er.async_get(hass)

    pool = _entity(hass, entry, "sensor", "dhcp_pool_lbr0")
    assert pool and hass.states.get(pool).state == "3.0"
    for key in ("firewall_rules", "dhcp_leases", "dhcp_reservations", "mac_filter_devices", "blocked_devices"):
        entity_id = _entity(hass, entry, "sensor", key)
        assert entity_id, key
        assert registry.async_get(entity_id).disabled_by is er.RegistryEntryDisabler.INTEGRATION, key
        assert hass.states.get(entity_id) is None, key
    assert _entity(hass, entry, "event", "new_client")
    assert _entity(hass, entry, "event", "router_changes")


async def test_events_fire_for_new_clients_and_firewall_changes(
    hass: HomeAssistant, entry: MockConfigEntry, router: dict[str, Any]
) -> None:
    """Nothing fires for what is there at start-up; changes afterwards do."""
    await _setup(hass, entry)
    new_client = _entity(hass, entry, "event", "new_client")
    changes = _entity(hass, entry, "event", "router_changes")
    assert hass.states.get(new_client).state == "unknown"
    assert hass.states.get(changes).state == "unknown"

    data = router["data"]
    data["client_list"].append(
        {"name": "New phone", "mac": "da:11:22:33:44:55", "ip": "192.0.2.88", "connection": "wifi", "band": "5G"}
    )
    data["firewall_rules"]["rules"].append({"name": "Open SSH", "enabled": True, "action": "allow"})
    await _refresh(hass, entry)

    state = hass.states.get(new_client)
    assert state.attributes["event_type"] == "new_client" and state.attributes["name"] == "New phone"
    assert state.attributes["private_mac"] is True
    state = hass.states.get(changes)
    assert state.attributes["event_type"] == "firewall_rules_changed" and state.attributes["added"] == ["Open SSH"]

    # the same data again: no second event
    before = hass.states.get(new_client).state
    await _refresh(hass, entry)
    assert hass.states.get(new_client).state == before


async def test_a_change_made_while_home_assistant_was_off_is_reported(
    hass: HomeAssistant, entry: MockConfigEntry, router: dict[str, Any], hass_storage: dict[str, Any]
) -> None:
    """The last state is stored, so the first update after a restart reports what changed."""
    old = copy.deepcopy(router["data"])
    from custom_components.synology_srm_plus.changes import detect  # noqa: PLC0415

    state, _ = detect(None, old)
    hass_storage[f"{DOMAIN}_{entry.entry_id}_changes"] = {"version": 1, "key": f"{DOMAIN}_{entry.entry_id}_changes", "data": state}
    router["data"]["firewall_rules"]["default_policy"]["ipv4_wan_to_lan"] = "allow"
    await _setup(hass, entry)
    changes = _entity(hass, entry, "event", "router_changes")
    assert hass.states.get(changes).attributes["event_type"] == "firewall_policy_changed"


async def test_risky_settings_raise_and_clear_repairs(
    hass: HomeAssistant, entry: MockConfigEntry, router: dict[str, Any]
) -> None:
    """A repair stays while the setting is unknown, and goes once it is safe."""
    registry = ir.async_get(hass)
    router["data"]["autoblock_settings"]["enable"] = False
    router["data"]["firewall_rules"]["default_policy"]["ipv4_wan_to_lan"] = "allow"
    await _setup(hass, entry)
    assert registry.async_get_issue(DOMAIN, f"auto_block_off_{entry.entry_id}")
    assert registry.async_get_issue(DOMAIN, f"firewall_open_{entry.entry_id}")

    router["data"]["autoblock_settings"] = None  # a failed read: unknown, not fixed
    await _refresh(hass, entry)
    assert registry.async_get_issue(DOMAIN, f"auto_block_off_{entry.entry_id}")

    router["data"]["autoblock_settings"] = {"enable": True}
    router["data"]["firewall_rules"]["default_policy"]["ipv4_wan_to_lan"] = "deny"
    await _refresh(hass, entry)
    assert registry.async_get_issue(DOMAIN, f"auto_block_off_{entry.entry_id}") is None
    assert registry.async_get_issue(DOMAIN, f"firewall_open_{entry.entry_id}") is None


async def test_remote_administration_is_not_a_repair(
    hass: HomeAssistant, entry: MockConfigEntry, router: dict[str, Any]
) -> None:
    """Letting SRM itself be reached from the internet is a choice: no repair for it."""
    router["data"]["firewall_rules"]["default_policy"]["ipv4_wan_to_srm"] = "allow"
    await _setup(hass, entry)
    assert not [i for i in ir.async_get(hass).issues.values() if i.domain == DOMAIN]


async def test_certificate_is_remembered_then_watched(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    """First sight is remembered; a different certificate later raises a fixable repair."""
    await _setup(hass, entry)
    assert entry.data[CONF_CERT_FINGERPRINT] == "aa" * 32
    registry = ir.async_get(hass)
    issue_id = f"{certificate.ISSUE_PREFIX}{entry.entry_id}"
    assert registry.async_get_issue(DOMAIN, issue_id) is None

    with patch.object(certificate, "fetch_fingerprint", return_value="bb" * 32):
        await certificate.async_check_certificate(hass, entry)
    issue = registry.async_get_issue(DOMAIN, issue_id)
    assert issue and issue.is_fixable and issue.data["fingerprint"] == "bb" * 32

    flow = await repairs.async_create_fix_flow(hass, issue_id, issue.data)
    flow.hass = hass
    result = await flow.async_step_confirm({})
    assert result["type"] == "create_entry"
    assert entry.data[CONF_CERT_FINGERPRINT] == "bb" * 32

    with patch.object(certificate, "fetch_fingerprint", return_value="bb" * 32):
        await certificate.async_check_certificate(hass, entry)
    assert registry.async_get_issue(DOMAIN, issue_id) is None


async def test_certificate_is_not_watched_when_verified_or_unreachable(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    """A verified connection needs no watching; an unreachable router raises nothing."""
    await _setup(hass, entry)
    registry = ir.async_get(hass)
    with patch.object(certificate, "fetch_fingerprint", return_value=None):
        await certificate.async_check_certificate(hass, entry)
    assert not [i for i in registry.issues.values() if i.domain == DOMAIN]

    hass.config_entries.async_update_entry(entry, data={**entry.data, "verify_ssl": True})
    with patch.object(certificate, "fetch_fingerprint", return_value="cc" * 32) as fetch:
        await certificate.async_check_certificate(hass, entry)
    fetch.assert_not_called()


def _flow_client(model: str | None = "RT2600ac") -> MagicMock:
    client = MagicMock()
    nodes = [{"node_id": 0, "model": model}] if model else []
    client.mesh.get_system_info.return_value = {"nodes": nodes}
    return client


async def _start_flow(hass: HomeAssistant, host: str, model: str | None = "RT2600ac") -> dict[str, Any]:
    user_input = {"host": host, "username": "admin", "password": "x", "port": 8001, "ssl": True, "verify_ssl": False}
    with (
        patch.object(config_flow, "build_client", return_value=_flow_client(model)),
        patch.object(config_flow, "logout_client"),
        patch.object(config_flow, "fetch_fingerprint", return_value="dd" * 32),
        patch("custom_components.synology_srm_plus.async_setup_entry", AsyncMock(return_value=True)),
    ):
        result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
        return await hass.config_entries.flow.async_configure(result["flow_id"], user_input)


async def test_new_entries_are_named_after_the_model(hass: HomeAssistant) -> None:
    """Not after the IP address; a second router of the same model gets its host added."""
    first = await _start_flow(hass, "192.0.2.1")
    assert first["type"] == "create_entry"
    assert first["title"] == "RT2600ac"
    assert first["data"][CONF_CERT_FINGERPRINT] == "dd" * 32
    second = await _start_flow(hass, "192.0.2.2")
    assert second["title"] == "RT2600ac (192.0.2.2)"


async def test_unknown_model_falls_back_to_the_host(hass: HomeAssistant) -> None:
    """A router that does not say its model keeps the address as its name."""
    result = await _start_flow(hass, "192.0.2.9", model=None)
    assert result["title"] == "192.0.2.9"
