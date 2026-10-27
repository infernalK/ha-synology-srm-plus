# Changelog

## 0.5.22

- Wi-Fi networks: new sensors per Wi-Fi network (the SRM profile, for example *IOT*): number of clients (with the bands and SSIDs in use) and download/upload traffic.
- Router card: the client traffic is shown in two sections, per connection (Total, Wired, Wi-Fi bands) and per Wi-Fi network. New option `traffic_by` (`both` by default, `bands` or `networks`).
- Clients card: two rows of filters that combine, per connection (band, wired, offline) and per Wi-Fi network, with counts that follow the other filter. New option `filter_by` (`both` by default, `connection` or `network`). Search also matches the network name.
- Visual editors for the five cards (title, router, and the options of each card).
- External address: only a valid address of the right family is shown. `0:0:0:0:0:0:0:0`, a MAC address, a link-local address or a non-global IPv6 now give *unknown* instead of a wrong value.
- Fixed in the clients card: clients listed twice and a "Wi-Fi undefined" chip when the per-network sensors were present.

## 0.5.21

- Fixed mixed-up answers from the router: the `synology-srm` library shares one parameters dictionary between all calls, so calls made at the same time sent each other's API, method and version and received the wrong payload (for example the external IP answering with the DDNS record, or the threat statistics with the sensor settings). Each call now has its own parameters. This was most visible on routers with several nodes.
- Threat statistics: if an answer lacks its data, the call is asked again alone and then with the other API versions the router lists; what was tried is reported once in the log and in the diagnostics.
- External IP: the answer is also read when the router wraps the list in `{records: [...]}`, and the address of the WAN connection is used when the external-IP service gives none.
- Router card: the ports are grouped per router, with the router's name as a sub-heading when there are several. A small line at the bottom shows the version of the cards and how many nodes and ports they received.
- New action `synology_srm_plus.debug_report`: a short text report (versions, routers, ports, external address, threat statistics, storage, entities without a value) with no names, addresses or MAC addresses, to paste when asking for help. The same report, the API versions and the state of the main entities are in the diagnostics file; addresses and entity ids are not reported there.

## 0.5.20

- Router card: fixed an empty extra *Router* card shown above the real one (introduced in 0.5.17). It came from device trackers, which belong to no router device and are now ignored.

## 0.5.20

- Cards: they are now loaded through a small self-healing loader (as in the Skolengo integration). On Firefox the cards could stay on "Configuration error" until a manual refresh; the loader re-imports the cards, retries if the elements are still missing and asks Lovelace to rebuild the cards left in error. The existing Lovelace resource is migrated automatically.

## 0.5.19

- Router card: with several router nodes (mesh), the ports of the main router are no longer mixed with those of the others; each other node shows its own ports in its tile. Tiles without a value (for example the external IP of a secondary router) are hidden.

## 0.5.18

- Clients card: the cable icon of wired clients is now coloured like the Wi-Fi signal bars (green from 1 Gbit/s, yellow at 100 Mbit/s, red below).

## 0.5.17

- Safe Access: the profile of a network, which SRM names `$lbr0$`, `$lbr2$`..., now takes the name of that network (for example *Primary Network*), read from the router's local networks. Entity ids are unchanged.
- Router card: with several routers it now shows one card per router (it mixed their ports, storage and addresses, and could pick a secondary router that has no external IP). A router without storage no longer shows 0 %.
- External IP: if no `WAN` entry carries an address, any entry that has one is used.

## 0.5.16

- Wired clients: the router's live traffic list is empty on the first call after a pause (it only fills while being asked), so an empty answer is now asked again after two seconds.

## 0.5.15

- Wired clients now have a download / upload rate (it was always 0): SRM gives none for them in the device list, so it is read from the router's live traffic, which only lists the devices that moved data during the last second.

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
