"""Constants for Synology SRM Plus."""

from datetime import timedelta

DOMAIN = "synology_srm_plus"

DEFAULT_PORT = 8001
DEFAULT_USERNAME = "admin"
DEFAULT_SSL = True
DEFAULT_VERIFY_SSL = False

SCAN_INTERVAL = timedelta(seconds=60)
