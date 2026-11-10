"""Privacy test: lists and personal attributes must stay out of the history database.

Run from the repository root:  python tests/test_privacy.py   (or with pytest)

Every attribute that holds a list or a dict, or that identifies a person or a network, must be
listed in the entity's `_unrecorded_attributes` (still readable as live state, never recorded).
A new list attribute added without that fails here.
"""

from __future__ import annotations

import copy
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

import smoke  # noqa: E402
from custom_components.synology_srm_plus import binary_sensor, coordinator, device_tracker, sensor  # noqa: E402
from custom_components.synology_srm_plus.clients import normalize_clients  # noqa: E402

# Small, harmless attributes that may stay in the history even though they are lists or dicts.
ALLOWED_RECORDED = {"bands", "by_band", "quota_minutes_by_weekday", "profile_ids", "default_policy"}
# Always personal or identifying: must never be recorded, whatever their type.
ALWAYS_UNRECORDED = {"inappropriate_websites", "profiles", "bssid", "ssids", "clients", "devices", "sessions", "addresses", "ddns_hostnames", "leases", "reservations", "rules"}


def _data() -> dict:
    data = copy.deepcopy(smoke.DATA)
    data["client_list"], data["offline_list"] = normalize_clients(data["clients"], data["wifi_devices"])
    data["macfilter_profiles"] = {"profiles": [{"profile_id": 1, "name": "Kids", "password": "x"}]}
    coordinator.SrmCoordinator._annotate_safe_profiles(data)  # noqa: SLF001
    return data


def _attribute_names(data: dict) -> list[tuple[str, str, object]]:
    """(entity key, attribute name, value) for every attribute the descriptions produce."""
    found = []
    descriptions = [*sensor.STATIC_SENSORS, *sensor._dynamic_descriptions(data)]  # noqa: SLF001
    descriptions += binary_sensor._descriptions(data)  # noqa: SLF001
    for desc in descriptions:
        if desc.attrs_fn:
            for name, value in (desc.attrs_fn(data) or {}).items():
                found.append((desc.key, name, value))
    return found


def test_list_attributes_are_not_recorded() -> None:
    recorded = []
    unrecorded = sensor.UNRECORDED_ATTRIBUTES
    for key, name, value in _attribute_names(_data()):
        if isinstance(value, (list, dict)) and name not in unrecorded and name not in ALLOWED_RECORDED:
            recorded.append(f"{key}.{name}")
    assert not recorded, f"attributes recorded in the history, add them to UNRECORDED_ATTRIBUTES: {recorded}"


def test_personal_attributes_are_not_recorded() -> None:
    missing = ALWAYS_UNRECORDED - sensor.UNRECORDED_ATTRIBUTES
    assert not missing, f"must be unrecorded: {sorted(missing)}"
    assert sensor.SrmSensor._unrecorded_attributes == sensor.UNRECORDED_ATTRIBUTES  # noqa: SLF001


def test_safe_access_websites_are_produced_and_unrecorded() -> None:
    names = {name for _, name, _ in _attribute_names(_data())}
    assert "inappropriate_websites" in names  # the sample data must keep covering it
    assert "inappropriate_websites" in sensor.UNRECORDED_ATTRIBUTES


def test_tracker_records_only_where_the_client_was() -> None:
    online, offline = normalize_clients(smoke.DATA["clients"], smoke.DATA["wifi_devices"])
    unrecorded = device_tracker.TRACKER_UNRECORDED_ATTRIBUTES
    skip = {"mac", "ip", "name"}  # not attributes of the tracker
    for client in [*online, *offline]:
        recorded = {k for k in client if k not in skip and k not in unrecorded}
        assert recorded <= device_tracker.RECORDED_TRACKER_ATTRIBUTES, recorded
    assert device_tracker.SrmClientTracker._unrecorded_attributes == unrecorded  # noqa: SLF001


def main() -> int:
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for test in tests:
        try:
            test()
            print(f"ok   {test.__name__}")
        except AssertionError as err:
            failed += 1
            print(f"FAIL {test.__name__}: {err}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
