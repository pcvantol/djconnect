"""Persistent Profile Platform storage."""

from __future__ import annotations

from dataclasses import replace
from typing import Any
import uuid

from ..dj_brain_capabilities import CapabilityPolicy, CapabilityPolicyMode
from .backend import BackendProvider, MusicBackendCapabilities, MusicBackendRegistration
from .device import Device, DeviceCapabilities, DevicePairingState, DeviceRuntimeMetadata
from .errors import ProfileNotFound, UnknownBackend, UnknownMusicAccount
from .household import FallbackConfiguration, Household, PrivacyDefaults, SharedConfiguration
from .models import clean_identifier
from .music_account import MusicAccount, MusicAccountKind
from .playback_zone import PlaybackZone, PlaybackZoneKind
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
from .resolver import ProfileResolver

STORE_KEY = "djconnect_profile_platform"
STORE_VERSION = 1
SCHEMA_VERSION = 1
DEFAULT_HOUSEHOLD_ID = "household-local"
DEFAULT_HOUSEHOLD_NAME = "DJConnect Household"


class ProfileStorageValidationError(ValueError):
    """Raised when Profile Platform storage contains invalid references."""


class ProfilePlatformStorage:
    """Load, validate and persist Profile Platform state."""

    def __init__(self, hass: Any | None = None, store: Any | None = None) -> None:
        self.hass = hass
        self._store = store if store is not None else self._create_store(hass)
        self._loaded = False
        self._household = default_household()

    @property
    def household(self) -> Household:
        """Return the loaded Household state."""
        return self._household

    async def async_load(self) -> Household:
        """Load Household state from Home Assistant Store."""
        if self._loaded:
            return self._household
        loaded = await self._store.async_load() if self._store is not None else None
        self._household = household_from_storage(loaded)
        self.validate_household(self._household)
        self._loaded = True
        return self._household

    async def async_save(self, household: Household | None = None) -> Household:
        """Validate and persist Household state."""
        if household is not None:
            self._household = household
        self.validate_household(self._household)
        self._loaded = True
        if self._store is not None:
            await self._store.async_save(household_to_storage(self._household))
        return self._household

    async def async_create_profile(
        self,
        display_name: str,
        *,
        profile_type: ProfileType = ProfileType.PERSONAL,
        privacy_mode: ProfilePrivacyMode = ProfilePrivacyMode.NORMAL,
        response_style: ResponseStyle = ResponseStyle.BALANCED,
        voice_style: VoiceStyle = VoiceStyle.DEFAULT,
        default_backend_id: str = "",
        default_music_account_id: str = "",
        fallback_playback_zone_id: str = "",
        profile_id: str | None = None,
    ) -> Profile:
        """Create and persist a Profile."""
        household = await self.async_load()
        name = clean_identifier(display_name)
        if not name:
            raise ProfileStorageValidationError("profile display_name is required")
        if _duplicate_profile_name(household, name):
            raise ProfileStorageValidationError("profile display_name already exists")
        profile = Profile(
            profile_id=clean_identifier(profile_id) or _new_id("profile"),
            display_name=name,
            profile_type=profile_type,
            privacy_mode=privacy_mode,
            preferences=ProfilePreferences(
                default_backend_id=default_backend_id,
                default_music_account_id=default_music_account_id,
                fallback_playback_zone_id=fallback_playback_zone_id,
                response_style=response_style,
                voice_style=voice_style,
            ),
        )
        updated = replace(
            household,
            profiles={**household.profiles, profile.profile_id: profile},
        )
        if not clean_identifier(updated.fallback.fallback_profile_id):
            updated = replace(
                updated,
                fallback=replace(updated.fallback, fallback_profile_id=profile.profile_id),
            )
        self._household = updated
        await self.async_save()
        return profile

    async def async_update_profile(
        self,
        profile_id: str,
        *,
        display_name: str | None = None,
        profile_type: ProfileType | None = None,
        privacy_mode: ProfilePrivacyMode | None = None,
        preferences: ProfilePreferences | None = None,
    ) -> Profile:
        """Update and persist a Profile."""
        household = await self.async_load()
        profile = _require_profile(household, profile_id)
        if display_name is not None:
            name = clean_identifier(display_name)
            if not name:
                raise ProfileStorageValidationError("profile display_name is required")
            if _duplicate_profile_name(household, name, exclude_profile_id=profile.profile_id):
                raise ProfileStorageValidationError("profile display_name already exists")
            profile = replace(profile, display_name=name)
        if profile_type is not None:
            profile = replace(profile, profile_type=profile_type)
        if privacy_mode is not None:
            profile = replace(profile, privacy_mode=privacy_mode)
        if preferences is not None:
            profile = replace(profile, preferences=preferences)
        self._household = replace(
            household,
            profiles={**household.profiles, profile.profile_id: profile},
        )
        await self.async_save()
        return profile

    async def async_delete_profile(
        self,
        profile_id: str,
        *,
        reassign_to_profile_id: str | None = None,
    ) -> Household:
        """Delete a Profile and optionally reassign references."""
        household = await self.async_load()
        profile = _require_profile(household, profile_id)
        reassign_id = clean_identifier(reassign_to_profile_id)
        fallback_id = clean_identifier(household.fallback.fallback_profile_id)
        if fallback_id == profile.profile_id and not reassign_id:
            raise ProfileStorageValidationError("cannot delete fallback profile without reassignment")
        if reassign_id:
            _require_profile(household, reassign_id)
        profiles = dict(household.profiles)
        profiles.pop(profile.profile_id)
        devices = {
            device_id: (
                replace(device, linked_profile_id=reassign_id)
                if device.linked_profile_id == profile.profile_id
                else device
            )
            for device_id, device in household.devices.items()
        }
        shared = replace(
            household.shared,
            room_profile_ids={
                room: (reassign_id if mapped == profile.profile_id else mapped)
                for room, mapped in household.shared.room_profile_ids.items()
                if mapped != profile.profile_id or reassign_id
            },
            area_profile_ids={
                area: (reassign_id if mapped == profile.profile_id else mapped)
                for area, mapped in household.shared.area_profile_ids.items()
                if mapped != profile.profile_id or reassign_id
            },
            voice_endpoint_profile_ids={
                endpoint: (reassign_id if mapped == profile.profile_id else mapped)
                for endpoint, mapped in household.shared.voice_endpoint_profile_ids.items()
                if mapped != profile.profile_id or reassign_id
            },
            ha_device_profile_ids={
                device: (reassign_id if mapped == profile.profile_id else mapped)
                for device, mapped in household.shared.ha_device_profile_ids.items()
                if mapped != profile.profile_id or reassign_id
            },
            ha_user_profile_ids={
                user: (reassign_id if mapped == profile.profile_id else mapped)
                for user, mapped in household.shared.ha_user_profile_ids.items()
                if mapped != profile.profile_id or reassign_id
            },
            player_profile_ids={
                player: (reassign_id if mapped == profile.profile_id else mapped)
                for player, mapped in household.shared.player_profile_ids.items()
                if mapped != profile.profile_id or reassign_id
            },
            playback_zone_profile_ids={
                zone: (reassign_id if mapped == profile.profile_id else mapped)
                for zone, mapped in household.shared.playback_zone_profile_ids.items()
                if mapped != profile.profile_id or reassign_id
            },
        )
        fallback = household.fallback
        if fallback_id == profile.profile_id:
            fallback = replace(fallback, fallback_profile_id=reassign_id)
        accounts = {
            account_id: replace(
                account,
                linked_profile_ids=frozenset(
                    reassign_id if item == profile.profile_id and reassign_id else item
                    for item in account.linked_profile_ids
                    if item != profile.profile_id or reassign_id
                ),
            )
            for account_id, account in household.music_accounts.items()
        }
        self._household = replace(
            household,
            profiles=profiles,
            devices=devices,
            music_accounts=accounts,
            shared=shared,
            fallback=fallback,
        )
        await self.async_save()
        return self._household

    async def async_upsert_device(
        self,
        device_id: str,
        client_type: str,
        *,
        display_name: str = "",
        linked_profile_id: str = "",
        room_id: str = "",
        default_playback_zone_id: str = "",
    ) -> Device:
        """Create or update a Device mapping."""
        household = await self.async_load()
        clean_device_id = clean_identifier(device_id)
        clean_client_type = clean_identifier(client_type)
        if not clean_device_id or not clean_client_type:
            raise ProfileStorageValidationError("device_id and client_type are required")
        linked_id = clean_identifier(linked_profile_id)
        if linked_id:
            _require_profile(household, linked_id)
        existing = household.devices.get(clean_device_id)
        device = Device(
            device_id=clean_device_id,
            client_type=clean_client_type,
            display_name=clean_identifier(display_name)
            or (existing.display_name if existing else clean_device_id),
            linked_profile_id=linked_id if linked_profile_id is not None else (
                existing.linked_profile_id if existing else ""
            ),
            room_id=clean_identifier(room_id) or (existing.room_id if existing else ""),
            default_playback_zone_id=clean_identifier(default_playback_zone_id)
            or (existing.default_playback_zone_id if existing else ""),
            capabilities=existing.capabilities if existing else DeviceCapabilities(),
            pairing_state=existing.pairing_state if existing else DevicePairingState.PAIRED,
            last_seen=existing.last_seen if existing else "",
            runtime=existing.runtime if existing else DeviceRuntimeMetadata(),
        )
        self._household = replace(
            household,
            devices={**household.devices, device.device_id: device},
        )
        await self.async_save()
        return device

    async def async_unlink_device(self, device_id: str) -> Device:
        """Remove a Device -> Profile mapping."""
        household = await self.async_load()
        device = household.devices.get(clean_identifier(device_id))
        if device is None:
            raise ProfileStorageValidationError("unknown device")
        device = replace(device, linked_profile_id="")
        self._household = replace(
            household,
            devices={**household.devices, device.device_id: device},
        )
        await self.async_save()
        return device

    async def async_upsert_music_backend(
        self,
        backend_id: str,
        provider: BackendProvider,
        *,
        display_name: str,
        capabilities: MusicBackendCapabilities | None = None,
        configuration: dict[str, Any] | None = None,
    ) -> MusicBackendRegistration:
        """Create or update music backend metadata."""
        household = await self.async_load()
        backend = MusicBackendRegistration(
            backend_id=backend_id,
            provider=provider,
            display_name=display_name,
            capabilities=capabilities or MusicBackendCapabilities(),
            configuration=_safe_provider_configuration(configuration or {}),
        )
        self._household = replace(
            household,
            music_backends={**household.music_backends, backend.backend_id: backend},
        )
        await self.async_save()
        return backend

    async def async_upsert_music_account(
        self,
        account_id: str,
        backend_id: str,
        *,
        kind: MusicAccountKind,
        display_name: str,
        linked_profile_ids: frozenset[str] | None = None,
        provider_account_id: str = "",
    ) -> MusicAccount:
        """Create or update music account metadata without secrets."""
        household = await self.async_load()
        if clean_identifier(backend_id) not in household.music_backends:
            raise UnknownBackend(clean_identifier(backend_id))
        links = linked_profile_ids or frozenset()
        for profile_id in links:
            _require_profile(household, profile_id)
        account = MusicAccount(
            account_id=account_id,
            backend_id=backend_id,
            kind=kind,
            display_name=display_name,
            linked_profile_ids=links,
            provider_account_id=provider_account_id,
        )
        self._household = replace(
            household,
            music_accounts={**household.music_accounts, account.account_id: account},
        )
        await self.async_save()
        return account

    async def async_set_fallback_profile(
        self,
        profile_id: str,
        *,
        require_profile: bool | None = None,
    ) -> Household:
        """Set fallback profile behavior."""
        household = await self.async_load()
        clean_profile_id = clean_identifier(profile_id)
        if clean_profile_id:
            _require_profile(household, clean_profile_id)
        fallback = replace(
            household.fallback,
            fallback_profile_id=clean_profile_id,
            require_profile=household.fallback.require_profile
            if require_profile is None
            else bool(require_profile),
        )
        self._household = replace(household, fallback=fallback)
        await self.async_save()
        return self._household

    async def async_set_profile_mapping(
        self,
        mapping_type: str,
        source_id: str,
        profile_id: str,
    ) -> Household:
        """Set or clear a Household-owned request-source -> Profile mapping."""
        household = await self.async_load()
        clean_source_id = clean_identifier(source_id)
        clean_profile_id = clean_identifier(profile_id)
        if not clean_source_id:
            raise ProfileStorageValidationError("mapping source_id is required")
        if clean_profile_id:
            _require_profile(household, clean_profile_id)
        field_name = _mapping_field_name(mapping_type)
        mapping = dict(getattr(household.shared, field_name))
        if clean_profile_id:
            mapping[clean_source_id] = clean_profile_id
        else:
            mapping.pop(clean_source_id, None)
        self._household = replace(
            household,
            shared=replace(household.shared, **{field_name: mapping}),
        )
        await self.async_save()
        return self._household

    def resolver(self) -> ProfileResolver:
        """Return a resolver for the loaded Household state."""
        return ProfileResolver.for_household(self._household)

    @staticmethod
    def validate_household(household: Household) -> None:
        """Validate storage references."""
        fallback_id = clean_identifier(household.fallback.fallback_profile_id)
        if fallback_id and fallback_id not in household.profiles:
            raise ProfileStorageValidationError("fallback profile does not exist")
        for device in household.devices.values():
            linked_id = clean_identifier(device.linked_profile_id)
            if linked_id and linked_id not in household.profiles:
                raise ProfileStorageValidationError("device mapped to missing profile")
        for mapping in (
            household.shared.room_profile_ids,
            household.shared.area_profile_ids,
            household.shared.voice_endpoint_profile_ids,
            household.shared.ha_device_profile_ids,
            household.shared.ha_user_profile_ids,
            household.shared.player_profile_ids,
            household.shared.playback_zone_profile_ids,
        ):
            for profile_id in mapping.values():
                if clean_identifier(profile_id) not in household.profiles:
                    raise ProfileStorageValidationError("mapping references missing profile")
        for account in household.music_accounts.values():
            if account.backend_id not in household.music_backends:
                raise UnknownBackend(account.backend_id)
            for profile_id in account.linked_profile_ids:
                if profile_id not in household.profiles:
                    raise ProfileStorageValidationError("account mapped to missing profile")
        for profile in household.profiles.values():
            prefs = profile.preferences
            if prefs.default_backend_id and prefs.default_backend_id not in household.music_backends:
                raise UnknownBackend(prefs.default_backend_id)
            if (
                prefs.default_music_account_id
                and prefs.default_music_account_id not in household.music_accounts
            ):
                raise UnknownMusicAccount(prefs.default_music_account_id)
            if prefs.default_music_account_id:
                account = household.music_accounts[prefs.default_music_account_id]
                if prefs.default_backend_id and account.backend_id != prefs.default_backend_id:
                    raise ProfileStorageValidationError("backend/account mismatch")

    @staticmethod
    def _create_store(hass: Any | None) -> Any | None:
        if hass is None:
            return None
        try:
            from homeassistant.helpers.storage import Store
        except Exception:  # noqa: BLE001
            return None
        return Store(hass, STORE_VERSION, STORE_KEY)


