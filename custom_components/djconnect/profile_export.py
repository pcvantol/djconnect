"""Safe Profile Platform export, import and reset flows."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from typing import Any
import uuid

from .domain import (
    ConversationReference,
    MoodState,
    MusicDNAReference,
    Profile,
    RecommendationReference,
)
from .domain.models import clean_identifier
from .domain.storage import (
    SCHEMA_VERSION as PROFILE_STORAGE_SCHEMA_VERSION,
    ProfilePlatformStorage,
    household_from_storage,
    household_to_storage,
)
from .profile_privacy import resolve_profile_privacy_policy

EXPORT_SCHEMA_VERSION = 1
PROFILE_EXPORT_FORMAT = "djconnect.profile.export"
HOUSEHOLD_EXPORT_FORMAT = "djconnect.household.export"
INTEGRATION_EXPORT_FORMAT = "djconnect.integration.export"
SECRET_KEY_FRAGMENTS = (
    "token",
    "password",
    "secret",
    "authorization",
    "proof",
    "credential",
    "refresh",
    "access",
    "apikey",
    "api_key",
    "private_key",
    "device_token",
    "apns",
)


class ProfileExportError(ValueError):
    """Raised for invalid export/import/reset requests."""

    code = "profile_export_error"


class UnsafeImportError(ProfileExportError):
    """Raised when import data contains unsafe secret-like fields."""

    code = "unsafe_import"


async def async_export_profile(
    manager: ProfilePlatformStorage,
    profile_id: str,
    *,
    include_personal_data: bool = True,
) -> dict[str, Any]:
    """Export one Profile without secrets."""
    household = await manager.async_load()
    profile = household.profiles.get(clean_identifier(profile_id))
    if profile is None:
        raise ProfileExportError("profile not found")
    policy = resolve_profile_privacy_policy(profile)
    storage = household_to_storage(household)["household"]
    profile_data = next(
        item for item in storage["profiles"] if item.get("profile_id") == profile.profile_id
    )
    include_personal = include_personal_data and policy.allow_profile_export
    profile_data = _redact_profile_data(profile_data, include_personal=include_personal)
    return _redact_secrets(
        {
            "success": True,
            "format": PROFILE_EXPORT_FORMAT,
            "schema_version": EXPORT_SCHEMA_VERSION,
            "profile": profile_data,
            "privacy": {
                "mode": policy.mode.value,
                "personal_data_included": include_personal,
                "secret_policy": "secrets_excluded_by_default",
            },
            "relink_required": _profile_relink_required(household_to_storage(household), profile),
        }
    )


async def async_export_household(manager: ProfilePlatformStorage) -> dict[str, Any]:
    """Export household Profile Platform metadata without secrets."""
    household = await manager.async_load()
    return _redact_secrets(
        {
            "success": True,
            "format": HOUSEHOLD_EXPORT_FORMAT,
            "schema_version": EXPORT_SCHEMA_VERSION,
            "profile_storage_schema_version": PROFILE_STORAGE_SCHEMA_VERSION,
            "household": household_to_storage(household)["household"],
            "secret_policy": "secrets_excluded_by_default",
            "relink_required": _accounts_relink_required(household_to_storage(household)),
        }
    )


async def async_export_integration(
    manager: ProfilePlatformStorage,
    *,
    non_secret_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Export the non-secret integration Profile Platform envelope."""
    household_export = await async_export_household(manager)
    return _redact_secrets(
        {
            "success": True,
            "format": INTEGRATION_EXPORT_FORMAT,
            "schema_version": EXPORT_SCHEMA_VERSION,
            "profile_platform": household_export,
            "non_secret_config": _redact_secrets(non_secret_config or {}),
            "excluded": {
                "oauth_tokens": True,
                "provider_refresh_tokens": True,
                "provider_secrets": True,
                "home_assistant_tokens": True,
                "apns_tokens": True,
                "device_tokens": True,
                "raw_credentials": True,
            },
            "relink_required": household_export.get("relink_required", []),
        }
    )


async def async_import_profile(
    manager: ProfilePlatformStorage,
    envelope: dict[str, Any],
    *,
    overwrite: bool = False,
    reassign_id: bool = False,
) -> dict[str, Any]:
    """Import one Profile, rejecting unsafe secret-bearing envelopes."""
    _validate_no_secret_fields(envelope)
    if envelope.get("format") != PROFILE_EXPORT_FORMAT or int(envelope.get("schema_version") or 0) != EXPORT_SCHEMA_VERSION:
        raise ProfileExportError("invalid profile export schema")
    profile_data = envelope.get("profile")
    if not isinstance(profile_data, dict):
        raise ProfileExportError("profile export is missing profile")
    household = await manager.async_load()
    storage = household_to_storage(household)
    import_id = clean_identifier(profile_data.get("profile_id"))
    if not import_id:
        raise ProfileExportError("profile export is missing profile_id")
    final_id = import_id
    collision = final_id in household.profiles
    if collision and not overwrite:
        if not reassign_id:
            raise ProfileExportError("profile_id collision")
        final_id = _new_profile_id(storage, import_id)
        profile_data = deepcopy(profile_data)
        profile_data["profile_id"] = final_id
    profiles = [
        item for item in storage["household"].get("profiles", [])
        if item.get("profile_id") != final_id
    ]
    profiles.append(profile_data)
    storage["household"]["profiles"] = profiles
    await manager.async_save(household_from_storage(storage))
    return {
        "success": True,
        "imported": "profile",
        "profile_id": final_id,
        "reassigned": final_id != import_id,
        "relink_required": envelope.get("relink_required", []),
    }


