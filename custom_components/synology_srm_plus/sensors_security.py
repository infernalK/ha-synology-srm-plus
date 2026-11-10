"""Security sensors: threat events, admin sign-ins, blocked addresses and devices, MAC filters."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from homeassistant.components.sensor import (
    SensorStateClass,
)
from homeassistant.const import (
    EntityCategory,
)

from .helpers import SrmSensorDescription, _dig, _num


def _parse_time(value: Any) -> datetime | None:
    try:
        return datetime.strptime(str(value), "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None


def _threat_events(d: dict[str, Any], hours: int | None) -> int | None:
    trends = _dig(d.get("tps_trends"), "trends")
    if not isinstance(trends, list):
        return None
    end = _parse_time(_dig(d.get("tps_trends"), "end"))
    total = 0
    for bucket in trends:
        if not isinstance(bucket, dict):
            continue
        if hours is not None:
            bucket_end = _parse_time(bucket.get("end"))
            if (
                end is None
                or bucket_end is None
                or bucket_end <= end - timedelta(hours=hours)
            ):
                continue
        total += int(bucket.get("total") or 0)
    return total


def _threat_levels(d: dict[str, Any]) -> dict[str, Any]:
    trends = _dig(d.get("tps_trends"), "trends")
    if not isinstance(trends, list):
        return {}
    levels = {
        k: sum(int(b.get(k) or 0) for b in trends if isinstance(b, dict))
        for k in ("high", "medium", "low")
    }
    return {
        **levels,
        "since": _dig(d.get("tps_trends"), "begin"),
        "until": _dig(d.get("tps_trends"), "end"),
    }


def _sessions(d: dict[str, Any]) -> list[dict[str, Any]]:
    """Sign-in records of the admin interface (SRM keeps a history, not the open sessions).

    Entries dated 1970 are unset records: they are dropped.
    """
    items = _dig(d.get("admin_sessions"), "items")
    if not isinstance(items, list):
        return []
    return [
        i
        for i in items
        if isinstance(i, dict) and not str(i.get("time", "")).startswith("1970")
    ]


def _blocked_clients(d: dict[str, Any]) -> list[dict[str, Any]]:
    """Clients (online or not) that the router blocks."""
    everyone = (d.get("client_list") or []) + (d.get("offline_list") or [])
    return [c for c in everyone if c.get("blocked") is True]


def _security_descriptions(data: dict[str, Any]) -> list[SrmSensorDescription]:
    """Threat events, new devices, admin sessions, blocked IPs, forwarded ports."""
    out: list[SrmSensorDescription] = []
    if isinstance(_dig(data.get("tps_trends"), "trends"), list):
        out.append(
            SrmSensorDescription(
                key="threat_events_24h",
                translation_key="threat_events_24h",
                state_class=SensorStateClass.MEASUREMENT,
                value_fn=lambda d: _threat_events(d, 24),
            )
        )
        out.append(
            SrmSensorDescription(
                key="threat_events_7d",
                translation_key="threat_events_7d",
                state_class=SensorStateClass.MEASUREMENT,
                value_fn=lambda d: _threat_events(d, None),
                attrs_fn=_threat_levels,
            )
        )
    if isinstance(_dig(data.get("new_devices"), "new_devices"), list):
        out.append(
            SrmSensorDescription(
                key="new_devices",
                translation_key="new_devices",
                state_class=SensorStateClass.MEASUREMENT,
                value_fn=lambda d: len(_dig(d.get("new_devices"), "new_devices") or []),
                attrs_fn=lambda d: {
                    "devices": _dig(d.get("new_devices"), "new_devices") or []
                },
            )
        )
    if isinstance(_dig(data.get("admin_sessions"), "items"), list):
        out.append(
            SrmSensorDescription(
                key="admin_sessions",
                translation_key="admin_sessions",
                state_class=SensorStateClass.MEASUREMENT,
                value_fn=lambda d: len(_sessions(d)),
                attrs_fn=lambda d: {
                    "sessions": [
                        {k: s.get(k) for k in ("who", "from", "type", "time", "descr")}
                        for s in _sessions(d)
                    ]
                },
            )
        )
    if _num(_dig(data.get("autoblock"), "total")) is not None:
        out.append(
            SrmSensorDescription(
                key="blocked_ips",
                translation_key="blocked_ips",
                state_class=SensorStateClass.MEASUREMENT,
                value_fn=lambda d: _num(_dig(d.get("autoblock"), "total")),
                attrs_fn=lambda d: {
                    k: v
                    for k, v in {
                        "auto_block_enabled": _dig(
                            d.get("autoblock_settings"), "enable"
                        ),
                        "failed_attempts": _dig(
                            d.get("autoblock_settings"), "attempts"
                        ),
                        "within_minutes": _dig(
                            d.get("autoblock_settings"), "within_mins"
                        ),
                        "expire_days": _dig(d.get("autoblock_settings"), "expire_day"),
                        "addresses": _dig(d.get("autoblock"), "addresses") or None,
                    }.items()
                    if v is not None
                },
            )
        )
    if isinstance(_dig(data.get("macfilter_profiles"), "profiles"), list):
        out.append(
            SrmSensorDescription(
                key="mac_filter_profiles",
                translation_key="mac_filter_profiles",
                # Lists of names, MAC and IP addresses: off on new installs (enable them in the
                # entity settings). Existing installs keep their entities as they are.
                entity_registry_enabled_default=False,
                state_class=SensorStateClass.MEASUREMENT,
                entity_category=EntityCategory.DIAGNOSTIC,
                value_fn=lambda d: len(
                    _dig(d.get("macfilter_profiles"), "profiles") or []
                ),
                attrs_fn=lambda d: {
                    "profiles": [
                        {k: v for k, v in p.items() if k != "password"}
                        for p in _dig(d.get("macfilter_profiles"), "profiles") or []
                        if isinstance(p, dict)
                    ]
                },
            )
        )
    if isinstance(_dig(data.get("macfilter_devices"), "devices"), list):
        out.append(
            SrmSensorDescription(
                key="mac_filter_devices",
                translation_key="mac_filter_devices",
                # Lists of names, MAC and IP addresses: off on new installs (enable them in the
                # entity settings). Existing installs keep their entities as they are.
                entity_registry_enabled_default=False,
                state_class=SensorStateClass.MEASUREMENT,
                entity_category=EntityCategory.DIAGNOSTIC,
                value_fn=lambda d: len(
                    _dig(d.get("macfilter_devices"), "devices") or []
                ),
                attrs_fn=lambda d: {
                    "devices": [
                        {
                            "name": x.get("name"),
                            "mac": str(x.get("mac_addr", "")).lower(),
                        }
                        for x in _dig(d.get("macfilter_devices"), "devices") or []
                        if isinstance(x, dict)
                    ],
                    "broadcast_storm_prevention": _dig(
                        d.get("macfilter_devices"), "enable_prevent_broadcast"
                    ),
                    "max_broadcast_packets_per_second": _dig(
                        d.get("macfilter_devices"), "maximum_broadcast"
                    ),
                },
            )
        )
    if isinstance(data.get("client_list"), list):
        out.append(
            SrmSensorDescription(
                key="blocked_devices",
                translation_key="blocked_devices",
                # Lists of names, MAC and IP addresses: off on new installs (enable them in the
                # entity settings). Existing installs keep their entities as they are.
                entity_registry_enabled_default=False,
                state_class=SensorStateClass.MEASUREMENT,
                value_fn=lambda d: len(_blocked_clients(d)),
                attrs_fn=lambda d: {
                    "devices": [
                        {k: c.get(k) for k in ("name", "mac", "ip") if c.get(k)}
                        for c in _blocked_clients(d)
                    ]
                },
            )
        )
    if isinstance(_dig(data.get("port_forward"), "rules"), list):
        out.append(
            SrmSensorDescription(
                key="port_forward_rules",
                translation_key="port_forward_rules",
                state_class=SensorStateClass.MEASUREMENT,
                entity_category=EntityCategory.DIAGNOSTIC,
                value_fn=lambda d: len(_dig(d.get("port_forward"), "rules") or []),
            )
        )
    return out