def default_household() -> Household:
    """Return an empty default Household."""
    return Household(
        household_id=DEFAULT_HOUSEHOLD_ID,
        display_name=DEFAULT_HOUSEHOLD_NAME,
        privacy_defaults=PrivacyDefaults(),
    )


def _mapping_field_name(mapping_type: str) -> str:
    normalized = clean_identifier(mapping_type).replace("-", "_")
    aliases = {
        "room": "room_profile_ids",
        "area": "area_profile_ids",
        "voice_endpoint": "voice_endpoint_profile_ids",
        "satellite": "voice_endpoint_profile_ids",
        "ha_device": "ha_device_profile_ids",
        "ha_user": "ha_user_profile_ids",
        "player": "player_profile_ids",
        "playback_zone": "playback_zone_profile_ids",
    }
    field_name = aliases.get(normalized, normalized)
    allowed = {
        "room_profile_ids",
        "area_profile_ids",
        "voice_endpoint_profile_ids",
        "ha_device_profile_ids",
        "ha_user_profile_ids",
        "player_profile_ids",
        "playback_zone_profile_ids",
    }
    if field_name not in allowed:
        raise ProfileStorageValidationError("unknown profile mapping type")
    return field_name


def household_from_storage(data: Any) -> Household:
    """Deserialize Household state from explicit storage schema."""
    if not isinstance(data, dict):
        return default_household()
    household_data = data.get("household") if isinstance(data.get("household"), dict) else data
    profiles = {
        item["profile_id"]: _profile_from_storage(item)
        for item in _object_list(household_data.get("profiles"))
        if isinstance(item, dict) and clean_identifier(item.get("profile_id"))
    }
    devices = {
        item["device_id"]: _device_from_storage(item)
        for item in _object_list(household_data.get("devices"))
        if isinstance(item, dict) and clean_identifier(item.get("device_id"))
    }
    backends = {
        item["backend_id"]: _backend_from_storage(item)
        for item in _object_list(household_data.get("music_backends"))
        if isinstance(item, dict) and clean_identifier(item.get("backend_id"))
    }
    accounts = {
        item["account_id"]: _account_from_storage(item)
        for item in _object_list(household_data.get("music_accounts"))
        if isinstance(item, dict) and clean_identifier(item.get("account_id"))
    }
    zones = {
        item["zone_id"]: _zone_from_storage(item)
        for item in _object_list(household_data.get("playback_zones"))
        if isinstance(item, dict) and clean_identifier(item.get("zone_id"))
    }
    fallback_raw = household_data.get("fallback") or {}
    shared_raw = household_data.get("shared") or {}
    privacy_raw = household_data.get("privacy_defaults") or {}
    return Household(
        household_id=clean_identifier(household_data.get("household_id")) or DEFAULT_HOUSEHOLD_ID,
        display_name=clean_identifier(household_data.get("display_name")) or DEFAULT_HOUSEHOLD_NAME,
        profiles=profiles,
        devices=devices,
        music_backends=backends,
        music_accounts=accounts,
        playback_zones=zones,
        fallback=FallbackConfiguration(
            fallback_profile_id=clean_identifier(fallback_raw.get("fallback_profile_id")),
            fallback_playback_zone_id=clean_identifier(fallback_raw.get("fallback_playback_zone_id")),
            require_profile=bool(fallback_raw.get("require_profile", True)),
        ),
        shared=SharedConfiguration(
            room_profile_ids=_clean_mapping(shared_raw.get("room_profile_ids")),
            area_profile_ids=_clean_mapping(shared_raw.get("area_profile_ids")),
            voice_endpoint_profile_ids=_clean_mapping(
                shared_raw.get("voice_endpoint_profile_ids")
                or shared_raw.get("satellite_profile_ids")
            ),
            ha_device_profile_ids=_clean_mapping(shared_raw.get("ha_device_profile_ids")),
            ha_user_profile_ids=_clean_mapping(shared_raw.get("ha_user_profile_ids")),
            player_profile_ids=_clean_mapping(shared_raw.get("player_profile_ids")),
            playback_zone_profile_ids=_clean_mapping(
                shared_raw.get("playback_zone_profile_ids")
            ),
            default_room_playback_zone_ids=_clean_mapping(
                shared_raw.get("default_room_playback_zone_ids")
            ),
        ),
        privacy_defaults=PrivacyDefaults(
            default_profile_privacy_mode=_enum(
                ProfilePrivacyMode,
                privacy_raw.get("default_profile_privacy_mode"),
                ProfilePrivacyMode.NORMAL,
            ),
            shared_device_privacy_mode=_enum(
                ProfilePrivacyMode,
                privacy_raw.get("shared_device_privacy_mode"),
                ProfilePrivacyMode.SHARED,
            ),
            guest_privacy_mode=_enum(
                ProfilePrivacyMode,
                privacy_raw.get("guest_privacy_mode"),
                ProfilePrivacyMode.GUEST_SAFE,
            ),
        ),
    )


