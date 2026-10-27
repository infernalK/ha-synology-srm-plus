"""Smoke test: build every entity description from sample router data and evaluate it.

Run from the repository root:  python tests/smoke.py
Needs `homeassistant` and `synology-srm` installed (no running Home Assistant).
"""

from __future__ import annotations

import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from custom_components.synology_srm_plus import binary_sensor, const, coordinator, sensor  # noqa: E402
from custom_components.synology_srm_plus.clients import normalize_clients  # noqa: E402

RAW_CLIENTS = [
    {"hostname": "Laptop", "mac": "AA:BB:CC:00:00:01", "ip_addr": "192.0.2.40", "is_online": True,
     "is_wireless": True, "connection": "wifi", "band": "5G", "wifi_ssid": "MyHome-5G",
     "signalstrength": 86, "current_rate": 866, "max_rate": 866, "transferRXRate": 4000000,
     "transferTXRate": 280000, "dev_type": "notebook", "mesh_node_name": "Router"},
    {"hostname": "Camera", "mac": "AA:BB:CC:00:00:02", "ip_addr": "192.0.2.101", "is_online": True, "is_baned": True,
     "is_wireless": True, "connection": "wifi", "band": "2.4G", "signalstrength": 48,
     "transferRXRate": 6000, "transferTXRate": 40000, "dev_type": "camera"},
    {"hostname": "NAS", "mac": "AA:BB:CC:00:00:03", "ip_addr": "192.0.2.11", "is_online": True,
     "is_wireless": False, "connection": "ethernet", "dev_type": "nas"},
    {"hostname": "Old phone", "mac": "AA:BB:CC:00:00:04", "ip_addr": "192.0.2.77", "is_online": False,
     "max_rate": 0, "is_guest": False, "dev_type": "phone"},
]
RAW_WIFI = {"device_list": [{"mac_address": "AA:BB:CC:00:00:01", "interface_name": "wlan100",
                              "bytes_rx": 10, "bytes_tx": 20, "signal": 80, "radio_type": "5G"}]}

