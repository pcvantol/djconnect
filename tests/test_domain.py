"""Tests for DJConnect core domain models."""

from __future__ import annotations

import unittest
from dataclasses import fields
from pathlib import Path
import sys
import types

package = types.ModuleType("custom_components.djconnect")
package.__path__ = [
    str(Path(__file__).resolve().parents[1] / "custom_components" / "djconnect")
]
sys.modules.setdefault("custom_components.djconnect", package)

from custom_components.djconnect.domain import (  # noqa: E402
    BackendProvider,
    Device,
    DeviceCapabilities,
    DeviceNotMapped,
    DevicePairingState,
    FallbackConfiguration,
    Household,
    MusicAccount,
    MusicAccountKind,
    MusicBackendCapabilities,
    MusicBackendRegistration,
    PlaybackZone,
    PlaybackZoneKind,
    Profile,
    ProfileCapabilities,
    ProfileNotFound,
    ProfilePreferences,
    ProfilePrivacyMode,
    ProfileRequired,
    ProfileResolutionContext,
    ProfileResolutionReason,
    ProfileResolver,
    ProfileState,
    ProfileType,
    SharedConfiguration,
)


class ProfileDomainModelTest(unittest.TestCase):
    """Validate Profile-owned personal state."""

    def test_profile_owns_personal_references_and_preferences(self) -> None:
        """Profile contains personal references, mood and preference fields."""
        profile = Profile(
            profile_id="profile-personal",
            display_name="Peter",
            profile_type=ProfileType.PERSONAL,
            privacy_mode=ProfilePrivacyMode.NORMAL,
            preferences=ProfilePreferences(
                default_backend_id="spotify-direct",
                default_music_account_id="spotify-peter",
                fallback_playback_zone_id="living-room",
            ),
            capabilities=ProfileCapabilities(profile_export=True),
            likes=frozenset({"spotify:track:1"}),
        )

        self.assertEqual(profile.profile_id, "profile-personal")
        self.assertEqual(profile.state, ProfileState.ACTIVE)
        self.assertEqual(profile.preferences.default_backend_id, "spotify-direct")
        self.assertEqual(profile.preferences.default_music_account_id, "spotify-peter")
        self.assertEqual(profile.preferences.fallback_playback_zone_id, "living-room")
        self.assertTrue(profile.capabilities.profile_export)
        self.assertIn("spotify:track:1", profile.likes)

    def test_profile_requires_identity(self) -> None:
        """Profile identity is mandatory."""
        with self.assertRaises(ValueError):
            Profile(profile_id="", display_name="Nope")


class DeviceDomainModelTest(unittest.TestCase):
    """Validate Device-owned runtime state only."""

    def test_device_owns_runtime_context(self) -> None:
        """Device tracks runtime state and links to a profile."""
        device = Device(
            device_id="djconnect-ios-ABCDEFGHIJKL",
            client_type="ios",
            display_name="Peter iPhone",
            linked_profile_id="profile-personal",
            room_id="living-room",
            capabilities=DeviceCapabilities(display=True, notifications=True, ask_dj=True),
            pairing_state=DevicePairingState.PAIRED,
        )

        self.assertEqual(device.device_id, "djconnect-ios-ABCDEFGHIJKL")
        self.assertEqual(device.client_type, "ios")
        self.assertEqual(device.linked_profile_id, "profile-personal")
        self.assertTrue(device.capabilities.ask_dj)

    def test_device_model_does_not_contain_personal_state(self) -> None:
        """Device fields must not become a personal identity store."""
        device_field_names = {field.name for field in fields(Device)}
        forbidden = {
            "music_dna",
            "music_dna_key",
            "conversation",
            "ask_dj_history",
            "recommendations",
            "mood",
            "voice_style",
            "response_style",
            "likes",
            "dislikes",
        }

        self.assertFalse(device_field_names & forbidden)

    def test_device_requires_identity(self) -> None:
        """Device identity is mandatory."""
        with self.assertRaises(ValueError):
            Device(device_id="", client_type="ios")