def household_to_storage(household: Household) -> dict[str, Any]:
    """Serialize Household state to explicit storage schema."""
    return {
        "version": SCHEMA_VERSION,
        "household": {
            "household_id": household.household_id,
            "display_name": household.display_name,
            "profiles": [_profile_to_storage(item) for item in household.profiles.values()],
            "devices": [_device_to_storage(item) for item in household.devices.values()],
            "music_backends": [
                _backend_to_storage(item) for item in household.music_backends.values()
            ],
            "music_accounts": [
                _account_to_storage(item) for item in household.music_accounts.values()
            ],
            "playback_zones": [_zone_to_storage(item) for item in household.playback_zones.values()],
            "fallback": {
                "fallback_profile_id": household.fallback.fallback_profile_id,
                "fallback_playback_zone_id": household.fallback.fallback_playback_zone_id,
                "require_profile": household.fallback.require_profile,
            },
            "shared": {
                "room_profile_ids": dict(household.shared.room_profile_ids),
                "area_profile_ids": dict(household.shared.area_profile_ids),
                "voice_endpoint_profile_ids": dict(
                    household.shared.voice_endpoint_profile_ids
                ),
                "ha_device_profile_ids": dict(household.shared.ha_device_profile_ids),
                "ha_user_profile_ids": dict(household.shared.ha_user_profile_ids),
                "player_profile_ids": dict(household.shared.player_profile_ids),
                "playback_zone_profile_ids": dict(
                    household.shared.playback_zone_profile_ids
                ),
                "default_room_playback_zone_ids": dict(
                    household.shared.default_room_playback_zone_ids
                ),
            },
            "privacy_defaults": {
                "default_profile_privacy_mode": household.privacy_defaults.default_profile_privacy_mode.value,
                "shared_device_privacy_mode": household.privacy_defaults.shared_device_privacy_mode.value,
                "guest_privacy_mode": household.privacy_defaults.guest_privacy_mode.value,
            },
        },
    }


