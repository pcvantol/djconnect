from __future__ import annotations

import asyncio
import importlib
from pathlib import Path
import sys
import types
import unittest

ROOT = Path(__file__).resolve().parents[1]


def install_stubs() -> None:
    homeassistant = sys.modules.setdefault("homeassistant", types.ModuleType("homeassistant"))
    helpers = sys.modules.setdefault("homeassistant.helpers", types.ModuleType("homeassistant.helpers"))
    aiohttp_client = sys.modules.setdefault(
        "homeassistant.helpers.aiohttp_client",
        types.ModuleType("homeassistant.helpers.aiohttp_client"),
    )
    homeassistant.helpers = helpers
    aiohttp_client.async_get_clientsession = lambda hass: hass.session
    package = types.ModuleType("custom_components.djconnect")
    package.__path__ = [str(ROOT / "custom_components" / "djconnect")]
    sys.modules.setdefault("custom_components.djconnect", package)


class FakeResponse:
    def __init__(self, status=200, data=None):
        self.status = status
        self.data = data if data is not None else {"success": True}

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def json(self):
        return self.data


class FakeSession:
    def __init__(self, response=None):
        self.calls = []
        self.response = response or FakeResponse()

    def post(self, url, **kwargs):
        self.calls.append({"url": url, **kwargs})
        return self.response


class FakeConfigEntries:
    def __init__(self):
        self.updates = []

    def async_update_entry(self, entry, **kwargs):
        self.updates.append((entry, kwargs))
        if "options" in kwargs:
            entry.options = kwargs["options"]


class CentralApiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        install_stubs()
        cls.api = importlib.import_module("custom_components.djconnect.central_api")

    def setUp(self) -> None:
        self.original_session = self.api.async_get_clientsession
        self.api.async_get_clientsession = lambda hass: hass.session

    def tearDown(self) -> None:
        self.api.async_get_clientsession = self.original_session

    def _runtime(self, *, token="djci_old_token", proof: str | None = None):
        entry = types.SimpleNamespace(
            entry_id="entry-1",
            data={},
            options={
                "api_base_url": "https://api.djconnect.dev",
                "ha_install_id": "ha-install-1",
                "device_id": "djconnect-ios-ABCDEFGHIJKL",
                "client_type": "ios",
            },
        )
        if token:
            entry.options["djconnect_install_token"] = token
        status = {}
        if proof:
            status["central_api_bootstrap_proof"] = proof
            status["central_api_bootstrap_proof_expires_at"] = "2099-06-20T14:30:00Z"
        return types.SimpleNamespace(entry=entry, device_status=status)

    def test_missing_token_requires_bootstrap_proof(self) -> None:
        hass = types.SimpleNamespace(
            session=FakeSession(FakeResponse(data={"success": True, "install_token": "djci_created_token"})),
            config_entries=FakeConfigEntries(),
        )
        runtime = self._runtime(token=None)

        with self.assertRaises(self.api.DJConnectCentralApiError) as ctx:
            asyncio.run(
                self.api.async_post(
                    hass,
                    runtime,
                    "/v1/push/event",
                    {"event_type": "ask_dj_response"},
                )
            )

        self.assertEqual(str(ctx.exception), "missing_bootstrap_proof")
        self.assertEqual(hass.session.calls, [])

    def test_missing_token_bootstraps_with_pairing_proof(self) -> None:
        hass = types.SimpleNamespace(
            session=FakeSession(FakeResponse(data={"success": True, "install_token": "djci_created_token"})),
            config_entries=FakeConfigEntries(),
        )
        runtime = self._runtime(token=None, proof="djcboot_pairing_proof")

        result = asyncio.run(
            self.api.async_post(
                hass,
                runtime,
                "/v1/push/event",
                {"event_type": "ask_dj_response"},
            )
        )

        self.assertTrue(result["success"])
        self.assertEqual(len(hass.session.calls), 2)
        bootstrap_call = hass.session.calls[0]
        self.assertEqual(bootstrap_call["url"], "https://api.djconnect.dev/v1/install/token")
        self.assertNotIn("Authorization", bootstrap_call["headers"])
        self.assertEqual(bootstrap_call["json"]["bootstrap_proof"], "djcboot_pairing_proof")
        self.assertEqual(bootstrap_call["json"]["device_id"], "djconnect-ios-ABCDEFGHIJKL")
        self.assertEqual(bootstrap_call["json"]["client_type"], "ios")
        self.assertEqual(bootstrap_call["json"]["ha_install_id"], "ha-install-1")
        self.assertEqual(runtime.entry.options["djconnect_install_token"], "djci_created_token")
        self.assertEqual(hass.session.calls[1]["headers"]["Authorization"], "Bearer djci_created_token")

    def test_missing_token_gives_clear_config_error_when_bootstrap_fails(self) -> None:
        hass = types.SimpleNamespace(
            session=FakeSession(FakeResponse(status=503, data={"success": False, "error": "token_unavailable"})),
            config_entries=FakeConfigEntries(),
        )
        runtime = self._runtime(token=None, proof="djcboot_pairing_proof")

        with self.assertRaises(self.api.DJConnectCentralApiError) as ctx:
            asyncio.run(self.api.async_post(hass, runtime, "/v1/push/event", {}))

        self.assertEqual(str(ctx.exception), "token_unavailable")

    def test_authorization_uses_djci_install_token(self) -> None:
        hass = types.SimpleNamespace(session=FakeSession())
        runtime = self._runtime(token="djci_install_123")

        result = asyncio.run(
            self.api.async_post(
                hass,
                runtime,
                "/v1/push/event",
                {"event_type": "ask_dj_response", "history_revision": 1},
            )
        )

        self.assertTrue(result["success"])
        call = hass.session.calls[0]
        self.assertEqual(call["url"], "https://api.djconnect.dev/v1/push/event")
        self.assertEqual(call["headers"]["Authorization"], "Bearer djci_install_123")
        self.assertEqual(call["headers"]["Content-Type"], "application/json")
        self.assertEqual(call["json"]["ha_install_id"], "ha-install-1")

    def test_rotate_replaces_token_only_after_success(self) -> None:
        hass = types.SimpleNamespace(
            session=FakeSession(FakeResponse(data={"success": True, "install_token": "djci_new_token"})),
            config_entries=FakeConfigEntries(),
        )
        runtime = self._runtime(token="djci_old_token")

        result = asyncio.run(self.api.async_rotate_install_token(hass, runtime))

        self.assertTrue(result["success"])
        self.assertEqual(runtime.entry.options["djconnect_install_token"], "djci_new_token")
        self.assertEqual(
            hass.session.calls[0]["headers"]["Authorization"],
            "Bearer djci_old_token",
        )

    def test_failed_rotate_keeps_existing_token(self) -> None:
        hass = types.SimpleNamespace(
            session=FakeSession(FakeResponse(status=500, data={"success": False, "error": "boom"})),
            config_entries=FakeConfigEntries(),
        )
        runtime = self._runtime(token="djci_old_token")

        result = asyncio.run(self.api.async_rotate_install_token(hass, runtime))

        self.assertFalse(result["success"])
        self.assertEqual(runtime.entry.options["djconnect_install_token"], "djci_old_token")

    def test_source_contains_no_global_relay_or_apns_provider_secrets(self) -> None:
        forbidden = (
            "DJCONNECT_" + "RELAY_" + "SECRET",
            "DJCONNECT_PUSH_" + "RELAY_" + "SECRET",
            "APNS_" + "PRIVATE_" + "KEY",
        )
        roots = [ROOT / "custom_components" / "djconnect", ROOT / "tests"]
        for root in roots:
            for path in root.rglob("*"):
                if path.is_file() and path.suffix in {".py", ".json", ".yaml", ".yml"}:
                    text = path.read_text(encoding="utf-8")
                    for needle in forbidden:
                        self.assertNotIn(needle, text, f"{needle} found in {path}")


if __name__ == "__main__":
    unittest.main()
