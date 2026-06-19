from __future__ import annotations

import asyncio
import importlib
from pathlib import Path
import sys
import types
import unittest

from tests.test_http_voice_helpers import install_http_stubs


ROOT = Path(__file__).resolve().parents[1]


class FakeMemory:
    def __init__(self):
        self.cleared = False
        self.updated = []
        self.generation = 0

    async def async_context_for_runtime(self, runtime, payload=None, *, user_id=None):
        key = f"user:{user_id}" if user_id else payload.get("memory_key") or runtime.device_status["device_id"]
        return {
            "memory_key": key,
            "memory": {
                "mood": 38,
                "favorite_genres": ["indie", "ambient"],
                "recent_tracks": [
                    {"artist": "The xx", "track_name": "Intro", "album_name": "xx"},
                    {"artist": "Bon Iver", "track_name": "Holocene", "album_name": "Bon Iver"},
                    {"artist": "Radiohead", "track_name": "Reckoner", "album_name": "In Rainbows"},
                ],
                "last_ask_dj": {
                    "input": "Draai iets rustigers",
                    "response_text": "Ik koos iets rustigers met dezelfde sfeer.",
                    "intent": "play_similar",
                    "track": {"artist": "The xx", "title": "Intro"},
                }
            },
            "session": [],
        }

    async def async_update_last_ask_dj(self, runtime, *, input_text, result, payload=None, user_id=None):
        self.updated.append((input_text, result, payload, user_id))
        return payload.get("memory_key") if payload else runtime.device_status["device_id"]

    async def async_mark_clear_required(self, runtime, payload=None, *, user_id=None):
        self.cleared = True
        self.generation += 1
        return {
            "memory_key": payload.get("memory_key") or runtime.device_status["device_id"],
            "ask_dj_clear_required": True,
            "generation": self.generation,
            "clear_requested_at": "2026-06-19T00:00:00+00:00",
        }

    async def async_history_state(self, runtime, payload=None, *, user_id=None, client_generation=None):
        return {
            "memory_key": payload.get("memory_key") or runtime.device_status["device_id"],
            "ask_dj_clear_required": client_generation is None or client_generation < self.generation,
            "generation": self.generation,
            "clear_requested_at": "2026-06-19T00:00:00+00:00" if self.generation else None,
        }


def make_runtime():
    class Runtime:
        config = {}
        device_token = "device-token"
        pairing_device_id = "djconnect-watchos-68B74487726D"
        device_status = {
            "device_id": "djconnect-watchos-68B74487726D",
            "client_type": "watchos",
            "device_name": "Apple Watch van Peter",
            "available_outputs": [{"id": "speaker-1", "name": "Woonkamer"}],
        }
        memory = FakeMemory()
        last_playback = {
            "track_name": "Intro",
            "artist": "The xx",
            "album_image_url": "https://img.example/intro.jpg",
            "device": {"id": "speaker-1", "name": "Woonkamer"},
            "volume_percent": 30,
        }

        def authorize_device_request(self, headers, body_device_id=None, client_type=None):
            return (
                headers.get("Authorization") == "Bearer device-token"
                and body_device_id == self.device_status["device_id"]
                and client_type == "watchos"
            )

        def client_type(self):
            return "watchos"

        def device_language(self):
            return "nl"

    return Runtime()


class AskDjTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        install_http_stubs()
        cls.ask_dj = importlib.import_module("custom_components.djconnect.ask_dj")
        cls.http = importlib.import_module("custom_components.djconnect.http")
        cls.const = importlib.import_module("custom_components.djconnect.const")

    def test_informational_request_does_not_modify_playback(self) -> None:
        runtime = make_runtime()
        calls = []

        async def command(hass, runtime_arg, command_name, value=None, *, play=None):
            calls.append(command_name)
            if command_name == "status":
                return {"success": True, "playback": runtime.last_playback}
            if command_name == "listening_profile":
                return {
                    "success": True,
                    "profile": {
                        "recent_tracks": [
                            {"artist": "The xx", "track_name": "Intro", "album_name": "xx"},
                            {"artist": "Bon Iver", "track_name": "Holocene", "album_name": "Bon Iver"},
                        ],
                        "top_artists_by_range": {
                            "short_term": [{"name": "The xx", "genres": ["indie"]}]
                        },
                        "top_tracks_by_range": {
                            "short_term": [{"artist": "Radiohead", "track_name": "Reckoner"}]
                        },
                        "inferred_genres": ["indie", "ambient"],
                        "sources": ["spotify_recently_played", "spotify_top_tracks_short_term"],
                    },
                }
            raise AssertionError(f"unexpected playback mutation: {command_name}")

        class Services:
            async def async_call(self, domain, service, data, **kwargs):
                return {"response": {"speech": {"plain": {"speech": "Omdat dit goed aansluit op je vorige rustiger verzoek."}}}}

        original_command = self.ask_dj.handle_spotify_command
        self.ask_dj.handle_spotify_command = command
        try:
            result = asyncio.run(
                self.ask_dj.async_handle_ask_dj(
                    types.SimpleNamespace(services=Services(), data={self.const.DOMAIN: {}}),
                    runtime,
                    {
                        "text": "Waarom koos je dit nummer?",
                        "device_id": runtime.device_status["device_id"],
                        "client_type": "watchos",
                        "memory_key": "shared",
                    },
                    user_id="user-1",
                )
            )
        finally:
            self.ask_dj.handle_spotify_command = original_command

        self.assertTrue(result["success"])
        self.assertEqual(calls, ["status"])
        self.assertEqual(result["intent"]["category"], "informational")
        self.assertIn("Omdat dit goed aansluit", result["text"])
        self.assertEqual(result["memory_key"], "user:user-1")
        self.assertTrue(result["images"][0]["url"].startswith(self.const.API_IMAGE_PROXY_BASE))

    def test_action_request_dispatches_spotify_command(self) -> None:
        runtime = make_runtime()
        calls = []

        async def command(hass, runtime_arg, command_name, value=None, *, play=None):
            calls.append((command_name, value))
            if command_name == "status":
                return {"success": True, "playback": runtime.last_playback}
            if command_name == "pause":
                return {"success": True, "playback": {"is_playing": False}}
            return {"success": True}

        original_command = self.ask_dj.handle_spotify_command
        self.ask_dj.handle_spotify_command = command
        try:
            result = asyncio.run(
                self.ask_dj.async_handle_ask_dj(
                    types.SimpleNamespace(services=types.SimpleNamespace(), data={self.const.DOMAIN: {}}),
                    runtime,
                    {
                        "text": "Pauzeer muziek",
                        "device_id": runtime.device_status["device_id"],
                        "client_type": "watchos",
                    },
                )
            )
        finally:
            self.ask_dj.handle_spotify_command = original_command

        self.assertTrue(result["success"])
        self.assertIn(("pause", None), calls)
        self.assertEqual(result["intent"]["category"], "action")
        self.assertEqual(result["action"], "pause")

    def test_personal_music_profile_analysis_does_not_modify_playback(self) -> None:
        runtime = make_runtime()
        calls = []

        async def command(hass, runtime_arg, command_name, value=None, *, play=None):
            calls.append(command_name)
            if command_name == "status":
                return {"success": True, "playback": runtime.last_playback}
            if command_name == "listening_profile":
                return {
                    "success": True,
                    "profile": {
                        "recent_tracks": [
                            {"artist": "The xx", "track_name": "Intro", "album_name": "xx"},
                            {"artist": "Bon Iver", "track_name": "Holocene", "album_name": "Bon Iver"},
                        ],
                        "top_artists_by_range": {
                            "short_term": [{"name": "The xx", "genres": ["indie"]}]
                        },
                        "top_tracks_by_range": {
                            "short_term": [{"artist": "Radiohead", "track_name": "Reckoner"}]
                        },
                        "inferred_genres": ["indie", "ambient"],
                        "sources": ["spotify_recently_played", "spotify_top_tracks_short_term"],
                    },
                }
            raise AssertionError(f"unexpected playback mutation: {command_name}")

        original_command = self.ask_dj.handle_spotify_command
        self.ask_dj.handle_spotify_command = command
        try:
            result = asyncio.run(
                self.ask_dj.async_handle_ask_dj(
                    types.SimpleNamespace(services=types.SimpleNamespace(), data={self.const.DOMAIN: {}}),
                    runtime,
                    {
                        "text": "Omschrijf eens waar ik zoal naar luisterde de afgelopen maand",
                        "device_id": runtime.device_status["device_id"],
                        "client_type": "watchos",
                    },
                    user_id="user-1",
                )
            )
        finally:
            self.ask_dj.handle_spotify_command = original_command

        self.assertTrue(result["success"])
        self.assertEqual(calls, ["status", "listening_profile"])
        self.assertEqual(result["intent"]["category"], "informational")
        self.assertEqual(result["intent"]["intent"], "personal_music_profile_analysis")
        self.assertEqual(result["action"], "profile_analysis")
        self.assertIn("de afgelopen maand", result["text"])
        self.assertIn("The xx - Intro", result["text"])
        self.assertIn("sources", result)
        self.assertTrue(any(source["source"] == "spotify_recently_played" for source in result["sources"]))

    def test_personal_music_profile_analysis_reports_insufficient_data(self) -> None:
        runtime = make_runtime()

        class EmptyMemory(FakeMemory):
            async def async_context_for_runtime(self, runtime, payload=None, *, user_id=None):
                return {"memory_key": "shared", "memory": {}, "session": []}

        runtime.memory = EmptyMemory()
        runtime.last_playback = {}

        async def command(hass, runtime_arg, command_name, value=None, *, play=None):
            if command_name == "status":
                return {"success": True, "playback": {}}
            if command_name == "listening_profile":
                return {"success": True, "profile": {}}
            raise AssertionError(f"unexpected playback mutation: {command_name}")

        original_command = self.ask_dj.handle_spotify_command
        self.ask_dj.handle_spotify_command = command
        try:
            result = asyncio.run(
                self.ask_dj.async_handle_ask_dj(
                    types.SimpleNamespace(services=types.SimpleNamespace(), data={self.const.DOMAIN: {}}),
                    runtime,
                    {
                        "text": "Make a profile of my music taste this year",
                        "device_id": runtime.device_status["device_id"],
                        "client_type": "watchos",
                    },
                )
            )
        finally:
            self.ask_dj.handle_spotify_command = original_command

        self.assertTrue(result["success"])
        self.assertEqual(result["intent"]["intent"], "personal_music_profile_analysis")
        self.assertIn("te weinig luistergeschiedenis", result["text"])
        self.assertIn("dit jaar", result["text"])

    def test_personal_music_recommendations_return_playback_actions_without_playing(self) -> None:
        runtime = make_runtime()
        calls = []

        async def command(hass, runtime_arg, command_name, value=None, *, play=None):
            calls.append(command_name)
            if command_name == "status":
                return {"success": True, "playback": runtime.last_playback}
            if command_name == "listening_profile":
                return {
                    "success": True,
                    "profile": {
                        "top_tracks_by_range": {
                            "short_term": [
                                {
                                    "uri": "spotify:track:123",
                                    "track_name": "Track Title",
                                    "artist": "Artist Name",
                                    "album_image_url": "https://img.example/album.jpg",
                                    "context_uri": "spotify:album:456",
                                }
                            ]
                        },
                        "sources": ["spotify_top_tracks_short_term"],
                    },
                }
            raise AssertionError(f"unexpected playback mutation: {command_name}")

        original_command = self.ask_dj.handle_spotify_command
        self.ask_dj.handle_spotify_command = command
        try:
            result = asyncio.run(
                self.ask_dj.async_handle_ask_dj(
                    types.SimpleNamespace(services=types.SimpleNamespace(), data={self.const.DOMAIN: {}}),
                    runtime,
                    {
                        "text": "Welke muziek raad je mij aan?",
                        "device_id": runtime.device_status["device_id"],
                        "client_type": "watchos",
                    },
                )
            )
        finally:
            self.ask_dj.handle_spotify_command = original_command

        self.assertTrue(result["success"])
        self.assertEqual(calls, ["status", "listening_profile"])
        self.assertEqual(result["intent"]["intent"], "personal_music_recommendations")
        self.assertEqual(result["action"], "none")
        self.assertEqual(result["playback_actions"][0]["uri"], "spotify:track:123")
        self.assertEqual(result["playback_actions"][0]["context_uri"], "spotify:album:456")
        self.assertTrue(result["playback_actions"][0]["image_url"].startswith(self.const.API_IMAGE_PROXY_BASE))

    def test_ask_dj_http_rejects_unknown_client_type(self) -> None:
        runtime = make_runtime()
        hass = types.SimpleNamespace(data={self.const.DOMAIN: {"runtime": runtime}})

        class Request:
            headers = {"Authorization": "Bearer device-token"}
            app = {"hass": hass}

            async def json(self):
                return {
                    "text": "Hallo DJ",
                    "device_id": runtime.device_status["device_id"],
                    "client_type": "android",
                }

        response = asyncio.run(self.http.DJConnectAskDjView(None).post(Request()))

        self.assertEqual(response["status_code"], 400)
        self.assertEqual(response["payload"]["error"], "invalid_client_type")

    def test_clear_and_history_state_endpoints_share_generation(self) -> None:
        runtime = make_runtime()
        hass = types.SimpleNamespace(data={self.const.DOMAIN: {"runtime": runtime}})

        class ClearRequest:
            headers = {"Authorization": "Bearer device-token"}
            app = {"hass": hass}

            async def json(self):
                return {
                    "device_id": runtime.device_status["device_id"],
                    "client_type": "watchos",
                    "memory_key": "shared",
                }

        clear = asyncio.run(self.http.DJConnectAskDjClearView(None).post(ClearRequest()))

        self.assertTrue(clear["payload"]["ask_dj_clear_required"])
        self.assertEqual(clear["payload"]["generation"], 1)

        class StateRequest:
            headers = {"Authorization": "Bearer device-token"}
            app = {"hass": hass}

            async def json(self):
                return {
                    "device_id": runtime.device_status["device_id"],
                    "client_type": "watchos",
                    "memory_key": "shared",
                    "generation": 0,
                }

        state = asyncio.run(self.http.DJConnectAskDjHistoryStateView(None).post(StateRequest()))

        self.assertTrue(state["payload"]["ask_dj_clear_required"])
        self.assertEqual(state["payload"]["generation"], 1)

    def test_multiple_images_are_proxied(self) -> None:
        hass = types.SimpleNamespace(data={self.const.DOMAIN: {}})
        result = self.ask_dj._normalize_ask_dj_response(
            hass,
            make_runtime(),
            {
                "success": True,
                "text": "Hier zijn twee hoezen.",
                "images": [
                    {"url": "https://img.example/1.jpg", "title": "One"},
                    {"url": "https://img.example/2.jpg", "title": "Two"},
                ],
            },
            self.ask_dj.AskDjIntent("informational", "ask_music_info"),
            memory_key="shared",
            playback_context={},
        )

        self.assertEqual(len(result["images"]), 2)
        self.assertTrue(all(item["url"].startswith(self.const.API_IMAGE_PROXY_BASE) for item in result["images"]))


if __name__ == "__main__":
    unittest.main()