def _profile_to_storage(profile: Profile) -> dict[str, Any]:
    prefs = profile.preferences
    return {
        "profile_id": profile.profile_id,
        "display_name": profile.display_name,
        "profile_type": profile.profile_type.value,
        "state": profile.state.value,
        "privacy_mode": profile.privacy_mode.value,
        "preferences": {
            "default_backend_id": prefs.default_backend_id,
            "default_music_account_id": prefs.default_music_account_id,
            "fallback_playback_zone_id": prefs.fallback_playback_zone_id,
            "response_style": prefs.response_style.value,
            "voice_style": prefs.voice_style.value,
            "language": prefs.language,
        },
        "metadata": {
            "created_at": profile.metadata.created_at,
            "updated_at": profile.metadata.updated_at,
            "created_by": profile.metadata.created_by,
            "labels": sorted(profile.metadata.labels),
            "source": profile.metadata.source,
        },
        "references": {
            "music_dna": {
                "key": profile.music_dna.key,
                "enabled": profile.music_dna.enabled,
                "revision": profile.music_dna.revision,
            },
            "conversation": {
                "key": profile.conversation.key,
                "revision": profile.conversation.revision,
                "clear_revision": profile.conversation.clear_revision,
            },
            "recommendations": {
                "key": profile.recommendations.key,
                "revision": profile.recommendations.revision,
            },
        },
        "mood": {
            "value": profile.mood.value,
            "zone": profile.mood.zone,
            "updated_at": profile.mood.updated_at,
        },
        "entitlements": {
            "community": profile.entitlements.community,
            "personal": profile.entitlements.personal,
            "cloud": profile.entitlements.cloud,
            "premium": profile.entitlements.premium,
            "experimental": sorted(profile.entitlements.experimental),
        },
        "capabilities": {
            "ask_dj": profile.capabilities.ask_dj,
            "music_dna": profile.capabilities.music_dna,
            "recommendations": profile.capabilities.recommendations,
            "profile_export": profile.capabilities.profile_export,
            "privacy_controls": profile.capabilities.privacy_controls,
            "shared_context": profile.capabilities.shared_context,
        },
        "capability_policy": {
            "mode": profile.capability_policy.mode.value,
            "allowed_capability_ids": sorted(profile.capability_policy.allowed_capability_ids),
        },
        "likes": sorted(profile.likes),
        "dislikes": sorted(profile.dislikes),
    }