class BackendAndPlaybackDomainModelTest(unittest.TestCase):
    """Validate backend/account/zone abstractions."""

    def test_backend_represents_provider_adapter(self) -> None:
        """Backend carries provider capabilities, not user identity."""
        backend = MusicBackendRegistration(
            backend_id="spotify-direct",
            provider=BackendProvider.SPOTIFY_DIRECT,
            display_name="Spotify Direct",
            capabilities=MusicBackendCapabilities(search=True, playlists=True, outputs=True),
        )

        self.assertEqual(backend.backend_id, "spotify-direct")
        self.assertEqual(backend.provider, BackendProvider.SPOTIFY_DIRECT)
        self.assertTrue(backend.capabilities.search)
        self.assertNotIn("profile_id", backend.configuration)

    def test_music_account_binds_provider_account_without_oauth(self) -> None:
        """Music account references backend/profile bindings without tokens."""
        account = MusicAccount(
            account_id="spotify-household",
            backend_id="spotify-direct",
            kind=MusicAccountKind.HOUSEHOLD,
            display_name="Household Spotify",
            linked_profile_ids=frozenset({"profile-household", "profile-personal"}),
            provider_account_id="spotify-user-123",
        )

        self.assertEqual(account.kind, MusicAccountKind.HOUSEHOLD)
        self.assertIn("profile-personal", account.linked_profile_ids)
        self.assertNotIn("token", account.metadata)

    def test_playback_zone_represents_target_only(self) -> None:
        """Playback Zone describes a target without playback implementation."""
        zone = PlaybackZone(
            zone_id="living-room",
            display_name="Living Room",
            kind=PlaybackZoneKind.MUSIC_ASSISTANT_PLAYER,
            backend_id="music-assistant",
            provider_target_id="media_player.living_room",
        )

        self.assertEqual(zone.zone_id, "living-room")
        self.assertEqual(zone.backend_id, "music-assistant")
        self.assertEqual(zone.provider_target_id, "media_player.living_room")


class HouseholdDomainModelTest(unittest.TestCase):
    """Validate Household-owned registrations and defaults."""

    def test_household_owns_profiles_devices_backends_accounts_and_defaults(self) -> None:
        """Household is the local platform boundary."""
        personal = Profile(profile_id="profile-personal", display_name="Peter")
        device = Device(
            device_id="djconnect-ios-ABCDEFGHIJKL",
            client_type="ios",
            linked_profile_id=personal.profile_id,
        )
        backend = MusicBackendRegistration(
            backend_id="spotify-direct",
            provider=BackendProvider.SPOTIFY_DIRECT,
            display_name="Spotify Direct",
        )
        account = MusicAccount(
            account_id="spotify-personal",
            backend_id=backend.backend_id,
            kind=MusicAccountKind.PERSONAL,
            display_name="Peter Spotify",
            linked_profile_ids=frozenset({personal.profile_id}),
        )

        household = Household(
            household_id="home",
            display_name="Home",
            profiles={personal.profile_id: personal},
            devices={device.device_id: device},
            music_backends={backend.backend_id: backend},
            music_accounts={account.account_id: account},
            fallback=FallbackConfiguration(fallback_profile_id=personal.profile_id),
        )

        self.assertEqual(household.profiles[personal.profile_id], personal)
        self.assertEqual(household.devices[device.device_id], device)
        self.assertEqual(household.music_backends[backend.backend_id], backend)
        self.assertEqual(household.music_accounts[account.account_id], account)
        self.assertEqual(household.fallback.fallback_profile_id, personal.profile_id)


