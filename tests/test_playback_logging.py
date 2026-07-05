from __future__ import annotations

import asyncio
import importlib
import logging
import types
import unittest

from tests.test_http_voice_helpers import install_http_stubs


class PlaybackLoggingTests(unittest.TestCase):
    def setUp(self) -> None:
        install_http_stubs()
        self.api_handlers = importlib.import_module("custom_components.djconnect.api_handlers")

    def test_command_endpoint_debug_log_omits_playback_secrets_and_metadata(self) -> None:
        runtime = types.SimpleNamespace(
            config={
                "client_type": "ios",
                "device_id": "djconnect-ios-ABCDEF123456",
                "music_backend": "spotify_direct",
                "spotify_refresh_token": "refresh-secret-token",
            },
            device_status={
                "client_type": "ios",
                "device_id": "djconnect-ios-ABCDEF123456",
                "backend_available": True,
            },
            device_token="device-secret-token",
            last_playback={},
            update=lambda **kwargs: None,
        )
        hass = types.SimpleNamespace(data={})

        original_resolve = self.api_handlers.resolve_runtime
        original_authorize = self.api_handlers.authorize_runtime_device_request
        original_run = self.api_handlers.http_helpers.run_music_command
        original_level = self.api_handlers._LOGGER.level

        async def run_music_command(_hass, _runtime, command, value=None, *, play=False):
            self.assertEqual(command, "play_uris")
            self.assertTrue(play)
            return {
                "success": True,
                "music_backend": "spotify_direct",
                "backend_available": True,
                "playback": {"has_playback": True, "state": "playing", "is_playing": True},
                "queue": [{"uri": "spotify:track:another-secret"}],
                "devices": [{"id": "spotify-device-secret", "name": "Living Room"}],
            }

        self.api_handlers.resolve_runtime = lambda *args, **kwargs: runtime
        self.api_handlers.authorize_runtime_device_request = lambda *args, **kwargs: True
        self.api_handlers.http_helpers.run_music_command = run_music_command
        self.api_handlers._LOGGER.setLevel(logging.DEBUG)
        try:
            with self.assertLogs(self.api_handlers._LOGGER, level="DEBUG") as captured:
                result, status = asyncio.run(
                    self.api_handlers.async_handle_command_payload(
                        hass,
                        {
                            "client_type": "ios",
                            "device_id": "djconnect-ios-ABCDEF123456",
                            "command": "play_uris",
                            "play": True,
                            "value": {
                                "uri": "spotify:track:very-secret",
                                "title": "Private Track",
                                "artist": "Secret Artist",
                                "target_player_id": "media_player.spotify_secret_room",
                            },
                        },
                        headers={
                            "Authorization": "Bearer device-secret-token",
                            "X-DJConnect-Device-ID": "djconnect-ios-ABCDEF123456",
                        },
                    )
                )
        finally:
            self.api_handlers.resolve_runtime = original_resolve
            self.api_handlers.authorize_runtime_device_request = original_authorize
            self.api_handlers.http_helpers.run_music_command = original_run
            self.api_handlers._LOGGER.setLevel(original_level)

        self.assertEqual(status, 200)
        self.assertTrue(result["success"])
        logs = "\n".join(captured.output)
        self.assertIn("DJConnect playback command request", logs)
        self.assertIn("DJConnect playback command result", logs)
        self.assertIn("command=play_uris", logs)
        self.assertIn("queue_items=1", logs)
        self.assertIn("device_id=djconnec...3456", logs)
        self.assertNotIn("spotify:track:very-secret", logs)
        self.assertNotIn("spotify:track:another-secret", logs)
        self.assertNotIn("Private Track", logs)
        self.assertNotIn("Secret Artist", logs)
        self.assertNotIn("device-secret-token", logs)
        self.assertNotIn("refresh-secret-token", logs)

    def test_queue_endpoint_debug_log_omits_queue_items(self) -> None:
        runtime = types.SimpleNamespace(
            config={
                "client_type": "ios",
                "device_id": "djconnect-ios-ABCDEF123456",
                "music_backend": "spotify_direct",
                "spotify_refresh_token": "refresh-secret-token",
            },
            device_status={
                "client_type": "ios",
                "device_id": "djconnect-ios-ABCDEF123456",
                "backend_available": True,
            },
            device_token="device-secret-token",
            last_playback={},
            update=lambda **kwargs: None,
        )
        hass = types.SimpleNamespace(data={})

        original_resolve = self.api_handlers.resolve_runtime
        original_authorize = self.api_handlers.authorize_runtime_device_request
        original_run = self.api_handlers.http_helpers.run_music_command
        original_level = self.api_handlers._LOGGER.level

        async def run_music_command(_hass, _runtime, command, value=None, *, play=False):
            self.assertEqual(command, "queue")
            self.assertFalse(play)
            return {
                "success": True,
                "music_backend": "spotify_direct",
                "backend_available": True,
                "queue": {
                    "context_uri": "spotify:playlist:secret-context",
                    "currently_playing": {
                        "uri": "spotify:track:current-secret",
                        "title": "Current Private Track",
                    },
                    "items": [
                        {
                            "uri": "spotify:track:queue-secret",
                            "title": "Queued Private Track",
                            "artist": "Hidden Artist",
                        }
                    ],
                },
            }

        self.api_handlers.resolve_runtime = lambda *args, **kwargs: runtime
        self.api_handlers.authorize_runtime_device_request = lambda *args, **kwargs: True
        self.api_handlers.http_helpers.run_music_command = run_music_command
        self.api_handlers._LOGGER.setLevel(logging.DEBUG)
        try:
            with self.assertLogs(self.api_handlers._LOGGER, level="DEBUG") as captured:
                result, status = asyncio.run(
                    self.api_handlers.async_handle_command_payload(
                        hass,
                        {
                            "client_type": "ios",
                            "device_id": "djconnect-ios-ABCDEF123456",
                            "command": "queue",
                        },
                        headers={
                            "Authorization": "Bearer device-secret-token",
                            "X-DJConnect-Device-ID": "djconnect-ios-ABCDEF123456",
                        },
                    )
                )
        finally:
            self.api_handlers.resolve_runtime = original_resolve
            self.api_handlers.authorize_runtime_device_request = original_authorize
            self.api_handlers.http_helpers.run_music_command = original_run
            self.api_handlers._LOGGER.setLevel(original_level)

        self.assertEqual(status, 200)
        self.assertTrue(result["success"])
        logs = "\n".join(captured.output)
        self.assertIn("DJConnect queue endpoint request", logs)
        self.assertIn("DJConnect queue endpoint result", logs)
        self.assertIn("queue_items=1", logs)
        self.assertIn("context_present=True", logs)
        self.assertIn("current_present=True", logs)
        self.assertNotIn("spotify:playlist:secret-context", logs)
        self.assertNotIn("spotify:track:current-secret", logs)
        self.assertNotIn("spotify:track:queue-secret", logs)
        self.assertNotIn("Current Private Track", logs)
        self.assertNotIn("Queued Private Track", logs)
        self.assertNotIn("Hidden Artist", logs)
        self.assertNotIn("device-secret-token", logs)
        self.assertNotIn("refresh-secret-token", logs)

    def test_playlists_endpoint_debug_log_omits_playlist_metadata(self) -> None:
        runtime = types.SimpleNamespace(
            config={
                "client_type": "ios",
                "device_id": "djconnect-ios-ABCDEF123456",
                "music_backend": "spotify_direct",
                "spotify_refresh_token": "refresh-secret-token",
            },
            device_status={
                "client_type": "ios",
                "device_id": "djconnect-ios-ABCDEF123456",
                "backend_available": True,
            },
            device_token="device-secret-token",
            last_playback={},
            update=lambda **kwargs: None,
        )
        hass = types.SimpleNamespace(data={})

        original_resolve = self.api_handlers.resolve_runtime
        original_authorize = self.api_handlers.authorize_runtime_device_request
        original_run = self.api_handlers.http_helpers.run_music_command
        original_level = self.api_handlers._LOGGER.level

        async def run_music_command(_hass, _runtime, command, value=None, *, play=False):
            self.assertEqual(command, "playlists")
            self.assertEqual(value["limit"], 12)
            self.assertFalse(play)
            return {
                "success": True,
                "music_backend": "spotify_direct",
                "backend_available": True,
                "playlists": [
                    {
                        "id": "spotify:playlist:secret-one",
                        "uri": "spotify:playlist:secret-one",
                        "name": "Private Playlist",
                        "owner": "Hidden Owner",
                        "image_url": "https://images.example/private.jpg",
                    }
                ],
                "count": 1,
            }

        self.api_handlers.resolve_runtime = lambda *args, **kwargs: runtime
        self.api_handlers.authorize_runtime_device_request = lambda *args, **kwargs: True
        self.api_handlers.http_helpers.run_music_command = run_music_command
        self.api_handlers._LOGGER.setLevel(logging.DEBUG)
        try:
            with self.assertLogs(self.api_handlers._LOGGER, level="DEBUG") as captured:
                result, status = asyncio.run(
                    self.api_handlers.async_handle_command_payload(
                        hass,
                        {
                            "client_type": "ios",
                            "device_id": "djconnect-ios-ABCDEF123456",
                            "command": "playlists",
                            "value": {"limit": 12, "market": "NL"},
                        },
                        headers={
                            "Authorization": "Bearer device-secret-token",
                            "X-DJConnect-Device-ID": "djconnect-ios-ABCDEF123456",
                        },
                    )
                )
        finally:
            self.api_handlers.resolve_runtime = original_resolve
            self.api_handlers.authorize_runtime_device_request = original_authorize
            self.api_handlers.http_helpers.run_music_command = original_run
            self.api_handlers._LOGGER.setLevel(original_level)

        self.assertEqual(status, 200)
        self.assertTrue(result["success"])
        logs = "\n".join(captured.output)
        self.assertIn("DJConnect playlists endpoint request", logs)
        self.assertIn("DJConnect playlists endpoint result", logs)
        self.assertIn("limit=12", logs)
        self.assertIn("playlists=1", logs)
        self.assertIn("count=1", logs)
        self.assertIn("aliases_present=True", logs)
        self.assertNotIn("spotify:playlist:secret-one", logs)
        self.assertNotIn("Private Playlist", logs)
        self.assertNotIn("Hidden Owner", logs)
        self.assertNotIn("images.example", logs)
        self.assertNotIn("device-secret-token", logs)
        self.assertNotIn("refresh-secret-token", logs)