def _profile_from_storage(data: dict[str, Any]) -> Profile:
    prefs = data.get("preferences") or {}
    refs = data.get("references") or {}
    metadata = data.get("metadata") or {}
    mood = data.get("mood") or {}
    entitlements = data.get("entitlements") or {}
    capabilities = data.get("capabilities") or {}
    capability_policy = data.get("capability_policy") or {}
    return Profile(
        profile_id=clean_identifier(data.get("profile_id")),
        display_name=clean_identifier(data.get("display_name")) or "Profile",
        profile_type=_enum(ProfileType, data.get("profile_type"), ProfileType.PERSONAL),
        state=_enum(ProfileState, data.get("state"), ProfileState.ACTIVE),
        privacy_mode=_enum(
            ProfilePrivacyMode,
            data.get("privacy_mode"),
            ProfilePrivacyMode.NORMAL,
        ),
        preferences=ProfilePreferences(
            default_backend_id=clean_identifier(prefs.get("default_backend_id")),
            default_music_account_id=clean_identifier(prefs.get("default_music_account_id")),
            fallback_playback_zone_id=clean_identifier(prefs.get("fallback_playback_zone_id")),
            response_style=_enum(ResponseStyle, prefs.get("response_style"), ResponseStyle.BALANCED),
            voice_style=_enum(VoiceStyle, prefs.get("voice_style"), VoiceStyle.DEFAULT),
            language=clean_identifier(prefs.get("language")),
        ),
        capability_policy=CapabilityPolicy(
            mode=_enum(CapabilityPolicyMode, capability_policy.get("mode"), CapabilityPolicyMode.FULL),
            allowed_capability_ids=frozenset(_list(capability_policy.get("allowed_capability_ids"))),
        ),
        metadata=ProfileMetadata(
            created_at=clean_identifier(metadata.get("created_at")),
            updated_at=clean_identifier(metadata.get("updated_at")),
            created_by=clean_identifier(metadata.get("created_by")),
            labels=frozenset(_list(metadata.get("labels"))),
            source=clean_identifier(metadata.get("source")) or "djconnect",
        ),
        music_dna=MusicDNAReference(
            key=clean_identifier((refs.get("music_dna") or {}).get("key")),
            enabled=bool((refs.get("music_dna") or {}).get("enabled")),
            revision=_int((refs.get("music_dna") or {}).get("revision")),
        ),
        conversation=ConversationReference(
            key=clean_identifier((refs.get("conversation") or {}).get("key")),
            revision=_int((refs.get("conversation") or {}).get("revision")),
            clear_revision=_int((refs.get("conversation") or {}).get("clear_revision")),
        ),
        recommendations=RecommendationReference(
            key=clean_identifier((refs.get("recommendations") or {}).get("key")),
            revision=_int((refs.get("recommendations") or {}).get("revision")),
        ),
        mood=MoodState(
            value=mood.get("value") if isinstance(mood.get("value"), int) else None,
            zone=clean_identifier(mood.get("zone")),
            updated_at=clean_identifier(mood.get("updated_at")),
        ),
        entitlements=FeatureEntitlements(
            community=bool(entitlements.get("community", True)),
            personal=bool(entitlements.get("personal", False)),
            cloud=bool(entitlements.get("cloud", False)),
            premium=bool(entitlements.get("premium", False)),
            experimental=frozenset(_list(entitlements.get("experimental"))),
        ),
        capabilities=ProfileCapabilities(
            ask_dj=bool(capabilities.get("ask_dj", True)),
            music_dna=bool(capabilities.get("music_dna", True)),
            recommendations=bool(capabilities.get("recommendations", True)),
            profile_export=bool(capabilities.get("profile_export", False)),
            privacy_controls=bool(capabilities.get("privacy_controls", True)),
            shared_context=bool(capabilities.get("shared_context", False)),
        ),
        likes=frozenset(_list(data.get("likes"))),
        dislikes=frozenset(_list(data.get("dislikes"))),
    )


