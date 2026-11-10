"""Watch the router's TLS certificate: remember it at setup, warn when it changes.

SRM presents its own certificate, which Home Assistant cannot verify, so by default the
connection is not verified. Instead of blocking anything, the fingerprint seen at setup is
remembered and a repair is raised if a later one differs (a renewed certificate, or someone
in between). Nothing stops working either way.
"""

from __future__ import annotations

from datetime import timedelta
import hashlib
import logging
import ssl
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_SSL, CONF_VERIFY_SSL
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.event import async_track_time_interval

from .const import CONF_CERT_FINGERPRINT, DOMAIN

_LOGGER = logging.getLogger(__name__)

CHECK_INTERVAL = timedelta(hours=6)
ISSUE_PREFIX = "certificate_changed_"


def fetch_fingerprint(host: str, port: int, timeout: float = 5) -> str | None:
    """Return the SHA-256 fingerprint of the certificate a server presents, or None.

    Blocking: run it in the executor. The certificate is only read, not verified.
    """
    try:
        pem = ssl.get_server_certificate((host, port), timeout=timeout)
        return hashlib.sha256(ssl.PEM_cert_to_DER_cert(pem)).hexdigest()
    except (OSError, ValueError) as err:
        _LOGGER.debug("Cannot read the certificate of %s:%s: %s", host, port, err)
        return None


def is_watched(data: Any) -> bool:
    """Whether this connection is HTTPS and not verified (so worth watching)."""
    return bool(data.get(CONF_SSL)) and not data.get(CONF_VERIFY_SSL)


def same_fingerprint(a: str | None, b: str | None) -> bool:
    """Compare two fingerprints, ignoring case and separators."""

    def clean(value: str | None) -> str:
        return (value or "").replace(":", "").lower()

    return bool(a) and clean(a) == clean(b)


async def async_check_certificate(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Remember the certificate on first sight; raise or clear the repair afterwards."""
    issue_id = ISSUE_PREFIX + entry.entry_id
    if not is_watched(entry.data):
        ir.async_delete_issue(hass, DOMAIN, issue_id)
        return
    seen = await hass.async_add_executor_job(
        fetch_fingerprint, entry.data[CONF_HOST], entry.data[CONF_PORT]
    )
    if seen is None:
        return  # unreachable right now: say nothing, the update failure already does
    pinned = entry.data.get(CONF_CERT_FINGERPRINT)
    if not pinned:
        hass.config_entries.async_update_entry(
            entry, data={**entry.data, CONF_CERT_FINGERPRINT: seen}
        )
    elif same_fingerprint(pinned, seen):
        ir.async_delete_issue(hass, DOMAIN, issue_id)
    else:
        ir.async_create_issue(
            hass,
            DOMAIN,
            issue_id,
            is_fixable=True,
            severity=ir.IssueSeverity.WARNING,
            translation_key="certificate_changed",
            translation_placeholders={"host": entry.data[CONF_HOST]},
            data={"entry_id": entry.entry_id, "fingerprint": seen},
        )


@callback
def async_watch_certificate(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Check now (in the background) and every few hours until the entry unloads."""

    async def _check(*_: object) -> None:
        try:
            await async_check_certificate(hass, entry)
        except Exception:  # noqa: BLE001 - a watcher must never break the integration
            _LOGGER.debug("Certificate check failed", exc_info=True)

    entry.async_create_background_task(hass, _check(), f"{DOMAIN}_certificate")
    entry.async_on_unload(async_track_time_interval(hass, _check, CHECK_INTERVAL))
