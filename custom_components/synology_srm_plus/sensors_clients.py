"""Client and Wi-Fi sensors: who is connected, per band and per Wi-Fi network."""

from __future__ import annotations

import re
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    EntityCategory,
    UnitOfDataRate,
)

from .clients import GROUP_OFFLINE, GROUP_WIRED, group_label
from .const import DOMAIN
from .helpers import (
    SrmSensorDescription,
    _clients,
    _dig,
    _find,
    _network_clients,
    _num,
    _wifi_network_names,
)


def _sum_network_rate(d: dict[str, Any], field: str, network: str) -> float:
    return sum(
        c[field]
        for c in _network_clients(d, network)
        if isinstance(c.get(field), (int, float)) and not isinstance(c.get(field), bool)
    )


def _network_attrs(d: dict[str, Any], network: str) -> dict[str, Any]:
    clients = _network_clients(d, network)
    # No "integration" nor client list: the clients card takes sensors that carry both
    # for connection groups and would list these clients a second time.
    return {
        "network": network,
        "bands": sorted({c["band"] for c in clients if c.get("band")}),
        "ssids": sorted({c["ssid"] for c in clients if c.get("ssid")}),
        "download": _sum_network_rate(d, "download", network),
        "upload": _sum_network_rate(d, "upload", network),
        "by_band": _network_by_band(clients),
    }