def _device_to_storage(device: Device) -> dict[str, Any]:
    return {
        "device_id": device.device_id,
        "client_type": device.client_type,
        "display_name": device.display_name,
        "linked_profile_id": device.linked_profile_id,
        "room_id": device.room_id,
        "default_playback_zone_id": device.default_playback_zone_id,
        "pairing_state": device.pairing_state.value,
        "last_seen": device.last_seen,
        "capabilities": device.capabilities.__dict__,
        "runtime": device.runtime.__dict__,
    }


def _device_from_storage(data: dict[str, Any]) -> Device:
    capabilities = data.get("capabilities") or {}
    runtime = data.get("runtime") or {}
    return Device(
        device_id=clean_identifier(data.get("device_id")),
        client_type=clean_identifier(data.get("client_type")),
        display_name=clean_identifier(data.get("display_name")),
        linked_profile_id=clean_identifier(data.get("linked_profile_id")),
        room_id=clean_identifier(data.get("room_id")),
        default_playback_zone_id=clean_identifier(data.get("default_playback_zone_id")),
        capabilities=DeviceCapabilities(**_known_kwargs(DeviceCapabilities, capabilities)),
        pairing_state=_enum(
            DevicePairingState,
            data.get("pairing_state"),
            DevicePairingState.UNPAIRED,
        ),
        last_seen=clean_identifier(data.get("last_seen")),
        runtime=DeviceRuntimeMetadata(**_known_kwargs(DeviceRuntimeMetadata, runtime)),
    )