DATA = {
    "system_utilization": {
        "cpu": {"1min_load": 125, "5min_load": 115, "15min_load": 110, "other_load": 2,
                "system_load": 29, "user_load": 28},
        "memory": {"real_usage": 52, "swap_usage": 7, "total_real": 475192, "avail_real": 74532,
                   "cached": 132056, "buffer": 20740, "total_swap": 4456440, "avail_swap": 4117420},
        "network": [{"device": "total", "rx": 1, "tx": 2}, {"device": "br0", "rx": 1, "tx": 2}],
        "disk": {"disk": [{"device": "sdr", "utilization": 0, "read_byte": 1, "write_byte": 2}]},
        "space": {"volume": [{"device": "mmcblk0p6", "utilization": 6, "read_byte": 1, "write_byte": 0}]},
    },
    "traffic_live": [],
    "external_ip": [{"ip": "203.0.113.42", "ipv6": "2001:db8::1", "type": "WAN"}],
    "ddns": {"records": [{"hostname": "example.test"}]},
    "system_info": {"nodes": [{"node_id": 0, "model": "RT2600ac", "firmware_ver": "SRM 1.3.1",
                               "uptime": 17903, "sn": "SERIAL"}]},
    "connection_status": {"ipv4": {"conn_status": "normal", "ifname": "br0", "ip": "192.0.2.2"},
                          "ipv6": {"conn_status": "normal", "ifname": "br0"}},
    "topology": {"net_topology": "bridge", "switching": False},
    "ethernet": [{"ifname": "br0", "ip": "192.0.2.2", "speed": 1000, "status": "connected", "mtu": 1500}],
    "clients": RAW_CLIENTS,
    "wifi_radio": {"status_list": [{"bssid": "00:11:22:33:44:55", "channel": 36, "radio_type": "5G"},
                                   {"bssid": "00:11:22:33:44:56", "channel": 2, "radio_type": "2.4G"}]},
    "radio_setting": {"radio_list": [{"radio_type": "5G", "channel_width": "20_40_80",
                                      "transmit_power": "high", "wireless_mode": "a_n_ac"}]},
    "wifi_devices": RAW_WIFI,
    "mesh_nodes": {"nodes": [{"node_id": 0, "name": "Router", "connected_devices": 19,
                              "current_rate_rx": 227831, "current_rate_tx": 2788821,
                              "node_status": "good", "network_status": "online", "led_mode": "normal"}]},
    "mesh_network": {"nodes": [{"node_id": 0, "wifi_radios": [
        {"band": "2.4G", "current_channel": 2, "current_rate_rx": 68637, "current_rate_tx": 7991},
        {"band": "5G", "current_channel": 36, "current_rate_rx": 5264, "current_rate_tx": 5700}]}]},
    "mesh_status": {"nodes": [], "overall_status": "good", "overall_status_msg": "good_overall"},
    "eth_ports": {"nodes": [{"node_id": 0, "eth_port_info": [
        {"has_link": True, "link_speed": 1000, "port": "wp1"},
        {"has_link": True, "link_speed": 1000, "port": "lp1"},
        {"has_link": False, "link_speed": 0, "port": "lp3"}]}]},
    "usb_volumes": {"volumes": [{"id": "U2/usbshare", "status": "normal", "total": 29003.15, "used": 4566.39}]},
    "tps_trends": {"begin": "2026-10-14 09:00:00", "end": "2026-10-21 13:33:44", "trends": [
        {"begin": "2026-10-21 01:00:00", "end": "2026-10-21 09:00:00", "high": 0, "low": 1, "medium": 0, "total": 1},
        {"begin": "2026-10-21 09:00:00", "end": "2026-10-21 17:00:00", "high": 0, "low": 2, "medium": 1, "total": 3},
        {"begin": "2026-10-14 09:00:00", "end": "2026-10-14 17:00:00", "high": 1, "low": 0, "medium": 0, "total": 1}]},
    "tps_sensor": {"enable_sensor": True, "enable_prevention": True, "status": "engine_started"},
    "new_devices": {"new_devices": [{"hostname": "Gadget", "mac": "aa:bb:cc:00:00:99"}]},
    "admin_sessions": {"items": [{"who": "admin", "from": "10.0.0.20", "type": "HTTP/HTTPS", "time": "2026/10/21 13:24:43"},
                                 {"who": "admin", "from": "203.0.113.7", "type": "HTTP/HTTPS", "time": "2026/10/20 09:02:11"}]},
    "autoblock": {"addresses": [{"ip": "203.0.113.9"}], "total": 1},
    "autoblock_settings": {"attempts": 5, "enable": True, "expire_day": 0, "within_mins": 1},
    "allow_wan": {"enable": True},
    "port_forward": {"rules": []},
    "safe_profiles": {"profiles": [{"profile_id": 2, "name": "Kids", "enable_filter": True,
                                    "enable_safe_search": True, "enable_timequota": True, "enable_blocktime": True}]},
    "macfilter_devices": {"devices": [{"mac_addr": "AA:BB:CC:00:00:04", "name": "Old phone"}], "enable_prevent_broadcast": True},
    "macfilter_profiles": {"profiles": []},
    "wifi_networks": coordinator.reduce_wifi_networks({"profiles": [
        {"id": 0, "name": "Primary Network", "network_type": "primary", "radio_list": [
            {"radio_type": "2.4G", "enable": True, "ssid": "MyHome", "mac_filter": {"profile_id": -1},
             "security": {"password": "hunter2", "psk": "secret"}},
            {"radio_type": "5G", "enable": True, "ssid": "MyHome-5G", "mac_filter": {"profile_id": 3}}]},
        {"id": 1, "name": "Guest Network", "radio_list": [{"radio_type": "5G", "enable": False, "mac_filter": {"profile_id": -1}}]}]}),
    "safe_devices": {"config_groups": [{"config_group_id": 2, "devices": ["AA:BB:CC:00:00:01", "aa:bb:cc:00:00:04", "aa:bb:cc:00:00:77"]}]},
    "safe_device_time": {"config_groups": [{"config_group_id": 2, "device_timespent": {
        "aa:bb:cc:00:00:01": {"total_spent": {"normal": 42, "reward": 0}}}}]},
    "safe_stats": {"config_groups": [{"id": 2, "concerned_status": "concerned", "time_spent_on_internet": 212,
                                      "inappropriate_website_hit": {"example.test": {"total": 18, "aa:bb": 18}}}]},
    "safe_schedule": {"profiles": [{"profile_id": 2, "schedules": {
        "blocktime_current": {"begin_time": 1, "end_time": 2}, "blocktime_next": {"begin_time": 3, "end_time": 4},
        "timequotas": [{"quota": 120, "weekday": 0}]}}]},
}


def values_of(descriptions, key):
    return next(d.value_fn(DATA) for _, d in descriptions if d.key == key)


