"""Profile-owned DJConnect state."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from ..models import clean_identifier


class ProfileType(StrEnum):
    """Canonical DJConnect Profile types."""

    PERSONAL = "personal"
    HOUSEHOLD = "household"
    ROOM = "room"
    GUEST = "guest"
    KIDS = "kids"
    PARTY = "party"


class ProfilePrivacyMode(StrEnum):
    """Profile privacy modes from the platform foundation."""

    NORMAL = "normal"
    PRIVATE = "private"
    SHARED = "shared"
    GUEST_SAFE = "guest-safe"


class ProfileState(StrEnum):
    """Lifecycle state for a DJConnect Profile."""

    ACTIVE = "active"
    DISABLED = "disabled"
    ARCHIVED = "archived"


class ResponseStyle(StrEnum):
    """Preferred response style for backend-owned DJ responses."""

    CONCISE = "concise"
    BALANCED = "balanced"
    EXPRESSIVE = "expressive"


class VoiceStyle(StrEnum):
    """Profile-owned voice tone preference."""

    DEFAULT = "default"
    LATE_NIGHT = "late_night"
    CLASSIC_RADIO = "classic_radio"
    ENERGY = "energy"
    CLEAN_HOST = "clean_host"


@dataclass(frozen=True)
class MusicDNAReference:
    """Reference to profile-owned Music DNA data."""

    key: str = ""
    enabled: bool = False
    revision: int = 0


@dataclass(frozen=True)
class ConversationReference:
    """Reference to profile-owned Ask DJ conversation history."""

    key: str = ""
    revision: int = 0
    clear_revision: int = 0


@dataclass(frozen=True)
class RecommendationReference:
    """Reference to profile-owned recommendation state."""

    key: str = ""
    revision: int = 0


@dataclass(frozen=True)
class MoodState:
    """Profile-owned durable mood state."""

    value: int | None = None
    zone: str = ""
    updated_at: str = ""


@dataclass(frozen=True)
class FeatureEntitlements:
    """Profile-level product entitlements."""

    community: bool = True
    personal: bool = False
    cloud: bool = False
    premium: bool = False
    experimental: frozenset[str] = field(default_factory=frozenset)


@dataclass(frozen=True)
class ProfileCapabilities:
    """Capabilities available to a profile."""

    ask_dj: bool = True
    music_dna: bool = True
    recommendations: bool = True
    profile_export: bool = False
    privacy_controls: bool = True
    shared_context: bool = False


@dataclass(frozen=True)
class ProfilePreferences:
    """Profile-owned preferences and defaults."""

    default_backend_id: str = ""
    default_music_account_id: str = ""
    fallback_playback_zone_id: str = ""
    response_style: ResponseStyle = ResponseStyle.BALANCED
    voice_style: VoiceStyle = VoiceStyle.DEFAULT
    language: str = ""


@dataclass(frozen=True)
class ProfileMetadata:
    """Metadata about a DJConnect Profile."""

    created_at: str = ""
    updated_at: str = ""
    created_by: str = ""
    labels: frozenset[str] = field(default_factory=frozenset)
    source: str = "djconnect"


@dataclass(frozen=True)
class Profile:
    """Primary DJConnect identity and personalization boundary."""

    profile_id: str
    display_name: str
    profile_type: ProfileType = ProfileType.PERSONAL
    state: ProfileState = ProfileState.ACTIVE
    privacy_mode: ProfilePrivacyMode = ProfilePrivacyMode.NORMAL
    preferences: ProfilePreferences = field(default_factory=ProfilePreferences)
    metadata: ProfileMetadata = field(default_factory=ProfileMetadata)
    music_dna: MusicDNAReference = field(default_factory=MusicDNAReference)
    conversation: ConversationReference = field(default_factory=ConversationReference)
    recommendations: RecommendationReference = field(default_factory=RecommendationReference)
    mood: MoodState = field(default_factory=MoodState)
    entitlements: FeatureEntitlements = field(default_factory=FeatureEntitlements)
    capabilities: ProfileCapabilities = field(default_factory=ProfileCapabilities)
    likes: frozenset[str] = field(default_factory=frozenset)
    dislikes: frozenset[str] = field(default_factory=frozenset)
    feature_settings: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate required profile identity."""
        if not clean_identifier(self.profile_id):
            raise ValueError("profile_id is required")
        if not clean_identifier(self.display_name):
            raise ValueError("display_name is required")