def _backend_to_storage(backend: MusicBackendRegistration) -> dict[str, Any]:
    return {
        "backend_id": backend.backend_id,
        "provider": backend.provider.value,
        "display_name": backend.display_name,
        "state": backend.state.value,
        "capabilities": backend.capabilities.__dict__,
        "configuration": _safe_provider_configuration(backend.configuration),
        "revision": backend.revision,
    }


def _backend_from_storage(data: dict[str, Any]) -> MusicBackendRegistration:
    return MusicBackendRegistration(
        backend_id=clean_identifier(data.get("backend_id")),
        provider=_enum(BackendProvider, data.get("provider"), BackendProvider.FUTURE_PROVIDER),
        display_name=clean_identifier(data.get("display_name")) or "Music Backend",
        capabilities=MusicBackendCapabilities(
            **_known_kwargs(MusicBackendCapabilities, data.get("capabilities") or {})
        ),
        configuration=_safe_provider_configuration(data.get("configuration") or {}),
        revision=_int(data.get("revision")),
    )


def _account_to_storage(account: MusicAccount) -> dict[str, Any]:
    return {
        "account_id": account.account_id,
        "backend_id": account.backend_id,
        "kind": account.kind.value,
        "display_name": account.display_name,
        "linked_profile_ids": sorted(account.linked_profile_ids),
        "provider_account_id": account.provider_account_id,
        "state": account.state.value,
        "scopes": sorted(account.scopes),
        "metadata": dict(account.metadata),
    }


