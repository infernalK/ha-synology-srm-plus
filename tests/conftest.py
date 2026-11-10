"""Shared fixtures: a config entry whose router answers come from the sample data."""

from __future__ import annotations

import copy
from pathlib import Path
import sys
from typing import Any
from unittest.mock import patch
import warnings

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

if sys.platform == "win32":
    # The harness blocks sockets, but Windows' event loop needs a local socket pair to run.
    import pytest_socket

    pytest_socket.disable_socket = lambda *args, **kwargs: None

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))
warnings.simplefilter("ignore")

import smoke  # noqa: E402  (the anonymised sample answers)
from custom_components.synology_srm_plus import coordinator as coordinator_module  # noqa: E402
from custom_components.synology_srm_plus.clients import normalize_clients  # noqa: E402
from custom_components.synology_srm_plus.const import DOMAIN  # noqa: E402

ENTRY_DATA = {
    "host": "192.0.2.1",
    "username": "admin",
    "password": "not-a-real-password",
    "port": 8001,
    "ssl": True,
    "verify_ssl": False,
}


def sample_data() -> dict[str, Any]:
    """A fresh copy of the sample router data, normalised like the coordinator does."""
    data = copy.deepcopy(smoke.DATA)
    data["client_list"], data["offline_list"] = normalize_clients(
        data["clients"], data["wifi_devices"]
    )
    coordinator_module.SrmCoordinator._annotate_safe_profiles(data)  # noqa: SLF001
    return data


@pytest.fixture(autouse=True)
def _enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Let Home Assistant load custom_components/."""


@pytest.fixture
def router() -> dict[str, Any]:
    """The data the fake router answers with; tests change it between updates."""
    return {"data": sample_data()}


@pytest.fixture
def entry(router: dict[str, Any]) -> MockConfigEntry:
    """A config entry (not yet set up)."""
    return MockConfigEntry(domain=DOMAIN, data=dict(ENTRY_DATA), title="RT2600ac")


@pytest.fixture(autouse=True)
def _fake_router(router: dict[str, Any]):
    """Replace the blocking router reads, the logout and the certificate lookup."""
    with (
        patch.object(
            coordinator_module.SrmCoordinator,
            "_fetch",
            lambda self: copy.deepcopy(router["data"]),
        ),
        patch("custom_components.synology_srm_plus.logout_client"),
        patch(
            "custom_components.synology_srm_plus.certificate.fetch_fingerprint",
            return_value="aa" * 32,
        ),
    ):
        yield
