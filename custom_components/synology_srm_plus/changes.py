"""Detect what changed on the router between two reads: new clients, firewall edits.

Pure functions over the coordinator data. The last state is stored by the coordinator, so a
change made while Home Assistant was off is reported once it is back. The first read only
records what is there: it never reports the state at start-up as a change.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

MAX_NEW_CLIENT_EVENTS = 5  # per update: a router that forgot its list must not flood events

POLICY_LABELS = {
    "ipv4_wan_to_lan": "IPv4 internet to LAN",
    "ipv4_wan_to_srm": "IPv4 internet to the router",
    "ipv6_wan_to_lan": "IPv6 internet to LAN",
    "ipv6_wan_to_srm": "IPv6 internet to the router",
}

_RULE_FIELDS = (
    "name",
    "enabled",
    "action",
    "chain",
    "ip_version",
    "protocol",
    "in_interface_type",
    "in_interface_value",
    "out_interface_type",
    "out_interface_value",
    "src_ip_type",
    "src_ip_value",
    "src_port_type",
    "src_port_value",
    "dst_ip_type",
    "dst_ip_value",
    "dst_port_type",
    "dst_port_value",
)


def firewall_rules(data: dict[str, Any]) -> list[dict[str, Any]] | None:
    """Return the firewall rules, or None when the router did not give them."""
    payload = data.get("firewall_rules")
    rules = payload.get("rules") if isinstance(payload, dict) else None
    if not isinstance(rules, list):
        return None
    return [r for r in rules if isinstance(r, dict)]


def default_policy(data: dict[str, Any]) -> dict[str, str] | None:
    """Return the firewall's default policy (allow / deny per direction), or None."""
    payload = data.get("firewall_rules")
    policy = payload.get("default_policy") if isinstance(payload, dict) else None
    if not isinstance(policy, dict):
        return None
    return {str(k): str(v) for k, v in policy.items()}


def rules_hash(rules: list[dict[str, Any]]) -> str:
    """Hash the rules and their order: it changes when a rule is added, edited, moved or toggled."""
    plain = [[r.get(f) for f in _RULE_FIELDS] for r in rules]
    return hashlib.sha256(json.dumps(plain, sort_keys=True, default=str).encode()).hexdigest()[:16]


def is_private_mac(mac: str) -> bool:
    """Whether a MAC address is locally administered (a phone's private / random address)."""
    try:
        return bool(int(mac.split(":")[0], 16) & 0x02)
    except (ValueError, IndexError):
        return False


def _names(rules: list[dict[str, Any]]) -> list[str]:
    return [str(r.get("name") or "") for r in rules]


def detect(
    previous: dict[str, Any] | None, data: dict[str, Any]
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Compare the new read with the stored state: return (new state, events).

    Each event is ``{"entity": "new_client" | "router_changes", "type": ..., "data": {...}}``.
    """
    state: dict[str, Any] = dict(previous or {})
    events: list[dict[str, Any]] = []
    first = previous is None

    online = data.get("client_list")
    if isinstance(online, list):
        known = set(state.get("known_clients") or [])
        fresh = [c for c in online if c.get("mac") and c["mac"] not in known]
        if not first:
            for client in fresh[:MAX_NEW_CLIENT_EVENTS]:
                events.append(
                    {
                        "entity": "new_client",
                        "type": "new_client",
                        "data": {
                            key: client[key]
                            for key in ("name", "mac", "ip", "connection", "band", "ssid")
                            if client.get(key) not in (None, "")
                        }
                        | {"private_mac": is_private_mac(client["mac"])},
                    }
                )
        state["known_clients"] = sorted(known | {c["mac"] for c in fresh})

    rules = firewall_rules(data)
    if rules is not None:
        digest = rules_hash(rules)
        old = state.get("firewall") or {}
        if old and old.get("hash") != digest:
            before, after = list(old.get("names") or []), _names(rules)
            added = [n for n in after if n not in before]
            removed = [n for n in before if n not in after]
            events.append(
                {
                    "entity": "router_changes",
                    "type": "firewall_rules_changed",
                    "data": {
                        "added": added,
                        "removed": removed,
                        "modified_or_moved": not added and not removed,
                        "rule_count": len(after),
                    },
                }
            )
        state["firewall"] = {"hash": digest, "names": _names(rules)}

    policy = default_policy(data)
    if policy is not None:
        old_policy = state.get("policy")
        if isinstance(old_policy, dict) and old_policy != policy:
            changed = {
                POLICY_LABELS.get(k, k): f"{old_policy.get(k)} -> {v}"
                for k, v in policy.items()
                if old_policy.get(k) != v
            }
            events.append(
                {
                    "entity": "router_changes",
                    "type": "firewall_policy_changed",
                    "data": {"changed": changed},
                }
            )
        state["policy"] = policy
    return state, events


def risks(data: dict[str, Any]) -> dict[str, bool | None]:
    """Router settings that weaken it: True when risky, False when safe, None when unknown."""
    auto_block = data.get("autoblock_settings")
    enabled = auto_block.get("enable") if isinstance(auto_block, dict) else None
    policy = default_policy(data)
    open_policy = None
    if policy is not None:
        # Only traffic into the LAN: reaching SRM itself from outside is a choice some make
        # on purpose (the admin interface warning already covers it).
        open_policy = any(policy.get(k) == "allow" for k in ("ipv4_wan_to_lan", "ipv6_wan_to_lan"))
    return {
        "auto_block_off": (not enabled) if isinstance(enabled, bool) else None,
        "firewall_open": open_policy,
    }
