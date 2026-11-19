"""DJConnect core domain model.

This package is intentionally runtime-neutral. It defines the Profile-centered
identity model that services, APIs and storage can depend on in later phases.
"""

from .backend import (
    BackendProvider,
    MusicBackendCapabilities,
    MusicBackendRegistration,
    MusicBackendState,
)
from ..dj_brain_capabilities import CapabilityPolicy, CapabilityPolicyMode
from .device import Device, DeviceCapabilities, DevicePairingState, DeviceRuntimeMetadata
from .errors import (
    DeviceNotMapped,
    ProfileNotFound,
    ProfileRequired,
    ResolverError,
    UnknownBackend,
    UnknownMusicAccount,
)
from .household import FallbackConfiguration, Household, PrivacyDefaults, SharedConfiguration
from .music_account import MusicAccount, MusicAccountKind, MusicAccountState
from .playback_zone import PlaybackZone, PlaybackZoneKind, PlaybackZoneState
from .profile import (
    ConversationReference,
    FeatureEntitlements,
    MoodState,
    MusicDNAReference,
    Profile,
    ProfileCapabilities,
    ProfileMetadata,
    ProfilePreferences,
    ProfilePrivacyMode,
    ProfileState,
    ProfileType,
    RecommendationReference,
    ResponseStyle,
    VoiceStyle,
)
from .resolver import (
    ProfileResolutionContext,
    ProfileResolutionReason,
    ProfileResolutionResult,
    ProfileResolver,
    ProfileResolverIndex,
)
from .storage import ProfilePlatformStorage, ProfileStorageValidationError

__all__ = [
    "BackendProvider",
    "CapabilityPolicy",
    "CapabilityPolicyMode",
    "ConversationReference",
    "Device",
    "DeviceCapabilities",
    "DeviceNotMapped",
    "DevicePairingState",
    "DeviceRuntimeMetadata",
    "FallbackConfiguration",
    "FeatureEntitlements",
    "Household",
    "MoodState",
    "MusicAccount",
    "MusicAccountKind",
    "MusicAccountState",
    "MusicBackendCapabilities",
    "MusicBackendRegistration",
    "MusicBackendState",
    "MusicDNAReference",
    "PlaybackZone",
    "PlaybackZoneKind",
    "PlaybackZoneState",
    "PrivacyDefaults",
    "Profile",
    "ProfileCapabilities",
    "ProfileMetadata",
    "ProfileNotFound",
    "ProfilePreferences",
    "ProfilePrivacyMode",
    "ProfileRequired",
    "ProfileResolutionContext",
    "ProfileResolutionReason",
    "ProfileResolutionResult",
    "ProfileResolver",
    "ProfileResolverIndex",
    "ProfilePlatformStorage",
    "ProfileStorageValidationError",
    "ProfileState",
    "ProfileType",
    "RecommendationReference",
    "ResolverError",
    "ResponseStyle",
    "SharedConfiguration",
    "UnknownBackend",
    "UnknownMusicAccount",
    "VoiceStyle",
]
