"""Pure R5 Help observation: exact request grammar and committed owner metadata.

No read may create a runtime, learn identity, load a Store or call a provider.
"""
from __future__ import annotations

from datetime import UTC, datetime
import hmac
import re
import unicodedata
from urllib.parse import unquote_to_bytes
import uuid

REQUIRED = frozenset({'schema_version', 'request_id', 'surface', 'language',
                      'catalogue_id', 'catalogue_revision', 'catalogue_sha256'})


def decode_query(raw: bytes, *, has_body: bool = False):
    if type(raw) is not bytes or has_body or not 0 < len(raw) <= 4096:
        raise ValueError('invalid_request')
    try:
        # HTTP raw query must be ASCII; non-ASCII data travels percent-encoded.
        raw.decode('ascii', errors='strict')
    except UnicodeDecodeError:
        raise ValueError('invalid_request') from None
    pairs = []
    seen = set()
    for part in raw.split(b'&'):
        key, equal, value = part.partition(b'=')
        if not equal or re.search(rb'%(?![0-9a-fA-F]{2})', part):
            raise ValueError('invalid_request')
        try:
            key = unquote_to_bytes(key.replace(b'+', b' ')).decode('utf-8', errors='strict')
            value = unquote_to_bytes(value.replace(b'+', b' ')).decode('utf-8', errors='strict')
        except UnicodeDecodeError:
            raise ValueError('invalid_request') from None
        if key not in REQUIRED | {'session_id'} or key in seen:
            raise ValueError('invalid_request')
        seen.add(key)
        pairs.append((key, value))
    if not REQUIRED <= seen:
        raise ValueError('invalid_request')
    # Only now convert the already validated multi-value collection to a map.
    data = dict(pairs)
    if data['schema_version'] != '1':
        raise ValueError('invalid_request')
    try:
        request_id = uuid.UUID(data['request_id'])
    except ValueError:
        raise ValueError('invalid_request') from None
    if request_id.version != 4 or str(request_id) != data['request_id']:
        raise ValueError('invalid_request')
    if data['surface'] not in {'ask_dj', 'active_session'}:
        raise ValueError('invalid_request')
    if data['language'] not in {'en', 'nl', 'de', 'fr', 'es'}:
        raise ValueError('invalid_request')
    if data['catalogue_id'] != 'ask_dj_examples_v1':
        raise ValueError('invalid_request')
    if (not re.fullmatch(r'[1-9][0-9]{0,9}', data['catalogue_revision'])
            or int(data['catalogue_revision']) > 2147483647):
        raise ValueError('invalid_request')
    if not re.fullmatch(r'[0-9a-f]{64}', data['catalogue_sha256']):
        raise ValueError('invalid_request')
    session = data.get('session_id')
    if session is not None and (not 1 <= len(session.encode('utf-8')) <= 256
            or session != session.strip()
            or any(unicodedata.category(c) in {'Cc', 'Cf'} for c in session)):
        raise ValueError('invalid_request')
    if data['surface'] == 'active_session' and session is None:
        raise ValueError('invalid_request')
    data['catalogue_revision'] = int(data['catalogue_revision'])
    return data


def _entry_config(entry):
    # DJConnectRuntime.config may construct ProfileBackendView. Never call it
    # from this read, even temporarily, and never undo such an allocation.
    return {**entry.data, **entry.options}


def _loaded_entries(hass):
    return [entry for entry in hass.config_entries.async_entries("djconnect")
            if entry.disabled_by is None and entry.state.value == "loaded"]


def _header(headers, key):
    values = headers.getall(key, []) if hasattr(headers, "getall") else [headers.get(key)]
    if len(values) != 1 or type(values[0]) is not str:
        raise PermissionError("unauthorized")
    return values[0]


