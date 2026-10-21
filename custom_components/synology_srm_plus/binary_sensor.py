"""Binary sensors for Synology SRM Plus."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import ipaddress
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import SrmConfigEntry
from .const import DOMAIN
from .coordinator import SrmCoordinator
from .sensor import (
    _dig,
    _find,
    _nodes,
    _sessions,
    port_label,
    safe_profiles,
    safe_schedule,
)


@dataclass(frozen=True, kw_only=True)
class SrmBinaryDescription(BinarySensorEntityDescription):
    """Binary sensor description with a function over the coordinator data."""

    value_fn: Callable[[dict[str, Any]], bool | None]
    placeholders: dict[str, str] | None = None
    attrs_fn: Callable[[dict[str, Any]], dict[str, Any] | None] | None = None


def _is_public(address: str) -> bool:
    try:
        return ipaddress.ip_address(address.split("%")[0]).is_global
    except ValueError:
        return False


def _external_session(d: dict[str, Any]) -> bool | None:
    if not isinstance(_dig(d.get("admin_sessions"), "items"), list):
        return None
    return any(_is_public(str(s.get("from", ""))) for s in _sessions(d))


def _port_link(d: dict[str, Any], node_id: Any, port: str) -> bool | None:
    node = _find(_nodes(d, "eth_ports"), node_id=node_id) or {}
    info = _find(node.get("eth_port_info"), port=port)
    return None if info is None else bool(info.get("has_link"))


def _block_attrs(d: dict[str, Any], pid: Any) -> dict[str, Any]:
    nxt = safe_schedule(d, pid).get("blocktime_next")
    begin = nxt.get("begin_time") if isinstance(nxt, dict) else None
    return {"next_block_start": begin} if begin else {}


def _descriptions(data: dict[str, Any]) -> list[SrmBinaryDescription]:
    out: list[SrmBinaryDescription] = []
    if isinstance(data.get("tps_sensor"), dict):
        out.append(
            SrmBinaryDescription(
                key="threat_protection",
                translation_key="threat_protection",
                value_fn=lambda d: bool(
                    _dig(d.get("tps_sensor"), "enable_sensor")
                    and _dig(d.get("tps_sensor"), "enable_prevention")
                ),
                attrs_fn=lambda d: {
                    "engine": _dig(d.get("tps_sensor"), "status"),
                    "mode": _dig(d.get("tps_sensor"), "network_security_mode"),
                },
            )
        )
    if isinstance(data.get("allow_wan"), dict):
        out.append(
            SrmBinaryDescription(
                key="srm_exposed_wan",
                translation_key="srm_exposed_wan",
                device_class=BinarySensorDeviceClass.PROBLEM,
                value_fn=lambda d: bool(_dig(d.get("allow_wan"), "enable")),
            )
        )
    if isinstance(_dig(data.get("admin_sessions"), "items"), list):
        out.append(
            SrmBinaryDescription(
                key="external_admin_session",
                translation_key="external_admin_session",
                device_class=BinarySensorDeviceClass.PROBLEM,
                value_fn=_external_session,
            )
        )
    for node in _nodes(data, "eth_ports"):
        nid = node.get("node_id")
        for port in node.get("eth_port_info") or []:
            name = port.get("port")
            if name:
                out.append(
                    SrmBinaryDescription(
                        key=f"port_link_{nid}_{name}",
                        translation_key="port_link",
                        placeholders={"node": str(nid), "port": port_label(name)},
                        device_class=BinarySensorDeviceClass.CONNECTIVITY,
                        entity_category=EntityCategory.DIAGNOSTIC,
                        value_fn=lambda d, n=nid, p=name: _port_link(d, n, p),
                    )
                )
    for profile in safe_profiles(data):
        pid, name = profile.get("profile_id"), profile.get("name")
        if pid is None or not name:
            continue
        out.append(
            SrmBinaryDescription(
                key=f"safe_blocked_{pid}",
                translation_key="safe_blocked",
                placeholders={"profile": str(name)},
                value_fn=lambda d, p=pid: bool(safe_schedule(d, p).get("blocktime_current")),
                attrs_fn=lambda d, p=pid: _block_attrs(d, p),
            )
        )
    return out


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SrmConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up binary sensors."""
    coordinator = entry.runtime_data
    async_add_entities(
        SrmBinarySensor(coordinator, desc) for desc in _descriptions(coordinator.data)
    )


class SrmBinarySensor(CoordinatorEntity[SrmCoordinator], BinarySensorEntity):
    """A binary sensor reading from the shared SRM coordinator."""

    _attr_has_entity_name = True
    entity_description: SrmBinaryDescription

    def __init__(self, coordinator: SrmCoordinator, description: SrmBinaryDescription) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self.entity_description = description
        entry = coordinator.config_entry
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_translation_placeholders = description.placeholders or {}
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, entry.entry_id)})

    @property
    def is_on(self) -> bool | None:
        """Return the state."""
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return the identifying placeholders and the description's attributes."""
        attrs: dict[str, Any] = dict(self.entity_description.placeholders or {})
        if self.entity_description.attrs_fn:
            attrs.update(self.entity_description.attrs_fn(self.coordinator.data) or {})
        return attrs or None
