"""Normalise the client list returned by SRM."""

from __future__ import annotations

from typing import Any

GROUP_WIRED = "Wired"

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


def client_group(client: dict[str, Any]) -> str:
    """Return the group of a client: its Wi-Fi band, or 'Wired'."""
    if client.get("connection") == "wifi" or client.get("band"):
        return str(client.get("band") or "Wi-Fi")
    return GROUP_WIRED


def group_label(group: str) -> str:
    """Return the display label of a group."""
    return group if group == GROUP_WIRED else f"Wi-Fi {group}"


def normalize_clients(
    clients: Any, wifi_devices: Any
) -> list[dict[str, Any]] | None:
    """Merge NSM.Device and Wifi.Device payloads into one clean list.

    Returns None when the router does not offer the client list.
    """
    if not isinstance(clients, list):
        return None

    wifi_by_mac: dict[str, dict[str, Any]] = {}
    device_list = (
        wifi_devices.get("device_list") if isinstance(wifi_devices, dict) else None
    )
    for dev in device_list or []:
        if isinstance(dev, dict) and dev.get("mac_address"):
            wifi_by_mac[str(dev["mac_address"]).lower()] = dev

    out: list[dict[str, Any]] = []
    for raw in clients:
        if not isinstance(raw, dict):
            continue
        mac = str(raw.get("mac") or "").lower()
        item: dict[str, Any] = {
            "name": raw.get("hostname") or mac or "unknown",
            "mac": mac,
        }
        for key, srm_key in _NSM_FIELDS.items():
            item[key] = raw.get(srm_key)
        wifi = wifi_by_mac.get(mac)
        if wifi:
            item["interface"] = wifi.get("interface_name")
            item["wifi_bytes_rx"] = wifi.get("bytes_rx")
            item["wifi_bytes_tx"] = wifi.get("bytes_tx")
        item["group"] = client_group(raw)
        out.append({k: v for k, v in item.items() if v is not None and v != ""})
    out.sort(key=lambda c: str(c["name"]).lower())
    return out
