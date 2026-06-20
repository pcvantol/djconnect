from __future__ import annotations

import asyncio
import importlib
import os
from pathlib import Path
import sys
import types
import unittest

ROOT = Path(__file__).resolve().parents[1]


def install_push_stubs() -> None:
    homeassistant = sys.modules.setdefault("homeassistant", types.ModuleType("homeassistant"))
    helpers = sys.modules.setdefault("homeassistant.helpers", types.ModuleType("homeassistant.helpers"))
    aiohttp_client = sys.modules.setdefault(
        "homeassistant.helpers.aiohttp_client",
        types.ModuleType("homeassistant.helpers.aiohttp_client"),
    )
    storage = sys.modules.setdefault(
        "homeassistant.helpers.storage",
        types.ModuleType("homeassistant.helpers.storage"),
    )
    homeassistant.helpers = helpers

    class Store:
        def __init__(self, *args, **kwargs):
            self.data = None

        async def async_load(self):
            return self.data

        async def async_save(self, data):
            self.data = data

    if not hasattr(storage, "Store"):
        storage.Store = Store
    if not hasattr(aiohttp_client, "async_get_clientsession"):
        aiohttp_client.async_get_clientsession = lambda hass: None
    package = types.ModuleType("custom_components.djconnect")
    package.__path__ = [str(ROOT / "custom_components" / "djconnect")]
    sys.modules.setdefault("custom_components.djconnect", package)


class FakeStore:
    def __init__(self, data=None):
        self.data = data
        self.saved = None

    async def async_load(self):
        return self.data

    async def async_save(self, data):
        self.saved = data
        self.data = data


class PushTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        install_push_stubs()
        cls.push = importlib.import_module("custom_components.djconnect.push")

    def test_register_stores_user_device_client_token_metadata(self) -> None:
        store = FakeStore()
        manager = self.push.PushRegistrationManager(store=store)

        result = asyncio.run(
            manager.async_register(
                user_id="user-1",
                payload={
                    "device_id": "djconnect-ios-ABCDEFGHIJKL",
                    "client_type": "ios",
                    "push_token": "token-secret-value",
                    "push_environment": "production",
                    "app_bundle_id": "dev.djconnect.app",
                    "app_version": "3.1.66",
                    "locale": "nl-NL",
                    "notification_categories": ["ask_dj_response", "playback_change"],
                },
            )
        )

        self.assertTrue(result["success"])
        registration = next(iter(store.saved["registrations"].values()))
        self.assertEqual(registration["user_id"], "user-1")
        self.assertEqual(registration["device_id"], "djconnect-ios-ABCDEFGHIJKL")
        self.assertEqual(registration["client_type"], "ios")
        self.assertEqual(registration["push_environment"], "production")
        self.assertEqual(registration["categories"], ["ask_dj_response", "playback_change"])
        self.assertNotEqual(registration["push_token_hash"], "token-secret-value")

    def test_unregister_disables_token(self) -> None:
        store = FakeStore()
        manager = self.push.PushRegistrationManager(store=store)
        payload = {
            "device_id": "djconnect-watchos-ABCDEFGHIJKL",
            "client_type": "watchos",
            "push_token": "watch-token",
        }

        asyncio.run(manager.async_register(user_id="user-1", payload=payload))
        result = asyncio.run(manager.async_unregister(user_id="user-1", payload=payload))

        self.assertTrue(result["success"])
        registration = next(iter(store.saved["registrations"].values()))
        self.assertTrue(registration["disabled"])

    def test_payload_contains_no_prompt_or_response_text(self) -> None:
        payload = self.push.build_apns_payload(
            event_type="ask_dj_response",
            history_revision=123,
            client_message_id="client-1",
            device_id="djconnect-ios-ABCDEFGHIJKL",
        )
        rendered = str(payload)

        self.assertEqual(payload["event_type"], "ask_dj_response")
        self.assertEqual(payload["history_revision"], 123)
        self.assertIn("Ask DJ heeft geantwoord.", rendered)
        self.assertNotIn("spotify_refresh_token", rendered)
        self.assertNotIn("raw prompt", rendered)
        self.assertNotIn("assistant response", rendered)

    def test_payload_without_optional_sync_fields_is_valid(self) -> None:
        payload = self.push.build_apns_payload(event_type="ask_dj_response")

        self.assertEqual(payload["event_type"], "ask_dj_response")
        self.assertNotIn("history_revision", payload)
        self.assertNotIn("client_message_id", payload)

    def test_disabled_without_credentials_does_not_raise(self) -> None:
        old_env = {key: os.environ.get(key) for key in ("APNS_TEAM_ID", "APNS_KEY_ID", "APNS_PRIVATE_KEY")}
        for key in old_env:
            os.environ.pop(key, None)
        try:
            hass = types.SimpleNamespace(data={})
            manager = self.push.PushRegistrationManager(store=FakeStore())
            client = self.push.APNsClient(hass, manager)
            result = asyncio.run(
                client.send_event(user_id="user-1", event_type="ask_dj_response", history_revision=1)
            )
        finally:
            for key, value in old_env.items():
                if value is not None:
                    os.environ[key] = value

        self.assertTrue(result["success"])
        self.assertFalse(result["push_supported"])
        self.assertTrue(result["disabled"])

    def test_invalid_apns_token_marks_registration_invalid(self) -> None:
        store = FakeStore()
        manager = self.push.PushRegistrationManager(store=store)
        registration_payload = {
            "device_id": "djconnect-ios-ABCDEFGHIJKL",
            "client_type": "ios",
            "push_token": "bad-token",
        }
        asyncio.run(manager.async_register(user_id="user-1", payload=registration_payload))
        registration = next(iter(store.saved["registrations"].values()))

        asyncio.run(manager.async_mark_error(registration, "BadDeviceToken", invalid=True))

        updated = next(iter(store.saved["registrations"].values()))
        self.assertTrue(updated["invalid"])
        self.assertTrue(updated["disabled"])
        self.assertEqual(updated["last_error_code"], "BadDeviceToken")

    def test_environment_base_urls(self) -> None:
        self.assertEqual(
            self.push._apns_base_url("sandbox"),
            "https://api.sandbox.push.apple.com",
        )
        self.assertEqual(
            self.push._apns_base_url("production"),
            "https://api.push.apple.com",
        )


if __name__ == "__main__":
    unittest.main()