def main() -> int:
    errors: list[str] = []

    online, offline = normalize_clients(DATA["clients"], DATA["wifi_devices"])
    assert [c["name"] for c in online] == ["Camera", "Laptop", "NAS"], online
    assert [c["name"] for c in offline] == ["Old phone"], offline
    assert "max_link_rate" not in offline[0] and "guest" not in offline[0], offline[0]
    assert online[1]["download"] == 4000000 and online[1]["interface"] == "wlan100", online[1]
    DATA["client_list"], DATA["offline_list"] = online, offline
    coordinator.SrmCoordinator._annotate_safe_profiles(DATA)  # noqa: SLF001

    en = json.loads((ROOT / "custom_components/synology_srm_plus/translations/en.json").read_text("utf-8"))
    fr = json.loads((ROOT / "custom_components/synology_srm_plus/translations/fr.json").read_text("utf-8"))

    descriptions = [
        ("sensor", d)
        for d in [*sensor.STATIC_SENSORS, *sensor._dynamic_descriptions(DATA)]  # noqa: SLF001
    ] + [("binary_sensor", d) for d in binary_sensor._descriptions(DATA)]  # noqa: SLF001

    seen_keys: set[str] = set()
    for domain, desc in descriptions:
        label = f"{domain}:{desc.key}"
        if desc.key in seen_keys:
            errors.append(f"duplicate key {desc.key}")
        seen_keys.add(desc.key)
        try:
            desc.value_fn(DATA)
            if desc.attrs_fn:
                desc.attrs_fn(DATA)
        except Exception as err:  # noqa: BLE001
            errors.append(f"{label}: {type(err).__name__}: {err}")
        for lang, tr in (("en", en), ("fr", fr)):
            entry = tr["entity"][domain].get(desc.translation_key)
            if entry is None:
                errors.append(f"{label}: no {lang} translation for {desc.translation_key}")
                continue
            for field in re.findall(r"{(\w+)}", entry["name"]):
                if field not in (desc.placeholders or {}):
                    errors.append(f"{label}: {lang} name needs placeholder {field}")

    kids = next(d for _, d in descriptions if d.key == "safe_time_2")
    devices = kids.attrs_fn(DATA)["devices"]
    assert [x["name"] for x in devices] == ["Laptop", "aa:bb:cc:00:00:77", "Old phone"], devices
    assert devices[0]["online"] and devices[0]["internet_minutes"] == 42, devices[0]
    assert not devices[1]["online"], devices[1]
    assert online[1]["safe_profile"] == "Kids", online[1]

    assert "hunter2" not in json.dumps(DATA["wifi_networks"]), "Wi-Fi password leaked into the data"
    assert values_of(descriptions, "wifi_mac_filter_0") is True and values_of(descriptions, "wifi_mac_filter_1") is False
    assert values_of(descriptions, "mac_filter_devices") == 1 and values_of(descriptions, "mac_filter_profiles") == 0
    assert values_of(descriptions, "blocked_devices") == 1, values_of(descriptions, "blocked_devices")

    blocked = next(d for _, d in descriptions if d.key == "blocked_ips")
    attrs = blocked.attrs_fn(DATA)
    assert attrs["failed_attempts"] == 5 and attrs["within_minutes"] == 1 and attrs["auto_block_enabled"] is True, attrs
    assert attrs["expire_days"] == 0 and attrs["addresses"] == [{"ip": "203.0.113.9"}], attrs

    # the threaded fetch: every due endpoint is called once, a failing one is isolated
    from unittest.mock import MagicMock  # noqa: PLC0415

    fake = object.__new__(coordinator.SrmCoordinator)
    fake.client = MagicMock()
    fake.client.http.call.return_value = {"nodes": []}
    fake.client.core.get_ngfw_traffic.side_effect = RuntimeError("boom")
    fake._available_apis = None  # noqa: SLF001
    fake._api_info = None  # noqa: SLF001
    fake._apis_loaded = True  # noqa: SLF001
    fake._poll = 0  # noqa: SLF001
    fake._cache = {}  # noqa: SLF001
    fake._warned = set()  # noqa: SLF001
    fake._versions = {}  # noqa: SLF001
    fake.probes = {}
    fake.config_entry = MagicMock(options={})
    fetched = fake._fetch()  # noqa: SLF001
    assert fake._poll == 1 and "mesh_nodes" in fetched and "client_list" in fetched, fetched.keys()
    assert fetched["traffic_live"] is None and "traffic_live" in fake._warned  # noqa: SLF001
    assert fake.client.http.call.call_count >= 10, fake.client.http.call.call_count
    # an answer without its data (here the threat trends) is probed, once, and reported
    assert fake.probes["tps_trends"]["version"] is None and "v1" in fake.probes["tps_trends"]["tried"], fake.probes
    fake._fetch()  # noqa: SLF001  (second poll: slow endpoints come from the cache)
    assert fake._poll == 2  # noqa: SLF001
    # Safe Access off: its endpoints are skipped, whatever the router offers
    fake.config_entry = MagicMock(options={"safe_access": False})
    off = fake._fetch()  # noqa: SLF001
    assert off["safe_profiles"] is None and off["safe_stats"] is None, off.keys()

    # URL credentials in error messages and in the HTTP libraries' debug logs
    leaky = Exception(
        "HTTPSConnectionPool(host='192.168.1.2', port=8001): Max retries exceeded with url: "
        "/webapi/auth.cgi?api=SYNO.API.Auth&version=2&method=Login&format=sid&account=admin&passwd=hunter2%21&_sid=SESSION123 (Caused by ...)"
    )
    message = coordinator.safe_error(leaky)
    for secret in ("hunter2", "SESSION123", "account=admin"):
        assert secret not in message, message
    assert "passwd=***" in message and "_sid=***" in message, message
    import logging  # noqa: PLC0415

    record = logging.LogRecord(
        "urllib3.connectionpool", logging.DEBUG, __file__, 1,
        '%s "GET /webapi/auth.cgi?account=%s&passwd=%s HTTP/1.1" 200', ("https://r:8001", "admin", "hunter2"), None,
    )
    assert coordinator._ScrubFilter().filter(record)  # noqa: SLF001
    assert "hunter2" not in record.getMessage() and "passwd=***" in record.getMessage(), record.getMessage()
    assert any(
        isinstance(f, coordinator._ScrubFilter)  # noqa: SLF001
        for f in logging.getLogger("urllib3.connectionpool").filters
    ), "log scrubber not installed"

    # the diagnostics file must not hold addresses, MACs, names or secrets
    from custom_components.synology_srm_plus import diagnostics  # noqa: PLC0415

    dumped_diag = json.dumps(diagnostics.redact_data(DATA), default=str)
    for private in (
        "192.0.2.40", "192.0.2.101", "192.0.2.11", "10.0.0.20", "203.0.113", "aa:bb:cc:00:00:01",
        "AA:BB:CC:00:00:01", "aa:bb:cc:00:00:99", "Laptop", "Old phone", "Gadget", "MyHome", "SERIAL", "Kids",
    ):
        assert private not in dumped_diag, f"diagnostics leak {private!r}"
    assert "xx:xx:xx" in json.dumps(coordinator.redact({"aa:bb:cc:dd:ee:ff": 1})), "MAC dict keys not masked"

    # secrets must not reach the log
    masked = coordinator.redact(
        {"password": "hunter2", "pin": "1234", "mac": "aa:bb:cc:dd:ee:ff", "ip": "84.55.140.122",
         "lan": "192.168.1.20", "nested": [{"wifi_psk": "x"}]}
    )
    dumped = json.dumps(masked)
    for secret in ("hunter2", "1234", "aa:bb:cc:dd:ee:ff", "84.55.140.122", "192.168.1.20", '"x"'):
        if secret in dumped:
            errors.append(f"redact leaked {secret}")

    # a few values we know
    values = {d.key: d.value_fn(DATA) for _, d in descriptions}
    expected = {
        "cpu_usage": 59, "load_1min": 1.25, "router_rx_0": 227831, "threat_events_24h": 4,
        "threat_events_7d": 5, "admin_sessions": 2, "blocked_ips": 1, "port_speed_0_lp3": 0, "usb_usage_U2_usbshare": 15.7,
        "clients_offline": 1, "clients_online": 3,
    }
    for key, want in expected.items():
        if values.get(key) != want:
            errors.append(f"{key}: expected {want!r}, got {values.get(key)!r}")

    # the profile of a network ($lbr0$) takes the network's name
    named = {
        "safe_profiles": {"profiles": [
            {"profile_id": 6, "name": "$lbr0$"}, {"profile_id": 7, "name": "$lbr3$"}, {"profile_id": 8, "name": "Kids"}]},
        "local_networks": {"lans": [{"id": "br0", "name": "Primary Network"}, {"id": "gbr0", "name": "Guest Network"}]},
        "safe_interfaces": {"config_groups": [
            {"config_group_id": 6, "interfaces": ["br0", "lbr0"]}, {"config_group_id": 7, "interfaces": []}]},
    }
    coordinator.SrmCoordinator._name_network_profiles(named)  # noqa: SLF001
    got = [p["name"] for p in named["safe_profiles"]["profiles"]]
    if got != ["Primary Network", "lbr3", "Kids"]:
        errors.append(f"network profile names: {got!r}")

    card = (ROOT / "custom_components/synology_srm_plus/www/synology-srm-card.js").read_text(encoding="utf-8")
    if f"const CARDS_VERSION = '{const.VERSION}'" not in card:
        errors.append("CARDS_VERSION in synology-srm-card.js differs from const.VERSION")

    print(f"{len(descriptions)} descriptions checked")
    for error in errors:
        print("ERROR", error)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
