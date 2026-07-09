"""Canonical Profile resolution for DJConnect.

Resolution order is defined by the Platform Foundation and must remain singular:

1. explicit profile_id
2. device_id mapping
3. Home Assistant user hint
4. room mapping
5. fallback profile
6. ProfileRequired
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from ..device import Device
from ..errors import DeviceNotMapped, ProfileNotFound, ProfileRequired
from ..household import Household
from ..models import clean_identifier
from ..profile import Profile


class ProfileResolutionReason(StrEnum):
    """Structured reason describing how a Profile was resolved."""

    EXPLICIT_PROFILE = "explicit_profile"
    DEVICE_MAPPING = "device_mapping"
    SATELLITE_MAPPING = "satellite_mapping"
    HA_USER_MAPPING = "ha_user_mapping"
    AREA_MAPPING = "area_mapping"
    PLAYBACK_ZONE_MAPPING = "playback_zone_mapping"
    FALLBACK = "fallback"


@dataclass(frozen=True)
class ProfileResolutionContext:
    """Typed request context used to resolve a DJConnect Profile.

    Only explicit_profile_id, device_id, ha_user_id and room_id actively affect
    Epic 3A runtime resolution. Other fields are reserved request-source
    signals for Epic 3B follow-up work and must not own personal state.
    """

    explicit_profile_id: str = ""
    device_id: str = ""
    client_type: str = ""
    ha_user_id: str = ""
    satellite_id: str = ""
    ha_device_id: str = ""
    area_id: str = ""
    room_id: str = ""
    player_id: str = ""
    playback_zone_id: str = ""
    session_id: str = ""
    request_source: str = ""
    speaker_identity_hint: str = ""

    def __post_init__(self) -> None:
        """Normalize context identifiers without adding persistence semantics."""
        for field_name in (
            "explicit_profile_id",
            "device_id",
            "client_type",
            "ha_user_id",
            "satellite_id",
            "ha_device_id",
            "area_id",
            "room_id",
            "player_id",
            "playback_zone_id",
            "session_id",
            "request_source",
            "speaker_identity_hint",
        ):
            object.__setattr__(self, field_name, clean_identifier(getattr(self, field_name)))


@dataclass(frozen=True)
class ProfileResolutionResult:
    """Resolved Profile plus safe diagnostics about the resolution path."""

    profile: Profile
    reason: ProfileResolutionReason
    signal: str = ""
    fallback_used: bool = False


@dataclass(frozen=True)
class ProfileResolverIndex:
    """Explicit resolver indexes derived from Household state.

    Later phases can build this index from persistence/config. Phase 1 keeps it
    in-memory and dependency-injected so services do not create their own
    resolution logic.
    """

    device_profile_ids: dict[str, str] = field(default_factory=dict)
    ha_user_profile_ids: dict[str, str] = field(default_factory=dict)
    room_profile_ids: dict[str, str] = field(default_factory=dict)
    fallback_profile_id: str = ""

    @classmethod
    def from_household(cls, household: Household) -> "ProfileResolverIndex":
        """Build resolver indexes from a Household model."""
        device_profile_ids = {
            device_id: device.linked_profile_id
            for device_id, device in household.devices.items()
            if clean_identifier(device.linked_profile_id)
        }
        return cls(
            device_profile_ids=device_profile_ids,
            ha_user_profile_ids=dict(household.shared.ha_user_profile_ids),
            room_profile_ids=dict(household.shared.room_profile_ids),
            fallback_profile_id=household.fallback.fallback_profile_id,
        )


class ProfileResolver:
    """The single canonical Profile resolver."""

    def __init__(
        self,
        profiles: dict[str, Profile],
        *,
        devices: dict[str, Device] | None = None,
        index: ProfileResolverIndex | None = None,
    ) -> None:
        self._profiles = profiles
        self._devices = devices or {}
        self._index = index or ProfileResolverIndex()

    @classmethod
    def for_household(cls, household: Household) -> "ProfileResolver":
        """Create a resolver for a Household."""
        return cls(
            household.profiles,
            devices=household.devices,
            index=ProfileResolverIndex.from_household(household),
        )

    def resolve(self, context: ProfileResolutionContext) -> Profile:
        """Resolve a Profile using the canonical priority order."""
        return self.resolve_with_result(context).profile

    def resolve_with_result(self, context: ProfileResolutionContext) -> ProfileResolutionResult:
        """Resolve a Profile and return safe resolution diagnostics."""
        explicit_profile_id = context.explicit_profile_id
        if explicit_profile_id:
            return ProfileResolutionResult(
                self._require_profile(explicit_profile_id),
                ProfileResolutionReason.EXPLICIT_PROFILE,
                signal=explicit_profile_id,
            )

        device_id = context.device_id
        if device_id:
            device_profile_id = self._profile_id_for_device(device_id)
            if device_profile_id:
                return ProfileResolutionResult(
                    self._require_profile(device_profile_id),
                    ProfileResolutionReason.DEVICE_MAPPING,
                    signal=device_id,
                )

        ha_user_id = context.ha_user_id
        if ha_user_id:
            ha_profile_id = clean_identifier(self._index.ha_user_profile_ids.get(ha_user_id))
            if ha_profile_id:
                return ProfileResolutionResult(
                    self._require_profile(ha_profile_id),
                    ProfileResolutionReason.HA_USER_MAPPING,
                    signal=ha_user_id,
                )

        room_id = context.area_id or context.room_id
        if room_id:
            room_profile_id = clean_identifier(self._index.room_profile_ids.get(room_id))
            if room_profile_id:
                return ProfileResolutionResult(
                    self._require_profile(room_profile_id),
                    ProfileResolutionReason.AREA_MAPPING,
                    signal=room_id,
                )

        fallback_profile_id = clean_identifier(self._index.fallback_profile_id)
        if fallback_profile_id:
            return ProfileResolutionResult(
                self._require_profile(fallback_profile_id),
                ProfileResolutionReason.FALLBACK,
                signal=fallback_profile_id,
                fallback_used=True,
            )

        raise ProfileRequired()

    def _profile_id_for_device(self, device_id: str) -> str:
        """Return linked profile for a device, or raise when explicitly unmapped."""
        mapped_profile_id = clean_identifier(self._index.device_profile_ids.get(device_id))
        if mapped_profile_id:
            return mapped_profile_id
        device = self._devices.get(device_id)
        if device is not None:
            linked_profile_id = clean_identifier(device.linked_profile_id)
            if linked_profile_id:
                return linked_profile_id
            raise DeviceNotMapped(device_id)
        return ""

    def _require_profile(self, profile_id: str) -> Profile:
        """Return an existing profile or raise a canonical error."""
        profile = self._profiles.get(profile_id)
        if profile is None:
            raise ProfileNotFound(profile_id)
        return profile
