"""Ephemeral current-recording fence beside the existing explicit Moment target.

No durable grant, playback command, profile enrichment or alternative model path.
Only actual provider observations advance this bounded one-frame Runtime state.
"""
from __future__ import annotations

import asyncio
import hashlib
from dataclasses import dataclass
import re
import secrets
import time
from typing import Any

from .const import DEFAULT_MUSIC_BACKEND, MUSIC_BACKEND_SPOTIFY_DIRECT

TTL_SECONDS = 30
_SELECTOR = {"schema_version": 1, "mode": "current"}
_URI = re.compile(r"spotify:track:[A-Za-z0-9]{22}")
_MESSAGES = {
    "invalid_track_insight_subject": {
        "en": "Choose either the current recording or a specific contribution.",
        "nl": "Kies de huidige opname of een specifieke bijdrage.",
        "de": "Wähle die aktuelle Aufnahme oder einen bestimmten Beitrag.",
        "fr": "Choisissez l’enregistrement actuel ou une contribution précise.",
        "es": "Elige la grabación actual o una contribución concreta.",
    },
    "current_track_unavailable": {
        "en": "The current recording could not be verified. Try again shortly.",
        "nl": "De huidige opname kon niet worden gecontroleerd. Probeer het zo opnieuw.",
        "de": "Die aktuelle Aufnahme konnte nicht geprüft werden. Versuche es gleich erneut.",
        "fr": "L’enregistrement actuel n’a pas pu être vérifié. Réessayez dans un instant.",
        "es": "No se pudo verificar la grabación actual. Inténtalo de nuevo en un momento.",
    },
    "track_insight_context_changed": {
        "en": "The recording or its context changed. Open the current recording again.",
        "nl": "De opname of de context is veranderd. Open de huidige opname opnieuw.",
        "de": "Die Aufnahme oder ihr Kontext hat sich geändert. Öffne die aktuelle Aufnahme erneut.",
        "fr": "L’enregistrement ou son contexte a changé. Ouvrez à nouveau l’enregistrement actuel.",
        "es": "La grabación o su contexto ha cambiado. Abre de nuevo la grabación actual.",
    },
}


def _error(code, locale, status):
    from .track_insight import TrackInsightError
    language = str(locale or "en").lower().replace("_", "-").split("-", 1)[0]
    return TrackInsightError(code, _MESSAGES[code].get(language, _MESSAGES[code]["en"]), status=status)


def requested(payload, locale):
    """A closed selector is independent of all legacy metadata/target overrides."""
    if "track_insight_subject" not in payload:
        return False
    value = payload["track_insight_subject"]
    if (not isinstance(value, dict) or value != _SELECTOR
            or type(value.get("schema_version")) is not int
            or any(key in payload for key in (
                "title", "track_name", "media_title", "name", "track", "artist", "artist_name", "media_artist", "artists",
                "album", "album_name", "media_album_name", "media_album", "playback", "media",
                "entity_id", "player_id", "music_backend", "backend", "provider", "uri", "media_identity",
                "track_insight_target", "conversation_context"))):
        raise _error("invalid_track_insight_subject", locale, 400)
    return True


@dataclass(eq=False)
class _Frame:
    uri: str
    state: str
    output: str
    position: int | None
    observed_at: float
    observation_id: str
    expires_at: float


def observe(runtime, uri, state, position, output="", *, new_context=False):
    """Record one accepted observation, including A→B→A, pause and replay/seek.

    Normal position progress and repeated reads never extend the original frame.
    Expired frames require an actual new observation and obtain a fresh identity.
    """
    now = time.monotonic()
    previous = getattr(runtime, "_current_insight_frame", None)
    position = position if type(position) is int and position >= 0 else None
    if (new_context or not isinstance(previous, _Frame) or (uri, state, output) != (previous.uri, previous.state, previous.output)
            or (position is not None and previous.position is not None and position < previous.position - 5000)
            or now - previous.observed_at >= TTL_SECONDS):
        previous = _Frame(str(uri), str(state), str(output), position, now, secrets.token_urlsafe(18), time.time() + TTL_SECONDS)
        runtime._current_insight_frame = previous
    elif position is not None:
        previous.position = position
    return previous


