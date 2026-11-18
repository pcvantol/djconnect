"""Tests for DJConnect Profile Platform persistence."""

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

from custom_components.djconnect.domain import (  # noqa: E402
    BackendProvider,
    ProfileResolutionContext,
    ProfileType,
)
from custom_components.djconnect.domain.music_account import MusicAccountKind  # noqa: E402
from custom_components.djconnect.domain.storage import (  # noqa: E402
    ProfilePlatformStorage,
    ProfileStorageValidationError,
    household_from_storage,
    household_to_storage,
)


class MemoryStore:
    """Small async storage fake."""

    def __init__(self, data=None):
        self.data = data
        self.saved = None

    async def async_load(self):
        return self.data

    async def async_save(self, data):
        self.saved = data
        self.data = data


class ProfilePlatformStorageTest(unittest.TestCase):
    """Validate Profile Platform persistence behavior."""

    def test_load_empty_state_creates_default_household(self) -> None:
        """Empty storage returns a valid default Household."""
        manager = ProfilePlatformStorage(store=MemoryStore())

        household = asyncio.run(manager.async_load())

        self.assertEqual(household.household_id, "household-local")
        self.assertEqual(household.profiles, {})
        self.assertEqual(household.devices, {})

    def test_save_load_roundtrip(self) -> None:
        """Household state survives explicit storage serialization."""
        store = MemoryStore()
        manager = ProfilePlatformStorage(store=store)

        profile = asyncio.run(manager.async_create_profile("Peter"))
        asyncio.run(
            manager.async_upsert_music_backend(
                "spotify_direct",
                BackendProvider.SPOTIFY_DIRECT,
                display_name="Spotify Direct",
                configuration={"client_id": "abc", "refresh_token": "secret"},
            )
        )
        asyncio.run(
            manager.async_upsert_music_account(
                "spotify-account",
                "spotify_direct",
                kind=MusicAccountKind.PERSONAL,
                display_name="Peter Spotify",
                linked_profile_ids=frozenset({profile.profile_id}),
            )
        )
        asyncio.run(
            manager.async_upsert_device(
                "djconnect-ios-ABCDEFGHIJKL",
                "ios",
                display_name="Peter iPhone",
                linked_profile_id=profile.profile_id,
            )
        )

        reloaded = asyncio.run(ProfilePlatformStorage(store=MemoryStore(store.saved)).async_load())

        self.assertIn(profile.profile_id, reloaded.profiles)
        self.assertIn("djconnect-ios-ABCDEFGHIJKL", reloaded.devices)
        self.assertIn("spotify-account", reloaded.music_accounts)
        backend_config = reloaded.music_backends["spotify_direct"].configuration
        self.assertEqual(backend_config["client_id"], "abc")
        self.assertNotIn("refresh_token", backend_config)

    def test_profile_crud_and_fallback_validation(self) -> None:
        """Profiles can be created, updated and protected as fallback."""
        manager = ProfilePlatformStorage(store=MemoryStore())
        profile = asyncio.run(manager.async_create_profile("Household", profile_type=ProfileType.HOUSEHOLD))

        updated = asyncio.run(manager.async_update_profile(profile.profile_id, display_name="Home"))

        self.assertEqual(updated.display_name, "Home")
        with self.assertRaises(ProfileStorageValidationError):
            asyncio.run(manager.async_delete_profile(profile.profile_id))

    def test_device_mapping_crud_and_resolver(self) -> None:
        """Persisted mappings feed the Phase 1 resolver."""
        manager = ProfilePlatformStorage(store=MemoryStore())
        profile = asyncio.run(manager.async_create_profile("Peter"))
        asyncio.run(
            manager.async_upsert_device(
                "djconnect-windows-ABCDEFGHIJKL",
                "windows",
                linked_profile_id=profile.profile_id,
            )
        )

        resolved = manager.resolver().resolve(
            ProfileResolutionContext(device_id="djconnect-windows-ABCDEFGHIJKL")
        )
        unlinked = asyncio.run(manager.async_unlink_device("djconnect-windows-ABCDEFGHIJKL"))

        self.assertEqual(resolved.profile_id, profile.profile_id)
        self.assertEqual(unlinked.linked_profile_id, "")

    def test_invalid_references_are_rejected(self) -> None:
        """Storage validation rejects missing profile references."""
        raw = household_to_storage(asyncio.run(ProfilePlatformStorage(store=MemoryStore()).async_load()))
        raw["household"]["devices"].append(
            {
                "device_id": "djconnect-ios-ABCDEFGHIJKL",
                "client_type": "ios",
                "linked_profile_id": "missing",
            }
        )

        with self.assertRaises(ProfileStorageValidationError):
            asyncio.run(ProfilePlatformStorage(store=MemoryStore(raw)).async_load())

    def test_household_from_storage_accepts_explicit_schema(self) -> None:
        """Deserializer uses explicit schema/version, not scattered implicit shapes."""
        household = household_from_storage({"version": 1, "household": {"profiles": []}})

        self.assertEqual(household.household_id, "household-local")


if __name__ == "__main__":
    unittest.main()