def paired_runtime(hass, headers):
    """Exact unique existing identity/token, no alias learning or active fallback."""
    from ..client_retirement import is_retired_entry
    from ..request_auth import is_real_device_id
    identifier = _header(headers, "X-DJConnect-Device-ID")
    authorization = _header(headers, "Authorization")
    if (not is_real_device_id(identifier) or not authorization.startswith("Bearer ")
            or not 0 < len(authorization) <= 4096):
        raise PermissionError("unauthorized")
    token = authorization[7:]
    if not token or token != token.strip() or not token.isascii():
        raise PermissionError("unauthorized")
    domain = hass.data.get("djconnect", {})
    matches = []
    for entry in _loaded_entries(hass):
        config = _entry_config(entry)
        runtime = domain.get(entry.entry_id)
        if (runtime is None or getattr(runtime, "entry", None) is not entry
                or is_retired_entry(entry) or config.get("device_id") != identifier):
            continue
        client_type = config.get("client_type")
        prefix = {"ios": "ios", "macos": "macos", "watchos": "watchos",
                  "raspberry_pi": "raspberry-pi"}.get(client_type)
        if prefix is None or not identifier.startswith("djconnect-" + prefix + "-"):
            continue
        matches.append((runtime, identifier, client_type))
    if len(matches) != 1:
        raise PermissionError("unauthorized")
    known = getattr(matches[0][0], "device_token", None)
    if (type(known) is not str or not known.isascii()
            or not hmac.compare_digest(known, token)):
        raise PermissionError("unauthorized")
    if ("X-DJConnect-Client-Type" in headers
            and _header(headers, "X-DJConnect-Client-Type") != matches[0][2]):
        raise PermissionError("unauthorized")
    return matches[0]


def _safe_media_id(value):
    return (type(value) is str and 1 <= len(value.encode("utf-8")) <= 1024
            and value == value.strip()
            and not any(unicodedata.category(c) in {"Cc", "Cf"} for c in value))


def _session_context(domain, owner, session_id, expected_source, result):
    """Only the explicitly requested own committed session; never recovery."""
    if session_id is None:
        return None, lambda: True
    manager = domain.get("session_runtime_manager")
    if (manager is None or manager._lock.locked()
            or owner in manager._pending_settings_confirmations
            or (owner, session_id) in manager._visual_ending):
        raise ValueError("context_unavailable")
    active = manager.current_active(owner)
    if (active is None or active.session_id != session_id
            or active.owner_profile_id != owner
            or str(active.runtime_state) != "active"
            or active.music_backend != expected_source["backend_id"]
            or manager._history_source_contexts.get(session_id) != expected_source
            or active.broadcast.content_pending):
        raise ValueError("context_unavailable")
    result["active_session"] = True
    playback = active.broadcast.state.playback
    stamp = None
    try:
        stamp = datetime.fromisoformat(playback.updated_at)
        fresh = (stamp.tzinfo is not None
                 and 0 <= (datetime.now(UTC) - stamp).total_seconds() < 30)
    except (ValueError, TypeError):
        fresh = False
    opportunity = manager._intra_track_opportunities.get(owner)
    observed_at = opportunity.last_observed_monotonic if opportunity is not None else None
    monotonic_age = (manager._monotonic_source() - observed_at
                     if opportunity is not None else None)
    original_observation_current = bool(
        opportunity is not None and opportunity.item_id == playback.item_id
        and 0 <= monotonic_age < 30)
    result["current_track"] = bool(
        fresh and original_observation_current
        and _safe_media_id(playback.item_id) and playback.title and playback.artist
        and playback.state in {"playing", "paused"})
    result["current_album"] = bool(result["current_track"] and playback.album)
    from .example_catalogue import _safe_slot
    if result["current_track"] and _safe_slot(playback.artist):
        result["slots"] = {"artist": playback.artist}
    forecast = active.broadcast.forecast
    state = forecast.as_dict()
    forecast_stamp = (forecast.revision, forecast.deadline, forecast.observation_deadline,
                      forecast.observation_wall_deadline, forecast.context_item_id)
    try:
        forecast_wall_end = datetime.fromisoformat(state.get("valid_until", ""))
    except (ValueError, TypeError):
        forecast_wall_end = None
    result["forecast_ready"] = bool(
        state.get("state") in {"ready", "limited"}
        and forecast.context_item_id == playback.item_id
        and (state.get("state") != "ready" or playback.state == "playing"))
    settings = (active.settings_generation, active.settings_revision,
                active.mood_revision, active.presence_revision, active.persona_revision)
    source = manager._history_source_contexts[session_id]
    original_opportunity = opportunity

    def current():
        # Recheck original deadlines after all projection callbacks/clock reads.
        # Identity equality alone cannot keep a 29.999-second source alive.
        if result["current_track"] and (
                stamp is None or not 0 <= (datetime.now(UTC) - stamp).total_seconds() < 30
                or original_opportunity.last_observed_monotonic != observed_at
                or not 0 <= manager._monotonic_source() - observed_at < 30):
            return False
        if result["forecast_ready"] and (
                (forecast.revision, forecast.deadline, forecast.observation_deadline,
                 forecast.observation_wall_deadline, forecast.context_item_id) != forecast_stamp
                or forecast.withdrawn or forecast.expired
                or forecast.clock() >= min(forecast_stamp[1], forecast_stamp[2])
                or forecast.wall_clock() >= forecast_stamp[3]
                or forecast_wall_end is None or forecast_wall_end.tzinfo is None
                or datetime.now(UTC) >= forecast_wall_end):
            return False
        return (domain.get("session_runtime_manager") is manager and not manager._lock.locked()
                and owner not in manager._pending_settings_confirmations
                and (owner, session_id) not in manager._visual_ending
                and manager.current_active(owner) is active
                and active.broadcast.state.playback is playback
                and not active.broadcast.content_pending
                and manager._history_source_contexts.get(session_id) is source
                and source == expected_source
                and (active.settings_generation, active.settings_revision, active.mood_revision,
                     active.presence_revision, active.persona_revision) == settings
                and manager._intra_track_opportunities.get(owner) is original_opportunity)
    return playback.item_id if result["current_track"] else None, current


