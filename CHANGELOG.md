# Changelog

## 0.5.0

- Real router throughput, per-band throughput, connected devices and router status (from the mesh node APIs).
- Ethernet ports: link state and speed (WAN and each LAN port).
- USB disk usage (%, used, total).
- Security: threat events (24 h / 7 days), new devices, admin sessions, blocked IPs, port forwarding rules, threat protection, and warnings when the admin interface is reachable from the Internet or an admin session comes from outside.
- Safe Access (parental control): per profile internet time, status, "blocked now" and active filters.
- Wi-Fi channel sensors now carry the channel width, transmit power and mode.
- Offline clients with their last connection (kept across restarts).
- New *Security* dashboard card; the router and clients cards show the new data; clients can be sorted by IP and last seen.
- `explore_api` now masks secrets, MAC addresses and public IPs in the log.
- Presence tracking: choose which clients get a presence entity; unselected ones are removed (no ghost entities).
- Brand icon, English and French README, validation workflow (hassfest + HACS), MIT license.

## 0.4.x

- Client details as attributes of the connection sensors, optional per-client presence entities, router and clients dashboard cards loaded as a Lovelace resource.
- `explore_api` service, diagnostics download.

## 0.1 – 0.3

- First versions: CPU, memory, network, Wi-Fi, storage and client sensors.
