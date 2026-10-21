"""Constants for Synology SRM Plus."""

from datetime import timedelta

DOMAIN = "synology_srm_plus"
VERSION = "0.4.1"  # keep in sync with manifest.json (also busts the card cache)

CONF_TRACK_CLIENTS = "track_clients"

CARD_URL = f"/{DOMAIN}/synology-srm-card.js"

DEFAULT_PORT = 8001
DEFAULT_USERNAME = "admin"
DEFAULT_SSL = True
DEFAULT_VERIFY_SSL = False

SCAN_INTERVAL = timedelta(seconds=60)