def committed_context(hass, runtime, identifier, client_type, *, session_id=None, owner=None):
    """Synchronous capture/build/final-check; no mutable result escapes authority.

    The caller serializes a detached projection in the same non-yielding turn.
    The loaded Profile witness is additional to selected runtime/source checks.
    """
    from ..profile_observation import capture_committed
    from ..capability_contract import _contract_versions
    from ..profile_backend import profile_backend_entry_id
    from ..use_cases import SpotifyDirectBackend, MusicAssistantBackend
    from .example_catalogue import capability
    from .help_configuration import entry_configuration_mask
    snapshot = capture_committed(hass)
    if snapshot is None:
        return None
    try:
        domain = hass.data["djconnect"]
        entry = runtime.entry
        entry_stamp = (entry.data, entry.options, getattr(entry, "modified_at", None),
                       getattr(runtime, "_receiver_end_generation", 0), runtime.device_token)
        if (entry not in _loaded_entries(hass) or domain.get(entry.entry_id) is not runtime):
            return None
        config = _entry_config(entry)
        if config.get("device_id") != identifier or config.get("client_type") != client_type:
            return None
        transfer_fence = domain.get("retired_provider_transfer_entries", set())
        if entry.entry_id in transfer_fence or config.get("profile_backend_entry_id") in transfer_fence:
            return None
        device = snapshot.household.devices.get(identifier)
        if (device is None or device.client_type != client_type
                or str(device.pairing_state) != "paired" or not device.binding_generation):
            return None
        profile_id = device.linked_profile_id
        if owner is not None and owner != profile_id:
            return None
        profile = snapshot.household.profiles.get(profile_id)
        if (profile is None or str(profile.state) != "active"
                or profile.capabilities.ask_dj is not True):
            return None
        preferences = profile.preferences
        backend = snapshot.household.music_backends.get(preferences.default_backend_id)
        account = snapshot.household.music_accounts.get(preferences.default_music_account_id)
        if (backend is None or str(backend.state) != "active" or account is None
                or str(account.state) != "active" or account.backend_id != backend.backend_id
                or profile_id not in account.linked_profile_ids):
            return None
        source_id = profile_backend_entry_id(hass, profile_id)
        if (source_id in transfer_fence
                or (config.get("profile_backend_entry_id") and (
                    config["profile_backend_entry_id"] != source_id
                    or config.get("music_account_id") != account.account_id))
                or (not config.get("profile_backend_entry_id") and source_id != entry.entry_id)):
            return None
        source_runtime = domain.get(source_id)
        if source_runtime is None or source_runtime.entry.entry_id != source_id:
            return None
        source = source_runtime.entry
        source_stamp = (source.data, source.options, getattr(source, "modified_at", None),
                        getattr(source_runtime, "_receiver_end_generation", 0))
        if source not in _loaded_entries(hass):
            return None
        source_config = _entry_config(source)
        adapter = {"spotify_direct": SpotifyDirectBackend,
                   "music_assistant": MusicAssistantBackend}.get(str(backend.provider))
        if adapter is None:
            return None
        available = (bool(getattr(source_runtime, "latest_spotify_refresh_token", None)
                          or source_config.get("spotify_refresh_token"))
                     if str(backend.provider) == "spotify_direct"
                     else bool(source_config.get("music_assistant_player")))
        result = {"catalogue": capability(), "contracts": _contract_versions(),
                  "paired": True, "online": True, "backend_available": available,
                  "spotify": str(backend.provider) == "spotify_direct",
                  **{key: value is True for key, value in adapter.capabilities.__dict__.items()},
                  "entry_configuration": entry_configuration_mask(hass, config)}
        result["agent_available"] = result["entry_configuration"]["listen.artist"]
        track, session_current = _session_context(domain, profile_id, session_id, {
            "backend_id": backend.backend_id, "music_account_id": account.account_id,
            "provider_entry_id": source_id, "provider_account_id": account.provider_account_id}, result)
        def current():
            try:
                return not (not snapshot.current() or domain.get(entry.entry_id) is not runtime
                    or runtime.entry is not entry or entry not in _loaded_entries(hass)
                    or entry.data is not entry_stamp[0] or entry.options is not entry_stamp[1]
                    or (getattr(entry, "modified_at", None), getattr(runtime, "_receiver_end_generation", 0),
                        runtime.device_token) != entry_stamp[2:]
                    or source_runtime.entry is not source or domain.get(source_id) is not source_runtime
                    or source not in _loaded_entries(hass)
                    or source.data is not source_stamp[0] or source.options is not source_stamp[1]
                    or (getattr(source, "modified_at", None),
                        getattr(source_runtime, "_receiver_end_generation", 0)) != source_stamp[2:]
                    or entry.entry_id in domain.get("retired_provider_transfer_entries", set())
                    or source_id in domain.get("retired_provider_transfer_entries", set())
                    or not result["entry_configuration"].current()
                    or not session_current())
            except Exception:
                return False
        if not current():
            return None
        result["_help_current"] = current
        return result, track
    except Exception:
        return None


