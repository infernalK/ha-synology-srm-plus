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

from custom_components.synology_srm_plus import binary_sensor, coordinator, sensor  # noqa: E402
from custom_components.synology_srm_plus.clients import normalize_clients  # noqa: E402

RAW_CLIENTS = [
    {"hostname": "Laptop", "mac": "AA:BB:CC:00:00:01", "ip_addr": "192.0.2.40", "is_online": True,
     "is_wireless": True, "connection": "wifi", "band": "5G", "wifi_ssid": "MyHome-5G",
     "signalstrength": 86, "current_rate": 866, "max_rate": 866, "transferRXRate": 4000000,
     "transferTXRate": 280000, "dev_type": "notebook", "mesh_node_name": "Router"},
    {"hostname": "Camera", "mac": "AA:BB:CC:00:00:02", "ip_addr": "192.0.2.101", "is_online": True,
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
    "autoblock": {"addresses": [], "total": 0},
    "allow_wan": {"enable": True},
    "port_forward": {"rules": []},
    "safe_profiles": {"profiles": [{"profile_id": 2, "name": "Kids", "enable_filter": True,
                                    "enable_safe_search": True, "enable_timequota": True, "enable_blocktime": True}]},
    "safe_stats": {"config_groups": [{"id": 2, "concerned_status": "concerned", "time_spent_on_internet": 212,
                                      "inappropriate_website_hit": {"example.test": {"total": 18, "aa:bb": 18}}}]},
    "safe_schedule": {"profiles": [{"profile_id": 2, "schedules": {
        "blocktime_current": {"begin_time": 1, "end_time": 2}, "blocktime_next": {"begin_time": 3, "end_time": 4},
        "timequotas": [{"quota": 120, "weekday": 0}]}}]},
}


def main() -> int:
    errors: list[str] = []

    online, offline = normalize_clients(DATA["clients"], DATA["wifi_devices"])
    assert [c["name"] for c in online] == ["Camera", "Laptop", "NAS"], online
    assert [c["name"] for c in offline] == ["Old phone"], offline
    assert "max_link_rate" not in offline[0] and "guest" not in offline[0], offline[0]
    assert online[1]["download"] == 4000000 and online[1]["interface"] == "wlan100", online[1]
    DATA["client_list"], DATA["offline_list"] = online, offline

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
        "threat_events_7d": 5, "admin_sessions": 2, "port_speed_0_lp3": 0, "usb_usage_U2_usbshare": 15.7,
        "clients_offline": 1, "clients_online": 3,
    }
    for key, want in expected.items():
        if values.get(key) != want:
            errors.append(f"{key}: expected {want!r}, got {values.get(key)!r}")

    print(f"{len(descriptions)} descriptions checked")
    for error in errors:
        print("ERROR", error)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
