"""Narrow versioned ordinary-pairing transport for active owner Session mood."""

from __future__ import annotations

from typing import Any

from .const import API_SESSION_MOOD, CLIENT_TYPES, DOMAIN

VERSION = 1
MOODS = ("chill", "groove", "energy", "party")


def capability() -> dict[str, Any]:
    """Describe the existing symbolic Session choices; never grant authority."""
    return {
        "available": True,
        "version": VERSION,
        "path": API_SESSION_MOOD,
        "method": "POST",
        "authentication": "paired_device_bearer",
        "moods": list(MOODS),
        "ordering": "expected_mood_revision",
        "scope": "active_device_bound_owner_session",
    }


async def async_handle_mood(hass, data, *, headers=None):
    """Validate and commit through the existing owner resolver and Runtime lock."""
    from .api_handlers import _async_owner_broadcast_session_context
    from .profile_context import profile_storage
    from .request_auth import (
        authorize_runtime_device_request,
        request_token,
        resolve_runtime,
        runtime_matches_device,
    )
    from .session_runtime import MoodRevisionConflictError

    def error(code, status, **extra):
        return {"success": False, "error": code, **extra}, status

    fields = {
        "contract_version",
        "client_type",
        "device_id",
        "session_id",
        "selected_mood",
        "expected_mood_revision",
    }
    if not isinstance(data, dict) or set(data) != fields:
        return error("invalid_request", 400)
    if type(data["contract_version"]) is not int or data["contract_version"] != VERSION:
        return error("unsupported_contract_version", 400)
    if type(data["selected_mood"]) is not str or data["selected_mood"] not in MOODS:
        return error("invalid_selected_mood", 400)
    revision = data["expected_mood_revision"]
    if type(revision) is not int or revision < 0:
        return error("invalid_mood_revision", 400)
    if (
        type(data["client_type"]) is not str
        or data["client_type"] not in CLIENT_TYPES
        or any(type(data[key]) is not str or not data[key] for key in ("device_id", "session_id"))
    ):
        return error("invalid_request", 400)
    headers = headers or {}
    if not str(headers.get("Authorization", "")).startswith("Bearer "):
        return error("unauthorized", 401)
    runtime = resolve_runtime(hass, data["device_id"], headers)
    if runtime is None:
        return error("unauthorized", 401)
    entry = getattr(runtime, "entry", None)
    entry_id = str(getattr(entry, "entry_id", ""))
    generation = getattr(runtime, "_receiver_end_generation", 0)

    def pairing_is_current():
        domain = hass.data.get(DOMAIN, {})
        if (
            entry is None
            or domain.get(entry_id) is not runtime
            or hass.config_entries.async_get_entry(entry_id) is not entry
            or entry.disabled_by is not None
            or getattr(getattr(entry, "state", None), "value", None) != "loaded"
        ):
            return False
        conf = {**entry.data, **entry.options}
        known = (
            getattr(runtime, "device_status", {}).get("device_id")
            or getattr(runtime, "pairing_device_id", "")
            or conf.get("device_id")
        )
        if (
            conf.get("device_token") != request_token(headers)
            or conf.get("device_id") != data["device_id"]
            or known != data["device_id"]
            or conf.get("client_type") != data["client_type"]
            or headers.get("X-DJConnect-Device-ID", data["device_id"]) != data["device_id"]
            or getattr(runtime, "_receiver_end_generation", 0) != generation
        ):
            return False
        return runtime_matches_device(
            runtime, data["device_id"]
        ) and authorize_runtime_device_request(
            runtime, headers, data["device_id"], data["client_type"]
        )

    # Reject before the generic authorizer can learn a pending setup-code identity.
    if not pairing_is_current():
        return error("unauthorized", 401)
    result, status, manager, profile_id = await _async_owner_broadcast_session_context(
        hass, data, headers=headers, source="active_session_mood"
    )
    if manager is None:
        return result, status

    def owner_is_current():
        """Synchronous final authority fence after lock acquisition, before commit."""
        if (
            not pairing_is_current()
            or hass.data.get(DOMAIN, {}).get("session_runtime_manager") is not manager
            or manager.receiver_entry_generation(entry_id) != generation
        ):
            return False
        try:
            profile = profile_storage(hass).resolver().resolve_bound_device(data["device_id"])
            return profile.profile_id == profile_id and profile.state.value == "active"
        except Exception:
            return False

    try:
        active = await manager.async_update_mood(
            owner_profile_id=profile_id,
            session_id=data["session_id"],
            selected_mood=data["selected_mood"],
            expected_revision=revision,
            authorize=owner_is_current,
        )
    except PermissionError:
        return error("unauthorized", 401)
    except MoodRevisionConflictError as exc:
        return error(
            "mood_revision_conflict",
            409,
            current={
                "session_id": exc.active.session_id,
                "selected_mood": exc.active.selected_mood,
                "mood_revision": exc.active.mood_revision,
            },
        )
    if active is None:
        return error("active_session_not_found", 404)
    return {
        "success": True,
        "contract_version": VERSION,
        "session_id": active.session_id,
        "selected_mood": active.selected_mood,
        "mood_revision": active.mood_revision,
        "changed": active.mood_revision != revision,
    }, 200
