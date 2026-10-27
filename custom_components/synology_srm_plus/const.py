"""Constants for Synology SRM Plus."""

from datetime import timedelta

DOMAIN = "synology_srm_plus"
VERSION = "0.5.22"  # keep in sync with manifest.json (also busts the card cache)

CONF_TRACK_CLIENTS = "track_clients"  # legacy option: track everyone
CONF_TRACK_ALL = "track_all"
CONF_TRACKED_CLIENTS = "tracked_clients"
CONF_SAFE_ACCESS = "safe_access"

CARD_URL = f"/{DOMAIN}/synology-srm-card.js"
# Small loader registered instead of the cards file itself (see its header).
LOADER_URL = f"/{DOMAIN}/synology-srm-loader.js"

DEFAULT_PORT = 8001
DEFAULT_USERNAME = "admin"
DEFAULT_SSL = True
DEFAULT_VERIFY_SSL = False

SCAN_INTERVAL = timedelta(seconds=60)
