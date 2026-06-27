from __future__ import annotations

import asyncio
import importlib
from pathlib import Path
import sys
import types
import unittest

from tests.test_ask_dj import make_runtime
from tests.test_http_voice_helpers import install_http_stubs

ROOT = Path(__file__).resolve().parents[1]


class AskDjAIToolRoutingTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        install_http_stubs()
        package = types.ModuleType("custom_components.djconnect")
        package.__path__ = [str(ROOT / "custom_components" / "djconnect")]
        sys.modules["custom_components.djconnect"] = package
        cls.ask_dj = importlib.import_module("custom_components.djconnect.ask_dj")

    def test_playback_context_routes_through_now_playing_tool(self) -> None:
        calls = []

        async def tool(hass, runtime, name, parameters=None, *, user_id=None):
            calls.append((name, parameters))
            return {"success": True, "playback": {"track_name": "Black"}}

        original = self.ask_dj.async_call_ai_tool
        self.ask_dj.async_call_ai_tool = tool
        try:
            result = asyncio.run(self.ask_dj._playback_context(types.SimpleNamespace(), make_runtime()))
        finally:
            self.ask_dj.async_call_ai_tool = original

        self.assertEqual(result["track_name"], "Black")
        self.assertEqual(calls, [("djconnect_now_playing", None)])

    def test_output_devices_route_through_list_outputs_tool(self) -> None:
        calls = []

        async def tool(hass, runtime, name, parameters=None, *, user_id=None):
            calls.append((name, parameters))
            return {"success": True, "outputs": [{"id": "speaker-1", "name": "Woonkamer"}]}

        original = self.ask_dj.async_call_ai_tool
        self.ask_dj.async_call_ai_tool = tool
        try:
            result = asyncio.run(
                self.ask_dj._output_devices(
                    types.SimpleNamespace(),
                    make_runtime(),
                    self.ask_dj.AskDjIntent("informational", "list_outputs", "devices"),
                )
            )
        finally:
            self.ask_dj.async_call_ai_tool = original

        self.assertEqual(result[0]["name"], "Woonkamer")
        self.assertEqual(calls, [("djconnect_list_outputs", None)])

    def test_track_insight_response_routes_through_track_insight_tool(self) -> None:
        calls = []

        async def tool(hass, runtime, name, parameters=None, *, user_id=None):
            calls.append((name, parameters))
            return {
                "track": {"title": "Black", "artist": "Pearl Jam"},
                "analysis": {"summary": "A spacious build."},
                "music_dna": {"summary": "This track fits your Music DNA."},
            }

        original = self.ask_dj.async_call_ai_tool
        self.ask_dj.async_call_ai_tool = tool
        try:
            result = asyncio.run(
                self.ask_dj._track_insight_response(
                    types.SimpleNamespace(),
                    make_runtime(),
                    {"text": "Geef Track Insight voor dit nummer"},
                )
            )
        finally:
            self.ask_dj.async_call_ai_tool = original

        self.assertEqual(result["type"], "track_insight")
        self.assertEqual(result["track_insight"]["track"]["title"], "Black")
        self.assertEqual(calls, [("djconnect_track_insight", {"text": "Geef Track Insight voor dit nummer"})])

    def test_recently_played_routes_through_recent_tool(self) -> None:
        calls = []

        async def tool(hass, runtime, name, parameters=None, *, user_id=None):
            calls.append((name, parameters))
            return {
                "success": True,
                "tracks": [
                    {
                        "track_name": "Black",
                        "artist": "Pearl Jam",
                        "played_at": self.ask_dj.datetime.now(self.ask_dj.timezone.utc).isoformat(),
                    }
                ],
            }

        original = self.ask_dj.async_call_ai_tool
        self.ask_dj.async_call_ai_tool = tool
        try:
            result = asyncio.run(
                self.ask_dj._recently_played_history_response(
                    types.SimpleNamespace(),
                    make_runtime(),
                    "Welke nummers heb ik afgelopen uur afgespeeld?",
                )
            )
        finally:
            self.ask_dj.async_call_ai_tool = original

        self.assertEqual(result["intent"]["intent"], "recently_played_history")
        self.assertEqual(calls[0][0], "djconnect_recently_played")

    def test_playlist_search_routes_through_search_tool(self) -> None:
        calls = []

        async def tool(hass, runtime, name, parameters=None, *, user_id=None):
            calls.append((name, parameters))
            return {"success": True, "result": {"playlists": [{"name": "Grunge", "uri": "spotify:playlist:g"}]}}

        original = self.ask_dj.async_call_ai_tool
        self.ask_dj.async_call_ai_tool = tool
        try:
            result = asyncio.run(
                self.ask_dj._spotify_playlist_search(types.SimpleNamespace(), make_runtime(), "grunge", limit=5)
            )
        finally:
            self.ask_dj.async_call_ai_tool = original

        self.assertEqual(result["playlists"][0]["name"], "Grunge")
        self.assertEqual(calls, [("djconnect_search_music", {"query": "grunge", "media_type": "playlist", "limit": 5})])

    def test_personal_recommendations_route_through_recommendation_tool(self) -> None:
        calls = []

        async def tool(hass, runtime, name, parameters=None, *, user_id=None):
            calls.append((name, parameters))
            return {
                "success": True,
                "spotify_profile": {
                    "top_tracks_by_range": {
                        "short_term": [
                            {
                                "track_name": "Black",
                                "artist": "Pearl Jam",
                                "uri": "spotify:track:black",
                            }
                        ]
                    }
                },
            }

        original = self.ask_dj.async_call_ai_tool
        self.ask_dj.async_call_ai_tool = tool
        try:
            result = asyncio.run(
                self.ask_dj._handle_informational(
                    types.SimpleNamespace(),
                    make_runtime(),
                    "Geef persoonlijke muziekaanbevelingen",
                    {},
                    {"memory": {}, "session": []},
                    {},
                    [],
                )
            )
        finally:
            self.ask_dj.async_call_ai_tool = original

        self.assertEqual(result["action"], "none")
        self.assertEqual(result["playback_actions"][0]["uri"], "spotify:track:black")
        self.assertEqual(calls, [("djconnect_build_recommendations", {"music_dna_key": None})])


if __name__ == "__main__":
    unittest.main()
