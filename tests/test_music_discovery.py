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
            "X-DJConnect-Client-Type": "ios",
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
                self.assertIsInstance(item["quality_score"], int)
                self.assertGreaterEqual(item["quality_score"], 0)
                self.assertLessEqual(item["quality_score"], 100)
                self.assertIn(item["quality_band"], {"low", "medium", "high"})
                self.assertTrue(item["quality_factors"])

    def test_feed_includes_expanded_backend_owned_sections(self) -> None:
        result, status = asyncio.run(
            music_discovery.async_handle_music_discovery_feed_payload(
                self.hass,
                _payload(),
                headers=self.headers,
                user_id="ha-user-1",
                force_refresh=True,
            )
        )

        self.assertEqual(status, 200)
        section_ids = [section["id"] for section in result["sections"]]
        self.assertIn("rediscover", section_ids)
        self.assertIn("artist_spotlight", section_ids)
        self.assertIn("accepted_recommendations", section_ids)
        rediscover = next(section for section in result["sections"] if section["id"] == "rediscover")
        self.assertEqual(rediscover["items"][0]["uri"], "spotify:track:top-track")
        artist_spotlight = next(section for section in result["sections"] if section["id"] == "artist_spotlight")
        self.assertEqual(artist_spotlight["items"][0]["uri"], "spotify:artist:the-xx")

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

    def test_feed_rebuilds_cached_feed_when_music_dna_context_changes(self) -> None:
        calls = []
        self._original_run_music_command = music_discovery.run_music_command

        async def command(hass, runtime, command_name, value=None, *, play=None):
            calls.append(command_name)
            if command_name == "artist_recommendations":
                suffix = len(calls)
                return {
                    "success": True,
                    "recommended_tracks": [
                        {
                            "track_name": f"Fresh Discovery {suffix}",
                            "artist": "New Artist",
                            "uri": f"spotify:track:fresh-discovery-{suffix}",
                        }
                    ],
                }
            return {"success": True, "tracks": []}

        music_discovery.run_music_command = command
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

        self.runtime.memory.recent_tracks = [
            {
                "track_name": "New Context Track",
                "artist": "Context Artist",
                "uri": "spotify:track:new-context",
            }
        ]
        third, _ = asyncio.run(
            music_discovery.async_handle_music_discovery_feed_payload(
                self.hass,
                _payload(),
                headers=self.headers,
                user_id="ha-user-1",
            )
        )

        self.assertGreater(third["revision"], second["revision"])
        self.assertFalse(third["cache"]["hit"])
        self.assertEqual(calls, ["artist_recommendations", "artist_recommendations"])

    def test_feed_writes_debug_logging_for_diagnostics(self) -> None:
        with self.assertLogs("custom_components.djconnect.music_discovery", level="DEBUG") as logs:
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
        output = "\n".join(logs.output)
        self.assertIn("Music Discovery feed request received", output)
        self.assertIn("Music Discovery feed built", output)
        self.assertIn("client_type=ios", output)
        self.assertIn("items=", output)

    def test_feed_does_not_publish_recent_tracks_as_discovery_items(self) -> None:
        self.runtime.memory.recent_tracks = [
            {
                "track_name": "Strobe - Radio Edit",
                "artist": "deadmau5",
                "uri": "spotify:track:strobe-radio-edit",
            },
            {
                "track_name": "Strobe - Radio Edit",
                "artist": "deadmau5",
                "uri": "spotify:track:strobe-radio-edit",
            },
            {
                "track_name": "Strobe - Radio Edit",
                "artist": "deadmau5",
                "uri": "spotify:track:strobe-radio-edit",
            },
            {
                "track_name": "Strobe - Radio Edit",
                "artist": "deadmau5",
                "uri": "spotify:track:strobe-radio-edit",
            },
        ]

        result, status = asyncio.run(
            music_discovery.async_handle_music_discovery_feed_payload(
                self.hass,
                _payload(),
                headers=self.headers,
                user_id="ha-user-1",
            )
        )

        self.assertEqual(status, 200)
        uris = [
            item["uri"]
            for section in result["sections"]
            for item in section["items"]
        ]
        self.assertNotIn("spotify:track:strobe-radio-edit", uris)

    def test_feed_refreshes_stale_recently_played_from_backend_history(self) -> None:
        calls = []
        self.runtime.memory.listening_profile_fresh = False
        self._original_run_music_command = music_discovery.run_music_command

        async def command(hass, runtime, command_name, value=None, *, play=None):
            calls.append((command_name, value, play))
            if command_name == "recently_played":
                return {
                    "success": True,
                    "tracks": [
                        {
                            "id": "native-spotify",
                            "track_name": "Native Spotify Track",
                            "artist": "Outside DJConnect",
                            "uri": "spotify:track:native-spotify",
                        }
                    ],
                }
            if command_name == "artist_recommendations":
                return {
                    "success": True,
                    "recommended_tracks": [
                        {
                            "track_name": "Native Spotify Track",
                            "artist": "Outside DJConnect",
                            "uri": "spotify:track:native-spotify",
                        },
                        {
                            "track_name": "Fresh Discovery",
                            "artist": "New Artist",
                            "uri": "spotify:track:fresh-discovery",
                        },
                    ],
                }
            raise AssertionError(f"unexpected command: {command_name}")

        music_discovery.run_music_command = command

        result, status = asyncio.run(
            music_discovery.async_handle_music_discovery_feed_payload(
                self.hass,
                _payload(),
                headers=self.headers,
                user_id="ha-user-1",
            )
        )

        self.assertEqual(status, 200)
        self.assertEqual([call[0] for call in calls], ["recently_played", "artist_recommendations"])
        self.assertEqual(
            self.runtime.memory.listening_profile_ttl_seconds,
            music_discovery.DISCOVERY_RECENTLY_PLAYED_REFRESH_SECONDS,
        )
        self.assertEqual(self.runtime.memory.listening_profile_ttl_seconds, 60 * 60)
        self.assertEqual(self.runtime.memory.updated_profiles[0]["sources"], ["spotify_recently_played"])
        section = next(section for section in result["sections"] if section["id"] == "new_for_you")
        self.assertEqual(section["items"][0]["uri"], "spotify:track:fresh-discovery")
        self.assertIn("The xx", section["items"][0]["reason"])
        self.assertIn("ambient", section["items"][0]["reason"])
        self.assertIn("music_dna_artists", section["items"][0]["reason_sources"])
        self.assertIn("music_dna_genres", section["items"][0]["reason_sources"])
        self.assertNotIn("spotify:track:native-spotify", [item["uri"] for item in section["items"]])

    def test_macos_feed_accepts_client_type_from_headers(self) -> None:
        runtime = _Runtime(
            client_type="macos",
            device_id="djconnect-macos-ABCDEF123456",
        )
        hass = types.SimpleNamespace(
            data={"djconnect": {"runtime": runtime}},
            states=types.SimpleNamespace(get=lambda entity_id: None),
        )

        result, status = asyncio.run(
            music_discovery.async_handle_music_discovery_feed_payload(
                hass,
                {"music_dna_key": "user:ha-user-1"},
                headers={
                    "Authorization": "Bearer token",
                    "X-DJConnect-Device-ID": "djconnect-macos-ABCDEF123456",
                    "X-DJConnect-Client-Type": "macos",
                },
                user_id="ha-user-1",
            )
        )

        self.assertEqual(status, 200)
        self.assertTrue(result["enabled"])
        self.assertNotEqual(result.get("reason"), "invalid_client_type")

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
        calls.clear()

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
        self.assertNotIn(
            "context_signature",
            self.runtime.music_discovery_cache["user:ha-user-1"],
        )

    def test_negative_feedback_records_signal_and_removes_cached_item(self) -> None:
        self._original_run_music_command = music_discovery.run_music_command

        async def command(hass, runtime, command_name, value=None, *, play=None):
            if command_name == "artist_recommendations":
                return {
                    "success": True,
                    "recommended_tracks": [
                        {
                            "track_name": "Fresh Discovery",
                            "artist": "New Artist",
                            "uri": "spotify:track:fresh-discovery",
                        }
                    ],
                }
            return {"success": True, "tracks": []}

        music_discovery.run_music_command = command
        feed, _ = asyncio.run(
            music_discovery.async_handle_music_discovery_feed_payload(
                self.hass,
                _payload(),
                headers=self.headers,
                user_id="ha-user-1",
                force_refresh=True,
            )
        )
        section = next(section for section in feed["sections"] if section["id"] == "new_for_you")
        item = section["items"][0]

        result, status = asyncio.run(
            music_discovery.async_handle_music_discovery_feedback_payload(
                self.hass,
                {
                    **_payload(),
                    "section_id": section["id"],
                    "discovery_item_id": item["id"],
                    "feedback": "hide_artist",
                },
                headers=self.headers,
                user_id="ha-user-1",
            )
        )

        self.assertEqual(status, 200)
        self.assertTrue(result["success"])
        self.assertEqual(result["feedback"], "hide_artist")
        self.assertTrue(result["music_dna_feedback_recorded"])
        self.assertEqual(self.runtime.memory.blocked_preferences[0]["kind"], "artist")
        self.assertEqual(self.runtime.memory.blocked_preferences[0]["name"], "New Artist")
        cached = self.runtime.music_discovery_cache["user:ha-user-1"]["response"]
        cached_uris = [
            cached_item["uri"]
            for cached_section in cached["sections"]
            for cached_item in cached_section["items"]
        ]
        self.assertNotIn(item["uri"], cached_uris)

    def test_feed_filters_blocked_items_and_artists(self) -> None:
        self.runtime.memory.blocked_items = [{"kind": "track", "name": "Blocked Track"}]
        self.runtime.memory.blocked_artists = [{"kind": "artist", "name": "Blocked Artist"}]
        self._original_run_music_command = music_discovery.run_music_command

        async def command(hass, runtime, command_name, value=None, *, play=None):
            if command_name == "artist_recommendations":
                return {
                    "success": True,
                    "recommended_tracks": [
                        {
                            "track_name": "Blocked Track",
                            "artist": "Allowed Artist",
                            "uri": "spotify:track:blocked-track",
                        },
                        {
                            "track_name": "Allowed Track",
                            "artist": "Blocked Artist",
                            "uri": "spotify:track:blocked-artist",
                        },
                        {
                            "track_name": "Fresh Discovery",
                            "artist": "New Artist",
                            "uri": "spotify:track:fresh-discovery",
                        },
                    ],
                }
            return {"success": True, "tracks": []}

        music_discovery.run_music_command = command

        result, status = asyncio.run(
            music_discovery.async_handle_music_discovery_feed_payload(
                self.hass,
                _payload(),
                headers=self.headers,
                user_id="ha-user-1",
                force_refresh=True,
            )
        )

        self.assertEqual(status, 200)
        section = next(section for section in result["sections"] if section["id"] == "new_for_you")
        self.assertEqual([item["uri"] for item in section["items"]], ["spotify:track:fresh-discovery"])

    def test_feed_dedupes_title_variants_album_overlap_and_artist_overload(self) -> None:
        self._original_run_music_command = music_discovery.run_music_command

        async def command(hass, runtime, command_name, value=None, *, play=None):
            if command_name == "artist_recommendations":
                return {
                    "success": True,
                    "recommended_tracks": [
                        {
                            "track_name": "Ocean Drive",
                            "artist": "Duke Dumont",
                            "album": "Ocean Drive",
                            "uri": "spotify:track:ocean-drive",
                        },
                        {
                            "track_name": "Ocean Drive - Radio Edit",
                            "artist": "Duke Dumont",
                            "album": "Ocean Drive",
                            "uri": "spotify:track:ocean-drive-radio",
                        },
                        {
                            "track_name": "Ocean Drive - Live 2024 Remaster",
                            "artist": "Duke Dumont",
                            "album": "Ocean Drive",
                            "uri": "spotify:track:ocean-drive-live",
                        },
                        {
                            "track_name": "Need U",
                            "artist": "Duke Dumont",
                            "uri": "spotify:track:need-u",
                        },
                        {
                            "track_name": "Won't Look Back",
                            "artist": "Duke Dumont",
                            "uri": "spotify:track:wont-look-back",
                        },
                        {
                            "track_name": "Fresh Discovery",
                            "artist": "New Artist",
                            "uri": "spotify:track:fresh-discovery",
                        },
                    ],
                }
            return {"success": True, "tracks": []}

        music_discovery.run_music_command = command

        result, status = asyncio.run(
            music_discovery.async_handle_music_discovery_feed_payload(
                self.hass,
                _payload(),
                headers=self.headers,
                user_id="ha-user-1",
                force_refresh=True,
            )
        )

        self.assertEqual(status, 200)
        section = next(section for section in result["sections"] if section["id"] == "new_for_you")
        self.assertEqual(
            [item["uri"] for item in section["items"]],
            ["spotify:track:ocean-drive", "spotify:track:need-u", "spotify:track:fresh-discovery"],
        )

    def test_quality_score_promotes_stronger_profile_matches(self) -> None:
        self._original_run_music_command = music_discovery.run_music_command

        async def command(hass, runtime, command_name, value=None, *, play=None):
            if command_name == "artist_recommendations":
                return {
                    "success": True,
                    "recommended_tracks": [
                        {
                            "track_name": "Good Unknown",
                            "artist": "Unknown Artist",
                            "uri": "spotify:track:unknown",
                        },
                        {
                            "track_name": "Strong Match",
                            "artist": "The xx",
                            "uri": "spotify:track:strong-match",
                            "album_image_url": "/api/djconnect/v1/image_proxy/strong",
                        },
                    ],
                }
            return {"success": True, "tracks": []}

        music_discovery.run_music_command = command

        result, status = asyncio.run(
            music_discovery.async_handle_music_discovery_feed_payload(
                self.hass,
                _payload(),
                headers=self.headers,
                user_id="ha-user-1",
                force_refresh=True,
            )
        )

        self.assertEqual(status, 200)
        section = next(section for section in result["sections"] if section["id"] == "new_for_you")
        self.assertEqual(section["items"][0]["uri"], "spotify:track:strong-match")
        self.assertGreater(section["items"][0]["quality_score"], section["items"][1]["quality_score"])
        self.assertEqual(section["items"][0]["quality_band"], "high")
        self.assertIn("favorite_artist_match", section["items"][0]["quality_factors"])


