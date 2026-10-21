"""Explore what a Synology SRM router returns through the synology-srm library.

Usage (PowerShell):
    pip install synology-srm
    $env:SRM_HOST = "192.168.1.1"
    $env:SRM_USER = "ha"
    $env:SRM_PASSWORD = "..."
    python scripts/explore_api.py

The password is read from the environment only. Output goes to stdout and to
scripts/explore_output.json (git-ignored) so it can be shared after review.
"""

import json
import os
import sys

import synology_srm

CALLS = [
    ("base.query_info", lambda c: c.base.query_info()),
    ("core.get_system_utilization", lambda c: c.core.get_system_utilization()),
    ("core.get_ngfw_traffic(live)", lambda c: c.core.get_ngfw_traffic("live")),
    ("core.get_ngfw_traffic(day)", lambda c: c.core.get_ngfw_traffic("day")),
    ("core.list_ddns_extip", lambda c: c.core.list_ddns_extip()),
    ("mesh.get_system_info", lambda c: c.mesh.get_system_info()),
    ("mesh.get_network_wanstatus", lambda c: c.mesh.get_network_wanstatus()),
    ("mesh.get_network_wifidevice", lambda c: c.mesh.get_network_wifidevice()),
]


def main() -> int:
    host = os.environ.get("SRM_HOST")
    user = os.environ.get("SRM_USER", "admin")
    password = os.environ.get("SRM_PASSWORD")
    if not host or not password:
        print("Set SRM_HOST and SRM_PASSWORD (and optionally SRM_USER).")
        return 1

    client = synology_srm.Client(
        host=host,
        port=int(os.environ.get("SRM_PORT", "8001")),
        username=user,
        password=password,
        https=True,
    )
    client.http.verify = False  # self-signed certificate on the router

    results = {}
    for name, call in CALLS:
        try:
            results[name] = call(client)
        except Exception as err:  # noqa: BLE001 - exploration script
            results[name] = {"error": f"{type(err).__name__}: {err}"}
        print(f"\n=== {name} ===")
        print(json.dumps(results[name], indent=2, default=str)[:4000])

    out = os.path.join(os.path.dirname(__file__), "explore_output.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=2, default=str)
    print(f"\nFull output saved to {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
