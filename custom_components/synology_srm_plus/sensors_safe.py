"""Safe Access (parental control) sensors."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.const import (
    EntityCategory,
    UnitOfTime,
)

from .helpers import SrmSensorDescription, _dig, _find, _num


def safe_profiles(d: dict[str, Any]) -> list[dict[str, Any]]:
    """Return the Safe Access (parental control) profiles."""
    profiles = _dig(d.get("safe_profiles"), "profiles")
    return (
        [p for p in profiles if isinstance(p, dict)]
        if isinstance(profiles, list)
        else []
    )


def safe_stat(d: dict[str, Any], pid: Any) -> dict[str, Any]:
    """Return the Safe Access statistics of one profile."""
    return _find(_dig(d.get("safe_stats"), "config_groups"), id=pid) or {}


def safe_schedule(d: dict[str, Any], pid: Any) -> dict[str, Any]:
    """Return the Safe Access schedules (block time, quota) of one profile."""
    found = _find(_dig(d.get("safe_schedule"), "profiles"), profile_id=pid) or {}
    return found.get("schedules") or {}


def _safe_devices(d: dict[str, Any], pid: Any) -> list[dict[str, Any]]:
    """Devices of a Safe Access profile, with their name, state and internet time."""
    group = (
        _find(_dig(d.get("safe_devices"), "config_groups"), config_group_id=pid) or {}
    )
    spent_group = (
        _find(_dig(d.get("safe_device_time"), "config_groups"), config_group_id=pid)
        or {}
    )
    times = spent_group.get("device_timespent")
    times = (
        {str(k).lower(): v for k, v in times.items()} if isinstance(times, dict) else {}
    )
    online = {c.get("mac"): c for c in d.get("client_list") or [] if c.get("mac")}
    offline = {c.get("mac"): c for c in d.get("offline_list") or [] if c.get("mac")}
    out: list[dict[str, Any]] = []
    for raw in group.get("devices") or []:
        mac = str(raw).lower()
        client = online.get(mac) or offline.get(mac) or {}
        entry: dict[str, Any] = {
            "name": client.get("name") or mac,
            "mac": mac,
            "online": mac in online,
        }
        if client.get("ip"):
            entry["ip"] = client["ip"]
        minutes = _dig(times.get(mac), "total_spent", "normal")
        if isinstance(minutes, (int, float)):
            entry["internet_minutes"] = minutes
        out.append(entry)
    out.sort(key=lambda e: (not e["online"], str(e["name"]).lower()))
    return out


def _safe_attrs(d: dict[str, Any], pid: Any) -> dict[str, Any]:
    profile = _find(safe_profiles(d), profile_id=pid) or {}
    stat = safe_stat(d, pid)
    hits = stat.get("inappropriate_website_hit")
    quotas = safe_schedule(d, pid).get("timequotas")
    return {
        "profile": profile.get("name"),
        "devices": _safe_devices(d, pid) or None,
        "concerned_status": stat.get("concerned_status"),
        "web_filter": profile.get("enable_filter"),
        "safe_search": profile.get("enable_safe_search"),
        "time_quota": profile.get("enable_timequota"),
        "block_time": profile.get("enable_blocktime"),
        "quota_minutes_by_weekday": (
            {
                q["weekday"]: q["quota"]
                for q in quotas
                if isinstance(q, dict) and "weekday" in q
            }
            if isinstance(quotas, list) and quotas
            else None
        ),
        "inappropriate_websites": (
            {site: v.get("total") for site, v in hits.items() if isinstance(v, dict)}
            if isinstance(hits, dict) and hits
            else None
        ),
    }


def _safe_descriptions(data: dict[str, Any]) -> list[SrmSensorDescription]:
    """Safe Access (parental control): internet time and status per profile."""
    out: list[SrmSensorDescription] = []
    for profile in safe_profiles(data):
        pid = profile.get("profile_id")
        name = profile.get("name")
        if pid is None or not name:
            continue
        ph = {"profile": str(name)}
        out.append(
            SrmSensorDescription(
                key=f"safe_time_{pid}",
                translation_key="safe_time",
                placeholders=ph,
                device_class=SensorDeviceClass.DURATION,
                native_unit_of_measurement=UnitOfTime.MINUTES,
                suggested_unit_of_measurement=UnitOfTime.HOURS,
                suggested_display_precision=1,
                state_class=SensorStateClass.MEASUREMENT,
                value_fn=lambda d, p=pid: _num(
                    safe_stat(d, p).get("time_spent_on_internet")
                ),
                attrs_fn=lambda d, p=pid: {
                    k: v for k, v in _safe_attrs(d, p).items() if v is not None
                },
            )
        )
        out.append(
            SrmSensorDescription(
                key=f"safe_status_{pid}",
                translation_key="safe_status",
                placeholders=ph,
                entity_category=EntityCategory.DIAGNOSTIC,
                value_fn=lambda d, p=pid: safe_stat(d, p).get("concerned_status"),
            )
        )
    return out
