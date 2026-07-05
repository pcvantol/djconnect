from __future__ import annotations

import asyncio
import importlib
import logging
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

    def test_unauthorized_music_dna_import_is_rejected(self) -> None:
        self.api_handlers.authorize_runtime_device_request = (
            lambda runtime, headers, device_id=None, client_type=None: False
        )

        result, status = asyncio.run(
            self.api_handlers.async_handle_music_dna_import_payload(
                self.hass,
                {
                    "device_id": "djconnect-ios-ABCDEFGHIJKL",
                    "client_type": "ios",
                    "profile": {
                        "success": True,
                        "enabled": True,
                        "profile": {"favorite_artists": ["The xx"]},
                    },
                },
                headers={"Authorization": "Bearer wrong"},
                user_id="ha-user-1",
            )
        )

        self.assertEqual(status, 401)
        self.assertEqual(result["error"], "unauthorized")

    def test_unauthorized_music_dna_export_is_rejected(self) -> None:
        self.api_handlers.authorize_runtime_device_request = (
            lambda runtime, headers, device_id=None, client_type=None: False
        )

        result, status = asyncio.run(
            self.api_handlers.async_handle_music_dna_export_payload(
                self.hass,
                {"device_id": "djconnect-ios-ABCDEFGHIJKL", "client_type": "ios"},
                headers={"Authorization": "Bearer wrong"},
                user_id="ha-user-1",
            )
        )

        self.assertEqual(status, 401)
        self.assertEqual(result["error"], "unauthorized")

    def test_export_returns_backend_envelope_with_profile_response(self) -> None:
        asyncio.run(
            self.memory.async_set_enabled(
                self.runtime,
                True,
                {"client_type": "ios", "app_version": "3.2.21"},
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
            self.api_handlers.async_handle_music_dna_export_payload(
                self.hass,
                {
                    "identity": {
                        "device_id": "djconnect-ios-ABCDEFGHIJKL",
                        "client_type": "ios",
                        "device_name": "iPhone",
                    },
                    "app_version": "3.2.21",
                },
                headers={"Authorization": "Bearer token"},
                user_id="ha-user-1",
            )
        )

        self.assertEqual(status, 200)
        self.assertTrue(result["success"])
        self.assertEqual(result["format"], "djconnect.music_dna.export")
        self.assertEqual(result["schema_version"], 1)
        self.assertEqual(result["exported_by_client_type"], "ios")
        self.assertEqual(result["app_version"], "3.2.21")
        self.assertIn("exported_at", result)
        self.assertTrue(result["profile"]["success"])
        self.assertTrue(result["profile"]["enabled"])
        self.assertEqual(result["profile"]["music_dna_key"], "user:ha-user-1")
        self.assertEqual(result["profile"]["profile"]["recent_tracks"][0]["artist"], "The xx")

    def test_import_disabled_music_dna_returns_conflict(self) -> None:
        result, status = asyncio.run(
            self.api_handlers.async_handle_music_dna_import_payload(
                self.hass,
                {
                    "device_id": "djconnect-ios-ABCDEFGHIJKL",
                    "client_type": "ios",
                    "profile": {
                        "success": True,
                        "music_dna_key": "user:ha-user-1",
                        "enabled": True,
                        "generation": 7,
                        "profile": {"favorite_artists": ["The xx"]},
                        "sources": [],
                    },
                },
                headers={"Authorization": "Bearer token"},
                user_id="ha-user-1",
            )
        )

        self.assertEqual(status, 409)
        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "music_dna_not_enabled")

    def test_import_overwrites_existing_profile_and_bumps_generation(self) -> None:
        enabled, status = asyncio.run(
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
        before_generation = enabled["generation"]
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

        previous = self.api_handlers._LOGGER.level
        self.api_handlers._LOGGER.setLevel(logging.DEBUG)
        try:
            with self.assertLogs(self.api_handlers._LOGGER, level="DEBUG") as captured:
                result, status = asyncio.run(
                    self.api_handlers.async_handle_music_dna_import_payload(
                        self.hass,
                        {
                            "identity": {
                                "device_id": "djconnect-ios-ABCDEFGHIJKL",
                                "client_type": "ios",
                                "device_name": "iPhone",
                            },
                            "language": "nl",
                            "profile": {
                                "format": "djconnect.music_dna.export",
                                "schema_version": 1,
                                "exported_at": "2026-07-04T19:30:00Z",
                                "exported_by_client_type": "ios",
                                "app_version": "3.2.20",
                                "profile": {
                                    "success": True,
                                    "music_dna_key": "user:ha-user-1",
                                    "enabled": True,
                                    "generation": 12,
                                    "updated_at": "2026-07-04T19:30:00Z",
                                    "profile": {
                                        "favorite_artists": ["Bicep"],
                                        "favorite_genres": ["electronica"],
                                        "recent_tracks": [
                                            {
                                                "title": "Glue",
                                                "artist": "Bicep",
                                                "uri": "spotify:track:glue",
                                            }
                                        ],
                                        "mood": {"value": 88, "zone": "party"},
                                    },
                                    "sources": [],
                                },
                            },
                        },
                        headers={"Authorization": "Bearer token"},
                        user_id="ha-user-1",
                    )
                )
        finally:
            self.api_handlers._LOGGER.setLevel(previous)
        logs = "\n".join(captured.output)
        self.assertIn("Music DNA import request", logs)
        self.assertIn("Music DNA import result", logs)
        self.assertIn("djconnect.music_dna.export", logs)
        self.assertNotIn("Bicep", logs)
        self.assertNotIn("Glue", logs)
        self.assertNotIn("spotify:track:glue", logs)
        self.assertNotIn("Bearer token", logs)

        self.assertEqual(status, 200)
        self.assertTrue(result["success"])
        self.assertTrue(result["enabled"])
        self.assertGreater(result["generation"], before_generation)
        self.assertEqual(result["profile"]["favorite_artists"][0]["name"], "Bicep")
        self.assertEqual(result["profile"]["favorite_genres"][0]["name"], "electronica")
        self.assertEqual(result["profile"]["recent_tracks"][0]["title"], "Glue")
        self.assertEqual(result["profile"]["mood"]["value"], 88)
        self.assertEqual(result["profile"]["mood"]["zone"], "party")
        self.assertNotEqual(result["profile"]["recent_tracks"][0]["artist"], "The xx")

        profile, status = asyncio.run(
            self.api_handlers.async_handle_music_dna_profile_payload(
                self.hass,
                {"device_id": "djconnect-ios-ABCDEFGHIJKL", "client_type": "ios"},
                headers={"Authorization": "Bearer token"},
                user_id="ha-user-1",
            )
        )

        self.assertEqual(status, 200)
        self.assertEqual(profile["generation"], result["generation"])
        self.assertEqual(profile["profile"]["favorite_artists"][0]["name"], "Bicep")
        self.assertEqual(profile["profile"]["recent_tracks"][0]["title"], "Glue")


if __name__ == "__main__":
    unittest.main()
