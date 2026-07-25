"""Profile-aware request context for DJConnect runtime entrypoints."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Any

from .const import CONF_CLIENT_TYPE, CONF_DEVICE_ID, DOMAIN
from .dj_brain_capabilities import CapabilityPolicy, allowed_intents
from .domain import (
    Profile,
    ProfilePrivacyMode,
    ProfileResolutionContext,
    ProfileResolutionReason,
)
from .domain.errors import DeviceNotMapped, ProfileNotFound, ProfileRequired, ResolverError
from .domain.storage import ProfilePlatformStorage, STORE_KEY as PROFILE_PLATFORM_STORE_KEY
from .profile_privacy import (
    ProfilePrivacyPolicy,
    privacy_response_metadata,
    resolve_profile_privacy_policy,
)

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class DJConnectRequestContext:
    """Resolved Profile context for services, APIs and orchestration."""

    profile: Profile
    profile_id: str
    device_id: str = ""
    client_type: str = ""
    ha_user_id: str = ""
    satellite_id: str = ""
    voice_endpoint_id: str = ""
    assist_pipeline_id: str = ""
    ha_device_id: str = ""
    area_id: str = ""
    room_id: str = ""
    player_id: str = ""
    playback_zone_id: str = ""
    session_id: str = ""
    backend_id: str = ""
    music_account_id: str = ""
    profile_playback_zone_id: str = ""
    privacy_mode: ProfilePrivacyMode = ProfilePrivacyMode.NORMAL
    privacy_policy: ProfilePrivacyPolicy = ProfilePrivacyPolicy(ProfilePrivacyMode.NORMAL)
    capability_policy: CapabilityPolicy = CapabilityPolicy()
    request_source: str = ""
    resolution_reason: ProfileResolutionReason = ProfileResolutionReason.FALLBACK
    resolution_signal: str = ""
    fallback_used: bool = False

    @property
    def music_dna_key(self) -> str:
        """Return the profile-scoped key used by current Music DNA adapters."""
        return f"profile:{self.profile_id}"

    @property
    def allowed_capability_intents(self) -> frozenset[str]:
        """Resolve the Profile's built-in capability policy for the Planner."""
        return allowed_intents(self.capability_policy)


class ProfileContextError(ResolverError):
    """Base error for request-context failures."""

    code = "profile_resolution_failed"
    status = 400


class ProfilePlatformNotConfigured(ProfileContextError):
    """Raised internally when no Profile Platform state exists yet."""

    code = "profile_platform_not_configured"


class ProfileBackendMissing(ProfileContextError):
    """Raised when a resolved profile has no usable backend."""

    code = "profile_backend_missing"

    def __init__(self, profile_id: str) -> None:
        self.profile_id = profile_id
        super().__init__(f"Profile has no configured music backend: {profile_id}")


class ProfileMusicAccountMissing(ProfileContextError):
    """Raised when a resolved profile references a missing music account."""

    code = "profile_music_account_missing"

    def __init__(self, profile_id: str, account_id: str) -> None:
        self.profile_id = profile_id
        self.account_id = account_id
        super().__init__(f"Profile music account is missing: {account_id}")


class ProfileBackendAccountMismatch(ProfileContextError):
    """Raised when profile account/backend references do not match."""

    code = "profile_backend_account_mismatch"

    def __init__(self, profile_id: str, backend_id: str, account_id: str) -> None:
        self.profile_id = profile_id
        self.backend_id = backend_id
        self.account_id = account_id
        super().__init__(f"Profile backend/account mismatch: {profile_id}")


def profile_error_payload(exc: Exception) -> tuple[dict[str, Any], int]:
    """Return structured profile error payload and HTTP-ish status."""
    if isinstance(exc, ProfileNotFound):
        return _payload("invalid_profile", str(exc), profile_id=exc.profile_id), 404
    if isinstance(exc, DeviceNotMapped):
        return _payload("device_not_mapped", str(exc), device_id=exc.device_id), 409
    if isinstance(exc, ProfileRequired):
        return _payload("profile_required", str(exc)), 428
    if isinstance(exc, ProfileContextError):
        return _payload(exc.code, str(exc)), exc.status
    return _payload("profile_resolution_failed", str(exc)), 400


