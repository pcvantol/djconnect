"""B purpose fences over the existing paired-device/Profile authority owners."""
from __future__ import annotations

import hashlib
import json
import re

from .display_admission import DisplayAdmissionError, DisplayOwnerBinding
from .const import DOMAIN


def _fingerprint(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=False, allow_nan=False).encode()).hexdigest()


async def resolve_display_owner(hass, identity, headers, manager, *, session_id=""):
    """Resolve ordinary pairing, without loading private history or Music DNA.

    Return current Profile plus a private credential-free stamp. No caller-
    selected Profile, server-admin auth substitute or empty-Origin privilege.
    """
    from .request_auth import resolve_runtime, authorize_runtime_device_request, validate_required_client_type
    from .profile_context import async_resolve_device_bound_request_context, profile_storage
    from .profile_privacy import resolve_profile_privacy_policy
    from .profile_backend import profile_backend_runtime
    from .ask_dj.dialogue import source_scope

    if (not isinstance(identity, dict) or set(identity) != {"device_id", "client_type"}
            or not isinstance(identity.get("client_type"), str)
            or identity.get("client_type") not in {"ios", "macos"}
            or not isinstance(identity.get("device_id"), str)
            or validate_required_client_type(identity) is None):
        raise DisplayAdmissionError("display_code_invalid", 400)
    runtime = resolve_runtime(hass, identity["device_id"], headers)
    if runtime is None or not authorize_runtime_device_request(runtime, headers, **identity):
        raise DisplayAdmissionError("unauthorized", 401)
    # Capture the admission that authenticated THIS request before the first
    # await. A later re-pair must not upgrade token-A's in-flight request to B.
    admitted_entry = runtime.entry
    entry_id = admitted_entry.entry_id
    original_runtime = runtime
    original_identity = dict(identity)
    token_fingerprint = _fingerprint(str(getattr(runtime, "device_token", "")))
    generation = manager.receiver_entry_generation(entry_id)
    try:
        context = await async_resolve_device_bound_request_context(
            hass, runtime, identity, request_source="display_owner")
    except Exception:
        raise DisplayAdmissionError("display_context_changed", 403) from None
    storage = profile_storage(hass)
    # Local bytes are fingerprinted once; no owner bearer/header is retained by
    # the long-lived validator closure or returned to a display.
    profile_id = context.profile_id
    authority_revision = storage.authority_revision

    def current_stamp():
        runtime = original_runtime
        entry = getattr(runtime, "entry", None)
        entries = getattr(hass, "config_entries", None)
        if (entry is not admitted_entry or entries is None or entries.async_get_entry(entry_id) is not entry
                or entry.disabled_by is not None or getattr(entry.state, "value", entry.state) != "loaded"
                or hass.data.get(DOMAIN, {}).get(entry_id) is not runtime
                or entry.data.get("device_token") != getattr(runtime, "device_token", None)
                or _fingerprint(str(getattr(runtime, "device_token", ""))) != token_fingerprint
                or manager.receiver_entry_generation(entry_id) != generation
                or getattr(runtime, "_receiver_end_generation", 0) != generation
                or storage.authority_revision != authority_revision):
            return None
        if not authorize_runtime_device_request(runtime,
                {"Authorization": "Bearer " + str(getattr(runtime, "device_token", ""))},
                **original_identity):
            return None
        device = storage.household.devices.get(original_identity["device_id"])
        binding_generation = getattr(device, "binding_generation", "")
        if not isinstance(binding_generation, str) or re.fullmatch(r"[a-f0-9]{32}", binding_generation) is None:
            return None
        profile = storage.resolver().resolve_bound_device(original_identity["device_id"])
        if profile.profile_id != profile_id:
            return None
        backend_id, account_id, _zone = source_scope(profile)
        backend = storage.household.music_backends.get(backend_id)
        account = storage.household.music_accounts.get(account_id)
        if backend_id and (backend is None or str(backend.state) != "active"):
            return None
        if account_id and (account is None or str(account.state) != "active"
                           or account.backend_id != backend_id
                           or (account.linked_profile_ids and profile_id not in account.linked_profile_ids)):
            return None
        provider = profile_backend_runtime(hass, runtime, provider_only=True)
        provider_entry = getattr(getattr(provider, "entry", None), "entry_id", "")
        source = {"backend_id": backend_id, "music_account_id": account_id,
                  "provider_account_id": getattr(account, "provider_account_id", ""),
                  "provider_entry_id": provider_entry}
        if session_id:
            active = manager.current_active(profile_id)
            if active is None or active.session_id != session_id:
                return None
            expected = manager._history_source_contexts.get(session_id, {})
            if any(expected.get(key) and expected[key] != value for key, value in source.items()):
                return None
        return _fingerprint({"profile": profile_id, "device": original_identity,
            "entry": entry_id, "generation": generation, "pairing": token_fingerprint,
            "binding_generation": binding_generation, "source": source,
            "scope": source_scope(profile), "privacy": str(resolve_profile_privacy_policy(profile, {}).mode),
            "backend_revision": getattr(backend, "revision", 0),
            "account_scopes": sorted(getattr(account, "scopes", ()))})

    try:
        stamp = current_stamp()
    except Exception:
        stamp = None
    if stamp is None:
        raise DisplayAdmissionError("display_context_changed", 403)

    revoked = False

    def current():
        nonlocal revoked
        try:
            revoked = revoked or current_stamp() != stamp
        except Exception:
            revoked = True
        return not revoked

    return context, DisplayOwnerBinding(profile_id, session_id, entry_id, stamp, current)