class ProfileResolverTest(unittest.TestCase):
    """Validate canonical Profile resolution."""

    def setUp(self) -> None:
        """Create a household with every resolution input mapped."""
        self.explicit = Profile(profile_id="profile-explicit", display_name="Explicit")
        self.device_profile = Profile(profile_id="profile-device", display_name="Device")
        self.ha_profile = Profile(profile_id="profile-ha", display_name="HA User")
        self.room_profile = Profile(
            profile_id="profile-room",
            display_name="Living Room",
            profile_type=ProfileType.ROOM,
            privacy_mode=ProfilePrivacyMode.SHARED,
        )
        self.fallback = Profile(
            profile_id="profile-fallback",
            display_name="Household",
            profile_type=ProfileType.HOUSEHOLD,
            privacy_mode=ProfilePrivacyMode.SHARED,
        )
        self.device = Device(
            device_id="djconnect-ios-ABCDEFGHIJKL",
            client_type="ios",
            linked_profile_id=self.device_profile.profile_id,
            room_id="living-room",
        )
        self.household = Household(
            household_id="home",
            display_name="Home",
            profiles={
                profile.profile_id: profile
                for profile in (
                    self.explicit,
                    self.device_profile,
                    self.ha_profile,
                    self.room_profile,
                    self.fallback,
                )
            },
            devices={self.device.device_id: self.device},
            shared=SharedConfiguration(
                room_profile_ids={"living-room": self.room_profile.profile_id},
                ha_user_profile_ids={"ha-user-1": self.ha_profile.profile_id},
            ),
            fallback=FallbackConfiguration(fallback_profile_id=self.fallback.profile_id),
        )
        self.resolver = ProfileResolver.for_household(self.household)

    def test_resolver_prefers_explicit_profile_id(self) -> None:
        """Explicit profile wins over every other hint."""
        profile = self.resolver.resolve(
            ProfileResolutionContext(
                explicit_profile_id=self.explicit.profile_id,
                device_id=self.device.device_id,
                ha_user_id="ha-user-1",
                room_id="living-room",
            )
        )

        self.assertEqual(profile.profile_id, self.explicit.profile_id)

    def test_resolver_uses_device_mapping_before_ha_user_hint(self) -> None:
        """Device mapping has priority over HA user hint."""
        profile = self.resolver.resolve(
            ProfileResolutionContext(
                device_id=self.device.device_id,
                ha_user_id="ha-user-1",
                room_id="living-room",
            )
        )

        self.assertEqual(profile.profile_id, self.device_profile.profile_id)

    def test_resolver_uses_ha_user_hint_before_room_mapping(self) -> None:
        """HA user hint has priority over room mapping."""
        profile = self.resolver.resolve(
            ProfileResolutionContext(ha_user_id="ha-user-1", room_id="living-room")
        )

        self.assertEqual(profile.profile_id, self.ha_profile.profile_id)

    def test_resolver_uses_room_mapping_before_fallback(self) -> None:
        """Room mapping has priority over fallback profile."""
        profile = self.resolver.resolve(ProfileResolutionContext(room_id="living-room"))

        self.assertEqual(profile.profile_id, self.room_profile.profile_id)

    def test_resolver_uses_area_mapping_as_room_context(self) -> None:
        """Area context maps through the current room mapping index."""
        profile = self.resolver.resolve(ProfileResolutionContext(area_id="living-room"))

        self.assertEqual(profile.profile_id, self.room_profile.profile_id)

    def test_resolver_uses_fallback_profile(self) -> None:
        """Fallback profile is used when no stronger hint resolves."""
        profile = self.resolver.resolve(ProfileResolutionContext())

        self.assertEqual(profile.profile_id, self.fallback.profile_id)

    def test_resolver_raises_profile_not_found_for_bad_explicit_profile(self) -> None:
        """Bad explicit profile id raises canonical error."""
        with self.assertRaises(ProfileNotFound):
            self.resolver.resolve(ProfileResolutionContext(explicit_profile_id="missing"))

    def test_resolver_raises_device_not_mapped_for_known_unmapped_device(self) -> None:
        """Known device without profile mapping raises canonical error."""
        unmapped = Device(device_id="djconnect-pi-ABCDEFGHIJKL", client_type="raspberry_pi")
        household = Household(
            household_id="home",
            display_name="Home",
            profiles={self.fallback.profile_id: self.fallback},
            devices={unmapped.device_id: unmapped},
            fallback=FallbackConfiguration(fallback_profile_id=self.fallback.profile_id),
        )
        resolver = ProfileResolver.for_household(household)

        with self.assertRaises(DeviceNotMapped):
            resolver.resolve(ProfileResolutionContext(device_id=unmapped.device_id))

    def test_resolver_raises_profile_required_without_fallback(self) -> None:
        """No matching hints and no fallback raises canonical error."""
        resolver = ProfileResolver(profiles={})

        with self.assertRaises(ProfileRequired):
            resolver.resolve(ProfileResolutionContext())

    def test_resolution_context_normalizes_and_is_immutable(self) -> None:
        """Resolution context keeps safe defaults and normalized identifiers."""
        context = ProfileResolutionContext(
            explicit_profile_id=" profile ",
            device_id=" device ",
            client_type=" ios ",
            ha_user_id=" ha-user ",
            satellite_id=" satellite ",
            ha_device_id=" ha-device ",
            area_id=" kitchen ",
            room_id=" room ",
            player_id=" player ",
            playback_zone_id=" zone ",
            session_id=" session ",
            request_source=" ask_dj ",
            speaker_identity_hint=" future-hint ",
        )

        self.assertEqual(context.explicit_profile_id, "profile")
        self.assertEqual(context.device_id, "device")
        self.assertEqual(context.client_type, "ios")
        self.assertEqual(context.area_id, "kitchen")
        self.assertEqual(context.speaker_identity_hint, "future-hint")
        with self.assertRaises(Exception):
            context.device_id = "changed"  # type: ignore[misc]

    def test_resolution_result_reason_is_reported(self) -> None:
        """Resolver can report a safe reason without changing resolve()."""
        result = self.resolver.resolve_with_result(
            ProfileResolutionContext(device_id=self.device.device_id)
        )

        self.assertEqual(result.profile.profile_id, self.device_profile.profile_id)
        self.assertEqual(result.reason, ProfileResolutionReason.DEVICE_MAPPING)
        self.assertEqual(result.signal, self.device.device_id)
        self.assertFalse(result.fallback_used)


if __name__ == "__main__":
    unittest.main()
