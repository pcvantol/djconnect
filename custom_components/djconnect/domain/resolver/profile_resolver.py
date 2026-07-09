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

from ..device import Device
from ..errors import DeviceNotMapped, ProfileNotFound, ProfileRequired
from ..household import Household
from ..models import clean_identifier
from ..profile import Profile


@dataclass(frozen=True)
class ProfileResolutionContext:
    """Inputs available while resolving a DJConnect Profile."""

    profile_id: str = ""
    device_id: str = ""
    ha_user_id: str = ""
    room_id: str = ""


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
        explicit_profile_id = clean_identifier(context.profile_id)
        if explicit_profile_id:
            return self._require_profile(explicit_profile_id)

        device_id = clean_identifier(context.device_id)
        if device_id:
            device_profile_id = self._profile_id_for_device(device_id)
            if device_profile_id:
                return self._require_profile(device_profile_id)

        ha_user_id = clean_identifier(context.ha_user_id)
        if ha_user_id:
            ha_profile_id = clean_identifier(self._index.ha_user_profile_ids.get(ha_user_id))
            if ha_profile_id:
                return self._require_profile(ha_profile_id)

        room_id = clean_identifier(context.room_id)
        if room_id:
            room_profile_id = clean_identifier(self._index.room_profile_ids.get(room_id))
            if room_profile_id:
                return self._require_profile(room_profile_id)

        fallback_profile_id = clean_identifier(self._index.fallback_profile_id)
        if fallback_profile_id:
            return self._require_profile(fallback_profile_id)

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