def _network_by_band(clients: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Clients and rates of one Wi-Fi network, split per band (2.4G, 5G...)."""
    out: dict[str, dict[str, Any]] = {}
    for c in clients:
        band = c.get("band")
        if not band:
            continue
        item = out.setdefault(str(band), {"clients": 0, "download": 0, "upload": 0})
        item["clients"] += 1
        for field in ("download", "upload"):
            value = c.get(field)
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                item[field] += value
    return dict(sorted(out.items()))


def _sum_rate(d: dict[str, Any], field: str, group: str | None) -> float:
    return sum(
        c[field]
        for c in _clients(d, group)
        if isinstance(c.get(field), (int, float)) and not isinstance(c.get(field), bool)
    )


def _avg_signal(d: dict[str, Any], group: str) -> float | None:
    signals = [
        c["signal"]
        for c in _clients(d, group)
        if isinstance(c.get("signal"), (int, float))
    ]
    return round(sum(signals) / len(signals), 1) if signals else None


def _radio(d: dict[str, Any], band: str) -> dict[str, Any]:
    return _find(_dig(d.get("wifi_radio"), "status_list"), radio_type=band) or {}


def _group_attrs(d: dict[str, Any], group: str) -> dict[str, Any]:
    """Attributes of a connection group: who is attached, and how."""
    clients = _clients(d, group)
    attrs: dict[str, Any] = {"integration": DOMAIN, "group": group, "clients": clients}
    if group != GROUP_WIRED:
        radio = _radio(d, group)
        attrs["channel"] = radio.get("channel")
        attrs["bssid"] = radio.get("bssid")
        attrs["ssids"] = sorted({c["ssid"] for c in clients if c.get("ssid")})
        attrs["average_signal"] = _avg_signal(d, group)
    attrs["download"] = _sum_rate(d, "download", group)
    attrs["upload"] = _sum_rate(d, "upload", group)
    return {k: v for k, v in attrs.items() if v is not None}


def _wifi_descriptions(data: dict[str, Any]) -> list[SrmSensorDescription]:
    """Channel and average signal per Wi-Fi band."""
    out: list[SrmSensorDescription] = []
    bands = {
        item["radio_type"]
        for item in _dig(data.get("wifi_radio"), "status_list") or []
        if isinstance(item, dict) and item.get("radio_type")
    } | {c["group"] for c in _clients(data) if c.get("group") != GROUP_WIRED}
    for band in sorted(bands):
        if _radio(data, band):
            out.append(
                SrmSensorDescription(
                    key=f"wifi_channel_{band}",
                    translation_key="wifi_channel",
                    placeholders={"band": band},
                    entity_category=EntityCategory.DIAGNOSTIC,
                    value_fn=lambda d, b=band: _num(_radio(d, b).get("channel")),
                    attrs_fn=lambda d, b=band: {
                        "bssid": _radio(d, b).get("bssid"),
                        **{
                            k: v
                            for k, v in (
                                _find(
                                    _dig(d.get("radio_setting"), "radio_list"),
                                    radio_type=b,
                                )
                                or {}
                            ).items()
                            if k in ("channel_width", "transmit_power", "wireless_mode")
                        },
                    },
                )
            )
        out.append(
            SrmSensorDescription(
                key=f"wifi_signal_{band}",
                translation_key="wifi_signal",
                placeholders={"band": band},
                native_unit_of_measurement=PERCENTAGE,
                state_class=SensorStateClass.MEASUREMENT,
                entity_category=EntityCategory.DIAGNOSTIC,
                value_fn=lambda d, b=band: _avg_signal(d, b),
            )
        )
    return out


def _client_descriptions(data: dict[str, Any]) -> list[SrmSensorDescription]:
    """Client counts (with the client list as attributes) and traffic, per group."""
    if not isinstance(data.get("client_list"), list):
        return []
    groups = sorted({c["group"] for c in _clients(data)})
    out = [
        SrmSensorDescription(
            key="clients_online",
            translation_key="clients_online",
            state_class=SensorStateClass.MEASUREMENT,
            value_fn=lambda d: len(_clients(d)),
        )
    ]
    for group in groups:
        out.append(
            SrmSensorDescription(
                key=f"clients_group_{group}",
                translation_key="clients_group",
                placeholders={"group": group_label(group)},
                state_class=SensorStateClass.MEASUREMENT,
                value_fn=lambda d, g=group: len(_clients(d, g)),
                attrs_fn=lambda d, g=group: _group_attrs(d, g),
            )
        )
    for network in _wifi_network_names(data):
        slug = re.sub(r"\W+", "_", network).strip("_").lower() or "network"
        out.append(
            SrmSensorDescription(
                key=f"clients_network_{slug}",
                translation_key="clients_network",
                placeholders={"network": network},
                state_class=SensorStateClass.MEASUREMENT,
                value_fn=lambda d, n=network: len(_network_clients(d, n)),
                attrs_fn=lambda d, n=network: _network_attrs(d, n),
            )
        )
        for field, tkey in (("download", "network_rx"), ("upload", "network_tx")):
            out.append(
                SrmSensorDescription(
                    key=f"{tkey}_{slug}",
                    translation_key=tkey,
                    placeholders={"network": network},
                    device_class=SensorDeviceClass.DATA_RATE,
                    native_unit_of_measurement=UnitOfDataRate.BYTES_PER_SECOND,
                    suggested_unit_of_measurement=UnitOfDataRate.MEGABITS_PER_SECOND,
                    suggested_display_precision=1,
                    state_class=SensorStateClass.MEASUREMENT,
                    value_fn=lambda d, f=field, n=network: _sum_network_rate(d, f, n),
                    attrs_fn=lambda d, n=network: {"network": n},
                )
            )
    if isinstance(data.get("offline_list"), list):
        out.append(
            SrmSensorDescription(
                key="clients_offline",
                translation_key="clients_offline",
                value_fn=lambda d: len(d.get("offline_list") or []),
                attrs_fn=lambda d: {
                    "integration": DOMAIN,
                    "group": GROUP_OFFLINE,
                    "clients": d.get("offline_list") or [],
                },
            )
        )
    for group in (None, *groups):
        label = "Total" if group is None else group
        for field, tkey in (("download", "client_rx"), ("upload", "client_tx")):
            out.append(
                SrmSensorDescription(
                    key=f"{tkey}_{label}",
                    translation_key=tkey,
                    placeholders={"group": label},
                    device_class=SensorDeviceClass.DATA_RATE,
                    native_unit_of_measurement=UnitOfDataRate.BYTES_PER_SECOND,
                    suggested_unit_of_measurement=UnitOfDataRate.MEGABITS_PER_SECOND,
                    suggested_display_precision=1,
                    state_class=SensorStateClass.MEASUREMENT,
                    value_fn=lambda d, f=field, g=group: _sum_rate(d, f, g),
                )
            )
    return out