def profile_resolution_context_from_payload(
    runtime: Any,
    payload: dict[str, Any] | None = None,
    *,
    user_id: str | None = None,
    request_source: str = "",
) -> ProfileResolutionContext:
    """Build canonical Profile resolution input from a runtime request payload."""
    payload = payload or {}
    device_id = str(
        payload.get(CONF_DEVICE_ID)
        or payload.get("device_id")
        or getattr(runtime, "pairing_device_id", "")
        or getattr(runtime, "device_status", {}).get(CONF_DEVICE_ID)
        or ""
    ).strip()
    return ProfileResolutionContext(
        explicit_profile_id=str(
            payload.get("profile_id") or payload.get("explicit_profile_id") or ""
        ).strip(),
        device_id=device_id,
        client_type=str(payload.get(CONF_CLIENT_TYPE) or payload.get("client_type") or "").strip(),
        ha_user_id=str(user_id or payload.get("ha_user_id") or payload.get("user_id") or "").strip(),
        satellite_id=str(
            payload.get("satellite_id") or payload.get("assist_satellite_id") or ""
        ).strip(),
        voice_endpoint_id=str(
            payload.get("voice_endpoint_id")
            or payload.get("voice_endpoint")
            or payload.get("assist_voice_endpoint_id")
            or ""
        ).strip(),
        assist_pipeline_id=str(
            payload.get("assist_pipeline_id") or payload.get("pipeline_id") or ""
        ).strip(),
        ha_device_id=str(payload.get("ha_device_id") or payload.get("ha_device") or "").strip(),
        area_id=str(payload.get("area_id") or payload.get("area") or "").strip(),
        room_id=str(payload.get("room_id") or payload.get("room") or "").strip(),
        player_id=str(payload.get("player_id") or payload.get("target_player_id") or "").strip(),
        playback_zone_id=str(
            payload.get("playback_zone_id") or payload.get("zone_id") or ""
        ).strip(),
        session_id=str(payload.get("session_id") or "").strip(),
        request_source=request_source,
        speaker_identity_hint=str(payload.get("speaker_identity_hint") or "").strip(),
    )


async def async_resolve_request_context(
    hass: Any,
    runtime: Any,
    payload: dict[str, Any] | None = None,
    *,
    user_id: str | None = None,
    request_source: str = "",
) -> DJConnectRequestContext:
    """Resolve Profile context through the canonical resolver."""
    payload = payload or {}
    manager = _profile_storage(hass)
    household = await manager.async_load()
    if (
        not household.profiles
        and not str(payload.get("profile_id") or "").strip()
    ):
        raise ProfilePlatformNotConfigured("Profile Platform is not configured.")
    context = profile_resolution_context_from_payload(
        runtime,
        payload,
        user_id=user_id,
        request_source=request_source,
    )
    resolution = manager.resolver().resolve_with_result(context)
    profile = resolution.profile
    privacy_policy = resolve_profile_privacy_policy(profile, payload)
    preferences = profile.preferences
    backend_id = preferences.default_backend_id
    music_account_id = preferences.default_music_account_id
    if backend_id and backend_id not in household.music_backends:
        raise ProfileBackendMissing(profile.profile_id)
    if music_account_id:
        account = household.music_accounts.get(music_account_id)
        if account is None:
            raise ProfileMusicAccountMissing(profile.profile_id, music_account_id)
        if backend_id and account.backend_id != backend_id:
            raise ProfileBackendAccountMismatch(profile.profile_id, backend_id, music_account_id)
    return DJConnectRequestContext(
        profile=profile,
        profile_id=profile.profile_id,
        device_id=context.device_id,
        client_type=context.client_type,
        ha_user_id=context.ha_user_id,
        satellite_id=context.satellite_id,
        voice_endpoint_id=context.voice_endpoint_id,
        assist_pipeline_id=context.assist_pipeline_id,
        ha_device_id=context.ha_device_id,
        area_id=context.area_id,
        room_id=context.room_id,
        player_id=context.player_id,
        playback_zone_id=context.playback_zone_id,
        session_id=context.session_id,
        backend_id=backend_id,
        music_account_id=music_account_id,
        profile_playback_zone_id=preferences.fallback_playback_zone_id,
        privacy_mode=privacy_policy.mode,
        privacy_policy=privacy_policy,
        capability_policy=profile.capability_policy,
        request_source=request_source,
        resolution_reason=resolution.reason,
        resolution_signal=resolution.signal,
        fallback_used=resolution.fallback_used,
    )