def _runtime_value(runtime):
    playback = getattr(runtime, "last_playback", None)
    playback = playback if isinstance(playback, dict) else {}
    device = playback.get("device")
    device = device if isinstance(device, dict) else {}
    return (str(playback.get("uri") or ""),
            "playing" if playback.get("is_playing") else "paused" if playback.get("uri") else "idle",
            playback.get("progress_ms"), str(device.get("name") or ""))


def observe_runtime_playback(runtime):
    """Consume changed normal Runtime playback; unrelated updates are not reads."""
    if not getattr(runtime, "_current_insight_requested", False):
        return
    value = _runtime_value(runtime)
    if value != getattr(runtime, "_current_insight_runtime_value", None):
        runtime._current_insight_runtime_value = value
        observe(runtime, *value)


@dataclass
class CurrentSubject:
    runtime: Any
    frame: _Frame
    backend: Any
    track: dict
    validate_owner: Any
    source_scope: Any
    scope: tuple
    locale: str | None
    observed: Any
    original_deadline: float
    knowledge_authority: Any = None

    def guard(self):
        if self.validate_owner is not None:
            self.validate_owner()
        try:
            same_scope = self.source_scope() == self.scope
        except Exception as exc:
            raise _error("track_insight_context_changed", self.locale, 409) from exc
        if (getattr(self.runtime, "_current_insight_frame", None) is not self.frame
                or not same_scope or time.monotonic() >= self.original_deadline):
            raise _error("track_insight_context_changed", self.locale, 409)

    async def verify(self):
        """Fresh read before response/cache; no stale fallback and no clock renewal."""
        self.guard()
        try:
            observed = await asyncio.wait_for(self.backend.async_observe_current_playback(), timeout=3)
        except Exception as exc:
            self.guard()
            raise _error("current_track_unavailable", self.locale, 503) from exc
        self.guard()
        observe(self.runtime, observed.media_identity, observed.state, observed.position_ms, observed.target_name)
        self.guard()
        if (observed.title, observed.artist, observed.album) != (self.observed.title, self.observed.artist, self.observed.album):
            raise _error("track_insight_context_changed", self.locale, 409)

    def limit_deadline(self, deadline):
        self.original_deadline = min(self.original_deadline, deadline)
        self.guard()

    def subject(self):
        self.guard()
        return {"mode": "current", "schema_version": 1, "media_identity": self.frame.uri,
                "observation_id": self.frame.observation_id,
                "expires_at": self.frame.expires_at - (self.frame.observed_at + TTL_SECONDS - self.original_deadline),
                "expires_in": max(0, int(self.original_deadline - time.monotonic()))}


