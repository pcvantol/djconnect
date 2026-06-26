from __future__ import annotations

import asyncio
import importlib
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


if __name__ == "__main__":
    unittest.main()
