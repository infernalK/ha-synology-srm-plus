# Changelog

## 0.5.14

- *Explore API* service (filter `Traffic`): also logs the live traffic of each client by name.

## 0.5.13

- *Explore API* service: with the filter `Traffic`, it now also probes per-device traffic calls with parameters, to find where the rate of wired clients (always 0 today) can be read.

## 0.5.12

- After the first install, a notification invites you to reload the page without cache so the dashboard cards show up (also documented in the README).

## 0.5.11

- Documentation: the install section now starts with searching *Synology SRM Plus* in HACS, now that the integration is in the default catalog.

## 0.5.10

- The connection settings (host, account, password, port, HTTPS) can now be changed with *Reconfigure* on the integration, without deleting and re-adding it. Entities and history are kept. Leave the password empty to keep the current one.

## 0.5.9

- *Router* card: new *Wi-Fi access points* section for the other router nodes (a repeater such as the MR2200ac): status, model, firmware, uptime, connected devices and throughput. The main router's tiles now always use node 0, whatever the order of the entities.

## 0.5.8

- *Access control* card: new option `show_blocked_ips: false` hides the list of blocked IP addresses and keeps only their number (useful when the router blocks tens of thousands). The list is still shown by default.

## 0.5.7

- New option **Use Safe Access** (*Configure* on the integration, on by default). Turned off, the Safe Access calls are no longer made and the Safe Access entities are deleted, for routers that do not use parental control.

## 0.5.6

- Privacy: the account, password and session id (sent by SRM as URL parameters) are scrubbed from error messages and from the `urllib3` debug logs; a failed login no longer logs a traceback.
- The diagnostics file now masks IP addresses, MAC addresses (also as dictionary keys), names, SSIDs and secrets everywhere, not only under a few keys; the explore log also masks account, user, host and SSID names.

## 0.5.5

- A call that fails while others run is retried once, alone, before being reported (the router can answer a busy request with an incomplete payload).
- The router is queried on a few threads: setup and updates are much faster (the first refresh took about a minute, which delayed Home Assistant's start).
- New *Access control* card (blocked IPs with the auto-block settings, Wi-Fi block list, custom MAC filters, blocked devices), split from the *Threat prevention* card.
- Wi-Fi MAC filtering sensors renamed to what SRM calls them: *Wi-Fi system block list* (applies to every SSID and takes precedence over custom filters; also holds the devices blocked by broadcast-storm prevention, whose settings are attributes) and *Custom MAC filters*.
- *Blocked IP addresses*: the auto-block settings (enabled, failed attempts, window, expiry) and the blocked addresses are now attributes of the sensor.

## 0.5.4

- MAC filtering (read-only): number of filter profiles, devices in the filter list, whether each Wi-Fi network uses a filter, and the devices the router blocks. Shown in the threat prevention card.
- The Wi-Fi network settings are reduced to harmless fields before being stored (the raw payload holds the Wi-Fi passwords).

## 0.5.3

- Cards: rates and Safe Access times are now read in the unit Home Assistant shows them in (Mbit/s, hours). Before, the router throughput, the client traffic tiles and the Safe Access total could be far too small.
- Safe Access: a device belongs to a single profile.

## 0.5.2

- Safe Access: the devices of each profile (online state, IP, internet time) as an attribute and in the card (click a profile to expand); each client shows its Safe Access profile.

## 0.5.1

- USB disk usage and blocked IPs now work: some DSM APIs live behind another endpoint than `entry.cgi`, which is read from the router's API list.
- A failing API call is logged as a warning once, then at debug level.

## 0.5.0

- Real router throughput, per-band throughput, connected devices and router status (from the mesh node APIs).
- Ethernet ports: link state and speed (WAN and each LAN port).
- USB disk usage (%, used, total).
- Security: threat events (24 h / 7 days), new devices, admin sessions, blocked IPs, port forwarding rules, threat protection, and warnings when the admin interface is reachable from the Internet or an admin session comes from outside.
- Safe Access (parental control): per profile internet time, status, "blocked now" and active filters.
- Wi-Fi channel sensors now carry the channel width, transmit power and mode.
- Offline clients with their last connection (kept across restarts).
- New *Threat prevention* and *Safe Access* dashboard cards (two separate cards); the router and clients cards show the new data; clients can be sorted by IP and last seen.
- `explore_api` now masks secrets, MAC addresses and public IPs in the log.
- Presence tracking: choose which clients get a presence entity; unselected ones are removed (no ghost entities).
- Brand icon, English and French README, validation workflow (hassfest + HACS), MIT license.

## 0.4.x

- Client details as attributes of the connection sensors, optional per-client presence entities, router and clients dashboard cards loaded as a Lovelace resource.
- `explore_api` service, diagnostics download.

## 0.1 – 0.3

- First versions: CPU, memory, network, Wi-Fi, storage and client sensors.
