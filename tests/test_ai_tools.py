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
    def __init__(self) -> None:
        self.pending = None
        self.context_memory = {"enabled": False, "mood": 42}

    async def async_context_for_runtime(self, runtime, payload=None, *, user_id=None):
        return {
            "music_dna_key": (payload or {}).get("music_dna_key") or "user:test",
            "memory": self.context_memory,
            "session": [],
        }

    async def async_profile(self, runtime, payload=None, *, user_id=None):
        return {
            "success": True,
            "music_dna_key": (payload or {}).get("music_dna_key") or "user:test",
            "enabled": True,
            "profile": {"summary": "Test Music DNA"},
            "sources": [{"source": "djconnect_music_dna"}],
        }

    async def async_store_pending_followup(self, runtime, followup, payload=None, *, user_id=None):
        self.pending = {"id": "followup-1", **followup, "handled": False}
        return self.pending

    async def async_consume_pending_followup(self, runtime, payload=None, *, user_id=None):
        pending = dict(self.pending or {})
        self.pending = None
        return pending


class AIToolsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        install_http_stubs()
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        cls.ai_tools = importlib.import_module("custom_components.djconnect.ai_tools")
        cls.tool_handlers = importlib.import_module("custom_components.djconnect.tool_handlers")
        cls.tool_registry = importlib.import_module("custom_components.djconnect.tool_registry")

    def setUp(self) -> None:
        self.runtime = types.SimpleNamespace(
            memory=FakeMemory(),
            config={"music_backend": "spotify_direct", "client_type": "ios"},
            device_status={
                "device_id": "djconnect-ios-ABCDEF123456",
                "client_type": "ios",
            },
            pairing_device_id="djconnect-ios-ABCDEF123456",
            device_token="token",
        )
        self.runtime.client_type = lambda: "ios"
        self.runtime.authorize_device_request = (
            lambda headers, device_id, client_type=None: headers.get("Authorization") == "Bearer token"
            and device_id == "djconnect-ios-ABCDEF123456"
            and client_type == "ios"
        )
        self.hass = types.SimpleNamespace()

    def test_all_tools_are_exposed_with_confirmation_boundaries(self) -> None:
        names = {tool["name"] for tool in self.ai_tools.AI_TOOLS}

        self.assertEqual(len(names), 13)
        self.assertIn("djconnect_prepare_playback_action", names)
        self.assertIn("djconnect_execute_confirmed_action", names)
        read_only = {
            tool["name"]
            for tool in self.ai_tools.AI_TOOLS
            if tool.get("read_only")
        }
        self.assertNotIn("djconnect_prepare_playback_action", read_only)
        self.assertNotIn("djconnect_execute_confirmed_action", read_only)
        self.assertIn("djconnect_track_insight", read_only)
        self.assertIn("djconnect_music_dna_profile", read_only)
        self.assertIn("djconnect_music_discovery_feed", read_only)
        self.assertIn("djconnect_vibecast_feed", read_only)
        self.assertIn("djconnect_music_backend_status", read_only)
        self.assertIs(self.ai_tools.AI_TOOLS, self.tool_registry.AI_TOOLS)
        self.assertIs(self.ai_tools.async_call_ai_tool, self.tool_handlers.async_call_ai_tool)

    def test_now_playing_list_outputs_and_search_call_backend_read_only(self) -> None:
        calls = []

        async def run_music_command(hass, runtime, command, value=None, *, play=None):
            calls.append((command, value, play))
            if command == "status":
                return {"success": True, "playback": {"track_name": "Black", "artist": "Pearl Jam"}}
            if command == "devices":
                return {"success": True, "devices": [{"id": "speaker-1", "name": "Woonkamer"}]}
            if command == "search_tracks":
                return {"success": True, "tracks": [{"title": "Black", "artist": "Pearl Jam"}]}
            return {"success": True}

        original = self.tool_handlers.run_music_command
        self.tool_handlers.run_music_command = run_music_command
        try:
            now = asyncio.run(
                self.ai_tools.async_call_ai_tool(self.hass, self.runtime, "djconnect_now_playing")
            )
            outputs = asyncio.run(
                self.ai_tools.async_call_ai_tool(self.hass, self.runtime, "djconnect_list_outputs")
            )
            search = asyncio.run(
                self.ai_tools.async_call_ai_tool(
                    self.hass,
                    self.runtime,
                    "djconnect_search_music",
                    {"query": "Black Pearl Jam", "media_type": "track"},
                )
            )
        finally:
            self.tool_handlers.run_music_command = original

        self.assertEqual(now["playback"]["track_name"], "Black")
        self.assertEqual(outputs["outputs"][0]["name"], "Woonkamer")
        self.assertEqual(search["result"]["tracks"][0]["title"], "Black")
        self.assertEqual(
            calls,
            [
                ("status", None, None),
                ("devices", None, None),
                ("search_tracks", {"query": "Black Pearl Jam", "limit": 5}, False),
            ],
        )

    def test_prepare_and_execute_confirmed_action_requires_pending_payload(self) -> None:
        calls = []

        async def run_music_command(hass, runtime, command, value=None, *, play=None):
            calls.append((command, value, play))
            return {"success": True, "playback": {"track_name": "Black"}}

        original = self.tool_handlers.run_music_command
        self.tool_handlers.run_music_command = run_music_command
        try:
            prepared = asyncio.run(
                self.ai_tools.async_call_ai_tool(
                    self.hass,
                    self.runtime,
                    "djconnect_prepare_playback_action",
                    {"title": "Black", "uri": "spotify:track:black", "kind": "track"},
                )
            )
            executed = asyncio.run(
                self.ai_tools.async_call_ai_tool(
                    self.hass,
                    self.runtime,
                    "djconnect_execute_confirmed_action",
                    {"response": "yes"},
                )
            )
        finally:
            self.tool_handlers.run_music_command = original

        self.assertTrue(prepared["success"])
        self.assertEqual(prepared["playback_actions"], [])
        self.assertEqual(executed["action"], "executed")
        self.assertEqual(calls, [("play_uris", {"uris": ["spotify:track:black"]}, True)])

    def test_music_dna_summary_is_read_only(self) -> None:
        result = asyncio.run(
            self.ai_tools.async_call_ai_tool(
                self.hass,
                self.runtime,
                "djconnect_music_dna_summary",
                {"music_dna_key": "user:test"},
            )
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["sources"][0]["source"], "djconnect_music_dna")

    def test_music_discovery_feed_tool_reads_feed_without_playback_mutation(self) -> None:
        self.runtime.memory.context_memory = {
            "enabled": True,
            "recent_tracks": [
                {
                    "uri": "spotify:track:black",
                    "track_name": "Black",
                    "artist": "Pearl Jam",
                    "album_image_url": "https://img.example/black.jpg",
                }
            ],
        }
        calls = []

        async def run_music_command(hass, runtime, command, value=None, *, play=None):
            calls.append((command, value, play))
            return {"success": True}

        original = self.tool_handlers.run_music_command
        self.tool_handlers.run_music_command = run_music_command
        try:
            result = asyncio.run(
                self.ai_tools.async_call_ai_tool(
                    self.hass,
                    self.runtime,
                    "djconnect_music_discovery_feed",
                    {"music_dna_key": "user:test", "limit": 1},
                    user_id="user-1",
                )
            )
        finally:
            self.tool_handlers.run_music_command = original

        self.assertTrue(result["success"])
        self.assertTrue(result["enabled"])
        self.assertEqual(result["source"], "music_dna")
        self.assertEqual(result["sections"][0]["id"], "because_you_like")
        self.assertEqual(result["sections"][0]["items"][0]["title"], "Black")
        self.assertEqual(calls, [])

    def test_music_backend_status_tool_returns_safe_metadata(self) -> None:
        result = asyncio.run(
            self.ai_tools.async_call_ai_tool(
                self.hass,
                self.runtime,
                "djconnect_music_backend_status",
            )
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["type"], "music_backend_status")
        self.assertEqual(result["selected"], "spotify_direct")
        self.assertIn("music_backend_capabilities", result)
        self.assertNotIn("spotify_refresh_token", result)

    def test_vibecast_feed_tool_uses_existing_gates_without_playback_mutation(self) -> None:
        self.hass.data = {"djconnect": {"runtime": self.runtime}}
        self.hass.states = types.SimpleNamespace(get=lambda entity_id: None)
        vibecast = importlib.import_module("custom_components.djconnect.vibecast")
        calls = []

        async def run_music_command(hass, runtime, command, value=None, *, play=None):
            calls.append((command, value, play))
            if command == "search_media":
                return {
                    "success": True,
                    "item": {
                        "artist": value.get("query"),
                        "image_url": "https://img.example/pearl-jam.jpg",
                    },
                }
            return {
                "success": True,
                "playback": {
                    "has_playback": True,
                    "is_playing": True,
                    "state": "playing",
                    "title": "Black",
                    "artist": "Pearl Jam",
                    "album": "Ten",
                },
            }

        original = vibecast.run_music_command
        vibecast.run_music_command = run_music_command
        try:
            result = asyncio.run(
                self.ai_tools.async_call_ai_tool(
                    self.hass,
                    self.runtime,
                    "djconnect_vibecast_feed",
                    {"locale": "nl-NL", "render_capabilities": "bold,accent"},
                )
            )
        finally:
            vibecast.run_music_command = original

        self.assertTrue(result["success"])
        self.assertTrue(result["enabled"])
        self.assertEqual(result["context"]["title"], "Black")
        self.assertTrue(result["context"]["artist_image_url"].startswith("/api/djconnect/v1/image_proxy/"))
        self.assertEqual(
            calls,
            [
                ("status", None, None),
                ("search_media", {"query": "Pearl Jam", "type": "artist", "limit": 1}, None),
            ],
        )


if __name__ == "__main__":
    unittest.main()
