# Synology SRM Plus

Home Assistant custom integration for Synology SRM routers (developed on an RT2600ac).
The built-in `synology_srm` integration only exposes connected devices; this one aims at
exposing data about the router itself (system utilization, traffic, WAN status, Wi-Fi radios,
external IP).

Status: **0.1.0 – discovery version.** It exposes one diagnostic sensor per SRM API endpoint with
the raw payload in the `data` attribute, and logs every payload at INFO level, so the real
response shapes can be inspected before building proper sensors.

## Install (HACS)

1. HACS → ⋮ → Custom repositories → add this repository, category *Integration*.
2. Install **Synology SRM Plus**, restart Home Assistant.
3. Settings → Devices & services → Add integration → *Synology SRM Plus*.
   Use an administrator account on the router (port 8001 by default).

To see the raw payloads in the logs:

```yaml
logger:
  logs:
    custom_components.synology_srm_plus: info
```

It uses the [synology-srm](https://github.com/aerialls/synology-srm) library and coexists with the
built-in integration.
