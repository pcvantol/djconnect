from __future__ import annotations

import asyncio
import importlib
import sys
import types
import unittest

from tests.test_config_flow_helpers import install_homeassistant_stubs


class UseCaseLayerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        install_homeassistant_stubs()
        cls.use_cases = importlib.import_module("custom_components.djconnect.use_cases")

    def test_run_music_command_uses_spotify_direct_adapter(self) -> None:
        calls: list[dict] = []

        async def fake_spotify_command(hass, runtime, command, value=None, *, play=None):
            calls.append(
                {
                    "hass": hass,
                    "runtime": runtime,
                    "command": command,
                    "value": value,
                    "play": play,
                }
            )
            return {"success": True, "playback": {"has_playback": True}}

        original = self.use_cases._handle_spotify_command
        self.use_cases._handle_spotify_command = fake_spotify_command
        try:
            hass = types.SimpleNamespace()
            runtime = types.SimpleNamespace(config={})
            result = asyncio.run(
                self.use_cases.run_music_command(
                    hass,
                    runtime,
                    "play",
                    "spotify:track:1",
                    play=True,
                )
            )
        finally:
            self.use_cases._handle_spotify_command = original

        self.assertEqual(calls[0]["command"], "play")
        self.assertEqual(calls[0]["value"], "spotify:track:1")
        self.assertTrue(calls[0]["play"])
        self.assertTrue(result["success"])
        self.assertTrue(result["backend_available"])
        self.assertEqual(result["provider"], "spotify_direct")

    def test_run_music_command_accepts_typed_command_enum(self) -> None:
        calls: list[dict] = []

        async def fake_spotify_command(hass, runtime, command, value=None, *, play=None):
            calls.append({"command": command, "value": value, "play": play})
            return {"success": True}

        original = self.use_cases._handle_spotify_command
        self.use_cases._handle_spotify_command = fake_spotify_command
        try:
            result = asyncio.run(
                self.use_cases.run_music_command(
                    types.SimpleNamespace(),
                    types.SimpleNamespace(config={}),
                    self.use_cases.MusicCommand.SET_VOLUME,
                    55,
                )
            )
        finally:
            self.use_cases._handle_spotify_command = original

        self.assertEqual(calls, [{"command": "set_volume", "value": 55, "play": None}])
        self.assertTrue(result["success"])

    def test_music_backend_result_preserves_extra_fields(self) -> None:
        result = self.use_cases.MusicBackendResult.from_mapping(
            {
                "success": True,
                "backend_available": True,
                "playback": {"track_name": "Alive"},
                "devices": [{"name": "Kitchen"}],
            },
            provider="spotify_direct",
        )

        self.assertEqual(
            result.to_dict(),
            {
                "devices": [{"name": "Kitchen"}],
                "success": True,
                "provider": "spotify_direct",
                "source": "spotify_direct",
                "backend_available": True,
                "playback": {"track_name": "Alive"},
            },
        )

    def test_playback_action_dto_serializes_backend_value(self) -> None:
        action = self.use_cases.PlaybackAction(
            id="spotify:track:1",
            kind="track",
            title="Alive",
            backend="spotify_direct",
            value=self.use_cases.BackendActionValue(
                uri="spotify:track:1",
                title="Alive",
            ),
        )

        self.assertEqual(
            action.to_dict(),
            {
                "id": "spotify:track:1",
                "kind": "track",
                "label": "Play Now",
                "button_label": "Play Now",
                "action_style": "play_now",
                "title": "Alive",
                "backend": "spotify_direct",
                "provider": "spotify",
                "music_backend_revision": 0,
                "value": {"uri": "spotify:track:1", "title": "Alive"},
            },
        )

    def test_build_playback_action_uses_spotify_uri_value(self) -> None:
        action = self.use_cases.build_playback_action(
            types.SimpleNamespace(config={"music_backend": "spotify_direct"}),
            {
                "uri": "spotify:album:abc",
                "title": "Album",
                "artist": "Artist",
                "image_url": "https://example.test/album.jpg",
            },
            "album",
            "Ask DJ result.",
        )

        self.assertEqual(action["uri"], "spotify:album:abc")
        self.assertEqual(action["value"]["uri"], "spotify:album:abc")
        self.assertEqual(action["kind"], "album")
        self.assertEqual(action["reason"], "Ask DJ result.")

    def test_build_playback_action_uses_music_assistant_item_id_value(self) -> None:
        action = self.use_cases.build_playback_action(
            types.SimpleNamespace(
                config={
                    "music_backend": "music_assistant",
                    "music_backend_revision": 3,
                    "music_assistant_player": "media_player.mass_living",
                }
            ),
            {
                "item_id": "library://playlist/abc",
                "title": "Playlist",
                "subtitle": "Library",
            },
            "playlist",
            "Ask DJ result.",
        )

        self.assertNotIn("uri", action)
        self.assertEqual(action["backend"], "music_assistant")
        self.assertEqual(action["music_backend_revision"], 3)
        self.assertEqual(action["value"]["item_id"], "library://playlist/abc")
        self.assertEqual(action["value"]["media_type"], "playlist")
        self.assertEqual(action["value"]["target_player_id"], "media_player.mass_living")

    def test_capability_fallback_raises_backend_error(self) -> None:
        uc = self.use_cases

        class QueueLessBackend:
            provider = "future_backend"
            capabilities = uc.MusicBackendCapabilities()

            async def handle_command(self, command, value=None, *, play=None):
                return {"success": True}

        use_cases = self.use_cases.DJConnectUseCases(
            types.SimpleNamespace(),
            types.SimpleNamespace(config={}),
            backend=QueueLessBackend(),
        )

        with self.assertRaises(self.use_cases.MusicBackendCapabilityError):
            asyncio.run(use_cases.get_queue())

    def test_backend_response_shape_is_normalized(self) -> None:
        uc = self.use_cases

        class MinimalBackend:
            provider = "minimal"
            capabilities = uc.MusicBackendCapabilities()

            async def handle_command(self, command, value=None, *, play=None):
                return {"playback": {"has_playback": False}}

        use_cases = self.use_cases.DJConnectUseCases(
            types.SimpleNamespace(),
            types.SimpleNamespace(config={}),
            backend=MinimalBackend(),
        )

        result = asyncio.run(use_cases.get_current_track())

        self.assertTrue(result["success"])
        self.assertTrue(result["backend_available"])
        self.assertEqual(result["provider"], "minimal")
        self.assertEqual(result["source"], "minimal")
        self.assertEqual(result["playback"], {"has_playback": False})

    def test_run_text_command_delegates_through_use_case_boundary(self) -> None:
        calls = []
        processor = types.ModuleType("custom_components.djconnect.processor")

        async def process_text_command(hass, runtime, text, *, play, correct_stt, user_id=None):
            calls.append((hass, runtime, text, play, correct_stt, user_id))
            return {"success": True, "dj_text": "Done"}

        processor.process_text_command = process_text_command
        original = sys.modules.get("custom_components.djconnect.processor")
        sys.modules["custom_components.djconnect.processor"] = processor
        try:
            hass = types.SimpleNamespace()
            runtime = types.SimpleNamespace(config={})
            result = asyncio.run(
                self.use_cases.run_text_command(
                    hass,
                    runtime,
                    "play something",
                    play=False,
                    correct_stt=True,
                    user_id="user-1",
                )
            )
        finally:
            if original is None:
                sys.modules.pop("custom_components.djconnect.processor", None)
            else:
                sys.modules["custom_components.djconnect.processor"] = original

        self.assertEqual(result["dj_text"], "Done")
        self.assertEqual(calls, [(hass, runtime, "play something", False, True, "user-1")])

    def test_music_assistant_backend_routes_player_services(self) -> None:
        uc = self.use_cases
        calls = []

        class State:
            state = "playing"
            attributes = {
                "friendly_name": "Kitchen",
                "media_title": "Bella",
                "media_artist": "Finnebassen",
                "media_album_name": "Bella EP",
                "media_content_id": "spotify:track:1",
                "media_content_type": "music",
                "volume_level": 0.45,
            }

        class States:
            def get(self, entity_id):
                return State()

        class Services:
            async def async_call(self, domain, service, data, *, blocking=False):
                calls.append((domain, service, data, blocking))

        hass = types.SimpleNamespace(states=States(), services=Services())
        runtime = types.SimpleNamespace(
            config={
                "music_backend": "music_assistant",
                "music_assistant_player": "media_player.mass_kitchen",
            }
        )

        result = asyncio.run(
            uc.run_music_command(hass, runtime, "set_volume", 42)
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["provider"], "music_assistant")
        self.assertEqual(result["playback"]["track_name"], "Bella")
        self.assertEqual(result["playback"]["volume_percent"], 45)
        self.assertEqual(
            calls,
            [
                (
                    "media_player",
                    "volume_set",
                    {
                        "entity_id": "media_player.mass_kitchen",
                        "volume_level": 0.42,
                    },
                    True,
                )
            ],
        )

    def test_music_assistant_backend_reports_configured_output(self) -> None:
        uc = self.use_cases

        class State:
            state = "paused"
            attributes = {"friendly_name": "Office"}

        class States:
            def get(self, entity_id):
                return State()

        hass = types.SimpleNamespace(states=States(), services=types.SimpleNamespace())
        runtime = types.SimpleNamespace(
            config={
                "music_backend": "music_assistant",
                "music_assistant_player": "media_player.mass_office",
            }
        )

        result = asyncio.run(uc.run_music_command(hass, runtime, "devices"))

        self.assertTrue(result["success"])
        self.assertEqual(result["provider"], "music_assistant")
        self.assertEqual(result["devices"][0]["entity_id"], "media_player.mass_office")
        self.assertEqual(result["devices"][0]["name"], "Office")

    def test_music_backend_metadata_reports_revision_capabilities_and_target(self) -> None:
        uc = self.use_cases

        class State:
            attributes = {"friendly_name": "Woonkamer"}

        class States:
            def get(self, entity_id):
                return State()

        hass = types.SimpleNamespace(states=States())
        runtime = types.SimpleNamespace(
            config={
                "music_backend": "music_assistant",
                "music_backend_revision": 4,
                "music_assistant_player": "media_player.mass_woonkamer",
            }
        )

        metadata = uc.music_backend_metadata(hass, runtime)

        self.assertEqual(metadata["music_backend"], "music_assistant")
        self.assertEqual(metadata["music_backend_name"], "Music Assistant")
        self.assertTrue(metadata["music_backend_available"])
        self.assertEqual(metadata["music_backend_revision"], 4)
        self.assertTrue(metadata["music_backend_capabilities"]["supports_volume"])
        self.assertEqual(
            metadata["music_target_player"],
            {"id": "media_player.mass_woonkamer", "name": "Woonkamer"},
        )

    def test_music_assistant_unsupported_use_case_degrades_by_capability(self) -> None:
        uc = self.use_cases
        hass = types.SimpleNamespace()
        runtime = types.SimpleNamespace(
            config={
                "music_backend": "music_assistant",
                "music_assistant_player": "media_player.mass_living",
            }
        )

        with self.assertRaises(uc.MusicBackendCapabilityError):
            asyncio.run(uc.run_music_command(hass, runtime, "recently_played"))

    def test_spotify_direct_action_fields_keep_legacy_uri_value(self) -> None:
        metadata = self.use_cases.music_backend_action_fields(
            types.SimpleNamespace(
                config={"music_backend": "spotify_direct", "music_backend_revision": 2}
            ),
            "track",
            "spotify:track:abc",
            "https://example.test/art.jpg",
            "Track",
            "Artist",
        )

        self.assertEqual(metadata["backend"], "spotify_direct")
        self.assertEqual(metadata["provider"], "spotify")
        self.assertEqual(metadata["music_backend_revision"], 2)
        self.assertEqual(
            metadata["value"],
            {
                "title": "Track",
                "subtitle": "Artist",
                "image_url": "https://example.test/art.jpg",
                "uri": "spotify:track:abc",
            },
        )

    def test_music_assistant_action_fields_use_generic_item_value(self) -> None:
        metadata = self.use_cases.music_backend_action_fields(
            types.SimpleNamespace(
                config={
                    "music_backend": "music_assistant",
                    "music_backend_revision": 7,
                    "music_assistant_player": "media_player.mass_living",
                }
            ),
            "album",
            "library://album/123",
            "",
            "Album",
            "Artist",
        )

        self.assertEqual(metadata["backend"], "music_assistant")
        self.assertEqual(metadata["provider"], "music_assistant")
        self.assertEqual(metadata["music_backend_revision"], 7)
        self.assertEqual(
            metadata["value"],
            {
                "title": "Album",
                "subtitle": "Artist",
                "item_id": "library://album/123",
                "provider": "music_assistant",
                "media_type": "album",
                "target_player_id": "media_player.mass_living",
            },
        )


if __name__ == "__main__":
    unittest.main()
