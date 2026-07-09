"""Household-owned DJConnect platform configuration."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..backend import MusicBackendRegistration
from ..device import Device
from ..models import clean_identifier
from ..music_account import MusicAccount
from ..playback_zone import PlaybackZone
from ..profile import Profile, ProfilePrivacyMode


@dataclass(frozen=True)
class FallbackConfiguration:
    """Household fallback behavior."""

    fallback_profile_id: str = ""
    fallback_playback_zone_id: str = ""
    require_profile: bool = True


@dataclass(frozen=True)
class SharedConfiguration:
    """Household shared room and routing mappings."""

    room_profile_ids: dict[str, str] = field(default_factory=dict)
    ha_user_profile_ids: dict[str, str] = field(default_factory=dict)
    default_room_playback_zone_ids: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class PrivacyDefaults:
    """Household privacy defaults."""

    default_profile_privacy_mode: ProfilePrivacyMode = ProfilePrivacyMode.NORMAL
    shared_device_privacy_mode: ProfilePrivacyMode = ProfilePrivacyMode.SHARED
    guest_privacy_mode: ProfilePrivacyMode = ProfilePrivacyMode.GUEST_SAFE


@dataclass(frozen=True)
class Household:
    """Local DJConnect platform boundary, usually one HA installation."""

    household_id: str
    display_name: str
    profiles: dict[str, Profile] = field(default_factory=dict)
    devices: dict[str, Device] = field(default_factory=dict)
    music_backends: dict[str, MusicBackendRegistration] = field(default_factory=dict)
    music_accounts: dict[str, MusicAccount] = field(default_factory=dict)
    playback_zones: dict[str, PlaybackZone] = field(default_factory=dict)
    fallback: FallbackConfiguration = field(default_factory=FallbackConfiguration)
    shared: SharedConfiguration = field(default_factory=SharedConfiguration)
    privacy_defaults: PrivacyDefaults = field(default_factory=PrivacyDefaults)

    def __post_init__(self) -> None:
        """Validate household identity."""
        if not clean_identifier(self.household_id):
            raise ValueError("household_id is required")
        if not clean_identifier(self.display_name):
            raise ValueError("display_name is required")
