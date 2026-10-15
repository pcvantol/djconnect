"""Dynamic native display admission; semantic Moments stay immutable.

Only existing field-qualified normalized facts and Runtime-authored context
are admitted. No provider access, payload interpretation or action execution.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
import hashlib
import json
import math
from typing import Any

from .session_facts import QualifiedSessionFact, SharedProducerFact, AlbumContinuityFact


@dataclass(frozen=True)
class MomentDeliveryBoundary:
    """Original publication clocks, never renewed by reads or reconnect."""

    published_monotonic: float
    published_at: str
    playback_item_id: str
    track_snapshot: tuple[tuple[str, Any], ...] = ()
    persona_revision: int | None = None

    def utc_at(self, deadline: float) -> str:
        return (datetime.fromisoformat(self.published_at) + timedelta(
            seconds=deadline - self.published_monotonic)).isoformat()


def source_deadline(fact: QualifiedSessionFact) -> float:
    observations = [fact.observed_at]
    if isinstance(fact, SharedProducerFact) and fact.previous_evidence is not None:
        observations.append(fact.previous_evidence.observed_at)
    if isinstance(fact, AlbumContinuityFact) and fact.previous_album is not None:
        observations.append(fact.previous_album.observed_at)
    deadline = min(observations) + 1800
    return min(deadline, fact.source_expires_at) if fact.source_expires_at is not None else deadline


def admission(moment: Any, boundary: MomentDeliveryBoundary | None, *,
              session_id: str, active: bool, flow_ids: set[str],
              playback_item_id: str, playing: bool, now: float) -> dict[str, Any]:
    """Fail closed without inferring provenance from rendered text or names."""
    result = {
        "moment_id": moment.moment_id,
        "qualification": "unqualified",
        "current_display_allowed": False,
        "active_flow_display_allowed": False,
        "source_expires_at": None,
        "display_expires_at": None,
        "executable_actions": [],
        "requires_spotify_attribution": False,
    }
    if boundary is None or moment.session_id != session_id or not active:
        return result
    try:
        stamp = datetime.fromisoformat(boundary.published_at)
        duration = moment.presentation_intent.maximum_duration_seconds
        if stamp.tzinfo is None or not isinstance(duration, int) or not 0 < duration <= 90:
            return result
        if not math.isfinite(now) or not math.isfinite(boundary.published_monotonic) or now < boundary.published_monotonic:
            return result
        deadline = boundary.published_monotonic + duration
    except (TypeError, ValueError, OverflowError):
        return result
    source = getattr(moment, 'source_fact', None)
    history_allowed = False
    if isinstance(source, QualifiedSessionFact):
        try:
            source_limit = source_deadline(source)
            result['source_expires_at'] = boundary.utc_at(source_limit)
            if now >= source_limit:
                result['qualification'] = 'expired'
                return result
            attributes = dict(moment.source_attribution)
            expected = {'provider': source.provider, 'url': source.source_url, 'license': source.license}
            if isinstance(source, SharedProducerFact) and source.previous_evidence:
                expected['url_previous'] = source.previous_evidence.source_url
            if not source.eligible(source.media_identity, now) or attributes != expected:
                return result
            bound_identity = hashlib.sha256(source.media_identity.encode()).hexdigest()[:24]
            if bound_identity != boundary.playback_item_id:
                return result
            history_allowed = source.provider in {'MusicBrainz', 'Wikidata'} and source.license == 'CC0-1.0'
            result['requires_spotify_attribution'] = source.provider == 'Spotify'
            deadline = min(deadline, source_limit)
        except (AttributeError, TypeError, ValueError, OverflowError):
            return result
    elif getattr(moment, 'genre_transition', None) is not None:
        from .session_runtime import GenreTransitionNarration
        from .context_expression import transition_copy
        proof = moment.genre_transition
        if not isinstance(proof, GenreTransitionNarration):
            return result
        source_limit = min(source_deadline(proof.earlier), proof.current.observed_at+30)
        result['source_expires_at'] = boundary.utc_at(source_limit)
        if not proof.eligible(now):
            result['qualification'] = 'expired'
            return result
        snapshot, metadata = dict(boundary.track_snapshot), dict(moment.generation_metadata)
        if (moment.moment_type.value != 'transition' or moment.knowledge_intent.intent_type.value != 'transition'
                or moment.source_references != ('session_flow',)
                or metadata.get('relation') != 'discover_same_artist_genre'
                or metadata.get('transition_from_moment_id') != proof.source_moment_id
                or metadata.get('transition_to_moment_id') != proof.target_moment_id
                or boundary.playback_item_id != proof.current.item_id
                or snapshot.get('title') != proof.current.title or snapshot.get('artist') != proof.current.artist
                or dict(moment.source_attribution) != {'provider': 'Spotify', 'url': proof.current.source_url,
                    'url_previous': proof.earlier.source_url, 'license': 'Spotify-Policy'}
                or moment.content != transition_copy(locale=proof.current.locale,
                    persona=moment.presentation_intent.dj_persona.value, context=proof.context(),
                    relation='discover_same_artist_genre')):
            return result
        result['requires_spotify_attribution'] = True
        deadline = min(deadline, source_limit)
    elif getattr(moment, 'observed_playback', None) is not None:
        from .session_runtime import ObservedPlaybackNarration
        from .context_expression import playback_copy
        observed = moment.observed_playback
        if not isinstance(observed, ObservedPlaybackNarration):
            return result
        source_limit = observed.observed_at + 30
        result['source_expires_at'] = boundary.utc_at(source_limit)
        if not observed.eligible(now):
            result['qualification'] = 'expired'
            return result
        snapshot = dict(boundary.track_snapshot)
        if (moment.moment_type.value != 'track' or moment.knowledge_intent.intent_type.value != 'track_context'
                or moment.source_references != ('spotify_playback_status',)
                or dict(moment.source_attribution) != {'provider': 'Spotify', 'url': observed.source_url, 'license': 'Spotify-Policy'}
                or boundary.playback_item_id != observed.item_id
                or snapshot.get('title') != observed.title or snapshot.get('artist') != observed.artist
                or moment.content not in {playback_copy(locale=observed.locale,
                    persona=moment.presentation_intent.dj_persona.value, form=form,
                    title=observed.title, artist=observed.artist) for form in (0, 1)}):
            return result
        result['requires_spotify_attribution'] = True
        deadline = min(deadline, source_limit)
    elif (not moment.source_attribution
          and moment.source_references == ('session_direction',)
          and moment.moment_type.value == 'session'
          and moment.knowledge_intent.intent_type.value == 'session_direction'
          and dict(moment.generation_metadata).get('context_source') == 'session_direction'
          and dict(moment.generation_metadata).get('validated') == 'true'):
        history_allowed = True
    else:
        return result
    result['qualification'] = 'qualified'
    result['display_expires_at'] = boundary.utc_at(deadline)
    result['current_display_allowed'] = bool(
        playing and boundary.playback_item_id and boundary.playback_item_id == playback_item_id
        and boundary.published_monotonic <= now < deadline)
    result['active_flow_display_allowed'] = history_allowed and moment.moment_id in flow_ids
    from .moment_navigation import navigation, TTL_SECONDS
    if result['qualification'] == 'qualified' and (result['current_display_allowed'] or result['active_flow_display_allowed']) and now < min(boundary.published_monotonic+TTL_SECONDS, source_deadline(source) if isinstance(source,QualifiedSessionFact) else deadline):
        result['navigation_actions'] = [{**nav,'expires_at':boundary.utc_at(min(boundary.published_monotonic+TTL_SECONDS,source_deadline(source)))} for action in moment.actions if (nav:=navigation(action)) and nav['reference']['session_id']==session_id and nav['reference']['moment_id']==moment.moment_id][:1]
    return result


def withdrawn_native_delivery(session_id: str) -> dict[str, Any]:
    """Complete terminal denial for one transport authority, never a grant."""
    result = {"schema_version": 1, "session_id": session_id,
              "current_moment_id": None, "active_flow_moment_ids": [],
              "admissions": [], "revocation_scope": "subscription"}
    result['revision'] = hashlib.sha256(json.dumps(result, sort_keys=True).encode()).hexdigest()[:24]
    return result
