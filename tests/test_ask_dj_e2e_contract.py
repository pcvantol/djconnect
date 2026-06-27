from __future__ import annotations

import asyncio
from datetime import timedelta
import importlib
from pathlib import Path
import types
import unittest

from tests.ask_dj_e2e_contract import AskDjE2ETrace, load_cases, validate_case_result
from tests.test_ask_dj import FakeMemory, make_runtime
from tests.test_http_voice_helpers import install_http_stubs


ROOT = Path(__file__).resolve().parents[1]
CASES_PATH = ROOT / "examples" / "ask_dj_e2e_cases.json"


class AskDjE2EContractTest(unittest.TestCase):
    IMPLEMENTED_INTENTS = {
        "ask_music_info",
        "artist_concerts",
        "artist_item_list",
        "blocked_music_preference",
        "build_playlist_from_seeds",
        "clarification_needed",
        "conversational_followup",
        "current_track_seed_mix",
        "current_track_versions",
        "dj_announcement",
        "help",
        "list_outputs",
        "mood_mix",
        "morning_music_suggestion",
        "next_track_info",
        "personal_memory_summary",
        "personal_music_profile_analysis",
        "personal_music_recommendations",
        "play_album_containing_track",
        "play_current_album",
        "play_music",
        "playback_control",
        "playback_mode_status",
        "playlist_recommendation_offer",
        "recently_played_history",
        "save_generated_playlist",
        "song_recommendations",
        "spotify_playlist_search",
        "spotify_user_playlists",
        "spotify_vibe_playlists",
        "technical_track_analysis",
        "track_artist_album_lookup",
        "track_title_choices",
    }

    @classmethod
    def setUpClass(cls) -> None:
        install_http_stubs()
        cls.ask_dj = importlib.import_module("custom_components.djconnect.ask_dj")
        cls.const = importlib.import_module("custom_components.djconnect.const")
        cls.cases = load_cases(CASES_PATH)

    def test_case_file_is_not_empty(self) -> None:
        self.assertGreaterEqual(len(self.cases), 1)

    def test_case_file_covers_all_implemented_intents(self) -> None:
        covered = {
            case.get("expect", {}).get("intent")
            for case in self.cases
            if case.get("expect", {}).get("intent")
        }
        self.assertEqual(sorted(self.IMPLEMENTED_INTENTS - covered), [])

    def test_case_file_covers_every_help_prompt_exactly(self) -> None:
        help_prompts = set(self.ask_dj._help_prompt_examples())
        covered_prompts = {
            case.get("request", {}).get("text")
            for case in self.cases
            if case.get("request", {}).get("text")
        }
        self.assertEqual(sorted(help_prompts - covered_prompts), [])

    def test_ask_dj_contract_cases(self) -> None:
        failures: list[str] = []
        for case in self.cases:
            with self.subTest(case=case["id"]):
                response, trace = self._run_case(case)
                errors = validate_case_result(case, response, trace)
                failures.extend(errors)
                self.assertEqual(errors, [])
        if failures:
            self.fail("\n".join(failures))

    def _run_case(self, case: dict) -> tuple[dict, AskDjE2ETrace]:
        runtime = make_runtime()
        runtime.last_playback = {
            **runtime.last_playback,
            "uri": "spotify:track:black",
            "track_name": "Black",
            "artist": "Pearl Jam",
            "album_name": "Ten",
            "album_uri": "spotify:album:ten",
            "context_uri": "spotify:album:ten",
        }
        trace = AskDjE2ETrace()

        class Memory(FakeMemory):
            async def async_listening_profile_is_fresh(self, runtime_arg, payload=None):
                return False

            async def async_update_listening_profile(self, runtime_arg, profile, payload=None):
                return None

            async def async_store_pending_followup(self, runtime_arg, followup, payload=None, *, user_id=None):
                trace.followups.append({"followup": followup, "payload": payload, "user_id": user_id})
                return {"id": f"followup-{len(trace.followups)}", **followup}

        runtime.memory = Memory()
        payload = {
            "device_id": runtime.device_status["device_id"],
            "client_message_id": f"e2e-{case['id']}",
            "audio_response": "never",
            **case["request"],
        }
        runtime.device_status["client_type"] = payload.get("client_type") or "watchos"

        async def command(hass, runtime_arg, command_name, value=None, *, play=None):
            trace.spotify_commands.append(command_name)
            if command_name == "status":
                if case["id"] == "morning_startup_confirmation":
                    return {"success": True, "playback": {"has_playback": False, "is_playing": False}}
                return {"success": True, "playback": runtime.last_playback}
            if command_name == "devices":
                return {
                    "success": True,
                    "devices": [
                        {"id": "speaker-1", "name": "Woonkamer", "is_active": True},
                        {"id": "speaker-2", "name": "Keuken", "is_active": False},
                    ],
                }
            if command_name == "queue":
                return {
                    "success": True,
                    "context_uri": "spotify:playlist:queue-context",
                    "queue": [
                        {
                            "track_name": "Queue Track",
                            "artist": "Queue Artist",
                            "uri": "spotify:track:queue-track",
                            "album_image_url": "https://img.example/queue.jpg",
                        }
                    ],
                }
            if command_name == "listening_profile":
                return {
                    "success": True,
                    "profile": {
                        "recent_tracks": [
                            {
                                "track_name": "Profile Track",
                                "artist": "Profile Artist",
                                "uri": "spotify:track:profile",
                                "album_image_url": "https://img.example/profile.jpg",
                            }
                        ],
                        "top_tracks_by_range": {
                            "short_term": [
                                {
                                    "uri": "spotify:track:morning",
                                    "track_name": "Morning Track",
                                    "artist": "Morning Artist",
                                    "album_image_url": "https://img.example/morning.jpg",
                                }
                            ]
                        },
                        "top_artists_by_range": {
                            "short_term": [{"name": "Radiohead", "genres": ["alternative rock"]}]
                        },
                        "inferred_genres": ["indie", "ambient"],
                        "sources": ["spotify_top_tracks_short_term"],
                    },
                }
            if command_name == "recently_played":
                now = self.ask_dj.datetime.now(self.ask_dj.timezone.utc)
                return {
                    "success": True,
                    "tracks": [
                        {
                            "track_name": "Bella",
                            "artist": "Finnebassen",
                            "played_at": (now - timedelta(minutes=10)).isoformat(),
                            "album_image_url": "https://img.example/bella.jpg",
                            "uri": "spotify:track:bella",
                        },
                        {
                            "track_name": "High On Me",
                            "artist": "Rossi.",
                            "played_at": (now - timedelta(minutes=45)).isoformat(),
                        },
                        {
                            "track_name": "Old Song",
                            "artist": "Older Artist",
                            "played_at": (now - timedelta(hours=2)).isoformat(),
                        },
                    ],
                }
            if command_name in {"save_current_track", "set_current_track_favorite"}:
                return {
                    "success": True,
                    "playback": {
                        "track_name": "Far Behind",
                        "artist": "Candlebox",
                        "uri": "spotify:track:far-behind",
                        "album_image_url": "https://img.example/far-behind.jpg",
                        "is_liked": value is not False,
                    },
                }
            if command_name in {"pause", "play"}:
                return {"success": True, "playback": runtime.last_playback}
            if command_name == "set_volume":
                return {"success": True, "playback": {**runtime.last_playback, "volume_percent": value}}
            if command_name in {"set_shuffle", "set_repeat"}:
                return {"success": True, "playback": runtime.last_playback}
            if command_name == "play":
                return {"success": True, "playback": runtime.last_playback}
            if command_name == "artist_albums":
                return {
                    "success": True,
                    "albums": [
                        {
                            "name": "OK Computer",
                            "title": "OK Computer",
                            "artist": "Radiohead",
                            "uri": "spotify:album:ok-computer",
                            "album_image_url": "https://img.example/ok.jpg",
                        }
                    ],
                }
            if command_name == "related_artists":
                return {
                    "success": True,
                    "artists": [{"name": "Massive Attack", "genres": ["trip hop"]}],
                }
            if command_name == "artist_profile":
                return {
                    "success": True,
                    "artist": {"name": "Pearl Jam", "genres": ["grunge"], "popularity": 80},
                }
            if command_name == "search_playlists":
                query = (value or {}).get("query", "mix") if isinstance(value, dict) else "mix"
                return {
                    "success": True,
                    "playlists": [
                        {
                            "name": f"{query.title()} Playlist",
                            "title": f"{query.title()} Playlist",
                            "owner": "Spotify",
                            "uri": "spotify:playlist:e2e",
                            "image_url": "https://img.example/playlist.jpg",
                        }
                    ],
                }
            if command_name == "search_tracks":
                query = (value or {}).get("query", "track") if isinstance(value, dict) else "track"
                if "zombie" in query.lower():
                    return {
                        "success": True,
                        "tracks": [
                            {
                                "track_name": "Zombie",
                                "title": "Zombie",
                                "artist": "The Cranberries",
                                "uri": "spotify:track:cranberries-zombie",
                                "album_image_url": "https://img.example/cranberries.jpg",
                            },
                            {
                                "track_name": "Zombie",
                                "title": "Zombie",
                                "artist": "Bad Wolves",
                                "uri": "spotify:track:bad-wolves-zombie",
                                "album_image_url": "https://img.example/bad-wolves.jpg",
                            },
                            {
                                "track_name": "Time of the Season",
                                "title": "Time of the Season",
                                "artist": "The Zombies",
                                "uri": "spotify:track:zombies-time",
                                "album_image_url": "https://img.example/zombies.jpg",
                            },
                        ],
                    }
                return {
                    "success": True,
                    "tracks": [
                        {
                            "track_name": "Zombie" if "zombie" in query.lower() else "Paranoid Android",
                            "title": "Zombie" if "zombie" in query.lower() else "Paranoid Android",
                            "artist": "The Cranberries" if "zombie" in query.lower() else "Radiohead",
                            "album_name": "No Need To Argue",
                            "uri": "spotify:track:e2e",
                            "album_uri": "spotify:album:e2e",
                            "album_image_url": "https://img.example/track.jpg",
                        }
                    ],
                }
            if command_name == "search_media":
                media_type = (value or {}).get("type") if isinstance(value, dict) else ""
                if media_type == "track":
                    return {
                        "success": True,
                        "item": {
                            "uri": "spotify:track:black",
                            "track_name": "Black",
                            "title": "Black",
                            "artist": "Pearl Jam",
                            "album_name": "Ten",
                            "album_uri": "spotify:album:ten",
                            "context_uri": "spotify:album:ten",
                            "album_image_url": "https://img.example/black.jpg",
                        },
                    }
                if media_type == "playlist":
                    return {
                        "success": True,
                        "item": {
                            "uri": "spotify:playlist:e2e-search",
                            "title": "E2E playlist",
                            "owner": "Spotify",
                            "image_url": "https://img.example/search-playlist.jpg",
                        },
                    }
                if media_type == "album":
                    return {
                        "success": True,
                        "item": {
                            "uri": "spotify:album:ten",
                            "title": "Ten",
                            "artist": "Pearl Jam",
                            "album_image_url": "https://img.example/ten.jpg",
                        },
                    }
                return {"success": False}
            if command_name == "search_albums":
                return {
                    "success": True,
                    "albums": [
                        {
                            "name": "In Rainbows",
                            "title": "In Rainbows",
                            "artist": "Radiohead",
                            "uri": "spotify:album:in-rainbows",
                            "album_image_url": "https://img.example/album.jpg",
                        }
                    ],
                }
            if command_name == "playlists":
                return {
                    "success": True,
                    "playlists": [
                        {
                            "name": "Liked Proxy",
                            "title": "Liked Proxy",
                            "owner": "Peter",
                            "uri": "spotify:playlist:liked-proxy",
                            "image_url": "https://img.example/user-playlist.jpg",
                        }
                    ],
                }
            if command_name == "artist_recommendations":
                return {
                    "success": True,
                    "tracks": [
                        {
                            "track_name": "Recommended Track",
                            "title": "Recommended Track",
                            "artist": "Recommended Artist",
                            "uri": "spotify:track:recommended",
                            "album_image_url": "https://img.example/recommended.jpg",
                        }
                    ],
                }
            raise AssertionError(f"unexpected Spotify command in {case['id']}: {command_name}")

        async def tts(hass, runtime_arg, text):
            trace.tts_requests.append(text)
            return {"audio_url_value": "/api/djconnect/tts/e2e.mp3"}

        original_command = self.ask_dj.run_music_command
        original_tts = self.ask_dj.async_send_dj_response_best_effort
        original_process_text = self.ask_dj.run_text_command
        self.ask_dj.run_music_command = command
        self.ask_dj.async_send_dj_response_best_effort = tts
        async def process_text(hass, runtime_arg, text, **kwargs):
            trace.process_text_requests.append(text)
            if case["id"] == "playback_request_no_active_output":
                raise RuntimeError("No active device")
            action = "previous" if "previous" in text.lower() or "vorige" in text.lower() else "next" if "next" in text.lower() or "volgende" in text.lower() else "play_music"
            return {
                "success": True,
                "text": "Vorige track gestart." if action == "previous" else "Volgende track gestart." if action == "next" else f"Ik zet {text} voor je klaar.",
                "dj_text": "Vorige track gestart." if action == "previous" else "Volgende track gestart." if action == "next" else f"Ik zet {text} voor je klaar.",
                "playback": runtime.last_playback,
            }
        self.ask_dj.run_text_command = process_text
        try:
            response = asyncio.run(
                self.ask_dj.async_handle_ask_dj(
                    types.SimpleNamespace(
                        services=types.SimpleNamespace(),
                        data={self.const.DOMAIN: {}},
                    ),
                    runtime,
                    payload,
                    user_id="e2e-user",
                )
            )
        finally:
            self.ask_dj.run_music_command = original_command
            self.ask_dj.async_send_dj_response_best_effort = original_tts
            self.ask_dj.run_text_command = original_process_text
        return response, trace
