"""Dynamic native display admission; semantic Moments stay immutable.

Only existing field-qualified normalized facts and Runtime-authored context
are admitted. No provider access, payload interpretation or action execution.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
import hashlib
import math
from typing import Any

from .session_facts import QualifiedSessionFact, SharedProducerFact


@dataclass(frozen=True)
class MomentDeliveryBoundary:
    """Original publication clocks, never renewed by reads or reconnect."""

    published_monotonic: float
    published_at: str
    playback_item_id: str

    def utc_at(self, deadline: float) -> str:
        return (datetime.fromisoformat(self.published_at) + timedelta(
            seconds=deadline - self.published_monotonic)).isoformat()


def source_deadline(fact: QualifiedSessionFact) -> float:
    observations = [fact.observed_at]
    if isinstance(fact, SharedProducerFact) and fact.previous_evidence is not None:
        observations.append(fact.previous_evidence.observed_at)
    return min(observations) + 1800


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
    elif (not moment.source_attribution
          and moment.source_references in {('session_flow',), ('session_direction',)}
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
    return result
