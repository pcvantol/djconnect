"""Bounded process-memory Visual Director. No HA, providers, stores or logs.

Interpretation is an allowlisted visual grammar, never a general agent. Native
STT/renderer/scene/undo state stay client-owned; interpreted is never applied.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime
import json
import math
import secrets
import time
import unicodedata
import uuid

VERSION = 1
BODY_LIMIT = 8192
TEXT_LIMIT = 1024
LEASE_SECONDS = 15
VISIT_SECONDS = 1800
OBSERVATION_SECONDS = 20
FIELDS = frozenset(("palette", "motion", "depth", "roughness", "deformation"))
IDENTITY = frozenset(("schema_version", "client_type", "device_id", "session_id", "visit_id"))
INTERPRET = IDENTITY | {
    "client_turn_id",
    "base_scene_revision",
    "context_lease_id",
    "observed_occurrence_id",
    "text",
    "active_scene",
    "dynamics_bias",
    "scope",
}
HEADERS = {"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"}


class VisualDirectorError(ValueError):
    """Allowlisted code only; never attach request text or context."""

    def __init__(self, code, status=400):
        self.code, self.status = code, status
        super().__init__(code)


def _require(ok, code="invalid_request", status=400):
    if not ok:
        raise VisualDirectorError(code, status)


def _string(value, limit):
    try:
        return (
            type(value) is str
            and bool(value.strip())
            and len(value.encode("utf-8", errors="strict")) <= limit
            and not any(ord(c) < 32 or ord(c) == 127 for c in value)
        )
    except UnicodeError:
        return False


def _uuid(value):
    if type(value) is not str:
        return False
    try:
        return str(uuid.UUID(value)) == value.lower()
    except ValueError:
        return False


def _number(value):
    return type(value) in (int, float) and math.isfinite(value) and 0 <= value <= 1


def parse_body(raw):
    """Byte-bound before decode; reject duplicate keys, nonfinite and deep trees."""
    _require(type(raw) is bytes and len(raw) <= BODY_LIMIT)

    def pairs(items):
        result = {}
        for key, value in items:
            _require(key not in result)
            result[key] = value
        return result

    def constant(_value):
        raise VisualDirectorError("invalid_request")

    def walk(value, depth=0):
        _require(depth <= 12)
        if type(value) is float:
            _require(math.isfinite(value))
        elif isinstance(value, dict):
            for child in value.values():
                walk(child, depth + 1)
        elif isinstance(value, list):
            for child in value:
                walk(child, depth + 1)

    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=pairs, parse_constant=constant)
        _require(type(value) is dict)
        walk(value)
        return value
    except (UnicodeError, ValueError, RecursionError):
        raise VisualDirectorError("invalid_request") from None


def validate_request(kind, data):
    try:
        _require(kind in {"context", "interpret", "revoke"} and type(data) is dict)
        _require(set(data) == (INTERPRET if kind == "interpret" else IDENTITY))
        _require(type(data["schema_version"]) is int and data["schema_version"] == VERSION)
        _require(data["client_type"] in ("ios", "macos") and _uuid(data["visit_id"]))
        _require(all(_string(data[k], 256) for k in ("device_id", "session_id")))
        if kind == "interpret":
            _require(
                _uuid(data["client_turn_id"])
                and type(data["base_scene_revision"]) is int
                and 0 <= data["base_scene_revision"] <= 2147483647
            )
            _require(
                all(_string(data[k], 256) for k in ("context_lease_id", "observed_occurrence_id"))
            )
            _require(_string(data["text"], TEXT_LIMIT) and _number(data["dynamics_bias"]))
            _require(data["scope"] in ("current_track", "while_in_vibescape"))
            scene = data["active_scene"]
            _require(type(scene) is dict and set(scene) == FIELDS)
            _require(
                type(scene["palette"]) is list
                and len(scene["palette"]) == 3
                and all(_number(x) for x in scene["palette"])
            )
            _require(all(_number(scene[k]) for k in FIELDS - {"palette"}))
    except (KeyError, TypeError, UnicodeError):
        raise VisualDirectorError("invalid_request") from None


def _normalized(text):
    folded = "".join(
        c for c in unicodedata.normalize("NFKD", text.casefold()) if not unicodedata.combining(c)
    )
    # Preserve unknown lexical content so unsupported scripts cannot disappear.
    return " ".join("".join(c if c.isalnum() or c.isspace() else " " for c in folded).split())


# Exact closed controls prevent a visual keyword from swallowing a music clause.
_CONTROL_TEXT = {
    "undo": (
        "ga terug naar hoe het net was",
        "ga een stap terug",
        "undo",
        "go back",
        "ruckgangig",
        "zuruck wie vorher",
        "annuler",
        "revenir en arriere",
        "deshacer",
        "volver atras",
    ),
    "reset": (
        "terug naar de dj",
        "volg dj",
        "reset to dj",
        "follow dj",
        "zuruck zum dj",
        "retour au dj",
        "volver al dj",
    ),
    "variant": (
        "maak een variant",
        "andere compositie",
        "make a variant",
        "another composition",
        "eine variante",
        "andere komposition",
        "une variante",
        "autre composition",
        "una variante",
        "otra composicion",
    ),
    "hold": (
        "hou deze stijl aan maar blijf varieren per nummer",
        "houd deze stijl aan",
        "hou deze stijl aan",
        "keep this style but vary each track",
        "keep this style",
        "diesen stil beibehalten",
        "garde ce style",
        "mantener este estilo",
    ),
}
_CONTROLS = {_normalized(t): k for k, texts in _CONTROL_TEXT.items() for t in texts}
_SCOPE_TEXT = {
    "current_track": (
        "alleen dit nummer",
        "only this track",
        "nur dieses lied",
        "seulement ce morceau",
        "solo esta cancion",
    ),
    "while_in_vibescape": (
        "hele verblijf",
        "zolang ik hier ben",
        "this whole visit",
        "wahrend dieses besuchs",
        "pendant cette visite",
        "durante esta visita",
    ),
}
_LEXICON = {
    "calm": {"rustiger", "calmer", "ruhiger", "calme", "tranquilo", "tranquila"},
    "fluid": {"vloeibaarder", "fluid", "flussiger", "fluide", "fluido", "fluida"},
    "fast": {"sneller", "faster", "schneller", "rapide", "rapido"},
    "depth": {"diepte", "depth", "tiefe", "profondeur", "profundidad"},
    "gold": {"goud", "gold", "dore", "or", "dorado", "oro"},
    "more": {"meer", "more", "mehr", "plus", "mas"},
    "less": {"minder", "less", "weniger", "moins", "menos"},
}
_FILLER = set(
    "maak het wat en iets nee wel een beetje make it a bit and no mach es etwas und et un peu de y haz lo mas".split()
)
_ALLOWED = _FILLER | set().union(*_LEXICON.values())


def interpret_visual(text, scene, scope):
    """Pure bounded grammar. Unknown or mixed intent has no fallback or effect."""
    normalized = _normalized(text)
    scopes = set()
    for choice, phrases in _SCOPE_TEXT.items():
        for phrase in phrases:
            token = _normalized(phrase)
            if token in normalized:
                scopes.add(choice)
                normalized = normalized.replace(token, " ")
    normalized = " ".join(normalized.split())
    _require(len(scopes) <= 1, "visual_direction_ambiguous", 422)
    scope = next(iter(scopes), scope)
    if normalized in _CONTROLS:
        kind = _CONTROLS[normalized]
        if kind == "hold":
            _require(not scopes or scope == "while_in_vibescape", "visual_direction_ambiguous", 422)
            return {"kind": kind, "scope": "while_in_vibescape"}
        return {"kind": kind}
    if normalized in {
        "doe dat maar anders",
        "do it differently",
        "mach es anders",
        "fais autrement",
        "hazlo diferente",
    }:
        raise VisualDirectorError("visual_direction_ambiguous", 422)
    # A single unrecognized word rejects the whole mixed statement.
    words = normalized.split()
    _require(words and all(w in _ALLOWED for w in words), "visual_only_unsupported", 422)
    _require("no" not in words, "visual_only_unsupported", 422)
    tags = {name for name, terms in _LEXICON.items() if terms.intersection(words)}
    # Unsupported inverse motion/fluid comparisons must never become the
    # positive instruction, even when filler separates the comparative.
    _require(
        not ("less" in tags and {"calm", "fast", "fluid"}.intersection(tags)),
        "visual_direction_ambiguous",
        422,
    )
    _require(not {"calm", "fast"} <= tags, "visual_direction_ambiguous", 422)
    patch = {}
    if "calm" in tags:
        patch["motion"] = round(scene["motion"] * 0.7, 6)
    if "fast" in tags:
        patch["motion"] = min(1.0, round(scene["motion"] + 0.15, 6))
    if "fluid" in tags:
        patch["roughness"] = round(scene["roughness"] * 0.75, 6)
        patch["deformation"] = min(1.0, round(scene["deformation"] + 0.1, 6))
    # Clause-local comparative avoids making 'less gold, more depth' both less.
    for concept, field_name in [("gold", "palette"), ("depth", "depth")]:
        indices = [i for i, word in enumerate(words) if word in _LEXICON[concept]]
        if not indices:
            continue
        directions = set()
        for index in indices:
            preceding = words[max(0, index - 2) : index]
            signs = {sign for sign in ("more", "less") if _LEXICON[sign].intersection(preceding)}
            _require(len(signs) == 1, "visual_direction_ambiguous", 422)
            directions.update(signs)
        _require(len(directions) == 1, "visual_direction_ambiguous", 422)
        less = "less" in directions
        if concept == "gold":
            target = (0.55, 0.60, 0.65) if less else (0.9, 0.7, 0.2)
            patch[field_name] = [
                round(0.72 * x + 0.28 * y, 6)
                for x, y in zip(scene[field_name], target, strict=True)
            ]
        else:
            patch[field_name] = min(
                1.0, max(0.0, round(scene[field_name] + (-0.15 if less else 0.15), 6))
            )
    _require(patch, "visual_direction_ambiguous", 422)
    return {"kind": "patch", "scope": scope, "patch": patch}


@dataclass(eq=False)
class _Observation:
    occurrence: str
    identity: tuple
    music: dict
    updated: float
    position: float | None
    state: str
    authorized: object
    valid: bool = True
    timer: object = None


@dataclass(eq=False)
class _Visit:
    actor: object
    source: object
    identifier: str
    deadline: float
    authorized: object
    valid: bool = True
    turns: set = field(default_factory=set)
    revision: int = -1
    inflight: str | None = None
    timer: object = None


@dataclass(eq=False)
class _Lease:
    visit: _Visit
    observation: _Observation
    source_authorized: object
    deadline: float
    expires_at: str
    timer: object = None


class VisualDirector:
    """Finite RAM admissions/tombstones, no transcript, scene or reply history."""

    maximum_visits = 256
    maximum_observations = 256

    def __init__(self, *, clock=time.monotonic, epoch=time.time, call_later="event_loop"):
        self.clock, self.epoch, self.call_later = clock, epoch, call_later
        self.observations, self.visits, self.leases = {}, {}, {}
        self.last_clock = 0.0
        self.yield_once = lambda: asyncio.sleep(0)

    def _now(self):
        now = self.clock()
        if not (type(now) in (int, float) and math.isfinite(now) and now >= self.last_clock):
            self.invalidate_all()
            raise VisualDirectorError("visual_context_expired", 410)
        self.last_clock = now
        return now

    def _schedule(self, delay, callback):
        if self.call_later is None:
            return None
        timer = (
            asyncio.get_running_loop().call_later
            if self.call_later == "event_loop"
            else self.call_later
        )
        return timer(max(0.0, delay), callback)

    @staticmethod
    def _cancel(timer):
        if timer is not None:
            timer.cancel()

    def _drop_lease(self, identifier):
        lease = self.leases.pop(identifier, None)
        if lease:
            self._cancel(lease.timer)

    def _retire(self, visit):
        visit.valid = False
        visit.authorized = None
        visit.inflight = None
        visit.turns.clear()
        for identifier, lease in list(self.leases.items()):
            if lease.visit is visit:
                self._drop_lease(identifier)
        if not any(v.valid and v.source is visit.source for v in self.visits.values()):
            observation = self.observations.pop(visit.source, None)
            if observation:
                observation.valid = False
                observation.music.clear()
                observation.authorized = None
                self._cancel(observation.timer)

    def _expire_visit(self, key, visit):
        if self.visits.get(key) is visit:
            self._retire(visit)
            self._cancel(visit.timer)
            # Keep the expired admission as an opaque bounded tombstone for a
            # second visit window; the first post-expiry poll cannot rearm it.
            remaining = visit.deadline + VISIT_SECONDS - self.clock()
            if remaining <= 0:
                self.visits.pop(key, None)
            else:
                visit.timer = self._schedule(remaining, lambda: self._expire_visit(key, visit))

    def sweep(self):
        now = self._now()
        for identifier, lease in list(self.leases.items()):
            if now >= lease.deadline:
                self._drop_lease(identifier)
        for key, visit in list(self.visits.items()):
            if now >= visit.deadline and (visit.valid or now >= visit.deadline + VISIT_SECONDS):
                # Do not remove a still-live tombstone to admit a new visit.
                self._expire_visit(key, visit)
        for source, observed in list(self.observations.items()):
            if now >= observed.updated + OBSERVATION_SECONDS:
                self.invalidate_observation(source)

    def interested(self, source):
        self.sweep()
        return any(visit.valid and visit.source is source for visit in self.visits.values())

    def invalidate_all(self):
        # Drop source/music/authorization immediately; retain only bounded
        # original-admission tombstones so teardown cannot rearm a late turn.
        for visit in list(self.visits.values()):
            self._retire(visit)
        for source in list(self.observations):
            self.withdraw(source)
        for identifier in list(self.leases):
            self._drop_lease(identifier)

    def invalidate_observation(self, source):
        """Missing playback clears media, not the original visit budget/clock."""
        observed = self.observations.pop(source, None)
        if observed:
            observed.valid = False
            observed.music.clear()
            observed.authorized = None
            self._cancel(observed.timer)

    def withdraw(self, source):
        for visit in list(self.visits.values()):
            if visit.source is source:
                self._retire(visit)
        observed = self.observations.pop(source, None)
        if observed:
            observed.valid = False
            observed.music.clear()
            observed.authorized = None
            self._cancel(observed.timer)

    def observe(self, source, *, media, target, position_ms, state, music, authorized):
        """Accepted actual observation only; never claim unobserved replay."""
        self.sweep()
        if not authorized():
            self.withdraw(source)
            return None
        if (
            not _string(media, 256)
            or not _string(target, 256)
            or state not in ("playing", "paused")
            or not all(_string(music.get(k), 256) for k in ("title", "artist"))
            or music.get("mood") not in ("chill", "groove", "energy", "party")
        ):
            self.invalidate_observation(source)
            return None
        now = self._now()
        previous = self.observations.get(source)
        position = (
            position_ms
            if type(position_ms) in (int, float) and math.isfinite(position_ms) and position_ms >= 0
            else None
        )
        discontinuity = False
        if previous and position is not None and previous.position is not None:
            expected = previous.position + (
                (now - previous.updated) * 1000 if previous.state == "playing" else 0
            )
            discontinuity = abs(position - expected) > 5000
        if previous and (previous.identity != (media, target) or discontinuity):
            previous.valid = False
            previous.music.clear()
            previous.authorized = None
            self._cancel(previous.timer)
            for identifier, lease in list(self.leases.items()):
                if lease.observation is previous:
                    # Retain only original lease/token until its <=15s expiry,
                    # allowing precise changed-versus-expired failure; no music.
                    self._cancel(lease.observation.timer)
            previous = None
        if previous is None:
            if len(self.observations) >= self.maximum_observations:
                return None
            previous = _Observation(
                secrets.token_urlsafe(24), (media, target), {}, now, position, state, authorized
            )
            self.observations[source] = previous
        self._cancel(previous.timer)
        previous.music = {
            "basis": "authorized_current_observation_and_selected_session_mood",
            "recording": {"title": music["title"], "artist": music["artist"]},
            "symbolic_session_mood": music["mood"],
            "genres": [],
            "audio_features": None,
        }
        previous.updated, previous.position, previous.state, previous.authorized = (
            now,
            position,
            state,
            authorized,
        )

        def expire():
            if (
                self.observations.get(source) is previous
                and self.clock() >= previous.updated + OBSERVATION_SECONDS
            ):
                self.invalidate_observation(source)

        previous.timer = self._schedule(OBSERVATION_SECONDS, expire)
        return previous.occurrence

    def _visit(self, actor, source, data, authorized):
        validate_request("context", data)
        self.sweep()
        _require(authorized(), "session_context_changed", 409)
        key = (actor, data["visit_id"].lower())
        visit = self.visits.get(key)
        if visit is None:
            _require(len(self.visits) < self.maximum_visits, "visual_rate_limited", 429)
            visit = _Visit(
                actor, source, data["visit_id"].lower(), self._now() + VISIT_SECONDS, authorized
            )
            self.visits[key] = visit
            visit.timer = self._schedule(VISIT_SECONDS, lambda: self._expire_visit(key, visit))
        _require(visit.valid and self._now() < visit.deadline, "visual_context_expired", 410)
        _require(visit.source is source, "visual_context_changed", 409)
        _require(visit.authorized(), "session_context_changed", 409)
        return key, visit

    async def context(self, actor, source, data, *, authorized):
        key, visit = self._visit(actor, source, data, authorized)
        observed = self.observations.get(source)
        _require(
            observed is not None and observed.valid and observed.authorized(),
            "current_playback_unavailable",
            503,
        )
        await self.yield_once()
        _require(
            self.visits.get(key) is visit and visit.valid and self._now() < visit.deadline,
            "visual_context_expired",
            410,
        )
        _require(authorized() and visit.authorized(), "session_context_changed", 409)
        _require(
            self.observations.get(source) is observed and observed.valid and observed.authorized(),
            "visual_context_changed",
            409,
        )
        _require(
            len(self.leases) < 1024
            and sum(
                lease.visit is visit and lease.observation.valid for lease in self.leases.values()
            )
            < 4,
            "visual_rate_limited",
            429,
        )
        duration = min(
            LEASE_SECONDS,
            observed.updated + OBSERVATION_SECONDS - self._now(),
            visit.deadline - self._now(),
        )
        _require(duration > 0, "visual_context_expired", 410)
        duration_ms = int(duration * 1000)
        _require(duration_ms > 0, "visual_context_expired", 410)
        issued = self.epoch()
        issued_at = datetime.fromtimestamp(issued, UTC).isoformat().replace("+00:00", "Z")
        expires_at = (
            datetime.fromtimestamp(issued + duration_ms / 1000, UTC)
            .isoformat()
            .replace("+00:00", "Z")
        )
        identifier = secrets.token_urlsafe(24)
        lease = _Lease(
            visit, observed, observed.authorized, self._now() + duration_ms / 1000, expires_at
        )
        self.leases[identifier] = lease
        lease.timer = self._schedule(duration_ms / 1000, lambda: self._drop_lease(identifier))
        return {
            "success": True,
            "schema_version": VERSION,
            "visit_id": data["visit_id"],
            "context_lease_id": identifier,
            "observed_occurrence_id": observed.occurrence,
            "issued_at": issued_at,
            "expires_at": expires_at,
            "lease_duration_ms": duration_ms,
            "music_context": json.loads(json.dumps(observed.music)),
        }

    def revoke(self, actor, source, data):
        validate_request("revoke", data)
        self.sweep()
        key = (actor, data["visit_id"].lower())
        visit = self.visits.get(key)
        if visit is None:
            _require(len(self.visits) < self.maximum_visits, "visual_rate_limited", 429)
            visit = _Visit(
                actor,
                source,
                data["visit_id"].lower(),
                self._now() + VISIT_SECONDS,
                None,
                valid=False,
            )
            self.visits[key] = visit
            visit.timer = self._schedule(VISIT_SECONDS, lambda: self._expire_visit(key, visit))
        self._retire(visit)
        return {
            "success": True,
            "schema_version": VERSION,
            "visit_id": data["visit_id"],
            "status": "revoked",
        }

    def _admit_turn(self, actor, source, data, authorized):
        self.sweep()
        _require(authorized(), "session_context_changed", 409)
        lease = self.leases.get(data["context_lease_id"])
        _require(lease is not None and self._now() < lease.deadline, "visual_context_expired", 410)
        visit, observation = lease.visit, lease.observation
        _require(visit.valid and self._now() < visit.deadline, "visual_context_expired", 410)
        _require(
            visit.actor == actor
            and visit.source is source
            and visit.identifier == data["visit_id"].lower(),
            "visual_context_changed",
            409,
        )
        _require(visit.authorized(), "session_context_changed", 409)
        _require(
            observation.valid
            and self.observations.get(source) is observation
            and observation.occurrence == data["observed_occurrence_id"],
            "visual_context_changed",
            409,
        )
        _require(
            lease.source_authorized() and observation.authorized(), "session_context_changed", 409
        )
        return lease

    async def interpret(self, actor, source, data, *, authorized):
        validate_request("interpret", data)
        lease = self._admit_turn(actor, source, data, authorized)
        visit = lease.visit
        turn, revision = data["client_turn_id"].lower(), data["base_scene_revision"]
        _require(
            turn not in visit.turns and revision >= visit.revision, "visual_context_changed", 409
        )
        _require(len(visit.turns) < 32, "visual_turn_limit_reached", 429)
        visit.turns.add(turn)
        visit.revision, visit.inflight = revision, turn
        await self.yield_once()
        self._admit_turn(actor, source, data, authorized)
        _require(visit.inflight == turn, "visual_context_changed", 409)
        visit.inflight = None
        directive = interpret_visual(data["text"], data["active_scene"], data["scope"])
        return {
            "success": True,
            "schema_version": VERSION,
            "status": "interpreted",
            **{
                k: data[k]
                for k in (
                    "visit_id",
                    "client_turn_id",
                    "base_scene_revision",
                    "context_lease_id",
                    "observed_occurrence_id",
                )
            },
            "expires_at": lease.expires_at,
            "directive": directive,
            "effect_code": "visual_"
            + ("patch" if directive["kind"] == "patch" else directive["kind"]),
        }
