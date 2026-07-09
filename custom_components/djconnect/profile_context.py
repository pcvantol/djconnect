"""Profile-aware request context for DJConnect runtime entrypoints."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .const import CONF_DEVICE_ID, DOMAIN
from .domain import Profile, ProfilePrivacyMode, ProfileResolutionContext
from .domain.errors import DeviceNotMapped, ProfileNotFound, ProfileRequired, ResolverError
from .domain.storage import ProfilePlatformStorage, STORE_KEY as PROFILE_PLATFORM_STORE_KEY


@dataclass(frozen=True)
class DJConnectRequestContext:
    """Resolved Profile context for services, APIs and orchestration."""

    profile: Profile
    profile_id: str
    device_id: str = ""
    ha_user_id: str = ""
    backend_id: str = ""
    music_account_id: str = ""
    playback_zone_id: str = ""
    privacy_mode: ProfilePrivacyMode = ProfilePrivacyMode.NORMAL
    request_source: str = ""

    @property
    def music_dna_key(self) -> str:
        """Return the profile-scoped key used by current Music DNA adapters."""
        return f"profile:{self.profile_id}"


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
    device_id = str(
        payload.get(CONF_DEVICE_ID)
        or getattr(runtime, "pairing_device_id", "")
        or getattr(runtime, "device_status", {}).get(CONF_DEVICE_ID)
        or ""
    ).strip()
    context = ProfileResolutionContext(
        profile_id=str(payload.get("profile_id") or "").strip(),
        device_id=device_id,
        ha_user_id=str(user_id or payload.get("user_id") or "").strip(),
        room_id=str(payload.get("room_id") or payload.get("room") or "").strip(),
    )
    profile = manager.resolver().resolve(context)
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
        device_id=device_id,
        ha_user_id=str(user_id or payload.get("user_id") or "").strip(),
        backend_id=backend_id,
        music_account_id=music_account_id,
        playback_zone_id=preferences.fallback_playback_zone_id,
        privacy_mode=profile.privacy_mode,
        request_source=request_source,
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
    if context.backend_id:
        payload.setdefault("profile_backend_id", context.backend_id)
    if context.music_account_id:
        payload.setdefault("profile_music_account_id", context.music_account_id)
    if context.playback_zone_id:
        payload.setdefault("profile_playback_zone_id", context.playback_zone_id)
    setattr(runtime, "profile_context_profile_id", context.profile_id)
    setattr(runtime, "profile_context_backend_id", context.backend_id)
    setattr(runtime, "profile_context_music_account_id", context.music_account_id)
    setattr(runtime, "profile_context_playback_zone_id", context.playback_zone_id)
    return context


def _profile_storage(hass: Any) -> ProfilePlatformStorage:
    domain_data = getattr(hass, "data", {}).setdefault(DOMAIN, {})
    manager = domain_data.get(PROFILE_PLATFORM_STORE_KEY)
    if not isinstance(manager, ProfilePlatformStorage):
        manager = ProfilePlatformStorage(hass)
        domain_data[PROFILE_PLATFORM_STORE_KEY] = manager
    return manager


def _payload(code: str, message: str, **extra: Any) -> dict[str, Any]:
    return {
        "success": False,
        "error": code,
        "message": message,
        **{key: value for key, value in extra.items() if value not in ("", None)},
    }
