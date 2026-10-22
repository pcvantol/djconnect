"""Read-only owner/source adapter for the process-memory Visual Director.

No generic Ask DJ, provider queries, Store creation, logs or persistent writes.
Only existing loaded pairing, Profile, active Session and accepted Stage1 samples
can authorize this surface. Original closures are captured before any await.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import hmac
import re

from .visual_director import VERSION, VisualDirector, VisualDirectorError, validate_request, _string

KEY = "vibescape_visual_director"
SOURCE_FIELDS = ("backend_id", "music_account_id", "provider_entry_id", "provider_account_id")


def _need(value, code="session_context_changed", status=409):
    if not value:
        raise VisualDirectorError(code, status)


def _domain(hass):
    return getattr(hass, "data", {}).get("djconnect", {})


def engine(hass, *, create=False):
    domain = _domain(hass)
    item = domain.get(KEY)
    if item is None and create:
        item = domain[KEY] = VisualDirector()
    _need(item is None or isinstance(item, VisualDirector), "visual_unavailable", 503)
    return item


def withdraw_all(hass):
    item = engine(hass)
    if item is not None:
        item.invalidate_all()


def withdraw_source(hass, observed):
    item = engine(hass)
    if item is not None:
        item.withdraw(observed.visual_source)


def invalidate_observer_metadata(hass, observed):
    item = engine(hass)
    if item is not None:
        item.invalidate_observation(observed.visual_source)


@dataclass(frozen=True)
class Admission:
    actor: tuple
    source: object
    authorized: object
    manager: object
    owner: str
    session_id: str
    observed: object
    broadcast: object
    mood: str
    previous_sample_serial: int = 0
    scope_authorized: object = None


def _entry_guard(hass, runtime, manager):
    from .client_identity import device_id_matches_client_type

    entry = getattr(runtime, "entry", None)
    _need(entry is not None, "visual_unavailable", 503)
    entry_id = entry.entry_id
    original_data, original_options = entry.data, entry.options
    conf = {**original_data, **original_options}
    device, client = conf.get("device_id"), conf.get("client_type")
    _need(device_id_matches_client_type(device, client), "unauthorized", 401)
    token = conf.get("device_token")
    _need(type(token) is str and bool(token), "unauthorized", 401)
    digest = hashlib.sha256(token.encode()).digest()
    generation = getattr(runtime, "_receiver_end_generation", 0)

    def allowed():
        try:
            return (
                hass.config_entries.async_get_entry(entry_id) is entry
                and _domain(hass).get(entry_id) is runtime
                and runtime.entry is entry
                and entry.data is original_data
                and entry.options is original_options
                and entry.disabled_by is None
                and getattr(entry.state, "value", entry.state) == "loaded"
                and getattr(runtime, "_receiver_end_generation", 0) == generation
                and manager.receiver_entry_generation(entry_id) == generation
                and hashlib.sha256(
                    str(({**entry.data, **entry.options}).get("device_token") or "").encode()
                ).digest()
                == digest
            )
        except Exception:
            return False

    _need(allowed(), "session_context_changed", 409)
    return conf, digest, allowed


def _capture(hass, runtime, session_id, *, owner=None):
    from .domain.storage import ProfilePlatformStorage, STORE_KEY
    from .domain.backend import BackendProvider
    from .profile_privacy import resolve_profile_privacy_policy

    domain = _domain(hass)
    storage = domain.get(STORE_KEY)
    manager = domain.get("session_runtime_manager")
    _need(
        isinstance(storage, ProfilePlatformStorage) and storage._loaded and manager is not None,
        "visual_unavailable",
        503,
    )
    conf, _digest, entry_allowed = _entry_guard(hass, runtime, manager)
    try:
        profile = storage.resolver().resolve_bound_device(conf["device_id"])
    except Exception:
        raise VisualDirectorError("unauthorized", 401) from None
    _need(profile is not None and str(profile.state) == "active", "unauthorized", 401)
    _need(
        str(profile.privacy_mode) in ("normal", "private")
        and resolve_profile_privacy_policy(profile).allow_personal_read,
        "unauthorized",
        401,
    )
    _need(owner is None or profile.profile_id == owner, "unauthorized", 401)
    owner = profile.profile_id
    revision = storage.authority_revision
    active = manager.current_active(owner)
    _need(active is not None and active.session_id == session_id, "session_context_changed", 409)
    _need(active.music_backend == "spotify_direct", "current_playback_unavailable", 503)
    _need((owner, session_id) not in manager._visual_ending, "session_context_changed", 409)
    source = manager._history_source_contexts.get(session_id)
    _need(
        type(source) is dict
        and all(type(source.get(k)) is str and source[k] for k in SOURCE_FIELDS),
        "current_playback_unavailable",
        503,
    )
    source_values = dict(source)
    device_id = conf["device_id"]
    registered = storage.household.music_backends.get(source["backend_id"])
    _need(
        registered is not None and registered.provider == BackendProvider.SPOTIFY_DIRECT,
        "current_playback_unavailable",
        503,
    )
    observers = domain.get("playback_observation_manager")
    observed = getattr(observers, "_spotify_sessions", {}).get(owner)
    _need(
        observed is not None and observed.session_id == session_id,
        "current_playback_unavailable",
        503,
    )
    source_token = observed.visual_source
    broadcast = active.broadcast
    mood = str(active.selected_mood)

    def allowed():
        try:
            current = manager.current_active(owner)
            return (
                entry_allowed()
                and _domain(hass).get(STORE_KEY) is storage
                and storage._loaded
                and storage.authority_revision == revision
                and storage.household.profiles.get(owner) is profile
                and storage.resolver().resolve_bound_device(device_id) is profile
                and _domain(hass).get("session_runtime_manager") is manager
                and current is not None
                and current.session_id == session_id
                and current.broadcast is broadcast
                and current.music_backend == "spotify_direct"
                and (owner, session_id) not in manager._visual_ending
                and manager._history_source_contexts.get(session_id) is source
                and source == source_values
                and _domain(hass).get("playback_observation_manager") is observers
                and observers._spotify_sessions.get(owner) is observed
                and observed.visual_source is source_token
            )
        except Exception:
            return False

    _need(allowed())
    return Admission(
        (hashlib.sha256((runtime.entry.entry_id + "\0" + device_id).encode()).digest(),),
        source_token,
        allowed,
        manager,
        owner,
        session_id,
        observed,
        broadcast,
        mood,
        broadcast.passive_observation_serial,
    )


def capture(hass, data, headers):
    """Authenticate only an already-paired Apple requester; never learn identity."""
    from .client_identity import device_id_matches_client_type

    _need(
        data.get("client_type") in ("ios", "macos")
        and device_id_matches_client_type(data.get("device_id"), data.get("client_type")),
        "unauthorized",
        401,
    )
    for header, key in (
        ("X-DJConnect-Device-ID", "device_id"),
        ("X-DJConnect-Client-Type", "client_type"),
    ):
        _need(not headers.get(header) or headers[header] == data[key], "unauthorized", 401)
    if hasattr(headers, "getall"):
        _need(len(headers.getall("Authorization", [])) == 1, "unauthorized", 401)
    authorization = headers.get("Authorization", "")
    _need(
        type(authorization) is str
        and authorization.startswith("Bearer ")
        and len(authorization) <= 1024,
        "unauthorized",
        401,
    )
    matches = {}
    for value in _domain(hass).values():
        entry = getattr(value, "entry", None)
        conf = {**getattr(entry, "data", {}), **getattr(entry, "options", {})}
        if (
            conf.get("device_id") == data["device_id"]
            and conf.get("client_type") == data["client_type"]
        ):
            matches[id(value)] = value
    _need(len(matches) == 1, "unauthorized", 401)
    runtime = next(iter(matches.values()))
    conf = {**runtime.entry.data, **runtime.entry.options}
    token = conf.get("device_token")
    _need(
        type(token) is str
        and bool(token)
        and hmac.compare_digest(authorization[7:].encode("utf-8"), token.encode("utf-8")),
        "unauthorized",
        401,
    )
    return _capture(hass, runtime, data["session_id"])


def _capture_observer(hass, observed):
    """Capture original source before existing Stage1 provider await; no query."""
    item = engine(hass)
    if item is None or not item.interested(observed.visual_source):
        return None
    try:
        admission = _capture(
            hass, observed.integration_runtime, observed.session_id, owner=observed.owner_profile_id
        )
        from .forecast_imagery import artist_authority

        original = admission.manager._history_source_contexts[observed.session_id]
        source_allowed = artist_authority(
            hass,
            observed.integration_runtime,
            owner_profile_id=admission.owner,
            expected_source=dict(original),
        )
        command = observed.command_revision

        def scope_allowed():
            return admission.authorized() and source_allowed()

        def allowed():
            try:
                current = admission.manager.current_active(admission.owner)
                return (
                    scope_allowed()
                    and observed.command_revision == command
                    and current is not None
                    and str(current.selected_mood) == admission.mood
                )
            except Exception:
                return False

        _need(allowed())
        return Admission(
            admission.actor,
            admission.source,
            allowed,
            admission.manager,
            admission.owner,
            admission.session_id,
            observed,
            admission.broadcast,
            admission.mood,
            admission.previous_sample_serial,
            scope_allowed,
        )
    except VisualDirectorError:
        item.withdraw(observed.visual_source)
        return None


def _accept_observation(hass, observed, result, admission):
    """Only the actual accepted projection may advance an opaque occurrence."""
    item = engine(hass)
    if item is None or admission is None:
        return False
    if not admission.authorized():
        if admission.scope_authorized is not None and admission.scope_authorized():
            item.invalidate_observation(observed.visual_source)
        else:
            item.withdraw(observed.visual_source)
        return False
    sample = getattr(admission.broadcast, "passive_observation", None)
    media = getattr(result, "media_identity", "")
    target_id = getattr(result, "target_id", "")
    # Keep only an integer acceptance serial, never the projection/tuple. A
    # retained old admission or stopped Vibe visit must not retain old media.
    serial = admission.broadcast.passive_observation_serial
    if serial == observed.visual_sample_serial:
        return False  # Reprocessing one accepted sample never renews freshness.
    playback = (
        sample[2] if sample is not None and serial > admission.previous_sample_serial else None
    )
    if (
        not re.fullmatch(r"spotify:track:[A-Za-z0-9]{22}", media)
        or not _string(target_id, 256)
        or playback is None
        or playback.item_id != hashlib.sha256(media.encode()).hexdigest()[:24]
        or (playback.state, playback.title, playback.artist, playback.target_name)
        != (result.state, result.title, result.artist, result.target_name)
    ):
        item.invalidate_observation(observed.visual_source)
        return False
    observed.visual_sample_serial = serial
    occurrence = item.observe(
        admission.source,
        media=media,
        target=hashlib.sha256(target_id.encode("utf-8")).hexdigest(),
        position_ms=result.position_ms,
        state=result.state,
        music={"title": result.title, "artist": result.artist, "mood": admission.mood},
        authorized=admission.authorized,
    )
    return occurrence is not None


def _background_failure(hass):
    item = _domain(hass).get(KEY)
    if isinstance(item, VisualDirector):
        item.invalidate_all()


def capture_observer(hass, observed):
    try:
        return _capture_observer(hass, observed)
    except Exception:
        _background_failure(hass)
        return None


def accept_observation(hass, observed, result, admission):
    try:
        return _accept_observation(hass, observed, result, admission)
    except Exception:
        _background_failure(hass)
        return False


async def handle(hass, kind, data, *, headers):
    try:
        validate_request(kind, data)
        admission = capture(hass, data, headers)
        item = engine(hass, create=kind in ("context", "revoke"))
        _need(item is not None, "visual_context_expired", 410)
        if kind == "context":
            _need(
                admission.manager.register_visual_withdrawal(
                    admission.owner,
                    admission.session_id,
                    admission.source,
                    lambda source=admission.source: item.withdraw(source),
                ),
                "visual_rate_limited",
                429,
            )
            answer = await item.context(
                admission.actor, admission.source, data, authorized=admission.authorized
            )
        elif kind == "interpret":
            answer = await item.interpret(
                admission.actor, admission.source, data, authorized=admission.authorized
            )
        else:
            answer = item.revoke(admission.actor, admission.source, data)
        _need(admission.authorized())
        return answer, 200
    except VisualDirectorError as exc:
        return {"success": False, "schema_version": VERSION, "error": exc.code}, exc.status
    except Exception:
        # Deliberately no exception/body logging and no alternate pipeline.
        return {"success": False, "schema_version": VERSION, "error": "visual_unavailable"}, 503
