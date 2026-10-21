# Synology SRM Plus

Home Assistant custom integration for **Synology SRM routers** (developed and tested on an
RT2600ac, SRM 1.3.2). The built-in `synology_srm` integration only exposes the connected
devices; this one exposes data about **the router itself**.

It works alongside the built-in integration (different domain) and is configured from the UI.

## What you get

| Group | Sensors |
|---|---|
| CPU | usage, user / system share, load average (1 / 5 / 15 min) |
| Memory | usage %, swap usage %, total / available / cached / buffers / swap (diagnostic) |
| Network | download / upload rate for the total and each interface (`br0`, `bwlan0`, `bwlan1`, `eth2`…) |
| Connection | IPv4 / IPv6 status, network mode (router / bridge), external IPv4 / IPv6 |
| Ethernet links | status, speed, IP per active interface |
| Wi-Fi | channel, client count and average signal per band, total clients |
| Storage | utilization, read and write rate per disk and volume |
| Router | uptime, firmware, model (serial number in the device page) |
| Diagnostic | number of live traffic entries (needs traffic statistics enabled on the router) |

Polling interval: 60 seconds. Everything is read locally from the SRM web API
(`https://<router>:8001`), using the [synology-srm](https://github.com/aerialls/synology-srm) library.

SRM models and firmwares differ: the integration reads the list of APIs your router offers and
**only creates the sensors whose API exists**. Missing ones are skipped without errors.

## Install

### HACS (custom repository)

1. HACS → ⋮ → *Custom repositories* → add `https://github.com/infernalK/ha-synology-srm-plus`,
   category **Integration**.
2. Install **Synology SRM Plus** and restart Home Assistant.
3. *Settings → Devices & services → Add integration → Synology SRM Plus*.

### Router account

Use an **administrator** account on the router (a dedicated one such as `ha` is recommended).
Default port is `8001`; the certificate is usually self-signed, so *Verify SSL* is off by default.

## Units and caveats

- **Client traffic** sensors sum the per-device `transfer_rx_rate` / `transfer_tx_rate` reported by SRM
  (total, per Wi-Fi band, wired). While a 4K video played on one 5 GHz client, that device reported about
  4.1 million, consistent with bytes per second (~33 Mbit/s). Use these for real throughput.
- The per-interface rates (`br0`, `eth2`…) come from the system utilization API and **stayed near zero
  during that 4K stream**, so they appear to miss hardware-accelerated forwarding. They are disabled by
  default on new installs.
- Disk rates are assumed to be in bytes per second (not verified).
- Load averages are reported by SRM multiplied by 100 and are divided back.
- The Wi-Fi signal value is shown as a percentage; Synology does not document its scale.
- Wi-Fi client sensors count the clients associated to this router (not mesh nodes).

## Help us support more models

This was built on a single router, so feedback from other models is very welcome.
Open an issue using the template and attach the **diagnostics file**:
*Settings → Devices & services → Synology SRM Plus → ⋮ → Download diagnostics*.
It lists the API names your router offers and the raw payloads, with MAC / IP addresses,
host names, serial number and credentials redacted. Please still skim it before posting.

## License

No license has been chosen yet.