def observe(hass, headers, query):
    """Closed detached R5 result; exact pins are compared, never adoption offers."""
    from .example_catalogue import capability, eligible
    runtime, identifier, client_type = paired_runtime(hass, headers)
    pin = capability()
    exact = (query["catalogue_id"] == pin["catalogue_id"]
             and query["catalogue_revision"] == pin["revision"]
             and query["catalogue_sha256"] == pin["sha256"])
    descriptor = {key: pin[key] for key in (
        "schema_version", "catalogue_id", "revision", "sha256", "qualified")} if exact else None
    result = {"schema_version": 1, "request_id": query["request_id"],
              "surface": query["surface"], "language": query["language"],
              "session_id": query.get("session_id"), "track_id": None,
              "catalogue": descriptor, "available": False,
              "observation_id": None, "eligible_entry_ids": []}
    if not exact or pin["qualified"] is not True:
        return result
    captured = committed_context(hass, runtime, identifier, client_type,
                                 session_id=query.get("session_id"))
    if captured is None:
        return result
    context, track = captured
    identifiers = [entry["id"] for entry in eligible(
        context, query["surface"], query["language"], for_help=True)]
    if not context["_help_current"]():
        return result
    result.update(available=True, observation_id=str(uuid.uuid4()), track_id=track,
                  eligible_entry_ids=identifiers)
    return ObservedResponse(result, context["_help_current"])



class ObservedResponse(dict):
    """Only ten wire keys; a private local fence survives until serialization."""
    def __init__(self, value, final_check):
        super().__init__(value)
        self.final_check = final_check

    def closed(self):
        return {**self, "available": False, "track_id": None,
                "observation_id": None, "eligible_entry_ids": []}
