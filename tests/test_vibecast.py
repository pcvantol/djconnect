from __future__ import annotations

import asyncio
import types
import unittest

from tests.test_http_voice_helpers import install_http_stubs

install_http_stubs()

from custom_components.djconnect.const import (  # noqa: E402
    CONF_CLIENT_TYPE,
    CONF_DEVICE_ID,
    CONF_MUSIC_BACKEND,
    CONF_MUSIC_BACKEND_REVISION,
    MUSIC_BACKEND_MUSIC_ASSISTANT,
)
from custom_components.djconnect import vibecast  # noqa: E402


class VibeCastTests(unittest.TestCase):
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
            "X-DJConnect-Locale": "nl-NL",
        }

    def tearDown(self) -> None:
        vibecast.run_music_command = self._original_run_music_command

    @property
    def _original_run_music_command(self):
        return getattr(self, "__original_run_music_command", vibecast.run_music_command)

    @_original_run_music_command.setter
    def _original_run_music_command(self, value):
        setattr(self, "__original_run_music_command", value)

    def _patch_status(self, result=None, *, raises: Exception | None = None):
        self._original_run_music_command = vibecast.run_music_command

        async def command(hass, runtime, command_name, value=None, *, play=None):
            self.assertEqual(command_name, "status")
            if raises is not None:
                raise raises
            return result or _status_payload()

        vibecast.run_music_command = command

    def test_authenticated_success_with_active_current_track(self) -> None:
        self._patch_status()
        result, status = asyncio.run(
            vibecast.async_handle_vibecast_payload(
                self.hass,
                {"client_type": "ios", "device_id": "djconnect-ios-ABCDEF123456"},
                headers=self.headers,
            )
        )
        self.assertEqual(status, 200)
        self.assertTrue(result["enabled"])
        self.assertEqual(result["context"]["title"], "Vibe Song")
        self.assertEqual(result["context"]["artist"], "The Contexts")
        self.assertEqual(result["context"]["music_backend"], "spotify_direct")
        self.assertGreaterEqual(len(result["items"]), 1)

    def test_no_active_playback_returns_disabled_json(self) -> None:
        self._patch_status({"success": True, "playback": {"has_playback": False}})
        result, status = asyncio.run(
            vibecast.async_handle_vibecast_payload(
                self.hass,
                {"client_type": "ios", "device_id": "djconnect-ios-ABCDEF123456"},
                headers=self.headers,
            )
        )
        self.assertEqual(status, 200)
        self.assertFalse(result["enabled"])
        self.assertEqual(result["reason"], "no_active_playback")
        self.assertEqual(result["items"], [])

    def test_feature_disabled_and_premium_unavailable_are_clean_disabled_responses(self) -> None:
        self.runtime.config["vibecast_enabled"] = False
        result, status = asyncio.run(
            vibecast.async_handle_vibecast_payload(
                self.hass,
                {"client_type": "ios", "device_id": "djconnect-ios-ABCDEF123456"},
                headers=self.headers,
            )
        )
        self.assertEqual(status, 200)
        self.assertEqual(result["reason"], "feature_disabled")
        self.runtime.config["vibecast_enabled"] = True
        self.runtime.config["vibecast_entitled"] = False
        result, status = asyncio.run(
            vibecast.async_handle_vibecast_payload(
                self.hass,
                {"client_type": "ios", "device_id": "djconnect-ios-ABCDEF123456"},
                headers=self.headers,
            )
        )
        self.assertEqual(status, 200)
        self.assertEqual(result["reason"], "premium_unavailable")

    def test_invalid_client_type_and_mismatch_do_not_clear_pairing(self) -> None:
        result, status = asyncio.run(
            vibecast.async_handle_vibecast_payload(
                self.hass,
                {"client_type": "esp32", "device_id": "djconnect-ios-ABCDEF123456"},
                headers={**self.headers, "X-DJConnect-Client-Type": "esp32"},
            )
        )
        self.assertEqual(status, 400)
        self.assertEqual(result["reason"], "invalid_client_type")
        self.assertEqual(self.runtime.device_token, "token")
        self.runtime.config[CONF_CLIENT_TYPE] = "macos"
        result, status = asyncio.run(
            vibecast.async_handle_vibecast_payload(
                self.hass,
                {"client_type": "ios", "device_id": "djconnect-ios-ABCDEF123456"},
                headers=self.headers,
            )
        )
        self.assertEqual(status, 400)
        self.assertEqual(result["reason"], "client_type_mismatch")
        self.assertEqual(self.runtime.device_token, "token")

    def test_provider_failure_is_safe_json_without_raw_error(self) -> None:
        self._patch_status(raises=RuntimeError("token secret provider exploded"))
        result, status = asyncio.run(
            vibecast.async_handle_vibecast_payload(
                self.hass,
                {"client_type": "ios", "device_id": "djconnect-ios-ABCDEF123456"},
                headers=self.headers,
            )
        )
        self.assertEqual(status, 200)
        self.assertFalse(result["enabled"])
        self.assertEqual(result["reason"], "provider_unavailable")
        self.assertNotIn("secret", str(result).lower())

    def test_cache_hit_reuses_revision_and_items(self) -> None:
        calls = []
        self._original_run_music_command = vibecast.run_music_command

        async def command(hass, runtime, command_name, value=None, *, play=None):
            calls.append(command_name)
            return _status_payload()

        vibecast.run_music_command = command
        payload = {"client_type": "ios", "device_id": "djconnect-ios-ABCDEF123456"}
        first, _ = asyncio.run(vibecast.async_handle_vibecast_payload(self.hass, payload, headers=self.headers))
        second, _ = asyncio.run(vibecast.async_handle_vibecast_payload(self.hass, payload, headers=self.headers))
        self.assertEqual(calls, ["status", "status"])
        self.assertEqual(first["revision"], second["revision"])
        self.assertEqual(first["items"], second["items"])
        self.assertTrue(second["cache"]["hit"])

    def test_structured_text_uses_allowed_segment_types_and_backend_neutral_context(self) -> None:
        self.runtime.config.update(
            {
                CONF_MUSIC_BACKEND: MUSIC_BACKEND_MUSIC_ASSISTANT,
                CONF_MUSIC_BACKEND_REVISION: 7,
            }
        )
        self._patch_status(_status_payload(provider="music_assistant"))
        result, status = asyncio.run(
            vibecast.async_handle_vibecast_payload(
                self.hass,
                {"client_type": "ios", "device_id": "djconnect-ios-ABCDEF123456", "locale": "en-US"},
                headers=self.headers,
            )
        )
        self.assertEqual(status, 200)
        self.assertEqual(result["context"]["music_backend"], "music_assistant")
        for item in result["items"]:
            for segment in item["text"]:
                self.assertIn(segment["type"], vibecast.ALLOWED_TEXT_SEGMENT_TYPES)
                self.assertNotIn("<", segment["value"])

    def test_ios_and_macos_active_track_requests_have_equivalent_contract_and_content_flow(self) -> None:
        ios = asyncio.run(_vibecast_for_client("ios"))
        macos = asyncio.run(_vibecast_for_client("macos"))

        for result in (ios, macos):
            self.assertTrue(result["enabled"])
            self.assertEqual(result["ttl_seconds"], 45)
            self.assertEqual(result["poll_after_seconds"], 20)
            self.assertEqual(result["context"]["title"], "Vibe Song")
            self.assertEqual(result["context"]["artist"], "The Contexts")
            self.assertEqual(result["context"]["music_backend"], "spotify_direct")
            self.assertEqual([item["kind"] for item in result["items"]], ["track_fact", "artist_fact", "listening_tip"])
            for item in result["items"]:
                for segment in item["text"]:
                    self.assertIn(segment["type"], vibecast.ALLOWED_TEXT_SEGMENT_TYPES)

        ios_without_revision = {key: value for key, value in ios.items() if key not in {"revision", "cache"}}
        macos_without_revision = {key: value for key, value in macos.items() if key not in {"revision", "cache"}}
        self.assertEqual(ios_without_revision, macos_without_revision)

    def test_ios_and_macos_disabled_reasons_are_equivalent(self) -> None:
        cases = [
            ("feature_disabled", {"vibecast_enabled": False}, None, None),
            ("premium_unavailable", {"vibecast_entitled": False}, None, None),
            ("no_active_playback", {}, {"success": True, "playback": {"has_playback": False}}, None),
            ("playback_inactive", {}, {"success": True, "playback": {"has_playback": True, "is_playing": False, "state": "paused", "title": "Vibe Song"}}, None),
            ("provider_unavailable", {}, None, RuntimeError("raw token provider failure")),
        ]
        for reason, config, status_payload, raises in cases:
            with self.subTest(reason=reason):
                ios = asyncio.run(
                    _vibecast_for_client(
                        "ios",
                        config=config,
                        status_payload=status_payload,
                        raises=raises,
                    )
                )
                macos = asyncio.run(
                    _vibecast_for_client(
                        "macos",
                        config=config,
                        status_payload=status_payload,
                        raises=raises,
                    )
                )
                self.assertEqual(ios["enabled"], False)
                self.assertEqual(macos["enabled"], False)
                self.assertEqual(ios["reason"], reason)
                self.assertEqual(macos["reason"], reason)
                self.assertEqual(ios["ttl_seconds"], macos["ttl_seconds"])
                self.assertEqual(ios["poll_after_seconds"], macos["poll_after_seconds"])
                self.assertEqual(ios["items"], macos["items"])
                self.assertNotIn("token", str(ios).lower())
                self.assertNotIn("token", str(macos).lower())

    def test_missing_render_capability_does_not_change_ios_macos_content_quality(self) -> None:
        ios = asyncio.run(_vibecast_for_client("ios", render_capabilities="bold,emphasis"))
        macos = asyncio.run(_vibecast_for_client("macos", render_capabilities="bold,emphasis"))

        self.assertTrue(ios["enabled"])
        self.assertTrue(macos["enabled"])
        self.assertEqual(
            {item["kind"] for item in ios["items"]},
            {item["kind"] for item in macos["items"]},
        )
        self.assertEqual(
            [[segment["value"] for segment in item["text"]] for item in ios["items"]],
            [[segment["value"] for segment in item["text"]] for item in macos["items"]],
        )


