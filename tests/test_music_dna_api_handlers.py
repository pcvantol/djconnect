from __future__ import annotations

import asyncio
import importlib
from pathlib import Path
import sys
import types
import unittest

from tests.test_http_voice_helpers import install_http_stubs


ROOT = Path(__file__).resolve().parents[1]


def runtime_for(memory):
    return types.SimpleNamespace(
        memory=memory,
        entry=types.SimpleNamespace(entry_id="entry-1"),
        config={},
        pairing_device_id="djconnect-ios-ABCDEFGHIJKL",
        device_status={
            "device_id": "djconnect-ios-ABCDEFGHIJKL",
            "client_type": "ios",
            "device_name": "iPhone",
        },
        client_type=lambda: "ios",
    )


class FakeStore:
    def __init__(self):
        self.data = None
        self.saved = None

    async def async_load(self):
        return self.data

    async def async_save(self, data):
        self.saved = data
        self.data = data


class MusicDnaApiHandlersTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        install_http_stubs()
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        cls.api_handlers = importlib.import_module("custom_components.djconnect.api_handlers")
        cls.music_dna = importlib.import_module("custom_components.djconnect.music_dna")

    def setUp(self) -> None:
        self.store = FakeStore()
        self.memory = self.music_dna.MusicDNAManager(store=self.store)
        self.runtime = runtime_for(self.memory)
        self.hass = types.SimpleNamespace()
        self._original_resolve_runtime = self.api_handlers.resolve_runtime
        self._original_authorize = self.api_handlers.authorize_runtime_device_request
        self.api_handlers.resolve_runtime = lambda hass, device_id, headers=None: self.runtime
        self.api_handlers.authorize_runtime_device_request = (
            lambda runtime, headers, device_id=None, client_type=None: True
        )

    def tearDown(self) -> None:
        self.api_handlers.resolve_runtime = self._original_resolve_runtime
        self.api_handlers.authorize_runtime_device_request = self._original_authorize

    def test_profile_returns_disabled_empty_profile_before_opt_in(self) -> None:
        result, status = asyncio.run(
            self.api_handlers.async_handle_music_dna_profile_payload(
                self.hass,
                {"device_id": "djconnect-ios-ABCDEFGHIJKL", "client_type": "ios"},
                headers={"Authorization": "Bearer token"},
                user_id="ha-user-1",
            )
        )

        self.assertEqual(status, 200)
        self.assertTrue(result["success"])
        self.assertFalse(result["enabled"])
        self.assertEqual(result["profile"], {})
        self.assertEqual(result["music_dna_key"], "user:ha-user-1")

    def test_settings_enables_music_dna_and_profile_returns_structured_data(self) -> None:
        result, status = asyncio.run(
            self.api_handlers.async_handle_music_dna_settings_payload(
                self.hass,
                {
                    "device_id": "djconnect-ios-ABCDEFGHIJKL",
                    "client_type": "ios",
                    "enabled": True,
                    "mood": 65,
                },
                headers={"Authorization": "Bearer token"},
                user_id="ha-user-1",
            )
        )
        self.assertEqual(status, 200)
        self.assertTrue(result["enabled"])

        asyncio.run(
            self.memory.async_update_last_ask_dj(
                self.runtime,
                input_text="Draai The xx",
                result={
                    "intent": {"intent": "play_music"},
                    "dj_text": "Komt eraan.",
                    "playback": {"track": {"title": "Intro", "artist": "The xx"}},
                },
                payload={"client_type": "ios"},
                user_id="ha-user-1",
            )
        )
        profile, status = asyncio.run(
            self.api_handlers.async_handle_music_dna_profile_payload(
                self.hass,
                {"device_id": "djconnect-ios-ABCDEFGHIJKL", "client_type": "ios"},
                headers={"Authorization": "Bearer token"},
                user_id="ha-user-1",
            )
        )

        self.assertEqual(status, 200)
        self.assertTrue(profile["enabled"])
        self.assertEqual(profile["profile"]["recent_tracks"][0]["artist"], "The xx")
        self.assertEqual(profile["profile"]["mood"]["value"], 65)

    def test_clear_preserves_opt_in_and_returns_empty_enabled_profile(self) -> None:
        asyncio.run(
            self.memory.async_set_enabled(
                self.runtime,
                True,
                {"client_type": "ios"},
                user_id="ha-user-1",
            )
        )
        asyncio.run(
            self.memory.async_update_last_ask_dj(
                self.runtime,
                input_text="Draai The xx",
                result={
                    "intent": {"intent": "play_music"},
                    "dj_text": "Komt eraan.",
                    "playback": {"track": {"title": "Intro", "artist": "The xx"}},
                },
                payload={"client_type": "ios"},
                user_id="ha-user-1",
            )
        )

        result, status = asyncio.run(
            self.api_handlers.async_handle_music_dna_clear_payload(
                self.hass,
                {"device_id": "djconnect-ios-ABCDEFGHIJKL", "client_type": "ios"},
                headers={"Authorization": "Bearer token"},
                user_id="ha-user-1",
            )
        )

        self.assertEqual(status, 200)
        self.assertTrue(result["enabled"])
        self.assertNotIn("recent_tracks", result["profile"])
        self.assertGreaterEqual(result["generation"], 1)

    def test_unauthorized_music_dna_request_is_rejected(self) -> None:
        self.api_handlers.authorize_runtime_device_request = (
            lambda runtime, headers, device_id=None, client_type=None: False
        )

        result, status = asyncio.run(
            self.api_handlers.async_handle_music_dna_profile_payload(
                self.hass,
                {"device_id": "djconnect-ios-ABCDEFGHIJKL", "client_type": "ios"},
                headers={"Authorization": "Bearer wrong"},
            )
        )

        self.assertEqual(status, 401)
        self.assertEqual(result["error"], "unauthorized")


if __name__ == "__main__":
    unittest.main()
