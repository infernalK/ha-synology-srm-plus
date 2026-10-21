<p align="center">
  <img src="https://raw.githubusercontent.com/infernalK/ha-synology-srm-plus/main/custom_components/synology_srm_plus/brand/icon.png" alt="Synology SRM Plus logo" width="140">
</p>

# Synology SRM Plus

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=infernalK&repository=ha-synology-srm-plus&category=integration)
[![Validate](https://github.com/infernalK/ha-synology-srm-plus/actions/workflows/validate.yaml/badge.svg)](https://github.com/infernalK/ha-synology-srm-plus/actions/workflows/validate.yaml)
[![License](https://img.shields.io/github/license/infernalK/ha-synology-srm-plus)](LICENSE)

**English** · [Français](README.fr.md)

**Everything your Synology router knows, inside Home Assistant: health, real traffic, Wi-Fi, every client, security and parental control, with ready-made dashboard cards.**

Developed and tested on an **RT2600ac (SRM 1.3.2)**. The built-in `synology_srm` integration only lists the connected devices; this one exposes the router itself. It works alongside the built-in integration (different domain) and is set up from the UI.

## What you get

| Group | Entities |
|---|---|
| Router | status, uptime, firmware, model, **real throughput** (rx / tx, including hardware-accelerated traffic), connected devices |
| CPU / memory | CPU usage, user / system share, load average (1 / 5 / 15 min), memory and swap usage, memory details (diagnostic) |
| Clients | online clients, **one sensor per connection** (Wi-Fi 2.4G, Wi-Fi 5G, Wired) whose attributes list every attached client, **offline clients with their last connection**, client download / upload (total and per connection) |
| Wi-Fi | per band: channel, throughput, average signal, client count; width / power / mode as attributes |
| Network | IPv4 / IPv6 connection status, network mode (router / bridge), external IPv4 / IPv6 (+ DDNS names), Ethernet links (status, speed, IP) |
| Ports | link speed and link state of the WAN port and each LAN port |
| Storage | **USB disk usage** (%, used, total), disk and volume activity |
| Security | threat events (24 h / 7 days), new devices, admin sessions, blocked IPs, port forwarding rules, threat protection on/off, **warnings** when the admin interface is reachable from the Internet or someone connected from outside |
| Safe Access (parental control) | per profile: internet time, status, "blocked now" schedule, which filters are active, flagged websites |
| Optional | presence entities (device trackers) for the clients you choose, or for all of them |

Polling interval: 60 seconds (slow-changing data is read less often to spare the router). Everything is read locally from the SRM web API (`https://<router>:8001`) with the [synology-srm](https://github.com/aerialls/synology-srm) library.

SRM models and firmwares differ: the integration reads the list of APIs your router offers and **only creates the entities whose API exists**. Missing ones are skipped without errors.

### Client details

Each connection sensor (e.g. `sensor.<router>_clients_wi_fi_5g`) has a `clients` attribute: for every device, its name, MAC, IPv4 / IPv6, Wi-Fi band, SSID and profile, signal, link rate, download and upload rates, device type, router node and the QoS / guest / blocked / parental-control flags. The *Offline clients* sensor lists the devices the router knows but that are gone, with the time they were **last seen** (kept across restarts). These attributes are kept out of the recorder, so they do not bloat the database.

If you prefer one entity per device, use the **presence tracking option** (*Configure* on the integration): pick the clients that get a presence entity, or track every client. Unselected clients are removed again, no ghost entities. It is the same idea as the built-in integration, so keep only one of the two if you do not want duplicates.

## Dashboard cards

Four cards are included and loaded automatically (no resource to add):

| Router card | | Clients card |
|---|---|---|
| ![Router card](docs/images/router-card.png) | ![Router card, details](docs/images/router-card-details.png) | ![Clients card](docs/images/clients-card.png) |

| Threat prevention card | Safe Access card |
|---|---|
| ![Threat prevention card](docs/images/threat-card.png) | ![Safe Access card](docs/images/safeaccess-card.png) |

*Rendered with neutral sample data. In Home Assistant the client icons are Material Design icons (the emoji here are stand-ins used by the preview harness) and the colors follow your theme.*

```yaml
type: custom:synology-srm-router-card     # gauges, traffic, bands, ports, USB, storage
```

```yaml
type: custom:synology-srm-clients-card    # every client, offline ones included
title: Clients
sort_by: download        # download | upload | signal | ip | name | last_seen
groups: [5G, 2.4G]       # optional filter (also: Wired, Offline)
max_height: 500          # optional, px
```

```yaml
type: custom:synology-srm-threat-card     # threat prevention: events, new devices, admin sessions, exposure
```

```yaml
type: custom:synology-srm-safeaccess-card # Safe Access (parental control): time online, status, schedules per profile
```

The cards find the integration's entities on their own; add `device_id: <id>` if you have several routers. In the clients card, click a client to expand all its details, double-click to open its connection sensor. A ready-made dashboard is in [dashboards/synology-srm.yaml](dashboards/synology-srm.yaml). The cards follow your Home Assistant language (English or French).

## Install

### HACS (custom repository)

1. HACS → ⋮ → *Custom repositories* → add `https://github.com/infernalK/ha-synology-srm-plus`, category **Integration** (or use the button at the top of this page).
2. Install **Synology SRM Plus** and restart Home Assistant.
3. *Settings → Devices & services → Add integration → Synology SRM Plus*.

### Router account

Use an **administrator** account on the router (a dedicated one such as `ha` is recommended). Default port is `8001`; the certificate is usually self-signed, so *Verify SSL* is off by default.

## Units and caveats

- **Client traffic** sums the per-device `transferRXRate` / `transferTXRate` reported by SRM. While a 4K video played on one 5 GHz client, that device reported about 4.1 million, consistent with bytes per second (~33 Mbit/s).
- **Router throughput** (`rx` / `tx`) comes from the mesh node list and includes traffic the router forwards in hardware. Which direction `rx` and `tx` mean for your network is not documented by Synology.
- The per-interface rates (`br0`, `eth2`…) come from the system utilization API and stayed near zero during that 4K stream, so they appear to miss hardware-accelerated forwarding. They are disabled by default on new installs.
- USB sizes are reported in MiB (a 32 GB key shows about 29 000).
- Load averages are reported by SRM multiplied by 100 and are divided back.
- The Wi-Fi signal value is shown as a percentage; Synology does not document its scale.
- Safe Access internet time is shown in minutes, over the period SRM reports; the unit and the period are not documented.
- **Last seen** only starts when the integration is installed: devices that were already offline have no date until they reconnect.

## Exploring your router

The router exposes hundreds of API endpoints and models differ. To help map what yours offers, call the service `synology_srm_plus.explore_api` (*Developer tools → Actions*, optional `filter` such as `Wifi`). It runs in the background for a few minutes, calls only read-only `get` / `list` methods, skips anything that looks like it could have a side effect, and writes what answers to the Home Assistant log (INFO level for `custom_components.synology_srm_plus`).

The log output is **masked**: passwords, keys and PINs, MAC addresses and public IP addresses are replaced. Device names, SSIDs and private addresses are not detected, so please skim it before sharing.

## Help us support more models

This was built on a single router, so feedback from other models is very welcome. Open an issue using the template and attach the **diagnostics file**: *Settings → Devices & services → Synology SRM Plus → ⋮ → Download diagnostics*. It lists the API names your router offers and the raw payloads, with addresses, host names, serial number and credentials redacted. Please still skim it before posting.

## License

MIT, see [LICENSE](LICENSE).