def _payload() -> dict:
    return {
        "device_id": "djconnect-ios-ABCDEF123456",
        "client_type": "ios",
        "music_dna_key": "user:ha-user-1",
    }


class _Runtime:
    def __init__(
        self,
        *,
        client_type: str = "ios",
        device_id: str = "djconnect-ios-ABCDEF123456",
    ) -> None:
        self.device_token = "token"
        self.config = {
            CONF_CLIENT_TYPE: client_type,
            CONF_DEVICE_ID: device_id,
        }
        self.device_status = dict(self.config)
        self.memory = _Memory()

    def client_type(self) -> str:
        return self.config[CONF_CLIENT_TYPE]

    def authorize_device_request(self, headers, body_device_id=None, client_type=None) -> bool:
        return (
            headers.get("Authorization") == "Bearer token"
            and body_device_id == self.config[CONF_DEVICE_ID]
            and client_type == self.config[CONF_CLIENT_TYPE]
        )


class _Memory:
    enabled = True

    def __init__(self) -> None:
        self.discovery_plays = []
        self.blocked_preferences = []
        self.blocked_items = []
        self.blocked_artists = []
        self.listening_profile_fresh = True
        self.listening_profile_ttl_seconds = None
        self.updated_profiles = []
        self.recent_tracks = [
            {
                "track_name": "Intro",
                "artist": "The xx",
                "uri": "spotify:track:intro",
                "album_image_url": "/api/djconnect/v1/image_proxy/art",
            }
        ]

    async def async_context_for_runtime(self, runtime, payload=None, *, user_id=None):
        return {
            "music_dna_key": f"user:{user_id}" if user_id else "user:test",
            "memory": {
                "enabled": self.enabled,
                "favorite_genres": ["ambient", "indie"],
                "favorite_artists": ["The xx"],
                "recent_tracks": self.recent_tracks,
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
                "blocked_items": self.blocked_items,
                "blocked_artists": self.blocked_artists,
                "listening_profile": {
                    "top_tracks_by_range": {
                        "medium_term": [
                            {
                                "title": "Top Track",
                                "artist": "The xx",
                                "uri": "spotify:track:top-track",
                            }
                        ]
                    },
                    "top_artists_by_range": {
                        "medium_term": [
                            {
                                "name": "The xx",
                                "uri": "spotify:artist:the-xx",
                            }
                        ]
                    },
                },
            },
        }

    async def async_listening_profile_is_fresh(self, runtime, payload=None, *, user_id=None, ttl_seconds=0):
        self.listening_profile_ttl_seconds = ttl_seconds
        return self.listening_profile_fresh

    async def async_update_listening_profile(self, runtime, profile, payload=None, *, user_id=None):
        self.updated_profiles.append(profile)
        self.recent_tracks = [
            track for track in profile.get("recent_tracks") or [] if isinstance(track, dict)
        ]
        self.listening_profile_fresh = True
        return "user:test"

    async def async_record_discovery_play(self, runtime, item, payload=None, *, user_id=None):
        self.discovery_plays.append(
            {
                "discovery_item_id": item.get("id"),
                "reason": item.get("reason"),
                "section_id": (payload or {}).get("section_id"),
            }
        )
        return "user:test"

    async def async_record_blocked_music_preference(self, runtime, item, payload=None, *, user_id=None):
        self.blocked_preferences.append(item)
        if item.get("kind") == "artist":
            self.blocked_artists.insert(0, item)
        else:
            self.blocked_items.insert(0, item)
        return "user:test"


if __name__ == "__main__":
    unittest.main()
