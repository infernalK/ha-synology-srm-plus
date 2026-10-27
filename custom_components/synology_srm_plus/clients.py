"""Normalise the client list returned by SRM."""

from __future__ import annotations

import re
from typing import Any

GROUP_WIRED = "Wired"
GROUP_OFFLINE = "Offline"

# normalised key -> SRM key (NSM.Device payload)
_NSM_FIELDS: dict[str, str] = {
    "ip": "ip_addr",
    "ipv6": "ip6_addr",
    "connection": "connection",
    "band": "band",
    "ssid": "wifi_ssid",
    "wifi_profile": "wifi_profile_name",
    "signal": "signalstrength",
    "link_rate": "current_rate",
    "max_link_rate": "max_rate",
    "rate_quality": "rate_quality",
    "download": "transferRXRate",
    "upload": "transferTXRate",
    "device_type": "dev_type",
    "mesh_node": "mesh_node_name",
    "guest": "is_guest",
    "blocked": "is_baned",
    "parental_control": "is_parental_controled",
    "qos": "is_qos",
    "high_priority": "is_high_qos",
    "low_priority": "is_low_qos",
    "beamforming": "is_beamforming_on",
}

# Offline devices may carry timestamps under names we do not know yet.
_TIME_KEY = re.compile(r"last|time|date|seen|online", re.I)


def client_group(client: dict[str, Any]) -> str:
    """Return the group of a client: its Wi-Fi band, or 'Wired'."""
    if client.get("connection") == "wifi" or client.get("band"):
        return str(client.get("band") or "Wi-Fi")
    return GROUP_WIRED


def group_label(group: str) -> str:
    """Return the display label of a group."""
    if group in (GROUP_WIRED, GROUP_OFFLINE):
        return group
    return f"Wi-Fi {group}"


def _live_rates(live: Any) -> dict[str, tuple[Any, Any]] | None:
    """Return (download, upload) per MAC from the NGFW live traffic, or None."""
    if not isinstance(live, list):
        return None
    return {
        str(row["deviceID"]).lower(): (row.get("download"), row.get("upload"))
        for row in live
        if isinstance(row, dict) and row.get("deviceID")
    }


def normalize_clients(
    clients: Any, wifi_devices: Any, live_traffic: Any = None
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]] | None:
    """Merge NSM.Device, Wifi.Device and live traffic into online / offline lists.

    Returns None when the router does not offer the client list.
    """
    if not isinstance(clients, list):
        return None
    live = _live_rates(live_traffic)

    wifi_by_mac: dict[str, dict[str, Any]] = {}
    device_list = (
        wifi_devices.get("device_list") if isinstance(wifi_devices, dict) else None
    )
    for dev in device_list or []:
        if isinstance(dev, dict) and dev.get("mac_address"):
            wifi_by_mac[str(dev["mac_address"]).lower()] = dev

    online: list[dict[str, Any]] = []
    offline: list[dict[str, Any]] = []
    for raw in clients:
        if not isinstance(raw, dict):
            continue
        mac = str(raw.get("mac") or "").lower()
        is_online = raw.get("is_online", True) is not False
        item: dict[str, Any] = {
            "name": raw.get("hostname") or mac or "unknown",
            "mac": mac,
        }
        for key, srm_key in _NSM_FIELDS.items():
            item[key] = raw.get(srm_key)
        if is_online:
            wifi = wifi_by_mac.get(mac)
            if wifi:
                item["interface"] = wifi.get("interface_name")
                item["wifi_bytes_rx"] = wifi.get("bytes_rx")
                item["wifi_bytes_tx"] = wifi.get("bytes_tx")
            item["group"] = client_group(raw)
            # SRM gives no rate in the device list for wired clients (hardware
            # forwarding): the live traffic list has it, and only names the devices
            # that moved data during the last second.
            if live is not None and item.get("download") is None:
                item["download"], item["upload"] = (
                    v or 0 for v in live.get(mac, (0, 0))
                )
        else:
            item["group"] = GROUP_OFFLINE
            # Rates and signal are meaningless once a device is gone.
            for key in ("signal", "link_rate", "download", "upload"):
                item.pop(key, None)
            extra = {
                k: v
                for k, v in raw.items()
                if _TIME_KEY.search(k) and k != "is_online" and v not in (None, "", 0)
            }
            if extra:
                item["extra"] = extra
        cleaned = {k: v for k, v in item.items() if v is not None and v != ""}
        if not is_online:
            # Offline devices: drop the flags and rates that are just "false" / 0.
            cleaned = {
                k: v for k, v in cleaned.items() if v is not False and v != 0
            }
        (online if is_online else offline).append(cleaned)
    online.sort(key=lambda c: str(c["name"]).lower())
    offline.sort(key=lambda c: str(c["name"]).lower())
    return online, offline
