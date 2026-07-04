from __future__ import annotations

import asyncio
import types
import unittest

from tests.test_http_voice_helpers import install_http_stubs

install_http_stubs()

from custom_components.djconnect import music_discovery  # noqa: E402
from custom_components.djconnect.const import CONF_CLIENT_TYPE, CONF_DEVICE_ID  # noqa: E402


class MusicDiscoveryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.runtime = _Runtime()
        self.hass = types.SimpleNamespace(
            data={"djconnect": {"runtime": self.runtime}},
            states=types.SimpleNamespace(get=lambda entity_id: None),
        )
        self.headers = {
            "Authorization": "Bearer token",
            "X-DJConnect-Device-ID": "djconnect-ios-ABCDEF123456",
        }

    def tearDown(self) -> None:
        music_discovery.run_music_command = self._original_run_music_command

    @property
    def _original_run_music_command(self):
        return getattr(self, "__original_run_music_command", music_discovery.run_music_command)

    @_original_run_music_command.setter
    def _original_run_music_command(self, value):
        setattr(self, "__original_run_music_command", value)

    def test_feed_disabled_until_music_dna_enabled(self) -> None:
        self.runtime.memory.enabled = False

        result, status = asyncio.run(
            music_discovery.async_handle_music_discovery_feed_payload(
                self.hass,
                _payload(),
                headers=self.headers,
                user_id="ha-user-1",
            )
        )

        self.assertEqual(status, 200)
        self.assertFalse(result["enabled"])
        self.assertEqual(result["reason"], "music_dna_disabled")
        self.assertEqual(result["sections"], [])

    def test_feed_uses_music_dna_signals_and_requires_reasons(self) -> None:
        result, status = asyncio.run(
            music_discovery.async_handle_music_discovery_feed_payload(
                self.hass,
                _payload(),
                headers=self.headers,
                user_id="ha-user-1",
            )
        )

        self.assertEqual(status, 200)
        self.assertTrue(result["enabled"])
        self.assertGreaterEqual(len(result["sections"]), 1)
        self.assertEqual(result["ttl_seconds"], music_discovery.DISCOVERY_TTL_SECONDS)
        for section in result["sections"]:
            self.assertTrue(section["items"])
            for item in section["items"]:
                self.assertIn(item["kind"], music_discovery.DISCOVERY_ITEM_KINDS)
                self.assertTrue(item["id"])
                self.assertTrue(item["title"])
                self.assertTrue(item["uri"])
                self.assertTrue(item["reason"])
                self.assertTrue(item["reason_sources"])

    def test_feed_cache_and_refresh_revision(self) -> None:
        first, _ = asyncio.run(
            music_discovery.async_handle_music_discovery_feed_payload(
                self.hass,
                _payload(),
                headers=self.headers,
                user_id="ha-user-1",
            )
        )
        second, _ = asyncio.run(
            music_discovery.async_handle_music_discovery_feed_payload(
                self.hass,
                _payload(),
                headers=self.headers,
                user_id="ha-user-1",
            )
        )

        self.assertEqual(first["revision"], second["revision"])
        self.assertTrue(second["cache"]["hit"])

    def test_play_validates_cached_item_starts_playback_and_records_feedback(self) -> None:
        calls = []
        self._original_run_music_command = music_discovery.run_music_command

        async def command(hass, runtime, command_name, value=None, *, play=None):
            calls.append((command_name, value, play))
            return {"success": True, "playback": {"track_name": "Intro"}}

        music_discovery.run_music_command = command
        feed, _ = asyncio.run(
            music_discovery.async_handle_music_discovery_feed_payload(
                self.hass,
                _payload(),
                headers=self.headers,
                user_id="ha-user-1",
            )
        )
        section = feed["sections"][0]
        item = section["items"][0]

        result, status = asyncio.run(
            music_discovery.async_handle_music_discovery_play_payload(
                self.hass,
                {
                    **_payload(),
                    "section_id": section["id"],
                    "discovery_item_id": item["id"],
                },
                headers=self.headers,
                user_id="ha-user-1",
            )
        )

        self.assertEqual(status, 200)
        self.assertTrue(result["played"])
        self.assertEqual(calls[0][0], "play_uris")
        self.assertTrue(calls[0][2])
        self.assertEqual(self.runtime.memory.discovery_plays[0]["discovery_item_id"], item["id"])
        self.assertEqual(self.runtime.memory.discovery_plays[0]["reason"], item["reason"])


def _payload() -> dict:
    return {
        "device_id": "djconnect-ios-ABCDEF123456",
        "client_type": "ios",
        "music_dna_key": "user:ha-user-1",
    }


class _Runtime:
    def __init__(self) -> None:
        self.device_token = "token"
        self.config = {
            CONF_CLIENT_TYPE: "ios",
            CONF_DEVICE_ID: "djconnect-ios-ABCDEF123456",
        }
        self.device_status = dict(self.config)
        self.memory = _Memory()

    def client_type(self) -> str:
        return "ios"

    def authorize_device_request(self, headers, body_device_id=None, client_type=None) -> bool:
        return (
            headers.get("Authorization") == "Bearer token"
            and body_device_id == "djconnect-ios-ABCDEF123456"
            and client_type == "ios"
        )


class _Memory:
    enabled = True

    def __init__(self) -> None:
        self.discovery_plays = []

    async def async_context_for_runtime(self, runtime, payload=None, *, user_id=None):
        return {
            "music_dna_key": f"user:{user_id}" if user_id else "user:test",
            "memory": {
                "enabled": self.enabled,
                "favorite_genres": ["ambient", "indie"],
                "favorite_artists": ["The xx"],
                "recent_tracks": [
                    {
                        "track_name": "Intro",
                        "artist": "The xx",
                        "uri": "spotify:track:intro",
                        "album_image_url": "/api/djconnect/image_proxy/art",
                    }
                ],
                "recent_favorite_tracks": [
                    {
                        "track_name": "Holocene",
                        "artist": "Bon Iver",
                        "uri": "spotify:track:holocene",
                    }
                ],
                "recommendation_plays": [
                    {
                        "title": "Recommended",
                        "subtitle": "Artist",
                        "uri": "spotify:track:recommended",
                        "reason": "Paste eerder goed bij je smaak.",
                    }
                ],
            },
        }

    async def async_record_discovery_play(self, runtime, item, payload=None, *, user_id=None):
        self.discovery_plays.append(
            {
                "discovery_item_id": item.get("id"),
                "reason": item.get("reason"),
                "section_id": (payload or {}).get("section_id"),
            }
        )
        return "user:test"


if __name__ == "__main__":
    unittest.main()
