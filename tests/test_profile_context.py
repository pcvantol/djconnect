"""Tests for DJConnect runtime Profile context resolution."""

from __future__ import annotations

import asyncio
from pathlib import Path
import sys
import types
import unittest

package = types.ModuleType("custom_components.djconnect")
package.__path__ = [
    str(Path(__file__).resolve().parents[1] / "custom_components" / "djconnect")
]
sys.modules.setdefault("custom_components.djconnect", package)

from custom_components.djconnect.const import CONF_DEVICE_ID, DOMAIN  # noqa: E402
from custom_components.djconnect.domain import BackendProvider  # noqa: E402
from custom_components.djconnect.domain import ProfileResolutionReason  # noqa: E402
from custom_components.djconnect.domain.storage import (  # noqa: E402
    ProfilePlatformStorage,
    STORE_KEY,
)
from custom_components.djconnect.profile_context import (  # noqa: E402
    ProfilePlatformNotConfigured,
    async_apply_profile_context,
    profile_error_payload,
    profile_resolution_context_from_payload,
)


class MemoryStore:
    """Small async storage fake."""

    def __init__(self, data=None):
        self.data = data

    async def async_load(self):
        return self.data

    async def async_save(self, data):
        self.data = data


def _runtime(device_id="djconnect-ios-ABCDEFGHIJKL"):
    return types.SimpleNamespace(
        pairing_device_id=device_id,
        device_status={CONF_DEVICE_ID: device_id},
        config={},
    )


class ProfileContextTest(unittest.TestCase):
    """Validate canonical runtime Profile context."""

    def setUp(self) -> None:
        self.hass = types.SimpleNamespace(data={DOMAIN: {}})
        self.manager = ProfilePlatformStorage(store=MemoryStore())
        self.hass.data[DOMAIN][STORE_KEY] = self.manager

    def test_explicit_profile_id_wins(self) -> None:
        first = asyncio.run(self.manager.async_create_profile("First"))
        second = asyncio.run(self.manager.async_create_profile("Second"))
        asyncio.run(
            self.manager.async_upsert_device(
                "djconnect-ios-ABCDEFGHIJKL",
                "ios",
                linked_profile_id=first.profile_id,
            )
        )

        payload = {"profile_id": second.profile_id, CONF_DEVICE_ID: "djconnect-ios-ABCDEFGHIJKL"}
        context = asyncio.run(
            async_apply_profile_context(self.hass, _runtime(), payload, request_source="test")
        )

        self.assertEqual(context.profile_id, second.profile_id)
        self.assertEqual(context.resolution_reason, ProfileResolutionReason.EXPLICIT_PROFILE)
        self.assertFalse(context.fallback_used)
        self.assertEqual(payload["music_dna_key"], f"profile:{second.profile_id}")
        self.assertNotIn("profile_resolution_reason", payload)

    def test_device_mapping_resolves_profile(self) -> None:
        profile = asyncio.run(self.manager.async_create_profile("Device Profile"))
        asyncio.run(
            self.manager.async_upsert_device(
                "djconnect-ios-ABCDEFGHIJKL",
                "ios",
                linked_profile_id=profile.profile_id,
            )
        )

        payload = {CONF_DEVICE_ID: "djconnect-ios-ABCDEFGHIJKL"}
        context = asyncio.run(
            async_apply_profile_context(self.hass, _runtime(), payload, request_source="test")
        )

        self.assertEqual(context.profile_id, profile.profile_id)
        self.assertEqual(context.resolution_reason, ProfileResolutionReason.DEVICE_MAPPING)
        self.assertEqual(payload["profile_id"], profile.profile_id)

    def test_fallback_profile_resolves_when_allowed(self) -> None:
        profile = asyncio.run(self.manager.async_create_profile("Fallback"))

        context = asyncio.run(
            async_apply_profile_context(
                self.hass,
                _runtime("djconnect-unknown"),
                {},
                request_source="test",
            )
        )

        self.assertEqual(context.profile_id, profile.profile_id)
        self.assertEqual(context.resolution_reason, ProfileResolutionReason.FALLBACK)
        self.assertTrue(context.fallback_used)

    def test_profile_required_error_is_structured(self) -> None:
        asyncio.run(self.manager.async_create_profile("Strict"))

        with self.assertRaises(Exception) as raised:
            asyncio.run(
                async_apply_profile_context(
                    self.hass,
                    _runtime("djconnect-unknown"),
                    {"profile_id": "missing"},
                    request_source="test",
                )
            )
        payload, status = profile_error_payload(raised.exception)

        self.assertEqual(status, 404)
        self.assertEqual(payload["error"], "invalid_profile")

    def test_backend_account_routing_from_profile(self) -> None:
        profile = asyncio.run(self.manager.async_create_profile("Peter"))
        asyncio.run(
            self.manager.async_upsert_music_backend(
                "spotify_direct",
                BackendProvider.SPOTIFY_DIRECT,
                display_name="Spotify Direct",
            )
        )
        asyncio.run(
            self.manager.async_update_profile(
                profile.profile_id,
                preferences=profile.preferences.__class__(
                    default_backend_id="spotify_direct",
                    response_style=profile.preferences.response_style,
                    voice_style=profile.preferences.voice_style,
                ),
            )
        )
        runtime = _runtime()

        context = asyncio.run(
            async_apply_profile_context(
                self.hass,
                runtime,
                {"profile_id": profile.profile_id},
                request_source="test",
            )
        )

        self.assertEqual(context.backend_id, "spotify_direct")
        self.assertEqual(runtime.profile_context_backend_id, "spotify_direct")

    def test_payload_constructs_full_profile_resolution_context(self) -> None:
        """Runtime payloads translate to one typed resolver context."""
        context = profile_resolution_context_from_payload(
            _runtime("djconnect-runtime"),
            {
                "profile_id": " profile-explicit ",
                "device_id": " djconnect-payload ",
                "client_type": " ios ",
                "ha_user_id": " ha-user ",
                "satellite_id": " satellite ",
                "ha_device_id": " ha-device ",
                "area_id": " kitchen ",
                "room_id": " room ",
                "target_player_id": " player ",
                "playback_zone_id": " zone ",
                "session_id": " session ",
                "speaker_identity_hint": " future ",
            },
            user_id=None,
            request_source=" ask_dj ",
        )

        self.assertEqual(context.explicit_profile_id, "profile-explicit")
        self.assertEqual(context.device_id, "djconnect-payload")
        self.assertEqual(context.client_type, "ios")
        self.assertEqual(context.ha_user_id, "ha-user")
        self.assertEqual(context.satellite_id, "satellite")
        self.assertEqual(context.ha_device_id, "ha-device")
        self.assertEqual(context.area_id, "kitchen")
        self.assertEqual(context.room_id, "room")
        self.assertEqual(context.player_id, "player")
        self.assertEqual(context.playback_zone_id, "zone")
        self.assertEqual(context.session_id, "session")
        self.assertEqual(context.request_source, "ask_dj")
        self.assertEqual(context.speaker_identity_hint, "future")

    def test_no_profile_platform_state_is_legacy_noop_signal(self) -> None:
        empty = ProfilePlatformStorage(store=MemoryStore())
        self.hass.data[DOMAIN][STORE_KEY] = empty

        with self.assertRaises(ProfilePlatformNotConfigured):
            asyncio.run(
                async_apply_profile_context(
                    self.hass,
                    _runtime(),
                    {CONF_DEVICE_ID: "djconnect-ios-ABCDEFGHIJKL"},
                    request_source="test",
                )
            )


if __name__ == "__main__":
    unittest.main()
