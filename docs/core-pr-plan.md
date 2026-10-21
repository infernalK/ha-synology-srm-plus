# Plan: contributing to Home Assistant Core

Goal: bring the router-level sensors into the built-in `synology_srm` integration, which today only
has a YAML `device_tracker` platform (`__init__.py`, `device_tracker.py`, `manifest.json`).

## Why it is a large change

- Core no longer accepts new YAML configuration: sensors require a **config flow** (UI setup) and a
  shared `DataUpdateCoordinator`, plus a migration/import of the existing YAML `device_tracker` config.
- Core requires **tests** (config flow, coordinator, sensors) with ~100 % coverage for config flows,
  translations (`strings.json`), `quality_scale.yaml`, and docs in the `home-assistant.io` repo.
- The code owner is `@aerialls`, who also maintains the `synology-srm` library: coordinate with them first.
- The library (`synology-srm` 0.2.3, 2022) has no wrappers for several APIs used here
  (`Router.ConnectionStatus`, `Router.Topology`, `Network.Ethernet`, `Wifi.Radio.Status`, `Wifi.Device`),
  which this prototype calls through `client.http.call`. Core wants API access in a PyPI library, so
  these wrappers should be added to the library (or a fork) and released first.

## Steps

1. Stabilise the custom component on several models (feedback via issues + diagnostics).
2. Open an issue/discussion on `aerialls/synology-srm` proposing the new wrappers; send a PR if welcome.
3. Fork `home-assistant/core`, branch from `dev`. Split into small PRs (Core reviewers prefer this):
   1. config flow + coordinator, keeping the YAML device_tracker via import;
   2. sensors (CPU / memory / network);
   3. Wi-Fi, connection and Ethernet sensors;
   4. diagnostics.
4. Docs PR on `home-assistant/home-assistant.io` for each step.

## Risks

- Changing a legacy integration with no recent activity may meet slow review.
- Entity unique IDs and translations must be final before merge: renaming later is a breaking change.
- Only one router model has been verified so far.