async def async_import_household(
    manager: ProfilePlatformStorage,
    envelope: dict[str, Any],
    *,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Import a household or full integration export."""
    _validate_no_secret_fields(envelope)
    household_payload = _household_payload_from_import(envelope)
    if household_payload is None:
        raise ProfileExportError("invalid household export schema")
    existing = await manager.async_load()
    if existing.profiles and not overwrite:
        raise ProfileExportError("household import would overwrite existing profiles")
    await manager.async_save(household_from_storage({"household": household_payload}))
    return {
        "success": True,
        "imported": "household",
        "profile_count": len(household_payload.get("profiles") or []),
        "relink_required": _accounts_relink_required({"household": household_payload}),
    }


async def async_clear_profile_personal_state(
    manager: ProfilePlatformStorage,
    profile_id: str,
    *,
    ask_dj: bool = False,
    music_dna: bool = False,
    recommendations: bool = False,
    mood: bool = False,
    all_state: bool = False,
) -> Profile:
    """Clear profile-owned personal references without deleting the Profile."""
    household = await manager.async_load()
    clean_profile_id = clean_identifier(profile_id)
    profile = household.profiles.get(clean_profile_id)
    if profile is None:
        raise ProfileExportError("profile not found")
    if all_state or ask_dj:
        profile = replace(profile, conversation=ConversationReference())
    if all_state or music_dna:
        profile = replace(profile, music_dna=MusicDNAReference())
    if all_state or recommendations:
        profile = replace(profile, recommendations=RecommendationReference(), likes=frozenset(), dislikes=frozenset())
    if all_state or mood:
        profile = replace(profile, mood=MoodState())
    await manager.async_save(
        replace(household, profiles={**household.profiles, profile.profile_id: profile})
    )
    return profile


def profile_export_error_payload(exc: Exception) -> tuple[dict[str, Any], int]:
    """Return structured export/import error payload."""
    code = getattr(exc, "code", "profile_export_error")
    status = 400
    if isinstance(exc, UnsafeImportError):
        status = 422
    return {"success": False, "error": code, "message": str(exc)}, status


def _redact_profile_data(profile_data: dict[str, Any], *, include_personal: bool) -> dict[str, Any]:
    profile_data = deepcopy(profile_data)
    if include_personal:
        return profile_data
    profile_data["references"] = {}
    profile_data["mood"] = {}
    profile_data["likes"] = []
    profile_data["dislikes"] = []
    return profile_data


def _redact_secrets(value: Any, *, allow_secret_keys: bool = False) -> Any:
    if isinstance(value, dict):
        return {
            str(key): _redact_secrets(
                item,
                allow_secret_keys=allow_secret_keys or str(key) == "excluded",
            )
            for key, item in value.items()
            if allow_secret_keys or not _is_secret_key(str(key))
        }
    if isinstance(value, list):
        return [_redact_secrets(item, allow_secret_keys=allow_secret_keys) for item in value]
    return value


def _validate_no_secret_fields(value: Any, path: str = "") -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            key_path = f"{path}.{key}" if path else str(key)
            if _is_secret_key(str(key)):
                raise UnsafeImportError(f"unsafe secret field in import: {key_path}")
            _validate_no_secret_fields(item, key_path)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _validate_no_secret_fields(item, f"{path}[{index}]")


def _is_secret_key(key: str) -> bool:
    normalized = key.lower()
    if normalized.startswith(("non_secret", "secret_policy")):
        return False
    return any(fragment in normalized for fragment in SECRET_KEY_FRAGMENTS)


def _household_payload_from_import(envelope: dict[str, Any]) -> dict[str, Any] | None:
    if int(envelope.get("schema_version") or 0) != EXPORT_SCHEMA_VERSION:
        return None
    if envelope.get("format") == HOUSEHOLD_EXPORT_FORMAT and isinstance(envelope.get("household"), dict):
        return deepcopy(envelope["household"])
    if envelope.get("format") == INTEGRATION_EXPORT_FORMAT:
        platform = envelope.get("profile_platform")
        if isinstance(platform, dict) and isinstance(platform.get("household"), dict):
            return deepcopy(platform["household"])
    return None


def _profile_relink_required(storage: dict[str, Any], profile: Profile) -> list[dict[str, str]]:
    account_id = profile.preferences.default_music_account_id
    return [
        item for item in _accounts_relink_required(storage)
        if not account_id or item.get("account_id") == account_id
    ]


def _accounts_relink_required(storage: dict[str, Any]) -> list[dict[str, str]]:
    household = storage.get("household") if isinstance(storage.get("household"), dict) else storage
    accounts = household.get("music_accounts") if isinstance(household, dict) else []
    result = []
    for account in accounts or []:
        if not isinstance(account, dict):
            continue
        result.append(
            {
                "account_id": str(account.get("account_id") or ""),
                "backend_id": str(account.get("backend_id") or ""),
                "reason": "provider_credentials_excluded",
            }
        )
    return [item for item in result if item["account_id"]]


def _new_profile_id(storage: dict[str, Any], base_id: str) -> str:
    existing = {
        str(item.get("profile_id") or "")
        for item in storage.get("household", {}).get("profiles", [])
        if isinstance(item, dict)
    }
    while True:
        candidate = f"{base_id}-import-{uuid.uuid4().hex[:6]}"
        if candidate not in existing:
            return candidate
