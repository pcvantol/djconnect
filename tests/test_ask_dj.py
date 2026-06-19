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

    def test_informational_text_chat_is_text_only_by_default(self) -> None:
        runtime = make_runtime()

        async def command(hass, runtime_arg, command_name, value=None, *, play=None):
            if command_name == "status":
                return {"success": True, "playback": runtime.last_playback}
            return {"success": True}

        async def fail_tts(hass, runtime_arg, text):
            raise AssertionError("informational text chat should not generate TTS by default")

        original_command = self.ask_dj.handle_spotify_command
        original_tts = self.ask_dj.async_send_dj_response_best_effort
        self.ask_dj.handle_spotify_command = command
        self.ask_dj.async_send_dj_response_best_effort = fail_tts
        try:
            result = asyncio.run(
                self.ask_dj.async_handle_ask_dj(
                    types.SimpleNamespace(services=types.SimpleNamespace(), data={self.const.DOMAIN: {}}),
                    runtime,
                    {
                        "text": "Waarom koos je dit nummer?",
                        "device_id": runtime.device_status["device_id"],
                        "client_type": "watchos",
                    },
                )
            )
        finally:
            self.ask_dj.handle_spotify_command = original_command
            self.ask_dj.async_send_dj_response_best_effort = original_tts

        self.assertTrue(result["success"])
        self.assertNotIn("audio_url", result)

    def test_informational_text_chat_can_force_audio_response(self) -> None:
        runtime = make_runtime()
        tts_calls = []

        async def command(hass, runtime_arg, command_name, value=None, *, play=None):
            if command_name == "status":
                return {"success": True, "playback": runtime.last_playback}
            return {"success": True}

        async def tts(hass, runtime_arg, text):
            tts_calls.append(text)
            return {"audio_url_value": "/api/djconnect/tts/forced.mp3"}

        original_command = self.ask_dj.handle_spotify_command
        original_tts = self.ask_dj.async_send_dj_response_best_effort
        self.ask_dj.handle_spotify_command = command
        self.ask_dj.async_send_dj_response_best_effort = tts
        try:
            result = asyncio.run(
                self.ask_dj.async_handle_ask_dj(
                    types.SimpleNamespace(services=types.SimpleNamespace(), data={self.const.DOMAIN: {}}),
                    runtime,
                    {
                        "text": "Waarom koos je dit nummer?",
                        "device_id": runtime.device_status["device_id"],
                        "client_type": "watchos",
                        "audio_response": "always",
                    },
                )
            )
        finally:
            self.ask_dj.handle_spotify_command = original_command
            self.ask_dj.async_send_dj_response_best_effort = original_tts

        self.assertTrue(result["success"])
        self.assertEqual(result["audio_url"], "/api/djconnect/tts/forced.mp3")
        self.assertTrue(tts_calls)

    def test_action_request_dispatches_spotify_command(self) -> None:
        runtime = make_runtime()
        calls = []
        tts_calls = []

        async def command(hass, runtime_arg, command_name, value=None, *, play=None):
            calls.append((command_name, value))
            if command_name == "status":
                return {"success": True, "playback": runtime.last_playback}
            if command_name == "pause":
                return {"success": True, "playback": {"is_playing": False}}
            return {"success": True}

        async def tts(hass, runtime_arg, text):
            tts_calls.append(text)
            return {"audio_url_value": "/api/djconnect/tts/action.mp3"}

        original_command = self.ask_dj.handle_spotify_command
        original_tts = self.ask_dj.async_send_dj_response_best_effort
        self.ask_dj.handle_spotify_command = command
        self.ask_dj.async_send_dj_response_best_effort = tts
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
            self.ask_dj.async_send_dj_response_best_effort = original_tts

        self.assertTrue(result["success"])
        self.assertIn(("pause", None), calls)
        self.assertEqual(result["intent"]["category"], "action")
        self.assertEqual(result["action"], "pause")
        self.assertEqual(result["audio_url"], "/api/djconnect/tts/action.mp3")
        self.assertTrue(tts_calls)

    def test_voice_play_artist_request_uses_playback_parser_with_stt_correction(self) -> None:
        runtime = make_runtime()
        calls = []

        async def command(hass, runtime_arg, command_name, value=None, *, play=None):
            if command_name == "status":
                return {"success": True, "playback": runtime.last_playback}
            return {"success": True}

        async def process(hass, runtime_arg, text, *, play=True, correct_stt=False):
            calls.append((text, play, correct_stt))
            return {
                "text": text,
                "intent": {"spotify_search_query": "Armin van Buuren"},
                "dj_text": "Ik zet Armin van Buuren voor je klaar.",
            }

        original_command = self.ask_dj.handle_spotify_command
        original_process = self.ask_dj.process_text_command
        self.ask_dj.handle_spotify_command = command
        self.ask_dj.process_text_command = process
        try:
            result = asyncio.run(
                self.ask_dj.async_handle_ask_dj(
                    types.SimpleNamespace(services=types.SimpleNamespace(), data={self.const.DOMAIN: {}}),
                    runtime,
                    {
                        "text": "speel Armin van Buuren",
                        "device_id": runtime.device_status["device_id"],
                        "client_type": "watchos",
                        "input_type": "voice",
                    },
                )
            )
        finally:
            self.ask_dj.handle_spotify_command = original_command
            self.ask_dj.process_text_command = original_process

        self.assertTrue(result["success"])
        self.assertEqual(result["intent"]["category"], "hybrid")
        self.assertEqual(result["intent"]["intent"], "play_music")
        self.assertEqual(calls, [("speel Armin van Buuren", True, True)])
        self.assertIn("Armin", result["dj_text"])

    def test_bare_voice_artist_request_is_treated_as_playback_request(self) -> None:
        runtime = make_runtime()
        calls = []

        async def command(hass, runtime_arg, command_name, value=None, *, play=None):
            if command_name == "status":
                return {"success": True, "playback": runtime.last_playback}
            return {"success": True}

        async def process(hass, runtime_arg, text, *, play=True, correct_stt=False):
            calls.append((text, play, correct_stt))
            return {
                "text": text,
                "intent": {"spotify_search_query": "Armin van Buuren"},
                "dj_text": "Ik zet Armin van Buuren voor je klaar.",
            }

        original_command = self.ask_dj.handle_spotify_command
        original_process = self.ask_dj.process_text_command
        self.ask_dj.handle_spotify_command = command
        self.ask_dj.process_text_command = process
        try:
            result = asyncio.run(
                self.ask_dj.async_handle_ask_dj(
                    types.SimpleNamespace(services=types.SimpleNamespace(), data={self.const.DOMAIN: {}}),
                    runtime,
                    {
                        "text": "Armin van Buuren",
                        "device_id": runtime.device_status["device_id"],
                        "client_type": "watchos",
                        "input_type": "voice",
                    },
                )
            )
        finally:
            self.ask_dj.handle_spotify_command = original_command
            self.ask_dj.process_text_command = original_process

        self.assertTrue(result["success"])
        self.assertEqual(result["intent"]["category"], "hybrid")
        self.assertEqual(result["intent"]["intent"], "play_music")
        self.assertEqual(calls, [("Armin van Buuren", True, True)])
        self.assertNotEqual(
            result["text"],
            "Ik heb nu niet genoeg betrouwbare broninformatie om daar zeker antwoord op te geven.",
        )

    def test_text_playback_request_failure_returns_chat_response_not_unavailable(self) -> None:
        runtime = make_runtime()

        async def command(hass, runtime_arg, command_name, value=None, *, play=None):
            if command_name == "status":
                return {"success": True, "playback": runtime.last_playback}
            return {"success": True}

        async def process(hass, runtime_arg, text, *, play=True, correct_stt=False):
            raise RuntimeError("Spotify device unavailable")

        original_command = self.ask_dj.handle_spotify_command
        original_process = self.ask_dj.process_text_command
        self.ask_dj.handle_spotify_command = command
        self.ask_dj.process_text_command = process
        try:
            result = asyncio.run(
                self.ask_dj.async_handle_ask_dj(
                    types.SimpleNamespace(services=types.SimpleNamespace(), data={self.const.DOMAIN: {}}),
                    runtime,
                    {
                        "text": "Speel Armin",
                        "device_id": runtime.device_status["device_id"],
                        "client_type": "watchos",
                    },
                )
            )
        finally:
            self.ask_dj.handle_spotify_command = original_command
            self.ask_dj.process_text_command = original_process

        self.assertTrue(result["success"])
        self.assertEqual(result["error"], "playback_failed")
        self.assertEqual(result["intent"]["category"], "hybrid")
        self.assertIn("muziekverzoek begrepen", result["dj_text"])
        self.assertNotEqual(result.get("error"), "ask_dj_unavailable")

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

    def test_clear_and_history_state_endpoints_share_revisions(self) -> None:
        runtime = make_runtime()
        hass = types.SimpleNamespace(data={self.const.DOMAIN: {"runtime": runtime}})

        class ClearRequest:
            headers = {"Authorization": "Bearer device-token"}
            app = {"hass": hass}
            context = types.SimpleNamespace(user_id="user-1")

            async def json(self):
                return {
                    "device_id": runtime.device_status["device_id"],
                    "client_type": "watchos",
                }

        clear = asyncio.run(self.http.DJConnectAskDjHistoryClearView(None).post(ClearRequest()))

        self.assertEqual(clear["payload"]["user_id"], "user-1")
        self.assertEqual(clear["payload"]["history_revision"], 1)
        self.assertEqual(clear["payload"]["clear_revision"], 1)
        self.assertEqual(clear["payload"]["messages"], [])

        class StateRequest:
            headers = {"Authorization": "Bearer device-token"}
            app = {"hass": hass}
            context = types.SimpleNamespace(user_id="user-1")

            async def json(self):
                return {
                    "device_id": runtime.device_status["device_id"],
                    "client_type": "watchos",
                    "history_revision": 0,
                    "clear_revision": 0,
                }

        state = asyncio.run(self.http.DJConnectAskDjHistoryStateView(None).post(StateRequest()))

        self.assertTrue(state["payload"]["ask_dj_clear_required"])
        self.assertEqual(state["payload"]["history_revision"], 1)
        self.assertEqual(state["payload"]["clear_revision"], 1)

    def test_message_endpoint_stores_history_for_sync(self) -> None:
        runtime = make_runtime()
        hass = types.SimpleNamespace(data={self.const.DOMAIN: {"runtime": runtime}})

        async def ask_dj(hass_arg, runtime_arg, payload, *, user_id=None):
            return {
                "success": True,
                "text": "Ik kies iets rustigers.",
                "dj_text": "Ik kies iets rustigers.",
                "images": [{"url": "/api/djconnect/image_proxy/abc", "title": "Cover"}],
                "links": [{"url": "https://example.test", "kind": "source"}],
                "sources": [{"source": "djconnect_memory", "kind": "source"}],
                "audio_url": "/api/djconnect/tts/abc.mp3",
                "playback_actions": [{"uri": "spotify:track:123", "kind": "track"}],
            }

        class MessageRequest:
            headers = {"Authorization": "Bearer device-token"}
            app = {"hass": hass}
            context = types.SimpleNamespace(user_id="user-1")

            async def json(self):
                return {
                    "client_message_id": "client-1",
                    "client_id": "watch",
                    "device_id": runtime.device_status["device_id"],
                    "client_type": "watchos",
                    "text": "Draai iets rustigers",
                }

        original = self.http.async_handle_ask_dj
        self.http.async_handle_ask_dj = ask_dj
        try:
            response = asyncio.run(self.http.DJConnectAskDjMessageView(None).post(MessageRequest()))
            duplicate = asyncio.run(self.http.DJConnectAskDjMessageView(None).post(MessageRequest()))
        finally:
            self.http.async_handle_ask_dj = original

        self.assertEqual(response["status_code"], 200)
        self.assertEqual(response["payload"]["history_revision"], 1)
        self.assertEqual(response["payload"]["user_message"]["client_message_id"], "client-1")
        self.assertEqual(response["payload"]["assistant_message"]["audio_url"], "/api/djconnect/tts/abc.mp3")
        self.assertEqual(response["payload"]["assistant_message"]["playback_actions"][0]["uri"], "spotify:track:123")
        self.assertTrue(duplicate["payload"]["deduplicated"])

        class HistoryRequest:
            headers = {
                "Authorization": "Bearer device-token",
                "X-DJConnect-Device-ID": runtime.device_status["device_id"],
            }
            app = {"hass": hass}
            context = types.SimpleNamespace(user_id="user-1")
            query = {}

        history = asyncio.run(self.http.DJConnectAskDjHistoryView(None).get(HistoryRequest()))

        self.assertEqual(history["payload"]["history_revision"], 1)
        self.assertEqual(len(history["payload"]["messages"]), 2)
        self.assertEqual(history["payload"]["messages"][0]["role"], "user")
        self.assertEqual(history["payload"]["messages"][1]["role"], "assistant")

    def test_message_endpoint_returns_200_for_text_playback_failure(self) -> None:
        runtime = make_runtime()
        hass = types.SimpleNamespace(data={self.const.DOMAIN: {"runtime": runtime}})

        async def ask_dj(hass_arg, runtime_arg, payload, *, user_id=None):
            return {
                "success": True,
                "error": "playback_failed",
                "text": "Ik heb je muziekverzoek begrepen, maar Spotify kon het nu niet starten.",
                "dj_text": "Ik heb je muziekverzoek begrepen, maar Spotify kon het nu niet starten.",
            }

        class MessageRequest:
            headers = {"Authorization": "Bearer device-token"}
            app = {"hass": hass}
            context = types.SimpleNamespace(user_id="user-1")

            async def json(self):
                return {
                    "client_message_id": "client-play-failed",
                    "client_id": "watch",
                    "device_id": runtime.device_status["device_id"],
                    "client_type": "watchos",
                    "text": "Speel Armin",
                }

        original = self.http.async_handle_ask_dj
        self.http.async_handle_ask_dj = ask_dj
        try:
            response = asyncio.run(self.http.DJConnectAskDjMessageView(None).post(MessageRequest()))
        finally:
            self.http.async_handle_ask_dj = original

        self.assertEqual(response["status_code"], 200)
        self.assertTrue(response["payload"]["success"])
        self.assertEqual(response["payload"]["error"], "playback_failed")
        self.assertEqual(response["payload"]["assistant_message"]["status"], "delivered")

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
