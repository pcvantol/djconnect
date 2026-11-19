from __future__ import annotations

import asyncio
import json
import logging
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
            if command_name == "search_media":
                self.assertEqual(value.get("type"), "artist")
                return {
                    "success": True,
                    "provider": "spotify",
                    "source": "spotify",
                    "item": {
                        "artist": value.get("query"),
                        "image_url": "https://img.example/the-contexts-artist.jpg",
                    },
                }
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
        self.assertTrue(result["context"]["artist_image_url"].startswith("/api/djconnect/v1/image_proxy/"))
        self.assertGreaterEqual(len(result["items"]), 1)

    def test_context_includes_top_trailing_genre_badge(self) -> None:
        self._patch_status(
            _status_payload()
            | {
                "playback": {
                    **_status_payload()["playback"],
                    "genres": ["melodic-techno", "progressive house"],
                }
            }
        )
        result, status = asyncio.run(
            vibecast.async_handle_vibecast_payload(
                self.hass,
                {"client_type": "ios", "device_id": "djconnect-ios-ABCDEF123456"},
                headers=self.headers,
            )
        )

        self.assertEqual(status, 200)
        self.assertEqual(
            result["context"]["genre_badge"],
            {
                "label": "melodic techno",
                "genre": "melodic-techno",
                "placement": "top_trailing",
            },
        )

    def test_artist_fact_carries_proxied_artist_shoutout_image(self) -> None:
        self._patch_status()
        result, status = asyncio.run(
            vibecast.async_handle_vibecast_payload(
                self.hass,
                {"client_type": "ios", "device_id": "djconnect-ios-ABCDEF123456"},
                headers=self.headers,
            )
        )

        self.assertEqual(status, 200)
        artist_item = next(item for item in result["items"] if item["kind"] == "artist_fact")
        self.assertTrue(artist_item["image_url"].startswith("/api/djconnect/v1/image_proxy/"))
        self.assertEqual(artist_item["thumbnail_url"], artist_item["image_url"])
        self.assertEqual(artist_item["image_source"], "spotify")
        token = artist_item["image_url"].rsplit("/", 1)[-1]
        self.assertEqual(
            self.hass.data["djconnect"]["image_proxy"][token],
            "https://img.example/the-contexts-artist.jpg",
        )

    def test_emoji_safe_clients_get_one_to_three_emoji_prefixes_per_bubble(self) -> None:
        self._patch_status()
        result, status = asyncio.run(
            vibecast.async_handle_vibecast_payload(
                self.hass,
                {
                    "client_type": "ios",
                    "device_id": "djconnect-ios-ABCDEF123456",
                    "render_capabilities": "bold,accent,emoji_safe",
                },
                headers=self.headers,
            )
        )
        self.assertEqual(status, 200)
        for item in result["items"]:
            emoji_segments = [segment for segment in item["text"] if segment["type"] == "emoji"]
            self.assertEqual(len(emoji_segments), 1)
            emojis = emoji_segments[0]["value"].strip().split()
            self.assertGreaterEqual(len(emojis), 1)
            self.assertLessEqual(len(emojis), 3)

    def test_emoji_safe_header_keeps_comma_separated_capabilities(self) -> None:
        result = asyncio.run(_vibecast_for_client("macos"))

        self.assertTrue(
            any(segment["type"] == "emoji" for item in result["items"] for segment in item["text"])
        )

    def test_conversation_agent_can_generate_track_specific_bubbles(self) -> None:
        self._patch_status(
            _status_payload()
            | {
                "playback": {
                    **_status_payload()["playback"],
                    "title": "Omen",
                    "artist": "Margarita Sipatova",
                    "album": "Omen",
                    "genres": ["melodic techno"],
                }
            }
        )
        original = vibecast.call_conversation_process_with_agent_retry
        payload = {
            "items": [
                {"kind": "trivia", "text": "Feitje: Omen gebruikt spanning als hoofdinstrument."},
                {"kind": "listening_tip", "text": "Luistertip: volg de baspuls onder de melodie."},
                {"kind": "artist_fact", "text": "Sfeer: Margarita Sipatova houdt het filmisch en strak."},
            ]
        }

        async def conversation(hass, data, debug=None):
            return {
                "response": {
                    "speech": {"plain": {"speech": json.dumps(payload)}},
                }
            }

        vibecast.call_conversation_process_with_agent_retry = conversation
        try:
            result, status = asyncio.run(
                vibecast.async_handle_vibecast_payload(
                    self.hass,
                    {
                        "client_type": "ios",
                        "device_id": "djconnect-ios-ABCDEF123456",
                        "render_capabilities": "bold,accent,emoji_safe",
                    },
                    headers=self.headers,
                )
            )
        finally:
            vibecast.call_conversation_process_with_agent_retry = original

        self.assertEqual(status, 200)
        rendered = " ".join(segment["value"] for item in result["items"] for segment in item["text"])
        self.assertIn("Omen gebruikt spanning", rendered)
        self.assertIn("baspuls onder de melodie", rendered)
        self.assertIn("Margarita Sipatova", rendered)
        self.assertTrue(all(item["source"]["kind"] == "conversation" for item in result["items"]))

    def test_local_fallback_varies_bubbles_by_track_metadata(self) -> None:
        first = vibecast._fallback_items(
            {
                "track_id": "spotify:track:omen",
                "title": "Omen",
                "artist": "Margarita Sipatova",
                "album": "Omen",
                "genres": ["melodic techno"],
            },
            "nl-nl",
            {"render_capabilities": "emoji_safe"},
        )
        second = vibecast._fallback_items(
            {
                "track_id": "spotify:track:strobe",
                "title": "Strobe - Radio Edit",
                "artist": "deadmau5",
                "album": "Strobe",
                "genres": ["progressive house", "edm"],
            },
            "nl-nl",
            {"render_capabilities": "emoji_safe"},
        )

        first_text = [" ".join(segment["value"] for segment in item["text"]) for item in first]
        second_text = [" ".join(segment["value"] for segment in item["text"]) for item in second]
        self.assertNotEqual(first_text, second_text)
        self.assertFalse(all("ritme en ruimte" in text for text in first_text + second_text))

    def test_clients_without_emoji_safe_do_not_get_emoji_segments(self) -> None:
        self._patch_status()
        result, status = asyncio.run(
            vibecast.async_handle_vibecast_payload(
                self.hass,
                {
                    "client_type": "ios",
                    "device_id": "djconnect-ios-ABCDEF123456",
                    "render_capabilities": "bold,accent",
                },
                headers=self.headers,
            )
        )
        self.assertEqual(status, 200)
        self.assertTrue(result["items"])
        self.assertFalse(
            any(segment["type"] == "emoji" for item in result["items"] for segment in item["text"])
        )

    def test_vibecast_cache_separates_emoji_safe_render_profiles(self) -> None:
        calls = []
        self._original_run_music_command = vibecast.run_music_command

        async def command(hass, runtime, command_name, value=None, *, play=None):
            calls.append(command_name)
            return _status_payload()

        vibecast.run_music_command = command
        payload = {"client_type": "ios", "device_id": "djconnect-ios-ABCDEF123456"}
        no_emoji, _ = asyncio.run(
            vibecast.async_handle_vibecast_payload(
                self.hass,
                {**payload, "render_capabilities": "bold,accent"},
                headers=self.headers,
            )
        )
        with_emoji, _ = asyncio.run(
            vibecast.async_handle_vibecast_payload(
                self.hass,
                {**payload, "render_capabilities": "bold,accent,emoji_safe"},
                headers=self.headers,
            )
        )
        self.assertEqual(calls, ["status", "search_media", "status", "search_media"])
        self.assertFalse(any(segment["type"] == "emoji" for item in no_emoji["items"] for segment in item["text"]))
        self.assertTrue(any(segment["type"] == "emoji" for item in with_emoji["items"] for segment in item["text"]))

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

    def test_provider_failure_debug_log_omits_raw_error_text(self) -> None:
        self._patch_status(raises=RuntimeError("token secret provider exploded"))
        previous = vibecast._LOGGER.level
        vibecast._LOGGER.setLevel(logging.DEBUG)
        try:
            with self.assertLogs(vibecast._LOGGER, level="DEBUG") as captured:
                result, status = asyncio.run(
                    vibecast.async_handle_vibecast_payload(
                        self.hass,
                        {"client_type": "ios", "device_id": "djconnect-ios-ABCDEF123456"},
                        headers=self.headers,
                    )
                )
        finally:
            vibecast._LOGGER.setLevel(previous)
        self.assertEqual(status, 200)
        self.assertEqual(result["reason"], "provider_unavailable")
        logs = "\n".join(captured.output).lower()
        self.assertIn("status lookup failed", logs)
        self.assertIn("runtimeerror", logs)
        self.assertNotIn("secret", logs)
        self.assertNotIn("bearer token", logs)

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
        self.assertEqual(calls, ["status", "search_media", "status"])
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

        ios_without_revision = _normalize_proxy_urls({key: value for key, value in ios.items() if key not in {"revision", "cache"}})
        macos_without_revision = _normalize_proxy_urls({key: value for key, value in macos.items() if key not in {"revision", "cache"}})
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
            "genres": ["indie pop"],
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
        if command_name == "search_media":
            return {
                "success": True,
                "provider": "spotify",
                "source": "spotify",
                "item": {
                    "artist": value.get("query") if isinstance(value, dict) else "",
                    "image_url": "https://img.example/the-contexts-artist.jpg",
                },
            }
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


def _normalize_proxy_urls(value):
    if isinstance(value, dict):
        return {key: _normalize_proxy_urls(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_normalize_proxy_urls(item) for item in value]
    if isinstance(value, str) and value.startswith("/api/djconnect/v1/image_proxy/"):
        return "/api/djconnect/v1/image_proxy/<token>"
    return value