def _account_from_storage(data: dict[str, Any]) -> MusicAccount:
    return MusicAccount(
        account_id=clean_identifier(data.get("account_id")),
        backend_id=clean_identifier(data.get("backend_id")),
        kind=_enum(MusicAccountKind, data.get("kind"), MusicAccountKind.PERSONAL),
        display_name=clean_identifier(data.get("display_name")) or "Music Account",
        linked_profile_ids=frozenset(_list(data.get("linked_profile_ids"))),
        provider_account_id=clean_identifier(data.get("provider_account_id")),
        scopes=frozenset(_list(data.get("scopes"))),
        metadata={str(key): str(value) for key, value in (data.get("metadata") or {}).items()},
    )


def _zone_to_storage(zone: PlaybackZone) -> dict[str, Any]:
    return {
        "zone_id": zone.zone_id,
        "display_name": zone.display_name,
        "kind": zone.kind.value,
        "backend_id": zone.backend_id,
        "provider_target_id": zone.provider_target_id,
        "room_id": zone.room_id,
        "state": zone.state.value,
        "capabilities": sorted(zone.capabilities),
    }


def _zone_from_storage(data: dict[str, Any]) -> PlaybackZone:
    return PlaybackZone(
        zone_id=clean_identifier(data.get("zone_id")),
        display_name=clean_identifier(data.get("display_name")) or "Playback Zone",
        kind=_enum(PlaybackZoneKind, data.get("kind"), PlaybackZoneKind.FUTURE_TARGET),
        backend_id=clean_identifier(data.get("backend_id")),
        provider_target_id=clean_identifier(data.get("provider_target_id")),
        room_id=clean_identifier(data.get("room_id")),
        capabilities=frozenset(_list(data.get("capabilities"))),
    )


def _enum(enum_type: Any, value: Any, default: Any) -> Any:
    try:
        return enum_type(str(value))
    except (TypeError, ValueError):
        return default


def _int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _list(value: Any) -> list[str]:
    if not isinstance(value, list | tuple | set | frozenset):
        return []
    return [clean_identifier(item) for item in value if clean_identifier(item)]


def _object_list(value: Any) -> list[Any]:
    if not isinstance(value, list | tuple):
        return []
    return list(value)


def _clean_mapping(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    return {
        clean_identifier(key): clean_identifier(val)
        for key, val in value.items()
        if clean_identifier(key) and clean_identifier(val)
    }


def _known_kwargs(cls: Any, values: dict[str, Any]) -> dict[str, Any]:
    fields = getattr(cls, "__dataclass_fields__", {})
    return {key: values[key] for key in fields if key in values}


def _safe_provider_configuration(values: dict[str, Any]) -> dict[str, Any]:
    blocked = ("token", "password", "secret", "authorization", "proof")
    return {
        str(key): value
        for key, value in values.items()
        if not any(fragment in str(key).lower() for fragment in blocked)
    }


def _duplicate_profile_name(
    household: Household,
    display_name: str,
    *,
    exclude_profile_id: str = "",
) -> bool:
    normalized = display_name.casefold()
    return any(
        profile.display_name.casefold() == normalized
        and profile.profile_id != exclude_profile_id
        for profile in household.profiles.values()
    )


def _require_profile(household: Household, profile_id: str) -> Profile:
    clean_profile_id = clean_identifier(profile_id)
    profile = household.profiles.get(clean_profile_id)
    if profile is None:
        raise ProfileNotFound(clean_profile_id)
    return profile


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"