class _Runtime:
    def __init__(self, client_type: str = "ios") -> None:
        device_id = f"djconnect-{client_type}-ABCDEF123456"
        self.device_token = "token"
        self.config = {
            CONF_CLIENT_TYPE: client_type,
            CONF_DEVICE_ID: device_id,
        }
        self.device_status = {
            CONF_CLIENT_TYPE: client_type,
            CONF_DEVICE_ID: device_id,
        }

    def client_type(self) -> str:
        return self.config[CONF_CLIENT_TYPE]

    def authorize_device_request(self, headers, body_device_id=None, client_type=None) -> bool:
        auth = headers.get("Authorization", "")
        return (
            auth == "Bearer token"
            and body_device_id == self.config[CONF_DEVICE_ID]
            and client_type == self.config[CONF_CLIENT_TYPE]
        )


def _status_payload(provider: str = "spotify_direct") -> dict:
    return {
        "success": True,
        "provider": provider,
        "playback": {
            "has_playback": True,
            "is_playing": True,
            "state": "playing",
            "track_id": f"{provider}:track:123",
            "title": "Vibe Song",
            "artist": "The Contexts",
            "album": "Contract Album",
        },
    }


async def _vibecast_for_client(
    client_type: str,
    *,
    config: dict | None = None,
    status_payload: dict | None = None,
    raises: Exception | None = None,
    render_capabilities: str = "bold,emphasis,magnify,accent,emoji_safe",
) -> dict:
    runtime = _Runtime(client_type)
    runtime.config.update(config or {})
    hass = types.SimpleNamespace(
        data={"djconnect": {"runtime": runtime}},
        states=types.SimpleNamespace(get=lambda entity_id: None),
    )
    original = vibecast.run_music_command

    async def command(hass, runtime, command_name, value=None, *, play=None):
        if raises is not None:
            raise raises
        return status_payload or _status_payload()

    vibecast.run_music_command = command
    try:
        result, status = await vibecast.async_handle_vibecast_payload(
            hass,
            {
                "client_type": client_type,
                "device_id": f"djconnect-{client_type}-ABCDEF123456",
                "locale": "en-US",
            },
            headers={
                "Authorization": "Bearer token",
                "X-DJConnect-Device-ID": f"djconnect-{client_type}-ABCDEF123456",
                "X-DJConnect-Client-Type": client_type,
                "X-DJConnect-Locale": "en-US",
                "X-DJConnect-Render-Capabilities": render_capabilities,
            },
        )
    finally:
        vibecast.run_music_command = original
    assert status == 200
    return result