async def resolve(hass, runtime, request, *, owner_profile_id, validate_owner):
    """Resolve actual current Spotify recording, also outside an active Session."""
    from .discovery_artwork import runtime_scope, credential_cache_scope
    from .session_runtime import session_runtime_manager
    from .spotify_backend import SpotifyBackend
    from .track_insight import _track_contract
    if validate_owner is not None:
        validate_owner()
    from .domain.backend import BackendProvider
    from .domain.storage import STORE_KEY
    selected = (getattr(runtime, "profile_context_backend_id", "")
                or runtime.config.get("music_backend") or DEFAULT_MUSIC_BACKEND)
    platform = getattr(hass, "data", {}).get("djconnect", {}).get(STORE_KEY)
    registered = getattr(getattr(platform, "household", None), "music_backends", {}).get(selected)
    if selected != MUSIC_BACKEND_SPOTIFY_DIRECT and not (
            registered is not None and registered.provider == BackendProvider.SPOTIFY_DIRECT
            and str(registered.state) == "active"):
        raise _error("current_track_unavailable", request.locale, 503)
    manager = session_runtime_manager(hass) if owner_profile_id else None
    def source_scope():
        active = manager.current_active(owner_profile_id) if manager else None
        opportunity = manager._intra_track_opportunities.get(owner_profile_id) if manager else None
        return (runtime_scope(runtime), credential_cache_scope(runtime), id(active), id(opportunity),
                getattr(opportunity, "generation", None),
                tuple(sorted(manager._history_source_contexts.get(active.session_id, {}).items())) if active else (),
                tuple(getattr(active, key, None) for key in ("mood_revision", "persona_revision", "settings_revision")))
    scope = source_scope()
    if not getattr(runtime, "_current_insight_requested", False):
        # Existing last_playback is a baseline, never a fresh observation.
        runtime._current_insight_runtime_value = _runtime_value(runtime)
    runtime._current_insight_requested = True
    previous = getattr(runtime, "_current_insight_frame", None)
    backend = SpotifyBackend(hass, runtime)
    try:
        observed = await asyncio.wait_for(backend.async_observe_current_playback(), timeout=3)
    except Exception as exc:
        if validate_owner is not None:
            validate_owner()
        raise _error("current_track_unavailable", request.locale, 503) from exc
    if validate_owner is not None:
        validate_owner()
    if source_scope() != scope or getattr(runtime, "_current_insight_frame", None) is not previous:
        raise _error("track_insight_context_changed", request.locale, 409)
    if (not _URI.fullmatch(observed.media_identity) or observed.state not in {"playing", "paused"}
            or not observed.title or not observed.artist):
        # Accept idle/non-track evidence only to withdraw older in-flight frames.
        observe(runtime, observed.media_identity, observed.state, observed.position_ms, observed.target_name)
        raise _error("current_track_unavailable", request.locale, 404)
    scope_fingerprint = hashlib.sha256(repr(scope).encode()).hexdigest()
    frame = observe(runtime, observed.media_identity, observed.state, observed.position_ms, observed.target_name,
                    new_context=getattr(runtime, "_current_insight_source_scope", None) != scope_fingerprint)
    runtime._current_insight_source_scope = scope_fingerprint
    track = _track_contract({"uri": observed.media_identity, "title": observed.title, "artist": observed.artist,
                            "album": observed.album, "artwork_url": observed.artwork_url,
                            "duration_ms": observed.duration_ms, "progress_ms": observed.position_ms,
                            "is_playing": observed.is_playing, "provider": MUSIC_BACKEND_SPOTIFY_DIRECT}, runtime, request)
    result = CurrentSubject(runtime, frame, backend, track, validate_owner, source_scope, scope, request.locale,
                            observed, frame.observed_at + TTL_SECONDS)
    result.guard()
    result.knowledge_authority = original_source_authority(hass, runtime, owner_profile_id)
    def authorize_genres():
        result.guard()
        return True
    # Reuse the existing display-only, exact-artist source path. Catalog genres
    # never become model input, audio measurements or durable Profile writes.
    evidence = await backend.async_observe_current_genres(observed, authorize=authorize_genres)
    result.guard()
    expiry = evidence.get("genre_source_expires_at")
    if (evidence.get("genres") and isinstance(expiry, (int, float))
            and expiry > time.monotonic()):
        result.track["genres"] = evidence["genres"]
        result.limit_deadline(expiry)
    return result


def original_source_authority(hass, runtime, owner_profile_id):
    """Capture original Session-source rights before any current-track lookup.

    Shared by the closed selector and ordinary no-selection current requests.
    This source check grants no model input on its own; qualified facts, exact
    recording, current opportunity, privacy and original expiry remain required.
    """
    from .session_runtime import session_runtime_manager
    from .forecast_imagery import artist_authority
    manager = session_runtime_manager(hass) if owner_profile_id else None
    active = manager.current_active(owner_profile_id) if manager else None
    captured = dict(manager._history_source_contexts.get(active.session_id, {})) if active else {}
    keys = {"backend_id", "music_account_id", "provider_entry_id", "provider_account_id"}
    if active is None or not keys <= captured.keys():
        return lambda: False
    authority = artist_authority(hass, runtime, owner_profile_id=owner_profile_id, expected_source=captured)
    def allowed():
        return (manager.current_active(owner_profile_id) is active
                and manager._history_source_contexts.get(active.session_id) == captured
                and authority())
    return allowed
