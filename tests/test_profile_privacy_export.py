"""Tests for DJConnect Profile privacy, export/import and reset flows."""

from __future__ import annotations

import asyncio
from dataclasses import replace
from pathlib import Path
import sys
import types
import unittest

package = types.ModuleType("custom_components.djconnect")
package.__path__ = [
    str(Path(__file__).resolve().parents[1] / "custom_components" / "djconnect")
]
sys.modules.setdefault("custom_components.djconnect", package)

from custom_components.djconnect.domain import (  # noqa: E402
    BackendProvider,
    ConversationReference,
    MoodState,
    MusicDNAReference,
    ProfilePrivacyMode,
    ProfileType,
    RecommendationReference,
)
from custom_components.djconnect.domain.storage import ProfilePlatformStorage  # noqa: E402
from custom_components.djconnect.profile_export import (  # noqa: E402
    UnsafeImportError,
    async_clear_profile_personal_state,
    async_export_household,
    async_export_integration,
    async_export_profile,
    async_import_profile,
)
from custom_components.djconnect.profile_privacy import resolve_profile_privacy_policy  # noqa: E402


class MemoryStore:
    """Small async storage fake."""

    def __init__(self, data=None):
        self.data = data

    async def async_load(self):
        return self.data

    async def async_save(self, data):
        self.data = data


class ProfilePrivacyExportTest(unittest.TestCase):
    """Validate Phase 4 privacy and export/import behavior."""

    def setUp(self) -> None:
        self.manager = ProfilePlatformStorage(store=MemoryStore())

    def test_private_session_blocks_personal_persistence(self) -> None:
        profile = asyncio.run(self.manager.async_create_profile("Private Test"))
        policy = resolve_profile_privacy_policy(profile, {"private_session": True})

        self.assertTrue(policy.private_session)
        self.assertFalse(policy.allow_history_persistence)
        self.assertFalse(policy.allow_music_dna_persistence)
        self.assertFalse(policy.allow_recommendation_persistence)
        self.assertFalse(policy.allow_mood_persistence)

    def test_guest_profile_redacts_export_personal_state(self) -> None:
        profile = asyncio.run(
            self.manager.async_create_profile(
                "Guest",
                profile_type=ProfileType.GUEST,
                privacy_mode=ProfilePrivacyMode.GUEST_SAFE,
            )
        )
        asyncio.run(self._set_personal_state(profile.profile_id))

        export = asyncio.run(async_export_profile(self.manager, profile.profile_id))

        self.assertEqual(export["profile"]["profile_id"], profile.profile_id)
        self.assertFalse(export["privacy"]["personal_data_included"])
        self.assertEqual(export["profile"]["references"], {})
        self.assertEqual(export["profile"]["likes"], [])

    def test_household_and_integration_exports_exclude_secrets(self) -> None:
        asyncio.run(self.manager.async_create_profile("Owner"))
        asyncio.run(
            self.manager.async_upsert_music_backend(
                "spotify",
                provider=BackendProvider.SPOTIFY_DIRECT,
                display_name="Spotify",
                configuration={"market": "NL", "refresh_token": "VERY_PRIVATE_TOKEN"},
            )
        )

        household = asyncio.run(async_export_household(self.manager))
        integration = asyncio.run(
            async_export_integration(
                self.manager,
            non_secret_config={"device_token": "VERY_PRIVATE_DEVICE_TOKEN", "safe": "ok"},
            )
        )

        self.assertNotIn("refresh_token", str(household))
        self.assertNotIn("VERY_PRIVATE", str(household))
        self.assertNotIn("VERY_PRIVATE", str(integration))
        self.assertIn("safe", integration["non_secret_config"])
        self.assertTrue(integration["excluded"]["oauth_tokens"])
        self.assertTrue(integration["excluded"]["device_tokens"])

    def test_profile_import_reassigns_collision(self) -> None:
        profile = asyncio.run(self.manager.async_create_profile("Imported"))
        export = asyncio.run(async_export_profile(self.manager, profile.profile_id))

        result = asyncio.run(
            async_import_profile(self.manager, export, reassign_id=True)
        )

        self.assertTrue(result["reassigned"])
        self.assertNotEqual(result["profile_id"], profile.profile_id)

    def test_import_rejects_secret_fields(self) -> None:
        profile = asyncio.run(self.manager.async_create_profile("Unsafe"))
        export = asyncio.run(async_export_profile(self.manager, profile.profile_id))
        export["profile"]["refresh_token"] = "nope"

        with self.assertRaises(UnsafeImportError):
            asyncio.run(async_import_profile(self.manager, export, reassign_id=True))

    def test_clear_all_personal_state_does_not_delete_profile(self) -> None:
        profile = asyncio.run(self.manager.async_create_profile("Clearable"))
        asyncio.run(self._set_personal_state(profile.profile_id))

        cleared = asyncio.run(
            async_clear_profile_personal_state(
                self.manager,
                profile.profile_id,
                all_state=True,
            )
        )

        self.assertEqual(cleared.profile_id, profile.profile_id)
        self.assertEqual(cleared.music_dna, MusicDNAReference())
        self.assertEqual(cleared.conversation, ConversationReference())
        self.assertEqual(cleared.recommendations, RecommendationReference())
        self.assertEqual(cleared.mood, MoodState())
        self.assertEqual(cleared.likes, frozenset())

    async def _set_personal_state(self, profile_id: str) -> None:
        household = await self.manager.async_load()
        profile = household.profiles[profile_id]
        profile = replace(
            profile,
            music_dna=MusicDNAReference(key=f"profile:{profile_id}", enabled=True, revision=3),
            conversation=ConversationReference(key=f"profile:{profile_id}", revision=4),
            recommendations=RecommendationReference(key=f"profile:{profile_id}", revision=5),
            mood=MoodState(value=80, zone="energy", updated_at="now"),
            likes=frozenset({"spotify:track:1"}),
            dislikes=frozenset({"spotify:track:2"}),
        )
        await self.manager.async_save(
            replace(household, profiles={**household.profiles, profile.profile_id: profile})
        )


if __name__ == "__main__":
    unittest.main()