async def async_resolve_device_bound_request_context(
    hass: Any,
    runtime: Any,
    payload: dict[str, Any] | None = None,
    *,
    request_source: str = "",
) -> DJConnectRequestContext:
    """Resolve a Profile exclusively through an authenticated device binding.

    This is intentionally narrower than normal request-context resolution. It
    is for owner-only session transports, where a client must never choose a
    Profile through a payload field, HA user, room, area or fallback Profile.
    """
    payload = payload or {}
    context = profile_resolution_context_from_payload(
        runtime, payload, request_source=request_source
    )
    manager = _profile_storage(hass)
    household = await manager.async_load()
    profile = manager.resolver().resolve_bound_device(context.device_id)
    privacy_policy = resolve_profile_privacy_policy(profile, {})
    preferences = profile.preferences
    backend_id = preferences.default_backend_id
    music_account_id = preferences.default_music_account_id
    if backend_id and backend_id not in household.music_backends:
        raise ProfileBackendMissing(profile.profile_id)
    if music_account_id:
        account = household.music_accounts.get(music_account_id)
        if account is None:
            raise ProfileMusicAccountMissing(profile.profile_id, music_account_id)
        if backend_id and account.backend_id != backend_id:
            raise ProfileBackendAccountMismatch(profile.profile_id, backend_id, music_account_id)
    return DJConnectRequestContext(
        profile=profile,
        profile_id=profile.profile_id,
        device_id=context.device_id,
        client_type=context.client_type,
        assist_pipeline_id=context.assist_pipeline_id,
        room_id=context.room_id,
        player_id=context.player_id,
        playback_zone_id=context.playback_zone_id,
        session_id=context.session_id,
        backend_id=backend_id,
        music_account_id=music_account_id,
        profile_playback_zone_id=preferences.fallback_playback_zone_id,
        privacy_mode=privacy_policy.mode,
        privacy_policy=privacy_policy,
        capability_policy=profile.capability_policy,
        request_source=request_source,
        resolution_reason=ProfileResolutionReason.DEVICE_MAPPING,
        resolution_signal=context.device_id,
    )


async def async_apply_profile_context(
    hass: Any,
    runtime: Any,
    payload: dict[str, Any],
    *,
    user_id: str | None = None,
    request_source: str = "",
) -> DJConnectRequestContext:
    """Resolve Profile and enrich payload for existing adapters."""
    context = await async_resolve_request_context(
        hass,
        runtime,
        payload,
        user_id=user_id,
        request_source=request_source,
    )
    payload["profile_id"] = context.profile_id
    payload.setdefault("music_dna_key", context.music_dna_key)
    payload["profile_privacy_mode"] = context.privacy_mode.value
    payload["profile_privacy"] = privacy_response_metadata(context.privacy_policy)
    payload["private_session"] = context.privacy_policy.private_session
    if context.backend_id:
        payload.setdefault("profile_backend_id", context.backend_id)
    if context.music_account_id:
        payload.setdefault("profile_music_account_id", context.music_account_id)
    if context.profile_playback_zone_id:
        payload.setdefault("profile_playback_zone_id", context.profile_playback_zone_id)
    _LOGGER.debug(
        "DJConnect Profile resolved source=%s reason=%s profile_id=%s device_id=%s "
        "has_satellite=%s area_id=%s fallback_used=%s",
        context.request_source or "unknown",
        context.resolution_reason.value,
        _safe_debug_identifier(context.profile_id),
        _safe_debug_identifier(context.device_id),
        bool(context.satellite_id or context.ha_device_id),
        _safe_debug_identifier(context.area_id or context.room_id),
        context.fallback_used,
    )
    setattr(runtime, "profile_context_profile_id", context.profile_id)
    setattr(runtime, "profile_context_backend_id", context.backend_id)
    setattr(runtime, "profile_context_music_account_id", context.music_account_id)
    setattr(runtime, "profile_context_playback_zone_id", context.profile_playback_zone_id)
    setattr(runtime, "profile_context_privacy_policy", context.privacy_policy)
    setattr(runtime, "profile_context_capability_policy", context.capability_policy)
    setattr(runtime, "profile_context_allowed_capability_intents", context.allowed_capability_intents)
    setattr(runtime, "profile_context_resolution_reason", context.resolution_reason.value)
    return context


def _profile_storage(hass: Any) -> ProfilePlatformStorage:
    domain_data = getattr(hass, "data", {}).setdefault(DOMAIN, {})
    manager = domain_data.get(PROFILE_PLATFORM_STORE_KEY)
    if not isinstance(manager, ProfilePlatformStorage):
        manager = ProfilePlatformStorage(hass)
        domain_data[PROFILE_PLATFORM_STORE_KEY] = manager
    return manager


def profile_storage(hass: Any) -> ProfilePlatformStorage:
    """Return the canonical Profile Platform storage manager."""
    return _profile_storage(hass)


def _payload(code: str, message: str, **extra: Any) -> dict[str, Any]:
    return {
        "success": False,
        "error": code,
        "message": message,
        **{key: value for key, value in extra.items() if value not in ("", None)},
    }


def _safe_debug_identifier(value: Any) -> str:
    """Return a bounded non-secret identifier for debug logs."""
    text = str(value or "").strip()
    if len(text) <= 64:
        return text
    return f"{text[:32]}...{text[-12:]}"
