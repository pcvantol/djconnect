"""Ephemeral server-owned DJ Session Runtime lifecycle."""

from __future__ import annotations

import asyncio
import copy
import hashlib
import json
import logging
import re
import secrets
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Awaitable, Callable
from uuid import uuid4

from .const import API_IMAGE_PROXY_BASE, DOMAIN
from .session_facts import QualifiedSessionFact, SharedProducerFact, PublishedRecordingContext
from .moment_expression import realize as realize_fact_expression
from .native_moment_delivery import (
    MomentDeliveryBoundary, admission as native_admission, withdrawn_native_delivery,
)
from .persistence import persistence_service
from .persistence.sessions import (
    ACTIVE as PERSISTENT_SESSION_ACTIVE,
    ENDED as PERSISTENT_SESSION_ENDED,
    INTERRUPTED as PERSISTENT_SESSION_INTERRUPTED,
    PersistentSessionRepository,
)
from .persistence.history import HistoricalProjectionRepository
from .presentation_composer import (
    PresentationComposer,
    PresentationCompositionOutcome,
    PresentationContext,
    PresentationProjection,
)

_LOGGER = logging.getLogger(__name__)


class SessionRuntimeState(StrEnum):
    """Canonical lifecycle states for the first v4 runtime slice."""

    IDLE = "idle"
    CREATING = "creating"
    ACTIVE = "active"
    ENDING = "ending"
    ENDED = "ended"


class PlannerState(StrEnum):
    """Lifecycle state for the ephemeral Session Planner foundation."""

    READY = "ready"


class SessionDirectionType(StrEnum):
    """Canonical, Runtime-owned directions for one active DJ Session."""

    BUILDING_ENERGY = "building_energy"
    MAINTAINING_ENERGY = "maintaining_energy"
    COOLING_DOWN = "cooling_down"
    EXPLORING = "exploring"
    DEEPENING = "deepening"
    RETURNING = "returning"
    RESETTING = "resetting"


class SessionStartStrategy(StrEnum):
    """Production Session objectives; Mood and Persona are separate dimensions."""

    CONTINUE = "continue"
    DISCOVER = "discover"
    MANUAL = "manual"


@dataclass(frozen=True)
class SessionDirection:
    """Timestamped Runtime state describing where the active Session is heading."""

    direction: SessionDirectionType
    initialized_at: str
    updated_at: str
    start_strategy: SessionStartStrategy

    def as_dict(self) -> dict[str, str]:
        return {
            "direction": self.direction.value,
            "initialized_at": self.initialized_at,
            "updated_at": self.updated_at,
            "start_strategy": self.start_strategy.value,
        }


class PlannerEventType(StrEnum):
    """Planner inputs that future runtime capabilities may submit."""

    TRACK_FINISHED = "track_finished"
    PLAYBACK_CHANGED = "playback_changed"
    MOOD_CHANGED = "mood_changed"
    AUDIENCE_SIGNAL = "audience_signal"
    CONVERSATION = "conversation"
    PLANNER_TICK = "planner_tick"
    TRACK_AVAILABLE = "track_available"


class AudienceSignalType(StrEnum):
    MORE_ENERGY = "more_energy"
    LESS_ENERGY = "less_energy"
    CHILL = "chill"
    DANCE = "dance"
    SURPRISE_US = "surprise_us"
    MORE_GUITARS = "more_guitars"
    MORE_VOCALS = "more_vocals"
    MORE_INSTRUMENTAL = "more_instrumental"
    GENRE_SUGGESTION = "genre_suggestion"
    ARTIST_SUGGESTION = "artist_suggestion"
    ARTIST_EXCLUSION = "artist_exclusion"
    MORE_LIKE_THIS = "more_like_this"


class BroadcastEventType(StrEnum):
    """Stable event vocabulary for future Broadcast Engine distribution."""

    RUNTIME_CREATED = "runtime_created"
    RUNTIME_ENDED = "runtime_ended"
    PLAYBACK_CHANGED = "playback_changed"
    PLAYBACK_PROGRESS = "playback_progress"
    PLANNER_UPDATED = "planner_updated"
    MOOD_CHANGED = "mood_changed"
    TRACK_CHANGED = "track_changed"
    SESSION_FLOW_UPDATED = "session_flow_updated"
    AUDIENCE_UPDATED = "audience_updated"
    BROADCAST_STARTED = "broadcast_started"
    BROADCAST_STOPPED = "broadcast_stopped"
    DJ_MOMENT_PUBLISHED = "dj_moment_published"
    PRESENTATION_PUBLISHED = "presentation_published"


class BroadcastAuthorizationScope(StrEnum):
    """Visibility scope bound to internal Broadcast recovery identity."""

    OWNER = "owner"


class KnowledgeIntentType(StrEnum):
    """The semantic contribution requested by the Planner."""

    TRACK_CONTEXT = "track_context"
    ARTIST_STORY = "artist_story"
    ALBUM_STORY = "album_story"
    GENRE_STORY = "genre_story"
    RECOMMENDATION = "recommendation"
    TRANSITION = "transition"
    SESSION_DIRECTION = "session_direction"
    SILENCE = "silence"


class PlannerDecisionType(StrEnum):
    CREATE_TRACK_CONTEXT = "create_track_context"
    CREATE_ARTIST_STORY = "create_artist_story"
    CREATE_ALBUM_STORY = "create_album_story"
    CREATE_GENRE_STORY = "create_genre_story"
    CREATE_SESSION_UPDATE = "create_session_update"
    CREATE_RECOMMENDATION = "create_recommendation"
    CREATE_TRANSITION = "create_transition"
    CREATE_DISCOVERY = "create_discovery"
    NO_TRANSITION = "no_transition"
    SILENCE = "silence"


@dataclass(frozen=True)
class PlannerDecision:
    decision_type: PlannerDecisionType
    reason: str
    knowledge_intent: KnowledgeIntent | None = None
    proposed_session_direction: SessionDirectionType | None = None
    transition_moment_ids: tuple[str, str] = ()
    transition_placement: str = ""
    transition_relation: str = ""
    transition_context: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class PlannerConfiguration:
    minimum_time_between_moments_seconds: float = 60.0
    maximum_track_context_per_track: int = 1
    allow_consecutive_silence: bool = True
    recommendation_preference: str = "balanced"
    exploration_preference: str = "balanced"
    energy_preference: str = "balanced"
    interaction_profile: str = "balanced"

    def as_dict(self) -> dict[str, Any]:
        return {
            "minimum_time_between_moments_seconds": self.minimum_time_between_moments_seconds,
            "maximum_track_context_per_track": self.maximum_track_context_per_track,
            "allow_consecutive_silence": self.allow_consecutive_silence,
            "recommendation_preference": self.recommendation_preference,
            "exploration_preference": self.exploration_preference,
            "energy_preference": self.energy_preference,
            "interaction_profile": self.interaction_profile,
        }


@dataclass(frozen=True)
class SessionStartConfiguration:
    """Immutable Runtime configuration selected when a Session begins."""

    strategy: SessionStartStrategy
    initial_direction: SessionDirectionType
    planner_configuration: PlannerConfiguration
    interaction_profile: str


@dataclass(frozen=True)
class DiscoverContext:
    """Safe, optional Music DNA projection for one active Discover Runtime."""

    personal_context_authorized: bool = False
    familiar_artists: tuple[str, ...] = ()
    familiar_genres: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "personal_context_authorized": self.personal_context_authorized,
            "familiar_artists": list(self.familiar_artists),
            "familiar_genres": list(self.familiar_genres),
        }


class DJMomentType(StrEnum):
    """Bounded first-production catalogue of immutable Moments."""

    TRACK = "track"
    ARTIST = "artist"
    ALBUM = "album"
    GENRE = "genre"
    RECOMMENDATION = "recommendation"
    TRANSITION = "transition"
    SESSION = "session"
    SILENCE = "silence"


class DJPersona(StrEnum):
    """Behavioural DJ identities; never a Voice provider configuration."""

    HOME_DJ = "home_dj"
    RADIO_DJ = "radio_dj"
    CLUB_DJ = "club_dj"
    FESTIVAL_DJ = "festival_dj"


@dataclass(frozen=True)
class NarrativeTrackEvidence:
    """Private, current-status proof selected by Knowledge for one observed track."""

    media_identity: str
    artist_id: str
    genres: tuple[str, ...]
    title: str
    artist: str


@dataclass(frozen=True)
class DiscoverNarrativeLine:
    """One pending Genre subject, bounded to the next accepted Runtime event."""

    source_moment_id: str
    source_title: str
    artist: str
    genre: str
    media_identity: str
    artist_id: str
    mood: str
    persona: DJPersona
    direction: SessionDirectionType
    event_number: int
    flow_id: str
    flow_revision: int


class DJMomentVisibility(StrEnum):
    """Server-owned projection boundary for a generated Moment."""

    OWNER_ONLY = "owner_only"
    SESSION_SHARED = "session_shared"
    PUBLIC_BROADCAST = "public_broadcast"


class DeliveryChannel(StrEnum):
    """Semantic delivery targets, not renderer-specific instructions."""

    BROADCAST = "broadcast"
    OWNER = "owner"
    SHARED = "shared"


@dataclass(frozen=True)
class KnowledgeIntent:
    """Planner-owned statement of what the DJ should communicate."""

    intent_type: KnowledgeIntentType
    goal: str
    track_key: str = ""

    def as_dict(self) -> dict[str, str]:
        return {"type": self.intent_type.value, "goal": self.goal}


@dataclass(frozen=True)
class PresentationIntent:
    """Frozen semantic guidance for one Moment's delivery."""

    source_session_mood: str
    dj_persona: DJPersona
    tone_of_voice: str
    energy_level: str
    delivery_style: str
    voice_style: str
    visual_theme: str
    importance: str
    maximum_duration_seconds: int
    delivery_channels: tuple[DeliveryChannel, ...]
    visibility: DJMomentVisibility

    def as_dict(self) -> dict[str, Any]:
        return {
            "source_session_mood": self.source_session_mood,
            "dj_persona": self.dj_persona.value,
            "tone_of_voice": self.tone_of_voice,
            "energy_level": self.energy_level,
            "delivery_style": self.delivery_style,
            "voice_style": self.voice_style,
            "visual_theme": self.visual_theme,
            "importance": self.importance,
            "maximum_duration_seconds": self.maximum_duration_seconds,
            "delivery_channels": [channel.value for channel in self.delivery_channels],
            "visibility": self.visibility.value,
        }


@dataclass(frozen=True)
class DJMomentAction:
    """A safe semantic follow-up action supplied by the server."""

    action_type: str
    label: str
    icon_hint: str
    priority: int
    required_capability: str
    payload: tuple[tuple[str, str], ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "action_type": self.action_type,
            "label": self.label,
            "icon_hint": self.icon_hint,
            "priority": self.priority,
            "required_capability": self.required_capability,
            "payload": dict(self.payload),
        }


@dataclass(frozen=True)
class DJMoment:
    """Universal immutable, validated presentation contribution."""

    moment_id: str
    session_id: str
    created_at: str
    moment_type: DJMomentType
    knowledge_intent: KnowledgeIntent
    presentation_intent: PresentationIntent
    title: str
    summary: str
    content: str
    artwork_url: str | None
    actions: tuple[DJMomentAction, ...]
    source_references: tuple[str, ...]
    generation_metadata: tuple[tuple[str, str], ...]
    source_context_fingerprint: str = field(default="", repr=False)
    source_attribution: tuple[tuple[str, str], ...] = ()
    visual_only: bool = field(default=False, repr=False)
    expression_form: str = field(default="", repr=False)
    source_fact: QualifiedSessionFact | None = field(default=None, repr=False)

    def as_dict(self) -> dict[str, Any]:
        return {
            "moment_id": self.moment_id,
            "session_id": self.session_id,
            "created_at": self.created_at,
            "type": self.moment_type.value,
            "knowledge_intent": self.knowledge_intent.as_dict(),
            "presentation_intent": self.presentation_intent.as_dict(),
            "title": self.title,
            "summary": self.summary,
            "content": self.content,
            "artwork": {"url": self.artwork_url} if self.artwork_url else None,
            "actions": [action.as_dict() for action in self.actions],
            "visibility": self.presentation_intent.visibility.value,
            "delivery_channels": [channel.value for channel in self.presentation_intent.delivery_channels],
            "importance": self.presentation_intent.importance,
            "source_references": list(self.source_references),
            "generation_metadata": dict(self.generation_metadata),
            **({"source_attribution": dict(self.source_attribution)} if self.source_attribution else {}),
        }


class SessionFlowPosition(StrEnum):
    """The bounded positions in the current rolling planning horizon."""

    NOW = "now"
    NEXT = "next"
    LATER = "later"


class SessionFlowItemType(StrEnum):
    """Initial deterministic item vocabulary for a Planner-produced flow."""

    CURRENT_TRACK = "current_track"
    PLANNING_HORIZON = "planning_horizon"
    MAINTAIN_DIRECTION = "maintain_direction"
    FUTURE_DIRECTION = "future_direction"
    FUTURE_PLACEHOLDER = "future_placeholder"
    DJ_MOMENT = "dj_moment"


class SessionFlowChangeType(StrEnum):
    """Canonical semantic changes committed by the Planner-owned Session Flow."""

    INITIALIZED = "initialized"
    REPUBLISHED = "republished"
    MOMENT_APPENDED = "moment_appended"


@dataclass(frozen=True)
class DJSessionFlowItem:
    """One typed item in a Planner-owned Session Flow."""

    item_id: str
    item_type: SessionFlowItemType
    position: SessionFlowPosition
    label: str
    moment_id: str = ""
    moment_type: str = ""

    def as_dict(self) -> dict[str, str]:
        """Return the renderer-safe representation of this flow item."""
        result = {
            "item_id": self.item_id,
            "item_type": str(self.item_type),
            "position": str(self.position),
            "label": self.label,
        }
        if self.moment_id:
            result["moment_id"] = self.moment_id
            result["moment_type"] = self.moment_type
        return result


@dataclass(frozen=True)
class DJSessionFlow:
    """Planner output describing DJ intent, never a playback queue or playlist."""

    flow_id: str
    flow_revision: int
    planning_horizon_minutes: int
    created_at: str
    items: tuple[DJSessionFlowItem, ...]

    def as_dict(self) -> dict[str, Any]:
        """Return the canonical current-horizon Session Flow."""
        return {
            "flow_id": self.flow_id,
            "flow_revision": self.flow_revision,
            "planning_horizon_minutes": self.planning_horizon_minutes,
            "created_at": self.created_at,
            "items": [item.as_dict() for item in self.items],
        }


@dataclass(frozen=True)
class SessionFlowChange:
    """One immutable Planner-owned committed semantic Session Flow revision."""

    flow_id: str
    revision: int
    change_type: SessionFlowChangeType
    flow: DJSessionFlow


@dataclass(frozen=True)
class SessionPlannerOutput:
    """Planner-owned output that exposes its canonical Session Flow."""

    session_flow: DJSessionFlow

    def as_dict(self) -> dict[str, Any]:
        """Return the transport-neutral Planner output."""
        return {"session_flow": self.session_flow.as_dict()}


@dataclass(frozen=True)
class PerformanceMemory:
    """Bounded Planner projection derived from the Runtime's Session Flow."""

    source_flow_id: str
    recent_moment_ids: tuple[str, ...] = ()
    recent_moment_types: tuple[DJMomentType, ...] = ()
    recent_artists: tuple[str, ...] = ()
    recent_albums: tuple[str, ...] = ()
    recent_genres: tuple[str, ...] = ()
    recent_recommendations: tuple[str, ...] = ()
    recent_session_directions: tuple[SessionDirectionType, ...] = ()
    recent_silence_count: int = 0
    recent_topics: tuple[tuple[DJMomentType, str], ...] = ()
    recent_context_fingerprints: tuple[str, ...] = ()
    topics_observed: bool = False

    @classmethod
    def from_session_flow(
        cls, flow: DJSessionFlow, moments: tuple[DJMoment, ...], *, window: int = 8
    ) -> "PerformanceMemory":
        """Project only recent Moment facts from the canonical Flow chronology."""
        by_id = {moment.moment_id: moment for moment in moments}
        ordered = tuple(
            by_id[item.moment_id]
            for item in flow.items
            if item.item_type is SessionFlowItemType.DJ_MOMENT and item.moment_id in by_id
        )[-window:]
        metadata = tuple(dict(moment.generation_metadata) for moment in ordered)
        return cls(
            source_flow_id=flow.flow_id,
            recent_moment_ids=tuple(moment.moment_id for moment in ordered),
            recent_moment_types=tuple(moment.moment_type for moment in ordered),
            recent_artists=_recent_metadata(metadata, "artist"),
            recent_albums=_recent_metadata(metadata, "album"),
            recent_genres=_recent_metadata(metadata, "genre"),
            recent_recommendations=_recent_metadata(metadata, "recommendation"),
            recent_session_directions=tuple(
                SessionDirectionType(value)
                for item in metadata
                if (value := item.get("direction", ""))
                if value in SessionDirectionType._value2member_map_
            ),
            recent_silence_count=sum(
                moment.moment_type is DJMomentType.SILENCE for moment in ordered
            ),
            recent_topics=tuple(
                topic for moment in ordered if (topic := _moment_topic(moment)) is not None
            ),
            recent_context_fingerprints=tuple(
                dict.fromkeys(
                    fingerprint
                    for moment in ordered
                    if (
                        fingerprint := moment.source_context_fingerprint or _context_fingerprint(
                            dict(moment.generation_metadata).get("artist", ""),
                            moment.summary,
                            moment.content,
                        )
                    )
                    and moment.moment_type
                    in {
                        DJMomentType.TRACK,
                        DJMomentType.ARTIST,
                        DJMomentType.ALBUM,
                        DJMomentType.GENRE,
                        DJMomentType.RECOMMENDATION,
                    }
                )
            ),
            topics_observed=True,
        )

    def as_dict(self) -> dict[str, Any]:
        """Expose safe, Runtime-scoped Planner context without personal data."""
        return {
            "source_flow_id": self.source_flow_id,
            "recent_moment_ids": list(self.recent_moment_ids),
            "recent_moment_types": [value.value for value in self.recent_moment_types],
            "recent_artists": list(self.recent_artists),
            "recent_albums": list(self.recent_albums),
            "recent_genres": list(self.recent_genres),
            "recent_recommendations": list(self.recent_recommendations),
            "recent_session_directions": [value.value for value in self.recent_session_directions],
            "recent_silence_count": self.recent_silence_count,
        }


@dataclass(frozen=True)
class UpcomingPlaybackEntry:
    """One normalized, provider-neutral future playback observation."""

    media_id: str
    duration_seconds: int = 0
    position: int = 0


@dataclass(frozen=True)
class UpcomingPlaybackProjection:
    """Provider-neutral future playback context; empty is a valid projection."""

    entries: tuple[UpcomingPlaybackEntry, ...] = ()
    observed_at: str = ""
    confidence: float = 0.0
    provider_supports_upcoming: bool = False
    max_entries: int = 20

    @property
    def observable_duration_seconds(self) -> int:
        return sum(max(0, entry.duration_seconds) for entry in self.entries)

    @classmethod
    def from_entries(
        cls,
        entries: tuple[UpcomingPlaybackEntry, ...],
        *,
        observed_at: str = "",
        confidence: float = 0.0,
        provider_supports_upcoming: bool = True,
        max_entries: int = 20,
    ) -> "UpcomingPlaybackProjection":
        """Bound observations without retaining provider queue structures."""
        ordered = tuple(sorted(entries, key=lambda entry: entry.position))[:max_entries]
        return cls(ordered, observed_at, max(0.0, min(1.0, confidence)), provider_supports_upcoming, max_entries)


@dataclass
class CandidatePlanningSlot:
    """A future planning opportunity, never a decision or realized Moment."""

    category: str
    starts_at_seconds: int
    ends_at_seconds: int
    is_current_track: bool = False


@dataclass(frozen=True)
class PlannerIntent:
    """One approved internal planning intent; it is not a DJMoment."""

    category: str
    generation: int


class PlannedIntentStatus(StrEnum):
    """Lifecycle of one speculative Planner-owned future intent."""

    PLANNED = "planned"
    SUPERSEDED = "superseded"
    APPROVED = "approved"
    DISCARDED = "discarded"


@dataclass(frozen=True)
class PlannedIntent:
    """One bounded future candidate; never a committed or realized Moment."""

    category: str
    slot: CandidatePlanningSlot
    generation: int
    confidence: float
    status: PlannedIntentStatus = PlannedIntentStatus.PLANNED

    def as_planner_intent(self) -> PlannerIntent:
        """Return the internal approval value without exposing the planning slot."""
        return PlannerIntent(category=self.category, generation=self.generation)


class KnowledgePrefetchStatus(StrEnum):
    """Lifecycle of Planner-owned knowledge preparation work."""

    PLANNED = "planned"
    INVALIDATED = "invalidated"


@dataclass(frozen=True)
class KnowledgePrefetch:
    """One future knowledge requirement; never retrieved knowledge or a Moment."""

    target_intent: PlannedIntent
    knowledge_category: str
    planning_generation: int
    status: KnowledgePrefetchStatus
    knowledge_confidence: float
    freshness: float
    invalidation_generation: int


@dataclass(frozen=True)
class KnowledgePrefetchRequest:
    """Immutable Planner-to-Knowledge Engine request with no Runtime object graph."""

    request_id: str
    target_category: str
    planning_slot: tuple[str, int, int]
    planning_generation: int
    knowledge_category: str
    subject_projection: tuple[tuple[str, str], ...]
    required_confidence: float
    freshness_constraint: float
    invalidation_generation: int

    @classmethod
    def from_prefetch(
        cls,
        prefetch: KnowledgePrefetch,
        *,
        subject_projection: tuple[tuple[str, str], ...],
    ) -> "KnowledgePrefetchRequest":
        """Bind a bounded observable subject projection to one planned requirement."""
        intent = prefetch.target_intent
        slot = intent.slot
        allowed = {"track", "artist", "album", "genre", "recommendation"}
        subject = tuple(
            (key, _bounded_text(value, 256))
            for key, value in subject_projection
            if key in allowed and _bounded_text(value, 256)
        )[:5]
        slot_identity = (slot.category, slot.starts_at_seconds, slot.ends_at_seconds)
        return cls(
            request_id=(
                f"prefetch-{prefetch.knowledge_category}-{intent.generation}-"
                f"{slot.starts_at_seconds}-{slot.ends_at_seconds}"
            ),
            target_category=intent.category,
            planning_slot=slot_identity,
            planning_generation=prefetch.planning_generation,
            knowledge_category=prefetch.knowledge_category,
            subject_projection=subject,
            required_confidence=prefetch.knowledge_confidence,
            freshness_constraint=prefetch.freshness,
            invalidation_generation=prefetch.invalidation_generation,
        )


class PreparedKnowledgeStatus(StrEnum):
    """Bounded typed outcomes of a Knowledge Prefetch execution."""

    PREPARED = "prepared"
    UNAVAILABLE = "unavailable"
    UNSUPPORTED = "unsupported"
    INVALID = "invalid"
    STALE = "stale"
    CANCELLED = "cancelled"
    SUPERSEDED = "superseded"


@dataclass(frozen=True)
class PreparedKnowledge:
    """Validated, non-narrative knowledge projection for one prefetch request."""

    request_id: str
    planning_generation: int
    knowledge_category: str
    status: PreparedKnowledgeStatus
    projection: tuple[tuple[str, str], ...] = ()
    confidence: float = 0.0
    freshness: float = 0.0
    is_valid: bool = False


class ReadinessStatus(StrEnum):
    """Planner-only approval eligibility for one future Planned Intent."""

    READY = "ready"
    WAITING = "waiting"
    BLOCKED = "blocked"
    EXPIRED = "expired"
    INVALID = "invalid"
    UNSUPPORTED = "unsupported"


@dataclass(frozen=True)
class ReadinessEvaluation:
    """Ephemeral Planner evaluation; it never carries prepared knowledge content."""

    target_intent: PlannedIntent
    planning_generation: int
    prepared_knowledge_available: bool
    prepared_knowledge_valid: bool
    confidence_threshold: float
    freshness_threshold: float
    invalidation_generation: int
    is_invalidated: bool
    execution_status: PreparedKnowledgeStatus | None
    status: ReadinessStatus


@dataclass(frozen=True)
class PlannerInfluence:
    """Normalized, bounded Runtime context consumed by Planner Intent Selection."""

    effective_mood: str = ""
    effective_direction: SessionDirectionType | None = None
    performance_memory: PerformanceMemory | None = None
    generation: int = 0
    confidence: float = 1.0
    freshness: float = 1.0
    is_valid: bool = True
    extensions: tuple[tuple[str, str], ...] = ()

    @classmethod
    def normalize(
        cls,
        *,
        mood: str = "",
        direction: SessionDirectionType | None = None,
        performance_memory: PerformanceMemory | None = None,
        generation: int = 0,
        confidence: float = 1.0,
        freshness: float = 1.0,
        is_valid: bool = True,
    ) -> "PlannerInfluence":
        """Normalize supported Runtime inputs without adding selection heuristics."""
        return cls(
            effective_mood=mood.strip().lower(),
            effective_direction=direction,
            performance_memory=performance_memory,
            generation=max(0, generation),
            confidence=max(0.0, min(1.0, confidence)),
            freshness=max(0.0, min(1.0, freshness)),
            is_valid=is_valid,
        )


@dataclass(frozen=True)
class TrackStartedPlanningInput:
    """Planner-owned, ephemeral input for one observed current-track opportunity."""

    session_id: str
    current_track_candidate: CandidatePlanningSlot | None
    upcoming_playback: UpcomingPlaybackProjection | None
    effective_mood: str
    effective_direction: SessionDirectionType
    performance_memory: PerformanceMemory
    planning_generation: int
    session_update_direction: SessionDirectionType | None = None
    planner_decision: PlannerDecision | None = None


class PlannerIntentSelector:
    """Select at most one supported candidate deterministically."""

    _SUPPORTED = (
        "silence",
        "session_update",
        "track_context",
        "artist_story",
        "album_story",
        "genre_story",
        "recommendation",
    )

    @classmethod
    def select(
        cls,
        window: "PlanningWindow",
        *,
        influence: PlannerInfluence | None = None,
        allowed_intents: frozenset[str] | None = None,
    ) -> PlannerIntent | None:
        """Use only normalized Planner influence to rank one future candidate."""
        influence = influence or PlannerInfluence()
        priorities = cls._SUPPORTED
        if not influence.is_valid:
            priorities = ("silence",)
        elif (
            influence.effective_mood == "chill"
            or influence.effective_direction is SessionDirectionType.COOLING_DOWN
        ):
            priorities = ("silence", "genre_story", "artist_story", "album_story", "recommendation")
        elif influence.effective_direction is SessionDirectionType.EXPLORING:
            priorities = ("recommendation", "artist_story", "album_story", "genre_story", "silence")
        for category in priorities:
            if allowed_intents is not None and category not in allowed_intents and category != "silence":
                continue
            if (
                influence.performance_memory is not None
                and cls._recently_used(category, influence.performance_memory)
            ):
                continue
            if any(slot.category == category for slot in window.candidate_slots):
                return PlannerIntent(category, window.generation)
        return None

    @staticmethod
    def _recently_used(category: str, memory: PerformanceMemory) -> bool:
        return {
            "artist_story": bool(memory.recent_artists),
            "album_story": bool(memory.recent_albums),
            "genre_story": bool(memory.recent_genres),
            "recommendation": bool(memory.recent_recommendations),
            "session_update": bool(memory.recent_session_directions),
            "transition": bool(memory.recent_moment_ids),
        }.get(category, False)


@dataclass
class PlanningWindow:
    """Planner-owned bounded future planning space derived from Horizon input."""

    starts_at: str
    ends_at: str
    observable_coverage_seconds: int = 0
    planning_coverage_seconds: int = 0
    generation: int = 0
    confidence: float = 0.0
    candidate_slots: tuple[CandidatePlanningSlot, ...] = ()
    planned_intents: tuple[PlannedIntent, ...] = ()
    approved_intent: PlannerIntent | None = None
    max_planned_intents: int = 20
    allowed_intents: frozenset[str] | None = None
    influence: PlannerInfluence = field(default_factory=PlannerInfluence)
    knowledge_prefetches: tuple[KnowledgePrefetch, ...] = ()
    readiness_evaluations: tuple[ReadinessEvaluation, ...] = ()

    _PREFETCH_CATEGORIES = {
        "artist_story": "artist",
        "album_story": "album",
        "genre_story": "genre",
        "recommendation": "recommendation",
    }

    @staticmethod
    def _prefetch_key(intent: PlannedIntent) -> tuple[str, int, int, int]:
        """Identify one bounded future requirement without provider metadata."""
        return (
            intent.category,
            intent.slot.starts_at_seconds,
            intent.slot.ends_at_seconds,
            intent.generation,
        )

    def plan_knowledge_prefetches(
        self,
        *,
        invalidation_generation: int,
        previous_prefetches: tuple[KnowledgePrefetch, ...] = (),
    ) -> tuple[KnowledgePrefetch, ...]:
        """Prepare bounded knowledge requirements for still-provisional future intents."""
        confidence = min(self.confidence, self.influence.confidence)
        active = tuple(
            KnowledgePrefetch(
                target_intent=intent,
                knowledge_category=self._PREFETCH_CATEGORIES[intent.category],
                planning_generation=intent.generation,
                status=KnowledgePrefetchStatus.PLANNED,
                knowledge_confidence=max(0.0, min(1.0, confidence)),
                freshness=self.influence.freshness,
                invalidation_generation=invalidation_generation,
            )
            for intent in self.planned_intents
            if intent.status is PlannedIntentStatus.PLANNED
            and intent.category in self._PREFETCH_CATEGORIES
        )
        active_keys = {self._prefetch_key(prefetch.target_intent) for prefetch in active}
        invalidated = tuple(
            KnowledgePrefetch(
                target_intent=prefetch.target_intent,
                knowledge_category=prefetch.knowledge_category,
                planning_generation=prefetch.planning_generation,
                status=KnowledgePrefetchStatus.INVALIDATED,
                knowledge_confidence=prefetch.knowledge_confidence,
                freshness=prefetch.freshness,
                invalidation_generation=invalidation_generation,
            )
            for prefetch in previous_prefetches
            if self._prefetch_key(prefetch.target_intent) not in active_keys
            and prefetch.status is KnowledgePrefetchStatus.PLANNED
        )
        self.knowledge_prefetches = (active + invalidated)[: self.max_planned_intents]
        self.readiness_evaluations = ()
        return self.knowledge_prefetches

    @staticmethod
    def _prefetch_request_id(prefetch: KnowledgePrefetch) -> str:
        """Derive the immutable execution identity without retaining a request."""
        slot = prefetch.target_intent.slot
        return (
            f"prefetch-{prefetch.knowledge_category}-{prefetch.target_intent.generation}-"
            f"{slot.starts_at_seconds}-{slot.ends_at_seconds}"
        )

    def evaluate_readiness(
        self,
        prepared_knowledge: tuple[PreparedKnowledge, ...] = (),
        *,
        invalidation_generation: int | None = None,
    ) -> tuple[ReadinessEvaluation, ...]:
        """Evaluate approval eligibility without exposing knowledge to approval logic."""
        active_invalidation_generation = (
            self.generation if invalidation_generation is None else invalidation_generation
        )
        prepared_by_request = {result.request_id: result for result in prepared_knowledge}
        prefetch_by_intent = {
            self._prefetch_key(prefetch.target_intent): prefetch
            for prefetch in self.knowledge_prefetches
            if prefetch.status is KnowledgePrefetchStatus.PLANNED
        }
        evaluations: list[ReadinessEvaluation] = []
        for intent in self.plan_intents():
            prefetch = prefetch_by_intent.get(self._prefetch_key(intent))
            result = (
                prepared_by_request.get(self._prefetch_request_id(prefetch))
                if prefetch is not None
                else None
            )
            invalidated = (
                intent.status is not PlannedIntentStatus.PLANNED
                or intent.generation != self.generation
                or (
                    prefetch is not None
                    and (
                        prefetch.planning_generation != self.generation
                        or prefetch.invalidation_generation != active_invalidation_generation
                    )
                )
                or (result is not None and result.planning_generation != self.generation)
            )
            available = result is not None
            valid = bool(result and result.is_valid)
            execution_status = result.status if result is not None else None
            if invalidated:
                status = ReadinessStatus.INVALID
            elif prefetch is None:
                status = ReadinessStatus.READY
            elif result is None:
                status = ReadinessStatus.WAITING
            elif result.status is PreparedKnowledgeStatus.UNSUPPORTED:
                status = ReadinessStatus.UNSUPPORTED
            elif result.status is PreparedKnowledgeStatus.STALE:
                status = ReadinessStatus.EXPIRED
            elif result.status is PreparedKnowledgeStatus.UNAVAILABLE:
                status = ReadinessStatus.BLOCKED
            elif result.status in {
                PreparedKnowledgeStatus.INVALID,
                PreparedKnowledgeStatus.CANCELLED,
                PreparedKnowledgeStatus.SUPERSEDED,
            } or not result.is_valid:
                status = ReadinessStatus.INVALID
            elif result.confidence < prefetch.knowledge_confidence:
                status = ReadinessStatus.BLOCKED
            elif result.freshness < prefetch.freshness:
                status = ReadinessStatus.EXPIRED
            else:
                status = ReadinessStatus.READY
            evaluations.append(
                ReadinessEvaluation(
                    target_intent=intent,
                    planning_generation=self.generation,
                    prepared_knowledge_available=available,
                    prepared_knowledge_valid=valid,
                    confidence_threshold=prefetch.knowledge_confidence if prefetch else 0.0,
                    freshness_threshold=prefetch.freshness if prefetch else 0.0,
                    invalidation_generation=active_invalidation_generation,
                    is_invalidated=invalidated,
                    execution_status=execution_status,
                    status=status,
                )
            )
        self.readiness_evaluations = tuple(evaluations)
        return self.readiness_evaluations

    def plan_intents(self) -> tuple[PlannedIntent, ...]:
        """Create deterministic provisional intents only for observed future slots."""
        if self.planned_intents:
            return self.planned_intents
        if self.planning_coverage_seconds <= 0 and not any(
            slot.is_current_track for slot in self.candidate_slots
        ):
            return ()

        eligible_slots = (
            slot
            for slot in sorted(
                self.candidate_slots,
                key=lambda slot: (slot.starts_at_seconds, slot.ends_at_seconds, slot.category),
            )
            if (
                slot.category in PlannerIntentSelector._SUPPORTED
                and (
                    self.allowed_intents is None
                    or slot.category == "silence"
                    or slot.category in self.allowed_intents
                )
                and (
                    slot.is_current_track
                    or (
                        0 <= slot.starts_at_seconds < slot.ends_at_seconds
                        and slot.ends_at_seconds <= self.planning_coverage_seconds
                    )
                )
            )
        )
        confidence = max(0.0, min(1.0, self.confidence))
        self.planned_intents = tuple(
            PlannedIntent(
                category=slot.category,
                slot=slot,
                generation=self.generation,
                confidence=confidence,
            )
            for slot in eligible_slots
        )[: self.max_planned_intents]
        return self.planned_intents

    def approve_earliest_planned_intent(self) -> PlannerIntent | None:
        """Approve only an already-ready earliest future intent, once per window."""
        if self.approved_intent is not None:
            return self.approved_intent

        readiness_by_intent = {
            self._prefetch_key(evaluation.target_intent): evaluation
            for evaluation in self.readiness_evaluations
        }
        planned_intents = self.plan_intents()
        for index, planned in enumerate(planned_intents):
            evaluation = readiness_by_intent.get(self._prefetch_key(planned))
            if (
                planned.status is not PlannedIntentStatus.PLANNED
                or evaluation is None
                or evaluation.status is not ReadinessStatus.READY
            ):
                continue
            approved = PlannedIntent(
                category=planned.category,
                slot=planned.slot,
                generation=planned.generation,
                confidence=planned.confidence,
                status=PlannedIntentStatus.APPROVED,
            )
            self.planned_intents = (
                planned_intents[:index] + (approved,) + planned_intents[index + 1 :]
            )
            self.approved_intent = approved.as_planner_intent()
            return self.approved_intent
        return None

    def select_intent(self, influence: PlannerInfluence | None = None) -> PlannerIntent | None:
        """Approve one deterministic candidate without realizing it."""
        if influence is not None:
            self.influence = influence
        if self.candidate_slots:
            return self.approve_earliest_planned_intent()
        self.approved_intent = PlannerIntentSelector.select(self, influence=self.influence)
        return self.approved_intent


@dataclass
class RollingSessionHorizon:
    """Planner-owned, ephemeral future-experience planning workspace."""

    window_minutes: int
    created_at: str
    planning_state: str = "empty"
    candidates: tuple[str, ...] = ()
    confidence: float = 0.0
    invalidation_generation: int = 0
    planned_at: str = ""
    upcoming_playback: UpcomingPlaybackProjection = field(default_factory=UpcomingPlaybackProjection)
    current_track_candidate: CandidatePlanningSlot | None = None
    planning_window: PlanningWindow | None = None
    influence: PlannerInfluence = field(default_factory=PlannerInfluence)
    allowed_intents: frozenset[str] | None = None
    consumed_slot_keys: tuple[tuple[str, int, int], ...] = ()
    _replanning_signature: tuple[Any, ...] | None = field(default=None, repr=False)

    @staticmethod
    def _slot_key(slot: CandidatePlanningSlot) -> tuple[str, int, int]:
        """Identify one runtime-local planning occurrence without media identity."""
        return (slot.category, slot.starts_at_seconds, slot.ends_at_seconds)

    def _candidate_slots(self, planning_coverage: int) -> tuple[CandidatePlanningSlot, ...]:
        """Derive only silence-capable slots from observable playback duration."""
        offset = 0
        slots: list[CandidatePlanningSlot] = []
        for entry in self.upcoming_playback.entries:
            duration = max(0, entry.duration_seconds)
            slot_end = min(offset + duration, planning_coverage)
            if offset < slot_end:
                slots.append(CandidatePlanningSlot("silence", offset, slot_end))
            offset += duration
            if offset >= planning_coverage:
                break
        if self.current_track_candidate is not None:
            slots.append(self.current_track_candidate)
        return tuple(slots)

    def _signature(self) -> tuple[Any, ...]:
        """Capture only bounded inputs that may materially change a provisional plan."""
        window = self.planning_window
        return (
            self.invalidation_generation,
            self.influence,
            self.upcoming_playback.entries,
            self.upcoming_playback.observed_at,
            self.upcoming_playback.confidence,
            self.upcoming_playback.provider_supports_upcoming,
            self.upcoming_playback.max_entries,
            self.current_track_candidate,
            tuple(self._slot_key(slot) for slot in window.candidate_slots) if window else (),
            tuple(
                (self._slot_key(intent.slot), intent.status.value, intent.generation)
                for intent in window.planned_intents
            )
            if window
            else (),
            self.consumed_slot_keys,
            self.allowed_intents,
        )

    @staticmethod
    def _with_status(intent: PlannedIntent, status: PlannedIntentStatus) -> PlannedIntent:
        """Copy an ephemeral intent while retaining its original decision fields."""
        return PlannedIntent(
            category=intent.category,
            slot=intent.slot,
            generation=intent.generation,
            confidence=intent.confidence,
            status=status,
        )

    def _new_planning_window(self, generation: int) -> PlanningWindow:
        """Build a fresh bounded window solely from the current normalized horizon."""
        coverage = self.upcoming_playback.observable_duration_seconds
        planning_coverage = min(coverage, self.window_minutes * 60)
        window = PlanningWindow(
            starts_at=self.created_at,
            ends_at=self.created_at,
            observable_coverage_seconds=coverage,
            planning_coverage_seconds=planning_coverage,
            generation=generation,
            confidence=(
                self.upcoming_playback.confidence
                if planning_coverage > 0
                else self.influence.confidence
            ),
            candidate_slots=self._candidate_slots(planning_coverage),
            influence=self.influence,
            allowed_intents=self.allowed_intents,
        )
        window.plan_intents()
        return window

    def build_planning_window(self) -> PlanningWindow:
        """Build bounded silence-capable slots only from observed playback duration."""
        self.planning_window = self._new_planning_window(self.invalidation_generation)
        self.planning_window.plan_knowledge_prefetches(
            invalidation_generation=self.invalidation_generation
        )
        self._replanning_signature = self._signature()
        return self.planning_window

    def mark_planned_intent_consumed(self, intent: PlannedIntent) -> None:
        """Prevent an already-consumed occurrence from returning in a later plan."""
        key = self._slot_key(intent.slot)
        if key not in self.consumed_slot_keys:
            self.consumed_slot_keys += (key,)
        if self.planning_window is None:
            return
        self.planning_window.planned_intents = tuple(
            self._with_status(planned, PlannedIntentStatus.DISCARDED)
            if self._slot_key(planned.slot) == key
            and planned.status in {PlannedIntentStatus.PLANNED, PlannedIntentStatus.APPROVED}
            else planned
            for planned in self.planning_window.planned_intents
        )
        self.planning_window.plan_knowledge_prefetches(
            invalidation_generation=self.invalidation_generation,
            previous_prefetches=self.planning_window.knowledge_prefetches,
        )

    def replan(
        self,
        *,
        upcoming_playback: UpcomingPlaybackProjection | None = None,
        influence: PlannerInfluence | None = None,
        current_track_candidate: CandidatePlanningSlot | None = None,
        allowed_intents: frozenset[str] | None = None,
    ) -> PlanningWindow:
        """Deterministically replace only invalid provisional planning after input change."""
        if upcoming_playback is not None:
            self.upcoming_playback = upcoming_playback
        if influence is not None:
            self.influence = influence
        if allowed_intents is not None:
            self.allowed_intents = allowed_intents
        self.current_track_candidate = current_track_candidate
        if self.planning_window is None:
            return self.build_planning_window()

        signature = self._signature()
        if signature == self._replanning_signature:
            return self.planning_window

        previous = self.planning_window
        generation = max(previous.generation + 1, self.invalidation_generation + 1)
        self.invalidation_generation = generation
        rebuilt = self._new_planning_window(generation)
        available = {self._slot_key(slot) for slot in rebuilt.candidate_slots}
        consumed = set(self.consumed_slot_keys)
        retained: list[PlannedIntent] = []
        retained_keys: set[tuple[str, int, int]] = set()
        for intent in previous.planned_intents:
            key = self._slot_key(intent.slot)
            if (
                intent.status is PlannedIntentStatus.APPROVED
                and (
                    self.allowed_intents is None
                    or intent.category == "silence"
                    or intent.category in self.allowed_intents
                )
            ):
                retained.append(intent)
                retained_keys.add(key)
            elif (
                intent.status is PlannedIntentStatus.PLANNED
                and key in available
                and key not in consumed
                and (
                    self.allowed_intents is None
                    or intent.category == "silence"
                    or intent.category in self.allowed_intents
                )
            ):
                retained.append(intent)
                retained_keys.add(key)
            elif intent.status is PlannedIntentStatus.PLANNED:
                retained.append(self._with_status(intent, PlannedIntentStatus.SUPERSEDED))

        generated = tuple(
            intent
            for intent in rebuilt.planned_intents
            if self._slot_key(intent.slot) not in retained_keys
            and self._slot_key(intent.slot) not in consumed
        )
        rebuilt.planned_intents = tuple(retained + list(generated))[: rebuilt.max_planned_intents]
        approved = next(
            (intent for intent in rebuilt.planned_intents if intent.status is PlannedIntentStatus.APPROVED),
            None,
        )
        rebuilt.approved_intent = approved.as_planner_intent() if approved is not None else None
        rebuilt.plan_knowledge_prefetches(
            invalidation_generation=generation,
            previous_prefetches=previous.knowledge_prefetches,
        )
        self.planning_window = rebuilt
        self._replanning_signature = self._signature()
        return rebuilt

    def invalidate(self) -> None:
        """Discard future candidates without creating a realized Moment."""
        self.candidates = ()
        self.planning_state = "empty"
        self.invalidation_generation += 1
        self.planning_window = None
        self._replanning_signature = None


@dataclass
class DJSessionPlanner:
    """One ephemeral Planner, owned exclusively by one active Runtime.

    The Planner owns the future: its rolling horizon, future Session Flow and
    future Broadcast generation. The Runtime owns the present, including mood;
    the Planner only consumes that runtime-owned context in later slices.
    """

    planner_state: PlannerState
    planning_horizon_minutes: int
    created_at: str
    last_replan_at: str
    current_goal: str
    pending_events: tuple[PlannerEventType, ...]
    output: SessionPlannerOutput
    horizon: RollingSessionHorizon | None = None
    audience_totals: dict[str, int] = field(default_factory=dict)
    recent_audience_activity: tuple[str, ...] = ()
    configuration: PlannerConfiguration = field(default_factory=PlannerConfiguration)
    last_spoken_moment_at: float = 0.0
    last_decision: PlannerDecision | None = None
    discover_event_number: int = 0
    discover_narrative_line: DiscoverNarrativeLine | None = None
    discover_narrative_closed: bool = False
    flow_change_journal: tuple[SessionFlowChange, ...] = ()
    elapsed_time_source: Callable[[], float] = field(
        default=time.monotonic, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        """Record the initial canonical Flow state without advancing its revision."""
        if self.flow_change_journal:
            return
        flow = self.output.session_flow
        self.flow_change_journal = (
            SessionFlowChange(
                flow_id=flow.flow_id,
                revision=flow.flow_revision,
                change_type=SessionFlowChangeType.INITIALIZED,
                flow=flow,
            ),
        )

    def _commit_session_flow(
        self, flow: DJSessionFlow, change_type: SessionFlowChangeType
    ) -> DJSessionFlow:
        """Commit exactly one semantic Flow mutation and its next revision."""
        current = self.output.session_flow
        committed = DJSessionFlow(
            flow_id=flow.flow_id,
            flow_revision=current.flow_revision + 1,
            planning_horizon_minutes=flow.planning_horizon_minutes,
            created_at=flow.created_at,
            items=flow.items,
        )
        self.output = SessionPlannerOutput(session_flow=committed)
        self.flow_change_journal = (
            *self.flow_change_journal,
            SessionFlowChange(
                flow_id=committed.flow_id,
                revision=committed.flow_revision,
                change_type=change_type,
                flow=committed,
            ),
        )
        self.last_replan_at = committed.created_at
        return committed

    def dispose_flow_change_journal(self) -> None:
        """Release Runtime-scoped semantic history when its Session ends."""
        self.flow_change_journal = ()

    def submit_audience_signal(self, signal: AudienceSignalType, value: str = "") -> None:
        """Aggregate one suggestion without interpreting it or changing playback."""
        key = f"{signal.value}:{value.strip()}" if value.strip() else signal.value
        self.audience_totals[key] = self.audience_totals.get(key, 0) + 1
        self.recent_audience_activity = (key, *self.recent_audience_activity)[:20]
        self.pending_events = (*self.pending_events, PlannerEventType.AUDIENCE_SIGNAL)

    def republish_session_flow(self) -> DJSessionFlow:
        """Rebuild the deterministic flow when Planner state later changes."""
        flow = _create_session_flow(
            session_id=self.output.session_flow.flow_id.removeprefix("flow-"),
            planning_horizon_minutes=self.planning_horizon_minutes,
            created_at=_timestamp(),
        )
        return self._commit_session_flow(flow, SessionFlowChangeType.REPUBLISHED)

    def evaluate_track_started(
        self,
        *,
        session_start_strategy: SessionStartStrategy = SessionStartStrategy.MANUAL,
        session_direction: SessionDirection,
        selected_mood: str,
        persona: DJPersona,
        knowledge_hints: dict[str, Any] | None = None,
        performance_memory: PerformanceMemory | None = None,
        discover_context: DiscoverContext | None = None,
        record_track_available: bool = True,
    ) -> PlannerDecision:
        """Make the bounded first production decision without invoking services."""
        if record_track_available:
            self.pending_events = (*self.pending_events, PlannerEventType.TRACK_AVAILABLE)
        performance_memory = performance_memory or PerformanceMemory("")
        discover_context = discover_context or DiscoverContext()
        mood = selected_mood.strip().lower()
        now = self.elapsed_time_source()
        if self.last_spoken_moment_at and now - self.last_spoken_moment_at < self.configuration.minimum_time_between_moments_seconds:
            self.last_decision = PlannerDecision(PlannerDecisionType.SILENCE, "minimum_interval")
            return self.last_decision
        proposed_direction = _planned_direction(
            current=session_direction.direction,
            selected_mood=mood,
            persona=persona,
        )
        direction_change_reason = "session_direction_changed"
        if (
            performance_memory.recent_moment_types[-2:]
            == (DJMomentType.SILENCE, DJMomentType.SILENCE)
            and session_direction.direction is not SessionDirectionType.RESETTING
            and DJMomentType.SESSION not in performance_memory.recent_moment_types[-3:]
        ):
            proposed_direction = SessionDirectionType.RESETTING
            direction_change_reason = "recent_silence_recovery"
        elif (
            session_direction.direction is SessionDirectionType.RESETTING
            and performance_memory.recent_session_directions[-1:]
            == (SessionDirectionType.RESETTING,)
        ):
            proposed_direction = SessionDirectionType.RETURNING
            direction_change_reason = "resetting_session_return"
        if proposed_direction is not session_direction.direction:
            if (
                DJMomentType.SESSION in performance_memory.recent_moment_types[-2:]
                and direction_change_reason != "resetting_session_return"
            ):
                self.last_decision = PlannerDecision(
                    PlannerDecisionType.SILENCE, "recent_session_update"
                )
                return self.last_decision
            intent = KnowledgeIntent(
                KnowledgeIntentType.SESSION_DIRECTION,
                "Communicate the updated direction of the active DJ Session.",
            )
            self.last_decision = PlannerDecision(
                PlannerDecisionType.CREATE_SESSION_UPDATE,
                direction_change_reason,
                intent,
                proposed_direction,
            )
            return self.last_decision
        if (
            (mood in {"deep", "focus", "chill"} or persona is DJPersona.CLUB_DJ)
            and performance_memory.recent_silence_count < 2
        ):
            self.last_decision = PlannerDecision(PlannerDecisionType.SILENCE, "mood_or_persona_prefers_silence")
            return self.last_decision
        hints = knowledge_hints or {}
        fingerprint = _context_fingerprint(
            hints.get("artist", ""), hints.get("summary", ""), hints.get("full_text", "")
        )
        if fingerprint and fingerprint in performance_memory.recent_context_fingerprints:
            self.last_decision = PlannerDecision(
                PlannerDecisionType.SILENCE, "no_fresh_session_context"
            )
            return self.last_decision
        choices = _prioritized_knowledge_choices(
            session_start_strategy=session_start_strategy,
            selected_mood=mood,
            persona=persona,
            session_direction=session_direction.direction,
            recommendation_preference=self.configuration.recommendation_preference,
        )
        choices = _space_recommendation_choices(
            choices,
            performance_memory=performance_memory,
            discover_context=discover_context,
            hints=hints,
        )
        choices = _space_recent_type_choices(
            choices,
            performance_memory=performance_memory,
            discover_context=discover_context,
            hints=hints,
        )
        for key, decision_type, intent_type, goal in choices:
            if _bounded_text(hints.get(key), 1200):
                if _performance_memory_repeats(
                    performance_memory, intent_type, hints
                ):
                    continue
                if _discover_context_repeats(discover_context, intent_type, hints):
                    continue
                intent = KnowledgeIntent(intent_type, goal)
                reason = (
                    f"discover_knowledge_hint:{key}"
                    if session_start_strategy is SessionStartStrategy.DISCOVER
                    else f"knowledge_hint:{key}"
                )
                self.last_decision = PlannerDecision(decision_type, reason, intent)
                return self.last_decision
        intent = KnowledgeIntent(
            KnowledgeIntentType.TRACK_CONTEXT,
            "Explain one relevant detail that improves appreciation of the current track.",
        )
        self.last_decision = PlannerDecision(PlannerDecisionType.CREATE_TRACK_CONTEXT, "track_context_appropriate", intent)
        return self.last_decision

    def record_spoken_moment(self) -> None:
        self.last_spoken_moment_at = self.elapsed_time_source()

    def select_intra_track_intent(
        self,
        *,
        first_type: DJMomentType,
        first_position_ms: int,
        first_read_seconds: int,
        observed_position_ms: int,
        duration_ms: int,
        safe_insight: dict[str, Any],
        performance_memory: PerformanceMemory,
        allowed_intents: frozenset[str] | None,
    ) -> KnowledgeIntent | None:
        """Approve one well-spaced, different evidenced current-track angle."""
        # This later contribution is Broadcast-only. Its observed spacing
        # leaves the first card readable and a short valid overlap for exit.
        minimum_gap_ms = max(15_000, min(60_000, (first_read_seconds - 15) * 1000))
        if (
            duration_ms < 180_000
            or observed_position_ms - first_position_ms < minimum_gap_ms
            or duration_ms - observed_position_ms < 45_000
        ):
            return None
        track = safe_insight.get("track", {})
        analysis = safe_insight.get("analysis", {})
        hints = _planner_knowledge_hints(safe_insight)
        if not all(hints.get(key) for key in ("title", "artist", "summary", "full_text")):
            return None
        choices = (
            (KnowledgeIntentType.GENRE_STORY, DJMomentType.GENRE, "genre_story"),
            (KnowledgeIntentType.TRACK_CONTEXT, DJMomentType.TRACK, "track_context"),
        )
        for intent_type, moment_type, capability in choices:
            if first_type is moment_type:
                continue
            if allowed_intents is not None and capability not in allowed_intents:
                continue
            if moment_type is DJMomentType.GENRE:
                if _primary_knowledge_evidence(intent_type, track, analysis) is None:
                    continue
                if _performance_memory_repeats(performance_memory, intent_type, hints):
                    continue
            elif first_type is not DJMomentType.GENRE:
                # Other first angles currently share Track Insight narrative
                # text; a Track card would merely repeat that text.
                continue
            return KnowledgeIntent(
                intent_type,
                "Add one distinct, source-backed perspective on the current track.",
            )
        return None

    def select_qualified_current_fact(
        self, *, facts: tuple[QualifiedSessionFact, ...], media_identity: str,
        used_keys: set[str], locale: str, allowed_intents: frozenset[str] | None,
        session_start_strategy: SessionStartStrategy, session_direction: SessionDirectionType,
        selected_mood: str, persona: DJPersona, performance_memory: PerformanceMemory,
        remaining_seconds: float,
        realized_copies: dict[int, tuple[str, str] | None] | None = None,
    ) -> tuple[KnowledgeIntent, QualifiedSessionFact] | None:
        """Rank only qualified, fitting current facts; never widen eligibility."""
        candidates = []
        now = time.monotonic()
        recent_type = _recent_factual_moment_type(performance_memory)
        for fact in facts:
            if fact.key in used_keys or not fact.eligible(media_identity, now):
                continue
            if isinstance(fact, SharedProducerFact) and not (
                session_start_strategy is SessionStartStrategy.DISCOVER
                and session_direction is SessionDirectionType.EXPLORING
            ):
                continue
            if allowed_intents is not None and fact.intent not in allowed_intents:
                continue
            localized = fact.copy_for(locale)
            if localized is None:
                continue
            if realized_copies is not None:
                localized = realized_copies.get(id(fact))
                if localized is None:
                    continue
            read_seconds = _presentation_intent(
                selected_mood, persona, reading_characters=sum(map(len, localized)),
                minimum_duration_seconds=40,
            ).maximum_duration_seconds
            if remaining_seconds < read_seconds + 5:
                continue
            moment_type = {"track_context": DJMomentType.TRACK, "album_story": DJMomentType.ALBUM,
                           "artist_story": DJMomentType.ARTIST}[fact.intent]
            score = {DJMomentType.TRACK: 30, DJMomentType.ALBUM: 20, DJMomentType.ARTIST: 10}[moment_type]
            reasons = ["current_scope"]
            if isinstance(fact, SharedProducerFact):
                score += 100
                reasons.append("shared_producer")
            if session_start_strategy is SessionStartStrategy.DISCOVER or session_direction is SessionDirectionType.EXPLORING:
                score += {DJMomentType.TRACK: 0, DJMomentType.ALBUM: 20, DJMomentType.ARTIST: 40}[moment_type]
                reasons.append("exploration")
            if session_direction is SessionDirectionType.DEEPENING:
                score += {DJMomentType.TRACK: 20, DJMomentType.ALBUM: 10, DJMomentType.ARTIST: 0}[moment_type]
                reasons.append("deepening")
            if moment_type is DJMomentType.ALBUM:
                if selected_mood in {"chill", "focus", "deep"}:
                    score += 5
                    reasons.append("mood_emphasis")
                if persona is DJPersona.RADIO_DJ:
                    score += 5
                    reasons.append("persona_emphasis")
            if recent_type is moment_type:
                score -= 25
                reasons.append("recent_type_demoted")
            # Stable complete tie-break: no dependence on retrieval order.
            rank = (-score, read_seconds, fact.key, fact.provider, fact.source_url, localized)
            candidates.append((rank, fact, reasons))
        if not candidates:
            self.last_decision = PlannerDecision(PlannerDecisionType.SILENCE, "contextual_fact:no_eligible_fit")
            return None
        _, fact, reasons = min(candidates, key=lambda candidate: candidate[0])
        intent = KnowledgeIntent(KnowledgeIntentType(fact.intent), "Share one qualified current-track fact.")
        decision_type = {KnowledgeIntentType.ARTIST_STORY: PlannerDecisionType.CREATE_ARTIST_STORY,
                         KnowledgeIntentType.ALBUM_STORY: PlannerDecisionType.CREATE_ALBUM_STORY}.get(intent.intent_type, PlannerDecisionType.CREATE_TRACK_CONTEXT)
        self.last_decision = PlannerDecision(decision_type, "contextual_fact:" + "+".join((*reasons, "readable_fit")), intent)
        return intent, fact

    def project_track_started_planning_input(
        self,
        *,
        session_id: str,
        upcoming_playback: UpcomingPlaybackProjection | None,
        session_start_strategy: SessionStartStrategy,
        session_direction: SessionDirection,
        selected_mood: str,
        persona: DJPersona,
        knowledge_hints: dict[str, Any],
        performance_memory: PerformanceMemory,
        discover_context: DiscoverContext,
    ) -> TrackStartedPlanningInput:
        """Project the existing deterministic choice into one current-track candidate."""
        previous_decision = self.last_decision
        decision = self.evaluate_track_started(
            session_start_strategy=session_start_strategy,
            session_direction=session_direction,
            selected_mood=selected_mood,
            persona=persona,
            knowledge_hints=knowledge_hints,
            performance_memory=performance_memory,
            discover_context=discover_context,
            record_track_available=False,
        )
        self.last_decision = previous_decision
        category = {
            PlannerDecisionType.SILENCE: "silence",
            PlannerDecisionType.CREATE_SESSION_UPDATE: "session_update",
        }.get(
            decision.decision_type,
            decision.knowledge_intent.intent_type.value if decision.knowledge_intent else "",
        )
        has_future_playback = bool(upcoming_playback and upcoming_playback.entries)
        candidate = (
            CandidatePlanningSlot(category, 0, 0, is_current_track=True)
            if not has_future_playback and category in PlannerIntentSelector._SUPPORTED
            else None
        )
        return TrackStartedPlanningInput(
            session_id=session_id,
            current_track_candidate=candidate,
            upcoming_playback=upcoming_playback,
            effective_mood=selected_mood.strip().lower(),
            effective_direction=session_direction.direction,
            performance_memory=performance_memory,
            planning_generation=self.horizon.invalidation_generation if self.horizon else 0,
            session_update_direction=decision.proposed_session_direction,
            planner_decision=decision,
        )

    def append_moment(
        self, moment: DJMoment, placement: SessionFlowPosition = SessionFlowPosition.NEXT
    ) -> DJSessionFlow:
        """Place an Engine-produced Moment without giving it scheduling control."""
        current = self.output.session_flow
        item = DJSessionFlowItem(
            item_id=f"moment-{moment.moment_id}",
            item_type=SessionFlowItemType.DJ_MOMENT,
            position=placement,
            label=moment.title,
            moment_id=moment.moment_id,
            moment_type=moment.moment_type.value,
        )
        flow = DJSessionFlow(
            flow_id=current.flow_id,
            flow_revision=current.flow_revision,
            planning_horizon_minutes=current.planning_horizon_minutes,
            created_at=_timestamp(),
            items=(*current.items, item),
        )
        return self._commit_session_flow(flow, SessionFlowChangeType.MOMENT_APPENDED)

    def note_discover_track_started(self) -> None:
        """Count only accepted observed opportunities, not duplicate URI polls."""
        self.discover_event_number += 1
        line = self.discover_narrative_line
        if line is not None and self.discover_event_number > line.event_number + 1:
            self.clear_discover_narrative()

    def clear_discover_narrative(self) -> None:
        """Close the one Runtime line without retaining its private identity."""
        self.discover_narrative_line = None
        self.discover_narrative_closed = True

    def evaluate_discover_narrative_after_moment(
        self,
        *,
        current_moment: DJMoment,
        strategy: SessionStartStrategy,
        session_direction: SessionDirection,
        selected_mood: str,
        persona: DJPersona,
        performance_memory: PerformanceMemory,
        evidence: NarrativeTrackEvidence | None,
    ) -> PlannerDecision | None:
        """Open once, then approve or abandon on the next accepted event."""
        if strategy is not SessionStartStrategy.DISCOVER or self.discover_narrative_closed:
            return None
        items = tuple(
            item for item in self.output.session_flow.items
            if item.item_type is SessionFlowItemType.DJ_MOMENT and item.moment_id
        )
        line = self.discover_narrative_line
        if line is not None:
            self.clear_discover_narrative()
            metadata = dict(current_moment.generation_metadata)
            if (
                self.discover_event_number != line.event_number + 1
                or evidence is None
                or current_moment.moment_type is not DJMomentType.TRACK
                or session_direction.direction is not line.direction
                or selected_mood != line.mood
                or persona is not line.persona
                or self.output.session_flow.flow_id != line.flow_id
                or self.output.session_flow.flow_revision != line.flow_revision + 1
                or len(items) < 2
                or items[-2].moment_id != line.source_moment_id
                or items[-2].moment_type != DJMomentType.GENRE.value
                or items[-1].moment_id != current_moment.moment_id
                or items[-1].moment_type != DJMomentType.TRACK.value
                or line.source_moment_id not in performance_memory.recent_moment_ids
                or DJMomentType.TRANSITION in performance_memory.recent_moment_types[-4:]
                or evidence.artist_id != line.artist_id
                or evidence.artist != line.artist
                or evidence.media_identity == line.media_identity
                or evidence.title == line.source_title
                or not any(genre.casefold() == line.genre.casefold() for genre in evidence.genres)
                or metadata.get("track_title") != evidence.title
                or metadata.get("artist") != evidence.artist
                or str(metadata.get("genre") or "").casefold() != line.genre.casefold()
            ):
                return None
            self.last_decision = PlannerDecision(
                PlannerDecisionType.CREATE_TRANSITION,
                "discover_same_artist_genre",
                KnowledgeIntent(
                    KnowledgeIntentType.TRANSITION,
                    "Connect the second observed track to the opened artist-genre context.",
                ),
                transition_moment_ids=(line.source_moment_id, current_moment.moment_id),
                transition_placement=SessionFlowPosition.NEXT.value,
                transition_relation="discover_same_artist_genre",
                transition_context=(
                    ("genre", line.genre),
                    ("artist", line.artist),
                    ("source_track", line.source_title),
                    ("target_track", evidence.title),
                ),
            )
            return self.last_decision
        metadata = dict(current_moment.generation_metadata)
        if (
            evidence is None
            or current_moment.moment_type is not DJMomentType.GENRE
            or session_direction.direction is not SessionDirectionType.EXPLORING
            or not items
            or items[-1].moment_id != current_moment.moment_id
            or current_moment.moment_id not in performance_memory.recent_moment_ids
            or DJMomentType.TRANSITION in performance_memory.recent_moment_types[-4:]
            or metadata.get("track_title") != evidence.title
            or metadata.get("artist") != evidence.artist
            or str(metadata.get("genre") or "").casefold() != current_moment.title.casefold()
            or not any(genre.casefold() == current_moment.title.casefold() for genre in evidence.genres)
        ):
            return None
        self.discover_narrative_line = DiscoverNarrativeLine(
            source_moment_id=current_moment.moment_id,
            source_title=evidence.title,
            artist=evidence.artist,
            genre=current_moment.title,
            media_identity=evidence.media_identity,
            artist_id=evidence.artist_id,
            mood=selected_mood,
            persona=persona,
            direction=session_direction.direction,
            event_number=self.discover_event_number,
            flow_id=self.output.session_flow.flow_id,
            flow_revision=self.output.session_flow.flow_revision,
        )
        return None

    def evaluate_transition_after_moment(
        self,
        *,
        triggering_intent: KnowledgeIntent,
        session_direction: SessionDirection,
        performance_memory: PerformanceMemory,
    ) -> PlannerDecision:
        """Approve one bounded Transition only when existing Flow context warrants it."""
        items = tuple(
            item
            for item in self.output.session_flow.items
            if item.item_type is SessionFlowItemType.DJ_MOMENT and item.moment_id
        )
        if (
            triggering_intent.intent_type is not KnowledgeIntentType.RECOMMENDATION
            or session_direction.direction is not SessionDirectionType.EXPLORING
            or len(items) < 2
            or DJMomentType.TRANSITION in performance_memory.recent_moment_types[-4:]
        ):
            return self._record_no_transition("transition_not_contextually_appropriate")
        previous, current = items[-2:]
        if (
            current.moment_type != DJMomentType.RECOMMENDATION.value
            or previous.moment_type
            not in {
                DJMomentType.TRACK.value,
                DJMomentType.ARTIST.value,
                DJMomentType.ALBUM.value,
                DJMomentType.GENRE.value,
            }
        ):
            return self._record_no_transition("transition_not_contextually_appropriate")
        intent = KnowledgeIntent(
            KnowledgeIntentType.TRANSITION,
            "Bridge the preceding music context into this exploration recommendation.",
        )
        self.last_decision = PlannerDecision(
            PlannerDecisionType.CREATE_TRANSITION,
            "exploring_recommendation_after_context",
            intent,
            transition_moment_ids=(previous.moment_id, current.moment_id),
            transition_placement=SessionFlowPosition.NEXT.value,
        )
        return self.last_decision

    def _record_no_transition(self, reason: str) -> PlannerDecision:
        """Keep an ordinary no-transition decision silent and explicit."""
        self.last_decision = PlannerDecision(PlannerDecisionType.NO_TRANSITION, reason)
        return self.last_decision

    def as_dict(self) -> dict[str, Any]:
        """Return the public Planner state and its owned Session Flow."""
        return {
            "planner_state": str(self.planner_state),
            "planning_horizon_minutes": self.planning_horizon_minutes,
            "created_at": self.created_at,
            "last_replan_at": self.last_replan_at,
            "current_goal": self.current_goal,
            "configuration": self.configuration.as_dict(),
            "pending_events": [str(event) for event in self.pending_events],
            "output": self.output.as_dict(),
        }


@dataclass(frozen=True)
class QualifiedFactRealization:
    summary: str
    content: str
    source_key: str
    expression_form: str = ""


@dataclass
class DJMomentEngine:
    """Runtime-owned creative execution for a bounded first Moment slice."""

    moments: tuple[DJMoment, ...] = ()
    _track_keys: set[str] = field(default_factory=set, repr=False)
    _expression_forms: tuple[str, ...] = field(default=(), repr=False)
    _expression_moment_ids: tuple[str, ...] = field(default=(), repr=False)

    @staticmethod
    def fact_key(fact: QualifiedSessionFact) -> str:
        key = f"{fact.source_url}|fact:{fact.key}"
        return key + ("|" + "|".join(fact.relation_key) if isinstance(fact,SharedProducerFact) else "")

    def preview_qualified_fact(self, *, fact: QualifiedSessionFact, selected_mood: str,
                               persona: DJPersona, locale: str, remaining_seconds: float) -> QualifiedFactRealization | None:
        """Pure Moment realization/read-fit; rejected previews have no memory."""
        original = fact.copy_for(locale)
        if original is None or not fact.eligible(fact.media_identity,time.monotonic()):
            return None
        last = next((key for key in reversed(self._expression_forms) if key.startswith(persona.value+":"+fact.key+":")), "")
        form = (int(last.rsplit(":",1)[-1])+1)%4 if last else 0
        try:
            expressed = realize_fact_expression(fact,locale=locale,persona=persona.value,form=form,mood=selected_mood)
        except (TypeError,ValueError,KeyError,IndexError,AttributeError):
            expressed = None
        variants = ((expressed, f"{persona.value}:{fact.key}:{form}" if fact.key in {"recording_credits", "shared_producer"} else ""), (original, ""))
        for localized, expression_form in variants:
            if localized is None:
                continue
            summary,content=localized
            characters=len(summary)+len(content)
            # Never let duration clamping or the renderer's text bound hide an
            # oversized fact. The exact source copy is the final short fallback.
            if len(summary)>320 or len(content)>1200 or characters>90*14:
                continue
            read_seconds=_presentation_intent(selected_mood,persona,reading_characters=characters,
                minimum_duration_seconds=40).maximum_duration_seconds
            if read_seconds+5 <= remaining_seconds:
                return QualifiedFactRealization(summary,content,self.fact_key(fact),expression_form)
        return None

    def commit_expression(self, moment: DJMoment, flow: DJSessionFlow) -> None:
        """Only actual published Flow may advance the bounded style sequence."""
        if (moment.expression_form and moment.moment_id not in self._expression_moment_ids
                and any(item.moment_id==moment.moment_id for item in flow.items)):
            self._expression_forms=(*self._expression_forms,moment.expression_form)[-6:]
            self._expression_moment_ids=(*self._expression_moment_ids,moment.moment_id)[-6:]

    def create_track_context(
        self,
        *,
        session_id: str,
        knowledge_intent: KnowledgeIntent,
        selected_mood: str,
        persona: DJPersona,
        locale: str,
        insight: dict[str, Any],
        source_insight: dict[str, Any] | None = None,
        fact_realization: QualifiedFactRealization | None = None,
    ) -> DJMoment:
        """Translate one selected Knowledge Context into one frozen Moment."""
        qualified = insight.get("_qualified_fact")
        if isinstance(qualified, QualifiedSessionFact):
            return self.create_qualified_fact(session_id=session_id, intent=knowledge_intent, fact=qualified,
                                              selected_mood=selected_mood, persona=persona, locale=locale, realization=fact_realization)
        track = insight.get("track") if isinstance(insight.get("track"), dict) else {}
        analysis = insight.get("analysis") if isinstance(insight.get("analysis"), dict) else {}
        title = _bounded_text(track.get("title"), 160)
        artist = _bounded_text(track.get("artist"), 160)
        summary = _bounded_text(analysis.get("summary"), 320)
        content = _bounded_text(analysis.get("full_text"), 1200)
        track_key = _track_key(track)
        if not title or not artist or not summary or not content or not track_key:
            return self.create_silence(
                session_id=session_id,
                selected_mood=selected_mood,
                persona=persona,
                locale=locale,
                reason="invalid_ai_output",
            )
        specialized = _specialize_track_moment(
            track, analysis, title, artist, summary, content, knowledge_intent.intent_type,
            locale,
        )
        if specialized is None:
            return self.create_silence(
                session_id=session_id,
                selected_mood=selected_mood,
                persona=persona,
                locale=locale,
                reason="invalid_knowledge_context",
            )
        moment_type, title, summary, content = specialized
        source_hints = _planner_knowledge_hints(source_insight or insight)
        angle_key = f"{track_key}|{moment_type.value}"
        if angle_key in self._track_keys:
            return self.create_silence(
                session_id=session_id,
                selected_mood=selected_mood,
                persona=persona,
                locale=locale,
                reason="duplicate_track_context",
            )
        self._track_keys.add(angle_key)
        moment = DJMoment(
            moment_id=f"moment-{uuid4().hex}",
            session_id=session_id,
            created_at=_timestamp(),
            moment_type=moment_type,
            knowledge_intent=KnowledgeIntent(
                knowledge_intent.intent_type, knowledge_intent.goal, track_key
            ),
            presentation_intent=_presentation_intent(
                selected_mood, persona, reading_characters=len(summary) + len(content),
                minimum_duration_seconds=45 if moment_type is DJMomentType.GENRE else 25,
            ),
            title=title,
            summary=summary,
            content=content,
            artwork_url=_bounded_text(track.get("artwork_url"), 2048) or None,
            actions=_moment_actions(moment_type, track, locale),
            source_references=("track_insight",),
            source_context_fingerprint=_context_fingerprint(
                source_hints["artist"], source_hints["summary"], source_hints["full_text"]
            ),
            generation_metadata=(
                ("provider", "track_insight"),
                ("track_title", _bounded_text(track.get("title"), 160)),
                ("artist", _bounded_text(track.get("artist"), 160)),
                ("album", _bounded_text(track.get("album"), 160)),
                (
                    "genre",
                    _bounded_text(analysis.get("genre"), 160)
                    or _bounded_text(track.get("genres"), 160),
                ),
                (
                    "recommendation",
                    _bounded_text(track.get("artist"), 160)
                    if moment_type is DJMomentType.RECOMMENDATION
                    else "",
                ),
                ("validated", "true"),
            ),
        )
        self.moments = (*self.moments, moment)
        return moment

    def create_qualified_fact(self, *, session_id: str, intent: KnowledgeIntent, fact: QualifiedSessionFact,
                              selected_mood: str, persona: DJPersona, locale: str,
                              realization: QualifiedFactRealization | None = None) -> DJMoment:
        realization = realization or self.preview_qualified_fact(fact=fact,selected_mood=selected_mood,
            persona=persona,locale=locale,remaining_seconds=float("inf"))
        key = self.fact_key(fact)
        expected = self.preview_qualified_fact(fact=fact,selected_mood=selected_mood,persona=persona,locale=locale,
            remaining_seconds=float("inf"))
        faithful_fallback = bool(realization and not realization.expression_form
            and (realization.summary,realization.content)==fact.copy_for(locale)
            and len(realization.summary)+len(realization.content)<=90*14
            and len(realization.summary)<=320 and len(realization.content)<=1200)
        if realization is None or (realization != expected and not faithful_fallback) or realization.source_key != key or not fact.eligible(fact.media_identity, time.monotonic()) or fact.intent != intent.intent_type.value or key in self._track_keys:
            return self.create_silence(session_id=session_id, selected_mood=selected_mood, persona=persona, locale=locale, reason="unqualified_or_duplicate_fact")
        summary, content = realization.summary, realization.content
        self._track_keys.add(key)
        moment_type = {"artist_story": DJMomentType.ARTIST, "album_story": DJMomentType.ALBUM, "genre_story": DJMomentType.GENRE}.get(fact.intent, DJMomentType.TRACK)
        moment = DJMoment(moment_id=f"moment-{uuid4().hex}", session_id=session_id, created_at=_timestamp(), moment_type=moment_type,
                          knowledge_intent=intent, presentation_intent=_presentation_intent(selected_mood, persona, reading_characters=len(summary)+len(content), minimum_duration_seconds=40),
                          title=summary, summary=summary, content=content, artwork_url=None, actions=(), source_references=(fact.provider,),
                          generation_metadata=(("provider", fact.provider), ("validated", "true")), source_context_fingerprint=hashlib.sha256(key.encode()).hexdigest(),
                          source_attribution=(("provider", fact.provider), ("url", fact.source_url), ("license", fact.license))
                          + ((("url_previous", fact.previous_evidence.source_url),)
                             if isinstance(fact, SharedProducerFact) and fact.previous_evidence else ()),
                          visual_only=True, expression_form=realization.expression_form, source_fact=fact)
        self.moments = (*self.moments, moment)
        return moment

    def create_silence(
        self,
        *,
        session_id: str,
        selected_mood: str,
        persona: DJPersona,
        locale: str,
        reason: str,
    ) -> DJMoment:
        """Record intentional non-interruption without creating fake content."""
        moment = DJMoment(
            moment_id=f"moment-{uuid4().hex}",
            session_id=session_id,
            created_at=_timestamp(),
            moment_type=DJMomentType.SILENCE,
            knowledge_intent=KnowledgeIntent(KnowledgeIntentType.SILENCE, "Do not interrupt the music."),
            presentation_intent=_presentation_intent(selected_mood, persona),
            title=_moment_copy(locale, "silence_title"),
            summary=_moment_copy(locale, "silence_summary"),
            content="",
            artwork_url=None,
            actions=(),
            source_references=(),
            generation_metadata=(("reason", reason), ("validated", "true")),
        )
        self.moments = (*self.moments, moment)
        return moment

    def create_transition(
        self,
        *,
        session_id: str,
        approval: PlannerDecision | None,
        selected_mood: str,
        persona: DJPersona,
        locale: str,
    ) -> DJMoment:
        """Perform only one complete Planner-approved Transition decision."""
        if not _valid_transition_approval(approval):
            return self.create_silence(
                session_id=session_id,
                selected_mood=selected_mood,
                persona=persona,
                locale=locale,
                reason="invalid_transition_approval",
            )
        source_id, target_id = approval.transition_moment_ids
        moments = {moment.moment_id: moment for moment in self.moments}
        source = moments.get(source_id)
        target = moments.get(target_id)
        relation = approval.transition_relation
        if (
            source is None
            or target is None
            or source.session_id != session_id
            or target.session_id != session_id
            or (
                not _valid_discover_transition_context(approval, source, target)
                if relation == "discover_same_artist_genre"
                else source.moment_type not in {
                    DJMomentType.TRACK, DJMomentType.ARTIST,
                    DJMomentType.ALBUM, DJMomentType.GENRE,
                } or target.moment_type is not DJMomentType.RECOMMENDATION
            )
        ):
            return self.create_silence(
                session_id=session_id,
                selected_mood=selected_mood,
                persona=persona,
                locale=locale,
                reason="invalid_transition_context",
            )
        context = dict(approval.transition_context)
        def copy(part: str) -> str:
            if relation == "discover_same_artist_genre":
                return _discover_transition_copy(locale, part, context)
            return _transition_copy(locale, part, source.title, target.title)
        moment = DJMoment(
            moment_id=f"moment-{uuid4().hex}",
            session_id=session_id,
            created_at=_timestamp(),
            moment_type=DJMomentType.TRANSITION,
            knowledge_intent=approval.knowledge_intent,
            presentation_intent=_presentation_intent(selected_mood, persona),
            title=copy("title"),
            summary=copy("summary"),
            content=copy("content"),
            artwork_url=None,
            actions=(),
            source_references=("session_flow",),
            generation_metadata=(
                ("transition_from_moment_id", source.moment_id),
                ("transition_to_moment_id", target.moment_id),
                ("placement", approval.transition_placement),
                *((("relation", relation),) if relation else ()),
                ("validated", "true"),
            ),
        )
        self.moments = (*self.moments, moment)
        return moment

    def create_session_update(
        self,
        *,
        session_id: str,
        selected_mood: str,
        persona: DJPersona,
        locale: str,
        session_direction: SessionDirection,
        knowledge_context: "KnowledgeContext | None",
    ) -> DJMoment:
        """Realize one Planner-approved Direction change from safe Session context."""
        if not _valid_session_update_context(
            knowledge_context, session_direction, selected_mood
        ):
            return self.create_silence(
                session_id=session_id,
                selected_mood=selected_mood,
                persona=persona,
                locale=locale,
                reason="invalid_session_update_context",
            )
        direction = knowledge_context.session_direction.direction
        moment = DJMoment(
            moment_id=f"moment-{uuid4().hex}",
            session_id=session_id,
            created_at=_timestamp(),
            moment_type=DJMomentType.SESSION,
            knowledge_intent=KnowledgeIntent(
                KnowledgeIntentType.SESSION_DIRECTION,
                "Communicate the updated direction of the active DJ Session.",
            ),
            presentation_intent=_presentation_intent(selected_mood, persona),
            title=_session_direction_copy(locale, direction, "title"),
            summary=_session_direction_copy(locale, direction, "summary"),
            content=_session_direction_copy(locale, direction, "content"),
            artwork_url=None,
            actions=(),
            source_references=("session_direction",),
            generation_metadata=(
                ("direction", direction.value),
                ("start_strategy", knowledge_context.session_start_strategy.value),
                ("context_source", "session_direction"),
                ("validated", "true"),
            ),
        )
        self.moments = (*self.moments, moment)
        return moment


@dataclass(frozen=True)
class KnowledgeContext:
    """Validated, renderer-safe knowledge assembled for one Intent."""

    track: tuple[tuple[str, str], ...]
    analysis: tuple[tuple[str, str], ...]
    sources: tuple[str, ...]
    personal_context_used: bool = False
    session_direction: SessionDirection | None = None
    session_start_strategy: SessionStartStrategy | None = None
    session_mood: str = ""
    discover_context: DiscoverContext | None = None
    performance_memory: PerformanceMemory | None = None
    qualified_fact: QualifiedSessionFact | None = None

    def as_insight(self) -> dict[str, Any]:
        """Adapt the safe context to the existing Moment Engine contract."""
        insight = {"track": dict(self.track), "analysis": dict(self.analysis)}
        if self.qualified_fact is not None:
            insight["_qualified_fact"] = self.qualified_fact
        if self.session_direction is not None:
            insight["session_direction"] = self.session_direction.as_dict()
        if self.session_start_strategy is not None:
            insight["session_start_strategy"] = self.session_start_strategy.value
        if self.session_mood:
            insight["session_mood"] = self.session_mood
        if self.discover_context is not None:
            insight["discover_context"] = self.discover_context.as_dict()
        if self.performance_memory is not None:
            insight["performance_memory"] = self.performance_memory.as_dict()
        return insight


@dataclass
class DJKnowledgeEngine:
    """Runtime-scoped assembly of relevant knowledge; never presentation."""

    assembled_contexts: tuple[KnowledgeContext, ...] = ()

    def assemble_qualified_fact(self, *, intent: KnowledgeIntent, fact: QualifiedSessionFact,
                                media_identity: str, locale: str) -> KnowledgeContext | None:
        """Accept only typed, fresh, exact-subject, attributable display evidence."""
        if fact.intent != intent.intent_type.value or not fact.eligible(media_identity, time.monotonic()) or not fact.copy_for(locale):
            return None
        # Qualified source proof is a transient handoff to Moment, not Knowledge
        # diagnostic history. Only the bounded published Runtime context owns it.
        return KnowledgeContext(track=(), analysis=(), sources=(fact.provider,), qualified_fact=fact)

    def select_discover_narrative_evidence(
        self, raw_insight: dict[str, Any], observed_media_identity: str
    ) -> NarrativeTrackEvidence | None:
        """Select only private, status-bound artist/genre proof for this event."""
        private = raw_insight.get("_session_narrative_evidence")
        track = raw_insight.get("track")
        if not isinstance(private, dict) or not isinstance(track, dict):
            return None
        media_identity = str(private.get("media_identity") or "").strip()
        artist_ids = private.get("artist_ids")
        genres = private.get("genres")
        if (
            private.get("source") != "spotify_playback_status"
            or private.get("backend") != "spotify_direct"
            or track.get("backend") != "spotify_direct"
            or private.get("is_playing") is not True
            or media_identity != observed_media_identity
            or not re.fullmatch(r"spotify:track:[A-Za-z0-9_-]{8,64}", media_identity)
            or not isinstance(artist_ids, list)
            or len(artist_ids) != 1
            or not isinstance(genres, list)
        ):
            return None
        artist_id = str(artist_ids[0] or "").strip()
        if not re.fullmatch(r"[A-Za-z0-9_-]{8,64}", artist_id):
            return None
        title = _narrative_label(private.get("title"), 160)
        artist = _narrative_label(private.get("artist"), 160)
        if (
            not title or not artist
            or title != _narrative_label(track.get("title"), 160)
            or artist != _narrative_label(track.get("artist"), 160)
        ):
            return None
        selected_genres = tuple(
            dict.fromkeys(
                label for value in genres[:10]
                if (label := _narrative_label(value, 80))
            )
        )
        track_genres = track.get("genres")
        if (
            not selected_genres
            or not isinstance(track_genres, list)
            or not all(genre in track_genres for genre in selected_genres)
        ):
            return None
        return NarrativeTrackEvidence(
            media_identity, artist_id, selected_genres, title, artist
        )

    async def async_assemble_track_context(
        self,
        *,
        intent: KnowledgeIntent,
        raw_insight: dict[str, Any],
        session_direction: SessionDirection | None = None,
        session_start_strategy: SessionStartStrategy | None = None,
        session_mood: str = "",
        discover_context: DiscoverContext | None = None,
        performance_memory: PerformanceMemory | None = None,
        personal_context_authorized: bool = False,
    ) -> KnowledgeContext:
        """Reuse Track Insight while excluding raw Profile and Music DNA data."""
        track = raw_insight.get("track") if isinstance(raw_insight.get("track"), dict) else {}
        analysis = raw_insight.get("analysis") if isinstance(raw_insight.get("analysis"), dict) else {}
        primary_evidence = _primary_knowledge_evidence(intent.intent_type, track, analysis)
        if primary_evidence is not None:
            evidence_source, evidence_key, evidence_value = primary_evidence
            track_values = {
                key: _bounded_text(track.get(key), 2048)
                for key in ("title", "artist", "album", "artwork_url", "backend")
            }
            analysis_values = {
                key: _bounded_text(analysis.get(key), 1200)
                for key in ("summary", "full_text")
            }
            if evidence_source == "track":
                track_values[evidence_key] = evidence_value
            else:
                analysis_values[evidence_key] = evidence_value
            return self._record(
                KnowledgeContext(
                    track=tuple((key, value) for key, value in track_values.items() if value),
                    analysis=tuple((key, value) for key, value in analysis_values.items() if value),
                    sources=("track_insight",),
                    personal_context_used=personal_context_authorized,
                    session_direction=session_direction,
                    session_start_strategy=session_start_strategy,
                    session_mood=session_mood,
                    discover_context=discover_context,
                    performance_memory=performance_memory,
                )
            )
        if intent.intent_type in _PRIMARY_EVIDENCE_INTENTS:
            return self._record(
                KnowledgeContext(
                    (), (), ("track_insight",),
                    personal_context_used=personal_context_authorized,
                    session_direction=session_direction,
                    session_start_strategy=session_start_strategy,
                    session_mood=session_mood,
                    discover_context=discover_context,
                    performance_memory=performance_memory,
                )
            )
        track_fields, analysis_fields = _knowledge_fields_for_intent(intent.intent_type)
        context = KnowledgeContext(
            track=tuple(
                (key, value)
                for key, value in ((key, _bounded_text(track.get(key), 2048)) for key in track_fields)
                if value
            ),
            analysis=tuple(
                (key, value)
                for key, value in ((key, _bounded_text(analysis.get(key), 1200)) for key in analysis_fields)
                if value
            ),
            sources=("track_insight",),
            personal_context_used=personal_context_authorized,
            session_direction=session_direction,
            session_start_strategy=session_start_strategy,
            session_mood=session_mood,
            discover_context=discover_context,
            performance_memory=performance_memory,
        )
        return self._record(context)

    async def async_resolve_approved_planned_intent(
        self,
        *,
        approved_intent: PlannerIntent,
        planned_intent: PlannedIntent,
        knowledge_intent: KnowledgeIntent,
        prefetch: KnowledgePrefetch,
        prepared_knowledge: tuple[PreparedKnowledge, ...],
        invalidation_generation: int,
        raw_insight: dict[str, Any],
        session_direction: SessionDirection | None = None,
        session_start_strategy: SessionStartStrategy | None = None,
        session_mood: str = "",
        discover_context: DiscoverContext | None = None,
        performance_memory: PerformanceMemory | None = None,
        personal_context_authorized: bool = False,
    ) -> KnowledgeContext:
        """Resolve an approved future intent from valid prefetch output or existing input."""
        prepared_context = self._matching_prepared_context(
            approved_intent=approved_intent,
            planned_intent=planned_intent,
            knowledge_intent=knowledge_intent,
            prefetch=prefetch,
            prepared_knowledge=prepared_knowledge,
            invalidation_generation=invalidation_generation,
            session_direction=session_direction,
            session_start_strategy=session_start_strategy,
            session_mood=session_mood,
            discover_context=discover_context,
            performance_memory=performance_memory,
            personal_context_authorized=personal_context_authorized,
        )
        if prepared_context is not None:
            return self._record(prepared_context)
        return await self.async_assemble_track_context(
            intent=knowledge_intent,
            raw_insight=raw_insight,
            session_direction=session_direction,
            session_start_strategy=session_start_strategy,
            session_mood=session_mood,
            discover_context=discover_context,
            performance_memory=performance_memory,
            personal_context_authorized=personal_context_authorized,
        )

    @staticmethod
    def _matching_prepared_context(
        *,
        approved_intent: PlannerIntent,
        planned_intent: PlannedIntent,
        knowledge_intent: KnowledgeIntent,
        prefetch: KnowledgePrefetch,
        prepared_knowledge: tuple[PreparedKnowledge, ...],
        invalidation_generation: int,
        session_direction: SessionDirection | None,
        session_start_strategy: SessionStartStrategy | None,
        session_mood: str,
        discover_context: DiscoverContext | None,
        performance_memory: PerformanceMemory | None,
        personal_context_authorized: bool,
    ) -> KnowledgeContext | None:
        """Accept one exact, current prepared result without mutating it."""
        expected_category = {
            "artist_story": "artist",
            "album_story": "album",
            "genre_story": "genre",
            "recommendation": "recommendation",
        }.get(planned_intent.category)
        same_prefetch_target = (
            prefetch.target_intent.category == planned_intent.category
            and prefetch.target_intent.slot == planned_intent.slot
            and prefetch.target_intent.generation == planned_intent.generation
        )
        if (
            planned_intent.status is not PlannedIntentStatus.APPROVED
            or approved_intent != planned_intent.as_planner_intent()
            or knowledge_intent.intent_type.value != planned_intent.category
            or expected_category is None
            or not same_prefetch_target
            or prefetch.status is not KnowledgePrefetchStatus.PLANNED
            or prefetch.knowledge_category != expected_category
            or prefetch.planning_generation != planned_intent.generation
            or prefetch.invalidation_generation != invalidation_generation
        ):
            return None
        expected_request_id = KnowledgePrefetchRequest.from_prefetch(
            prefetch, subject_projection=()
        ).request_id
        prepared = next(
            (
                result
                for result in prepared_knowledge
                if result.request_id == expected_request_id
            ),
            None,
        )
        if (
            prepared is None
            or prepared.status is not PreparedKnowledgeStatus.PREPARED
            or not prepared.is_valid
            or prepared.planning_generation != planned_intent.generation
            or prepared.knowledge_category != expected_category
            or prepared.confidence < prefetch.knowledge_confidence
            or prepared.freshness < prefetch.freshness
            or len(prepared.projection) != 1
        ):
            return None
        subject_key, subject_value = prepared.projection[0]
        if subject_key != expected_category or _bounded_text(subject_value, 256) != subject_value:
            return None
        track = ()
        analysis = ()
        if expected_category == "genre":
            analysis = (("genre", subject_value),)
        elif expected_category == "recommendation":
            track = (("related_tracks", subject_value),)
        else:
            track = ((expected_category, subject_value),)
        return KnowledgeContext(
            track=track,
            analysis=analysis,
            sources=("prepared_knowledge",),
            personal_context_used=personal_context_authorized,
            session_direction=session_direction,
            session_start_strategy=session_start_strategy,
            session_mood=session_mood,
            discover_context=discover_context,
            performance_memory=performance_memory,
        )

    def assemble_session_direction_context(
        self,
        session_direction: SessionDirection,
        session_start_strategy: SessionStartStrategy,
        session_mood: str,
        performance_memory: PerformanceMemory,
    ) -> KnowledgeContext:
        """Record Runtime-owned Direction as safe context without provider access."""
        return self._record(
            KnowledgeContext(
                (), (), ("session_direction",), session_direction=session_direction,
                session_start_strategy=session_start_strategy,
                session_mood=session_mood,
                performance_memory=performance_memory,
            )
        )

    def execute_prefetch(self, request: KnowledgePrefetchRequest) -> PreparedKnowledge:
        """Validate a bounded request using only already-observable subject context."""
        required_subject = {
            "artist": "artist",
            "album": "album",
            "genre": "genre",
            "recommendation": "recommendation",
        }
        subject_key = required_subject.get(request.knowledge_category)
        if subject_key is None:
            return PreparedKnowledge(
                request.request_id,
                request.planning_generation,
                request.knowledge_category,
                PreparedKnowledgeStatus.UNSUPPORTED,
            )
        if request.required_confidence <= 0:
            return PreparedKnowledge(
                request.request_id,
                request.planning_generation,
                request.knowledge_category,
                PreparedKnowledgeStatus.INVALID,
            )
        if request.freshness_constraint <= 0:
            return PreparedKnowledge(
                request.request_id,
                request.planning_generation,
                request.knowledge_category,
                PreparedKnowledgeStatus.STALE,
            )
        subject = dict(request.subject_projection)
        value = subject.get(subject_key, "")
        if not value:
            return PreparedKnowledge(
                request.request_id,
                request.planning_generation,
                request.knowledge_category,
                PreparedKnowledgeStatus.UNAVAILABLE,
            )
        return PreparedKnowledge(
            request.request_id,
            request.planning_generation,
            request.knowledge_category,
            PreparedKnowledgeStatus.PREPARED,
            projection=((subject_key, value),),
            confidence=min(1.0, request.required_confidence),
            freshness=min(1.0, request.freshness_constraint),
            is_valid=True,
        )

    def _record(self, context: KnowledgeContext) -> KnowledgeContext:
        self.assembled_contexts = (*self.assembled_contexts, context)
        return context


@dataclass
class KnowledgePrefetchExecutionBoundary:
    """Runtime-only boundary separating Planner eligibility from knowledge validation."""

    def submit(
        self,
        *,
        prefetch: KnowledgePrefetch,
        subject_projection: tuple[tuple[str, str], ...],
        window: PlanningWindow,
        invalidation_generation: int,
        knowledge_engine: DJKnowledgeEngine,
    ) -> PreparedKnowledge:
        """Submit one eligible requirement without retrieval, queuing or caching."""
        request = KnowledgePrefetchRequest.from_prefetch(
            prefetch, subject_projection=subject_projection
        )
        active = any(
            candidate == prefetch
            and candidate.status is KnowledgePrefetchStatus.PLANNED
            and candidate.planning_generation == window.generation
            and candidate.invalidation_generation == invalidation_generation
            for candidate in window.knowledge_prefetches
        )
        if not active:
            return PreparedKnowledge(
                request.request_id,
                request.planning_generation,
                request.knowledge_category,
                PreparedKnowledgeStatus.SUPERSEDED,
            )
        if prefetch.target_intent.status is not PlannedIntentStatus.PLANNED:
            return PreparedKnowledge(
                request.request_id,
                request.planning_generation,
                request.knowledge_category,
                PreparedKnowledgeStatus.CANCELLED,
            )
        return knowledge_engine.execute_prefetch(request)


@dataclass
class PlanningRuntimeCoordinator:
    """Runtime-only coordinator for the existing planning and knowledge lifecycle."""

    last_planning_generation: int | None = None
    last_lifecycle_state: str = "idle"
    last_fallback_reason: str | None = None
    last_approval_source: str | None = None
    last_realized_intent: PlannedIntent | None = None
    last_session_direction: SessionDirection | None = None
    disposed: bool = False

    async def async_coordinate_track_started(
        self,
        *,
        planner: DJSessionPlanner,
        knowledge_engine: DJKnowledgeEngine,
        moment_engine: DJMomentEngine,
        session_id: str,
        selected_mood: str,
        persona: DJPersona,
        locale: str,
        session_direction: SessionDirection,
        session_start_strategy: SessionStartStrategy,
        performance_memory: PerformanceMemory,
        discover_context: DiscoverContext,
        raw_insight: dict[str, Any],
        planning_input: TrackStartedPlanningInput,
        allowed_intents: frozenset[str] | None = None,
    ) -> DJMoment | None:
        """Run the authoritative planning lifecycle; ``None`` preserves fallback."""
        self.last_lifecycle_state = "entered"
        self.last_fallback_reason = None
        self.last_approval_source = None
        self.last_realized_intent = None
        self.last_session_direction = None
        horizon = planner.horizon
        if self.disposed or horizon is None:
            return self._fallback("planning_runtime_unavailable")
        influence = PlannerInfluence.normalize(
            mood=selected_mood,
            direction=session_direction.direction,
            performance_memory=performance_memory,
            generation=horizon.invalidation_generation,
        )
        window = horizon.replan(
            upcoming_playback=planning_input.upcoming_playback,
            influence=influence,
            current_track_candidate=planning_input.current_track_candidate,
            allowed_intents=allowed_intents,
        )
        self.last_planning_generation = window.generation
        prefetches = window.plan_knowledge_prefetches(
            invalidation_generation=horizon.invalidation_generation,
            previous_prefetches=window.knowledge_prefetches,
        )
        subject_projection = _planning_subject_projection(raw_insight)
        boundary = KnowledgePrefetchExecutionBoundary()
        prepared = tuple(
            boundary.submit(
                prefetch=prefetch,
                subject_projection=subject_projection,
                window=window,
                invalidation_generation=horizon.invalidation_generation,
                knowledge_engine=knowledge_engine,
            )
            for prefetch in prefetches
            if prefetch.status is KnowledgePrefetchStatus.PLANNED
        )
        window.evaluate_readiness(
            prepared, invalidation_generation=horizon.invalidation_generation
        )
        approved = window.approve_earliest_planned_intent()
        if approved is None:
            if allowed_intents is not None:
                self.last_lifecycle_state = "completed"
                return moment_engine.create_silence(
                    session_id=session_id,
                    selected_mood=selected_mood,
                    persona=persona,
                    locale=locale,
                    reason="capability_policy_no_eligible_intent",
                )
            return self._fallback("no_ready_planned_intent")
        planned = next(
            (
                intent
                for intent in window.planned_intents
                if intent.status is PlannedIntentStatus.APPROVED
                and intent.as_planner_intent() == approved
            ),
            None,
        )
        if planned is None:
            return self._fallback("planning_state_invalid")
        self.last_approval_source = "planned_intent"
        if planned.category == "silence":
            moment = moment_engine.create_silence(
                session_id=session_id,
                selected_mood=selected_mood,
                persona=persona,
                locale=locale,
                reason="planned_silence",
            )
            self.last_realized_intent = planned
            self.last_lifecycle_state = "completed"
            return moment
        if planned.category == "session_update":
            direction = planning_input.session_update_direction
            if direction is None:
                return self._fallback("session_update_direction_unavailable")
            updated_direction = SessionDirection(
                direction=direction,
                initialized_at=session_direction.initialized_at,
                updated_at=_timestamp(),
                start_strategy=session_direction.start_strategy,
            )
            knowledge = knowledge_engine.assemble_session_direction_context(
                updated_direction,
                session_start_strategy,
                selected_mood,
                performance_memory,
            )
            moment = moment_engine.create_session_update(
                session_id=session_id,
                selected_mood=selected_mood,
                persona=persona,
                locale=locale,
                session_direction=updated_direction,
                knowledge_context=knowledge,
            )
            self.last_session_direction = updated_direction
            self.last_realized_intent = planned
            self.last_lifecycle_state = "completed"
            return moment
        prefetch = next(
            (
                candidate
                for candidate in prefetches
                if candidate.target_intent.category == planned.category
                and candidate.target_intent.slot == planned.slot
                and candidate.target_intent.generation == planned.generation
            ),
            None,
        )
        knowledge_intent = _knowledge_intent_for_planned_category(planned.category)
        if knowledge_intent is None:
            return self._fallback("unsupported_planned_intent")
        if prefetch is None:
            knowledge = await knowledge_engine.async_assemble_track_context(
                intent=knowledge_intent,
                raw_insight=raw_insight,
                session_direction=session_direction,
                session_start_strategy=session_start_strategy,
                session_mood=selected_mood,
                discover_context=discover_context,
                performance_memory=performance_memory,
            )
        else:
            knowledge = await knowledge_engine.async_resolve_approved_planned_intent(
                approved_intent=approved,
                planned_intent=planned,
                knowledge_intent=knowledge_intent,
                prefetch=prefetch,
                prepared_knowledge=prepared,
                invalidation_generation=horizon.invalidation_generation,
                raw_insight=raw_insight,
                session_direction=session_direction,
                session_start_strategy=session_start_strategy,
                session_mood=selected_mood,
                discover_context=discover_context,
                performance_memory=performance_memory,
            )
        moment = moment_engine.create_track_context(
            session_id=session_id,
            knowledge_intent=knowledge_intent,
            selected_mood=selected_mood,
            persona=persona,
            locale=locale,
            insight=_planning_realization_insight(knowledge, raw_insight, knowledge_intent),
            source_insight=raw_insight,
        )
        if moment.moment_type is DJMomentType.SILENCE:
            self.last_realized_intent = planned
            self.last_lifecycle_state = "completed"
            return moment
        self.last_realized_intent = planned
        self.last_lifecycle_state = "completed"
        return moment

    def confirm_published(self, planner: DJSessionPlanner) -> None:
        """Consume a planned occurrence only after Runtime publication succeeds."""
        if self.last_realized_intent is not None and planner.horizon is not None:
            planner.horizon.mark_planned_intent_consumed(self.last_realized_intent)
        self.last_realized_intent = None

    def _fallback(self, reason: str) -> DJMoment | None:
        """Record the bounded reason before the Runtime invokes legacy orchestration."""
        self.last_lifecycle_state = "fallback"
        self.last_fallback_reason = reason
        return None

    def dispose(self) -> None:
        """Release coordinator-only lifecycle state with its Runtime."""
        self.last_planning_generation = None
        self.last_lifecycle_state = "disposed"
        self.last_fallback_reason = None
        self.last_approval_source = None
        self.last_realized_intent = None
        self.last_session_direction = None
        self.disposed = True


def _planning_subject_projection(raw_insight: dict[str, Any]) -> tuple[tuple[str, str], ...]:
    """Pass only already-safe, bounded planning subjects to the existing boundary."""
    track = raw_insight.get("track") if isinstance(raw_insight.get("track"), dict) else {}
    analysis = raw_insight.get("analysis") if isinstance(raw_insight.get("analysis"), dict) else {}
    values = (
        ("artist", track.get("artist")),
        ("album", track.get("album")),
        ("genre", analysis.get("genre") or track.get("genres")),
        ("recommendation", track.get("related_tracks") or analysis.get("similar_tracks")),
    )
    return tuple(
        (key, bounded)
        for key, value in values
        if (bounded := _bounded_text(value, 256))
    )


def _knowledge_intent_for_planned_category(category: str) -> KnowledgeIntent | None:
    """Adapt an approved Planner category to the existing Knowledge contract."""
    intents = {
        "track_context": KnowledgeIntent(
            KnowledgeIntentType.TRACK_CONTEXT,
            "Explain one relevant detail that improves appreciation of the current track.",
        ),
        "artist_story": KnowledgeIntent(
            KnowledgeIntentType.ARTIST_STORY,
            "Share relevant artist or production context.",
        ),
        "album_story": KnowledgeIntent(
            KnowledgeIntentType.ALBUM_STORY,
            "Share relevant album context.",
        ),
        "genre_story": KnowledgeIntent(
            KnowledgeIntentType.GENRE_STORY,
            "Explain relevant genre context.",
        ),
        "recommendation": KnowledgeIntent(
            KnowledgeIntentType.RECOMMENDATION,
            "Recommend one related work when it adds value.",
        ),
    }
    return intents.get(category)


def _planning_realization_insight(
    knowledge: KnowledgeContext,
    raw_insight: dict[str, Any],
    knowledge_intent: KnowledgeIntent,
) -> dict[str, Any]:
    """Retain only selected safe Track Insight while Prepared Knowledge supplies evidence."""
    raw_track = raw_insight.get("track") if isinstance(raw_insight.get("track"), dict) else {}
    raw_analysis = raw_insight.get("analysis") if isinstance(raw_insight.get("analysis"), dict) else {}
    track_fields, analysis_fields = _knowledge_fields_for_intent(knowledge_intent.intent_type)
    track = {
        key: raw_track[key]
        for key in track_fields
        if _bounded_text(raw_track.get(key), 2048)
    }
    analysis = {
        key: raw_analysis[key]
        for key in analysis_fields
        if _bounded_text(raw_analysis.get(key), 1200)
    }
    track.update(dict(knowledge.track))
    analysis.update(dict(knowledge.analysis))
    return {"track": track, "analysis": analysis}


def _knowledge_fields_for_intent(
    intent_type: KnowledgeIntentType,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Select only existing metadata relevant to one Planner-owned intent."""
    track_fields = ("title", "artist", "album", "artwork_url", "backend")
    analysis_fields = ("summary", "full_text")
    if intent_type is KnowledgeIntentType.ARTIST_STORY:
        return (
            (*track_fields, "producer", "composer", "recording_context", "related_artists"),
            (*analysis_fields, "production_notes", "instrumentation", "arrangement_notes"),
        )
    if intent_type is KnowledgeIntentType.ALBUM_STORY:
        return (
            (*track_fields, "release_year", "release_date"),
            (*analysis_fields, "mood", "vibe", "texture"),
        )
    if intent_type is KnowledgeIntentType.GENRE_STORY:
        return (
            (*track_fields, "genres"),
            (*analysis_fields, "genre", "subgenre", "mood", "vibe"),
        )
    if intent_type is KnowledgeIntentType.RECOMMENDATION:
        return (
            (*track_fields, "related_tracks", "related_artists"),
            (*analysis_fields, "similar_tracks", "listening_cues"),
        )
    return (
        (*track_fields, "genres"),
        (*analysis_fields, "genre", "subgenre", "mood", "vibe", "texture", "emotional_tone", "production_notes", "instrumentation", "arrangement_notes", "listening_cues", "similar_tracks"),
    )


_PRIMARY_EVIDENCE_INTENTS = frozenset(
    {
        KnowledgeIntentType.ARTIST_STORY,
        KnowledgeIntentType.ALBUM_STORY,
        KnowledgeIntentType.GENRE_STORY,
        KnowledgeIntentType.RECOMMENDATION,
    }
)


def _primary_knowledge_evidence(
    intent_type: KnowledgeIntentType,
    track: dict[str, Any],
    analysis: dict[str, Any],
) -> tuple[str, str, str] | None:
    """Select exactly one safe evidence value by the approved intent precedence."""
    candidates: tuple[tuple[str, str, int], ...]
    if intent_type is KnowledgeIntentType.ARTIST_STORY:
        candidates = (
            ("track", "producer", 160),
            ("track", "composer", 160),
            ("track", "recording_context", 600),
            ("track", "related_artists", 1200),
            ("analysis", "production_notes", 1200),
            ("analysis", "instrumentation", 1200),
            ("analysis", "arrangement_notes", 1200),
        )
    elif intent_type is KnowledgeIntentType.ALBUM_STORY:
        candidates = (("track", "release_year", 32), ("track", "release_date", 32))
    elif intent_type is KnowledgeIntentType.GENRE_STORY:
        candidates = (("analysis", "genre", 160), ("track", "genres", 160))
    elif intent_type is KnowledgeIntentType.RECOMMENDATION:
        candidates = (
            ("track", "related_tracks", 1200),
            ("track", "related_artists", 1200),
            ("analysis", "similar_tracks", 1200),
            ("analysis", "listening_cues", 1200),
        )
    else:
        return None

    for source, key, limit in candidates:
        value = _bounded_evidence_value((track if source == "track" else analysis).get(key), limit)
        if value:
            return source, key, value
    return None


def _bounded_evidence_value(value: Any, limit: int) -> str:
    """Accept only bounded scalar evidence or the first safe value in a sequence."""
    if isinstance(value, str):
        return _bounded_text(value, limit)
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return _bounded_text(value, limit)
    if isinstance(value, (list, tuple)):
        for item in value:
            if isinstance(item, str):
                bounded = _bounded_text(item, limit)
                if bounded:
                    return bounded
    return ""


@dataclass(frozen=True)
class _FrozenBroadcastMapping:
    """Internal immutable representation that preserves mapping boundaries."""

    items: tuple[tuple[str, Any], ...]


def _freeze_broadcast_payload(value: Any) -> Any:
    """Store delivery evidence without retaining mutable publication payloads."""
    if isinstance(value, dict):
        return _FrozenBroadcastMapping(
            tuple(
                (str(key), _freeze_broadcast_payload(item))
                for key, item in value.items()
            )
        )
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_broadcast_payload(item) for item in value)
    return value


def _thaw_broadcast_payload(value: Any) -> Any:
    """Copy an internal immutable replay payload into a renderer-safe event."""
    if isinstance(value, _FrozenBroadcastMapping):
        return {key: _thaw_broadcast_payload(item) for key, item in value.items}
    if isinstance(value, tuple):
        return [_thaw_broadcast_payload(item) for item in value]
    return value


@dataclass(frozen=True)
class RendererSafePlaybackProjection:
    """Backend-neutral, ephemeral playback data safe for Renderer Hosts."""

    state: str = "idle"
    item_id: str = ""
    title: str = ""
    artist: str = ""
    album: str = ""
    artwork_url: str = ""
    target_name: str = ""
    duration_ms: int | None = None
    position_ms: int | None = None
    updated_at: str = ""
    up_next: tuple[tuple[str, str], ...] = ()
    source_url: str = ""

    @classmethod
    def from_observation(
        cls,
        *,
        state: str,
        media_identity: str = "",
        title: str = "",
        artist: str = "",
        album: str = "",
        artwork_url: str = "",
        target_name: str = "",
        duration_ms: int | None = None,
        position_ms: int | None = None,
        up_next: dict[str, Any] | None = None,
    ) -> "RendererSafePlaybackProjection":
        """Normalize only already-observed, renderer-safe metadata."""
        normalized_state = str(state or "idle").strip().lower()
        if normalized_state not in {"playing", "paused", "stopped", "idle"}:
            normalized_state = "idle"
        if normalized_state in {"idle", "stopped"}:
            return cls(state=normalized_state)
        identity = str(media_identity or "").strip()
        item_id = hashlib.sha256(identity.encode()).hexdigest()[:24] if identity else ""
        safe_duration = duration_ms if isinstance(duration_ms, int) and duration_ms >= 0 else None
        safe_position = None
        if (
            safe_duration is not None
            and isinstance(position_ms, int)
            and position_ms >= 0
        ):
            safe_position = min(position_ms, safe_duration)
        return cls(
            state=normalized_state,
            item_id=item_id,
            title=_bounded_text(title, 256),
            artist=_bounded_text(artist, 256),
            album=_bounded_text(album, 256),
            artwork_url=_safe_artwork_url(artwork_url),
            target_name=_bounded_text(target_name, 256),
            duration_ms=safe_duration,
            position_ms=safe_position,
            updated_at=_timestamp(),
            source_url="https://open.spotify.com/track/" + identity.rsplit(":", 1)[-1] if re.fullmatch(r"spotify:track:[A-Za-z0-9]{22}", identity) else "",
            up_next=tuple((key, value) for key, value in {
                "current_item_id": item_id,
                "title": _bounded_text((up_next or {}).get("title"), 256),
                "artist": _bounded_text((up_next or {}).get("artist"), 256),
                "artwork_url": _safe_artwork_url((up_next or {}).get("artwork_url")),
                "expires_at": _bounded_text((up_next or {}).get("expires_at"), 40),
            }.items() if value) if up_next and item_id else (),
        )

    def same_content(self, other: "RendererSafePlaybackProjection") -> bool:
        return self.__dict__ | {"updated_at": ""} == other.__dict__ | {"updated_at": ""}

    def as_dict(self) -> dict[str, Any]:
        """Expose only renderer-safe presentation fields."""
        result: dict[str, Any] = {"state": self.state}
        for key in ("item_id", "title", "artist", "album", "artwork_url", "target_name", "updated_at"):
            value = getattr(self, key)
            if value:
                result[key] = value
        if self.duration_ms is not None:
            result["duration_ms"] = self.duration_ms
        if self.position_ms is not None:
            result["position_ms"] = self.position_ms
        if self.up_next:
            result["up_next"] = dict(self.up_next)
        if self.source_url:
            result["source_url"] = self.source_url
        return result


@dataclass(frozen=True)
class DJBroadcastState:
    """Canonical, renderer-safe representation of the current DJ Session."""

    session_id: str
    runtime_state: SessionRuntimeState
    selected_mood: str
    planning_state: PlannerState
    planning_horizon_minutes: int
    session_direction: SessionDirection
    started_at: str
    session_flow: DJSessionFlow
    locale: str = "en"
    audience_totals: dict[str, int] = field(default_factory=dict)
    recent_audience_activity: tuple[str, ...] = ()
    dj_moments: tuple[DJMoment, ...] = ()
    presentations: tuple[PresentationProjection, ...] = ()
    playback: "RendererSafePlaybackProjection" = field(default_factory=lambda: RendererSafePlaybackProjection())

    def as_dict(self, *, include_owner_only: bool = True) -> dict[str, Any]:
        """Return canonical state with its Planner-produced Session Flow."""
        return {
            "session": {
                "session_id": self.session_id,
                "runtime_state": str(self.runtime_state),
                "selected_mood": self.selected_mood,
                "locale": self.locale,
            },
            "playback": self.playback.as_dict(),
            "planner": {
                "planning_state": str(self.planning_state),
                "planning_horizon_minutes": self.planning_horizon_minutes,
                "current_direction": self.session_direction.direction.value,
                "session_direction": self.session_direction.as_dict(),
            },
            "session_flow": self.session_flow.as_dict(),
            "audience": {"signal_totals": self.audience_totals, "recent_activity": list(self.recent_audience_activity)},
            "dj_moments": [
                moment.as_dict()
                for moment in self.dj_moments
                if include_owner_only or moment.presentation_intent.visibility is not DJMomentVisibility.OWNER_ONLY
            ],
            "presentations": [
                presentation.as_dict()
                for presentation in self.presentations
                if include_owner_only
                or presentation.visibility != DJMomentVisibility.OWNER_ONLY.value
            ],
            "broadcast": {"started_at": self.started_at},
        }


@dataclass(frozen=True)
class BroadcastReplayEntry:
    """One immutable, internal record of a Broadcast publication."""

    delivery_sequence: int
    event_type: BroadcastEventType
    session_id: str
    payload: Any
    owner_only: bool
    recovery_cursor: str


@dataclass(frozen=True)
class BroadcastRecoveryCursor:
    """Immutable internal reference to one owner-authorized delivery boundary."""

    session_id: str
    delivery_sequence: int
    snapshot_watermark: int
    authorization_scope: BroadcastAuthorizationScope
    opaque_value: str


@dataclass
class PlaybackProgressClock:
    """Runtime-scoped server clock corrected by backend playback snapshots."""

    session_id: str
    item_id: str
    anchor_position_ms: int
    duration_ms: int
    anchor_monotonic: float
    last_published_position_ms: int


@dataclass
class DJSessionBroadcastEngine:
    """One ephemeral distribution owner for one active Session Runtime.

    The Engine publishes only canonical Broadcast State. It never plans,
    executes playback or renders a presentation; future renderers consume this
    state and the stable Broadcast Event vocabulary through the Runtime.
    """

    state: DJBroadcastState
    pending_events: tuple[BroadcastEventType, ...] = ()
    replay_log_limit: int = 128
    broadcast_token: str = field(default_factory=lambda: secrets.token_urlsafe(32), repr=False)
    delivery_sequence: int = field(default=0, init=False)
    replay_log: tuple[BroadcastReplayEntry, ...] = field(default=(), init=False)
    recovery_cursor: BroadcastRecoveryCursor | None = field(default=None, init=False)
    _subscribers: dict[str, tuple[Callable[[dict[str, Any]], None], bool]] = field(
        default_factory=dict, init=False, repr=False
    )
    _pending_subscriptions: dict[str, list[dict[str, Any]]] = field(
        default_factory=dict, init=False, repr=False
    )
    _moment_playback_item_ids: dict[str, str] = field(
        default_factory=dict, init=False, repr=False
    )

    _moment_delivery_boundaries: dict[str, MomentDeliveryBoundary] = field(default_factory=dict, init=False, repr=False)
    _native_revision: str = field(default="", init=False, repr=False)
    _owner_only_moment_ids: set[str] = field(default_factory=set, init=False, repr=False)
    _invalidated_current_moment_ids: set[str] = field(default_factory=set, init=False, repr=False)
    _owner_subscription_entries: dict[str, str] = field(default_factory=dict, init=False, repr=False)
    _revoked_subscriptions: set[str] = field(default_factory=set, init=False, repr=False)
    _withdrawal_sent: set[str] = field(default_factory=set, init=False, repr=False)

    def __post_init__(self) -> None:
        """Keep replay retention bounded even for internal construction callers."""
        self.replay_log_limit = max(1, self.replay_log_limit)

    def subscribe(
        self, callback: Callable[[dict[str, Any]], None]
    ) -> tuple[str, dict[str, Any]]:
        """Register one renderer and return its required initial snapshot."""
        subscription_id = self.register_subscription(callback)
        return subscription_id, self.as_dict()

    def register_subscription(self, callback: Callable[[dict[str, Any]], None]) -> str:
        """Register one renderer without constructing a Broadcast snapshot."""
        subscription_id = f"broadcast-subscription-{uuid4().hex}"
        self._subscribers[subscription_id] = (callback, True)
        return subscription_id

    def register_pending_subscription(self, callback: Callable[[dict[str, Any]], None]) -> str:
        """Register one owner renderer while its initial snapshot is delivered."""
        subscription_id = self.register_subscription(callback)
        self._pending_subscriptions[subscription_id] = []
        return subscription_id

    def activate_subscription(self, subscription_id: str) -> None:
        """Flush setup-time events only after the initial snapshot was sent."""
        pending_events = self._pending_subscriptions.pop(subscription_id, None)
        subscriber = self._subscribers.get(subscription_id)
        if pending_events is None or subscriber is None:
            return
        callback, include_owner_only = subscriber
        if subscription_id in self._revoked_subscriptions:
            for event in pending_events:
                callback(event)
            self.unsubscribe(subscription_id)
            return
        for event in pending_events:
            callback({**event, "payload": self._safe_delivery_payload(
                event["payload"], include_owner_only=include_owner_only)})

    def subscribe_with_broadcast_token(
        self, token: str, callback: Callable[[dict[str, Any]], None]
    ) -> tuple[str, dict[str, Any]] | None:
        """Attach a read-only Receiver only when its runtime token matches."""
        if not token or not secrets.compare_digest(self.broadcast_token, token):
            return None
        subscription_id = f"broadcast-subscription-{uuid4().hex}"
        self._subscribers[subscription_id] = (callback, False)
        return subscription_id, self.as_dict(include_owner_only=False)

    def broadcast_token_contract(self) -> dict[str, Any]:
        """Return the safe, read-only Receiver capability contract."""
        return {
            "session_id": self.state.session_id,
            "broadcast_token": self.broadcast_token,
            "capabilities": {
                "view_broadcast": True,
                "like": False,
                "audience_signals": True,
                "ask_dj": False,
                "owner_controls": False,
            },
        }

    def unsubscribe(self, subscription_id: str) -> None:
        """Remove a renderer subscription without changing Broadcast State."""
        self._subscribers.pop(subscription_id, None)
        self._pending_subscriptions.pop(subscription_id, None)
        self._owner_subscription_entries.pop(subscription_id, None)
        self._revoked_subscriptions.discard(subscription_id)
        self._withdrawal_sent.discard(subscription_id)

    @property
    def subscriber_count(self) -> int:
        """Expose bounded transport lifecycle state for verification only."""
        return len(self._subscribers)

    def update_runtime_state(self, runtime_state: SessionRuntimeState) -> None:
        """Reflect the Runtime lifecycle in its canonical Broadcast State."""
        self.state = DJBroadcastState(**{**self.state.__dict__, "runtime_state": runtime_state})
        if runtime_state is SessionRuntimeState.ACTIVE:
            self._publish(BroadcastEventType.RUNTIME_CREATED, {"session": self.as_dict()["session"]})
            self._publish(
                BroadcastEventType.BROADCAST_STARTED,
                {"broadcast": self.as_dict()["broadcast"]},
            )

    def publish_session_flow(self, session_flow: DJSessionFlow) -> None:
        """Publish the Runtime-supplied Planner output to Broadcast State."""
        self.state = DJBroadcastState(**{**self.state.__dict__, "session_flow": session_flow})
        state = self.as_dict()
        self._publish(BroadcastEventType.PLANNER_UPDATED, {"planner": state["planner"]})
        self._publish(BroadcastEventType.SESSION_FLOW_UPDATED, {"session_flow": state["session_flow"]})

    def update_session_direction(self, session_direction: SessionDirection) -> None:
        """Reflect a Planner-approved, Runtime-owned Direction change."""
        self.state = DJBroadcastState(
            **{**self.state.__dict__, "session_direction": session_direction}
        )
        self._publish(BroadcastEventType.PLANNER_UPDATED, {"planner": self.as_dict()["planner"]})

    def update_playback(self, playback: RendererSafePlaybackProjection) -> bool:
        """Publish one replacement projection only when its safe content changes."""
        if self.state.playback.same_content(playback):
            return False
        old = self.state.playback
        if (playback.state != "playing" or old.item_id != playback.item_id
                or old.target_name != playback.target_name):
            self.invalidate_current_delivery()
        self.state = DJBroadcastState(**{**self.state.__dict__, "playback": playback})
        self._publish(BroadcastEventType.PLAYBACK_CHANGED, {"playback": self.as_dict()["playback"]})
        return True

    def update_playback_progress(self, playback: RendererSafePlaybackProjection) -> bool:
        """Publish a server-calculated playback position without provider access."""
        if self.state.playback.same_content(playback):
            return False
        self.state = DJBroadcastState(**{**self.state.__dict__, "playback": playback})
        self._publish(BroadcastEventType.PLAYBACK_PROGRESS, {"playback": self.as_dict()["playback"]})
        return True

    def publish_audience_state(self, totals: dict[str, int], recent_activity: tuple[str, ...]) -> None:
        self.state = DJBroadcastState(**{**self.state.__dict__, "audience_totals": dict(totals), "recent_audience_activity": recent_activity})
        self._publish(BroadcastEventType.AUDIENCE_UPDATED, {"audience": self.as_dict()["audience"]})

    def publish_moment(self, moment: DJMoment) -> None:
        """Project a validated Moment without exposing private projections."""
        if moment.session_id != self.state.session_id or any(
                previous.moment_id == moment.moment_id for previous in self.state.dj_moments):
            return
        self.prepare_moment_delivery(moment)
        playback_item_id = self.state.playback.item_id
        if playback_item_id:
            self._moment_playback_item_ids[moment.moment_id] = playback_item_id
        self.state = DJBroadcastState(**{**self.state.__dict__, "dj_moments": (*self.state.dj_moments, moment)})
        if moment.moment_type is not DJMomentType.SILENCE:
            projected = moment.as_dict()
            if playback_item_id:
                projected["playback_item_id"] = playback_item_id
            self._publish(BroadcastEventType.DJ_MOMENT_PUBLISHED, {"dj_moment": projected})

    def publish_presentation(self, presentation: PresentationProjection) -> None:
        """Publish one immutable renderer-safe Presentation after composition."""
        self.state = DJBroadcastState(
            **{**self.state.__dict__, "presentations": (*self.state.presentations, presentation)}
        )
        self._publish(
            BroadcastEventType.PRESENTATION_PUBLISHED,
            {"presentation": presentation.as_dict()},
        )

    def close(self) -> None:
        """Notify renderers of Runtime termination, then release every subscription."""
        state = self.as_dict()
        self._publish(BroadcastEventType.RUNTIME_ENDED, {"session": state["session"]})
        self._publish(BroadcastEventType.BROADCAST_STOPPED, {"broadcast": state["broadcast"]})
        self._subscribers.clear()
        self._pending_subscriptions.clear()
        self.replay_log = ()
        self.delivery_sequence = 0
        self.recovery_cursor = None
        self._moment_delivery_boundaries.clear()
        self._owner_only_moment_ids.clear()
        self._invalidated_current_moment_ids.clear()
        self._native_revision = ""
        self._owner_subscription_entries.clear()
        self._revoked_subscriptions.clear()
        self._withdrawal_sent.clear()

    def _publish(self, event_type: BroadcastEventType, payload: dict[str, Any]) -> None:
        """Deliver one incremental, renderer-safe event to active subscribers."""
        self.delivery_sequence += 1
        opaque_cursor = secrets.token_urlsafe(32)
        payload = self._safe_delivery_payload(payload)
        self._native_revision = payload["native_delivery"]["revision"]
        self._append_replay_entry(event_type, payload, opaque_cursor)
        self._issue_recovery_cursor(opaque_cursor)
        event = {
            "event_type": str(event_type),
            "session_id": self.state.session_id,
            "delivery_sequence": self.delivery_sequence,
            "payload": payload,
        }
        for subscription_id, (callback, include_owner_only) in tuple(self._subscribers.items()):
            if not include_owner_only and _payload_contains_owner_only_moment(payload):
                continue
            if subscription_id in self._revoked_subscriptions:
                if subscription_id in self._withdrawal_sent:
                    continue
                self._withdrawal_sent.add(subscription_id)
                scoped_event = {**event, "event_type": BroadcastEventType.BROADCAST_STOPPED.value,
                                "payload": self.subscription_withdrawal_payload()}
            else:
                scoped_event = {**event, "payload": self._safe_delivery_payload(
                    payload, include_owner_only=include_owner_only)}
            pending_events = self._pending_subscriptions.get(subscription_id)
            if pending_events is not None:
                if subscription_id in self._revoked_subscriptions:
                    pending_events[:] = [scoped_event]
                else:
                    pending_events.append(scoped_event)
                continue
            callback(scoped_event)

    def _append_replay_entry(
        self, event_type: BroadcastEventType, payload: dict[str, Any], recovery_cursor: str
    ) -> None:
        """Retain one bounded, authorization-aware record for future replay only."""
        entry = BroadcastReplayEntry(
            delivery_sequence=self.delivery_sequence,
            event_type=event_type,
            session_id=self.state.session_id,
            payload=_freeze_broadcast_payload(payload),
            owner_only=_payload_contains_owner_only_moment(payload),
            recovery_cursor=recovery_cursor,
        )
        self.replay_log = (*self.replay_log, entry)[-self.replay_log_limit :]

    def _issue_recovery_cursor(self, opaque_value: str) -> None:
        """Bind one opaque internal cursor to the newest owner delivery boundary."""
        if not self.replay_log or self.replay_log[-1].delivery_sequence != self.delivery_sequence:
            self.recovery_cursor = None
            return
        self.recovery_cursor = BroadcastRecoveryCursor(
            session_id=self.state.session_id,
            delivery_sequence=self.delivery_sequence,
            snapshot_watermark=self._snapshot_watermark(include_owner_only=True),
            authorization_scope=BroadcastAuthorizationScope.OWNER,
            opaque_value=opaque_value,
        )

    def owner_recovery_cursor(self) -> str | None:
        """Return only the current opaque owner cursor, never its infrastructure."""
        if self.recovery_cursor is None:
            return None
        return self.recovery_cursor.opaque_value

    def recover_owner(self, recovery_cursor: str) -> dict[str, Any] | None:
        """Replay a bounded owner projection or require a fresh snapshot.

        A syntactically invalid cursor is rejected. A valid-shaped cursor that
        no longer maps to the bounded Runtime log deterministically falls back
        to the current owner snapshot.
        """
        if not isinstance(recovery_cursor, str) or len(recovery_cursor) < 32:
            return None
        if any(moment.source_attribution for moment in self.state.dj_moments):
            return self._snapshot_required_recovery()
        cursor_entry = next(
            (
                entry
                for entry in self.replay_log
                if secrets.compare_digest(entry.recovery_cursor, recovery_cursor)
            ),
            None,
        )
        if cursor_entry is None or cursor_entry.session_id != self.state.session_id:
            return self._snapshot_required_recovery()
        replay_entries = tuple(
            entry for entry in self.replay_log if entry.delivery_sequence > cursor_entry.delivery_sequence
        )
        expected_sequences = tuple(
            range(cursor_entry.delivery_sequence + 1, self.delivery_sequence + 1)
        )
        if tuple(entry.delivery_sequence for entry in replay_entries) != expected_sequences:
            return self._snapshot_required_recovery()
        return {
            "recovery": "replayed",
            "events": [
                {
                    "event_type": str(entry.event_type),
                    "session_id": entry.session_id,
                    "delivery_sequence": entry.delivery_sequence,
                    "payload": self._safe_delivery_payload(_thaw_broadcast_payload(entry.payload)),
                }
                for entry in replay_entries
            ],
            "snapshot_watermark": self._snapshot_watermark(include_owner_only=True),
            "recovery_cursor": self.owner_recovery_cursor(),
        }

    def _snapshot_required_recovery(self) -> dict[str, Any]:
        """Return the sole safe fallback when bounded replay is unavailable."""
        return {
            "recovery": "snapshot_required",
            "snapshot": self.as_dict(),
            "recovery_cursor": self.owner_recovery_cursor(),
        }

    def as_dict(self, *, include_owner_only: bool = True) -> dict[str, Any]:
        """Expose only canonical Broadcast State to future renderers."""
        projection = self.state.as_dict(include_owner_only=include_owner_only)
        for moment in projection["dj_moments"]:
            playback_item_id = self._moment_playback_item_ids.get(
                str(moment.get("moment_id") or "")
            )
            if playback_item_id:
                moment["playback_item_id"] = playback_item_id
        projection = self._safe_delivery_payload(projection, include_owner_only=include_owner_only)
        projection["broadcast"]["snapshot_watermark"] = self._snapshot_watermark(
            include_owner_only=include_owner_only
        )
        return projection

    def subscription_withdrawal_payload(self) -> dict[str, Any]:
        """Withdraw one channel's authority without ending the Profile Session."""
        return {"broadcast": {"subscription_state": "revoked"},
                "native_delivery": withdrawn_native_delivery(self.state.session_id)}

    def revoke_owner_entry_subscriptions(self, entry_id: str) -> None:
        """Reuse the existing entry-unload boundary; pending source frames die."""
        revoked = {key for key, value in self._owner_subscription_entries.items()
                   if value == entry_id and key not in self._revoked_subscriptions}
        if not revoked:
            return
        self._revoked_subscriptions.update(revoked)
        # One real delivery boundary: unaffected subscribers get ordinary Flow
        # state; revoked channels get only the terminal empty projection.
        self._publish(BroadcastEventType.SESSION_FLOW_UPDATED,
                      {"session_flow": self.state.session_flow.as_dict()})
        for subscription_id in revoked:
            if subscription_id not in self._pending_subscriptions:
                self.unsubscribe(subscription_id)

    def prepare_moment_delivery(self, moment: DJMoment) -> None:
        """Bind original clocks and visibility before its Flow label is sent."""
        if moment.session_id != self.state.session_id:
            return
        self._moment_delivery_boundaries.setdefault(moment.moment_id, MomentDeliveryBoundary(
            time.monotonic(), moment.created_at, self.state.playback.item_id))
        if moment.presentation_intent.visibility is DJMomentVisibility.OWNER_ONLY:
            self._owner_only_moment_ids.add(moment.moment_id)

    def invalidate_current_delivery(self) -> None:
        """Previously published cards cannot become current again after disruption."""
        self._invalidated_current_moment_ids.update(moment.moment_id for moment in self.state.dj_moments)

    def native_delivery(self, *, include_owner_only: bool = True) -> dict[str, Any]:
        """Project present authority without changing immutable semantic state."""
        flow_ids = {item.moment_id for item in self.state.session_flow.items if item.moment_id}
        entries = [native_admission(
            moment, self._moment_delivery_boundaries.get(moment.moment_id),
            session_id=self.state.session_id, active=self.state.runtime_state is SessionRuntimeState.ACTIVE,
            flow_ids=flow_ids, playback_item_id=self.state.playback.item_id,
            playing=self.state.playback.state == "playing", now=time.monotonic())
            for moment in self.state.dj_moments
            if self.state.runtime_state is SessionRuntimeState.ACTIVE
            and moment.moment_type is not DJMomentType.SILENCE
            and (include_owner_only or moment.presentation_intent.visibility is not DJMomentVisibility.OWNER_ONLY)]
        latest = next((moment.moment_id for moment in reversed(self.state.dj_moments)
                       if moment.moment_type is not DJMomentType.SILENCE
                       and self._moment_playback_item_ids.get(moment.moment_id) == self.state.playback.item_id), None)
        current = next((entry["moment_id"] for entry in entries
                        if entry["moment_id"] == latest and entry["current_display_allowed"]
                        and latest not in self._invalidated_current_moment_ids), None)
        # Only the newest admissible contribution is prominent now.
        for entry in entries:
            entry["current_display_allowed"] = entry["moment_id"] == current
        result = {"schema_version": 1, "session_id": self.state.session_id,
                  "current_moment_id": current,
                  "active_flow_moment_ids": [entry["moment_id"] for entry in entries
                                             if entry["active_flow_display_allowed"]],
                  "admissions": entries, "revocation_scope": "session"}
        result["revision"] = hashlib.sha256(json.dumps(result, sort_keys=True).encode()).hexdigest()[:24]
        return result

    def _safe_delivery_payload(self, payload: dict[str, Any], *, include_owner_only: bool = True) -> dict[str, Any]:
        """Remove expired source copies at every transport delivery boundary."""
        native = self.native_delivery(include_owner_only=include_owner_only)
        # Use all scopes for redaction even when the receiver lacks an owner card.
        all_admissions = self.native_delivery()["admissions"]
        ended = self.state.runtime_state is not SessionRuntimeState.ACTIVE
        source_ids = {moment.moment_id for moment in self.state.dj_moments if moment.source_attribution}
        excluded = {entry["moment_id"] for entry in all_admissions
                    if entry["moment_id"] in source_ids and entry["qualification"] != "qualified"}
        if ended:
            excluded.update(moment.moment_id for moment in self.state.dj_moments)
        if not include_owner_only:
            excluded.update(self._owner_only_moment_ids)
        result = copy.deepcopy(payload)
        if "dj_moments" in result:
            result["dj_moments"] = [m for m in result["dj_moments"] if m.get("moment_id") not in excluded]
        if result.get("dj_moment", {}).get("moment_id") in excluded:
            result.pop("dj_moment", None)
        if "presentations" in result:
            result["presentations"] = [p for p in result["presentations"] if p.get("source_moment_id") not in excluded]
        if result.get("presentation", {}).get("source_moment_id") in excluded:
            result.pop("presentation", None)
        if "session_flow" in result:
            result["session_flow"]["items"] = [item for item in result["session_flow"]["items"]
                                               if item.get("moment_id") not in excluded]
        result["native_delivery"] = native
        return result

    def refresh_native_delivery(self) -> None:
        """Use the existing observation tick for expiry/invalidation events."""
        revision = self.native_delivery()["revision"]
        if revision != self._native_revision:
            self._native_revision = revision
            self._publish(BroadcastEventType.SESSION_FLOW_UPDATED,
                          {"session_flow": self.state.session_flow.as_dict()})

    def _snapshot_watermark(self, *, include_owner_only: bool) -> int:
        """Return the newest retained delivery represented by this projection."""
        if include_owner_only:
            return self.delivery_sequence
        for entry in reversed(self.replay_log):
            if not entry.owner_only:
                return entry.delivery_sequence
        return 0


class ActiveSessionExistsError(RuntimeError):
    """Raised when a Profile already owns an active DJ Session."""

    def __init__(self, profile_id: str) -> None:
        self.profile_id = profile_id
        super().__init__(f"Profile already has an active DJ Session: {profile_id}")


@dataclass
class PresentationCompositionDiagnostics:
    """Bounded Runtime-only outcome evidence; never a Broadcast projection."""

    last_outcomes: tuple[PresentationCompositionOutcome, ...] = ()
    composition_count: int = 0

    def record(self, outcomes: tuple[PresentationCompositionOutcome, ...]) -> None:
        self.last_outcomes = outcomes
        self.composition_count += 1


@dataclass
class IntraTrackOpportunity:
    """Private, bounded current-item opportunity owned by the active Runtime."""

    session_id: str
    media_identity: str
    item_id: str
    source_context: tuple[str, str, str, str]
    generation: int = 0
    last_observed_position_ms: int | None = None
    last_observed_monotonic: float = 0.0
    first_moment_position_ms: int | None = None
    first_moment_type: DJMomentType | None = None
    first_read_seconds: int = 0
    safe_insight: dict[str, Any] = field(default_factory=dict)
    pending: bool = False
    spent: bool = False
    blocked: bool = False
    resume_ready_at: float = 0.0
    qualified_facts: tuple[QualifiedSessionFact, ...] = ()
    used_fact_keys: set[str] = field(default_factory=set)
    fact_count: int = 0
    last_fact_position_ms: int | None = None
    last_fact_read_seconds: int = 0


def _safe_intra_track_insight(raw_insight: dict[str, Any]) -> dict[str, Any]:
    """Retain only already approved Track Insight fields within one Runtime."""
    track = raw_insight.get("track")
    analysis = raw_insight.get("analysis")
    if not isinstance(track, dict) or not isinstance(analysis, dict):
        return {}
    safe_track = {
        key: _bounded_evidence_value(track.get(key), limit)
        for key, limit in (
            ("title", 160), ("artist", 160), ("album", 160),
            ("backend", 40), ("genres", 160),
        )
    }
    safe_track["artwork_url"] = _safe_artwork_url(track.get("artwork_url"))
    safe_analysis = {
        key: _bounded_evidence_value(analysis.get(key), limit)
        for key, limit in (("summary", 320), ("full_text", 1200), ("genre", 160))
    }
    if not all(safe_track.get(key) for key in ("title", "artist")):
        return {}
    return {"track": safe_track, "analysis": safe_analysis}


@dataclass(frozen=True)
class DJSessionRuntime:
    """Minimum ephemeral state for one active DJ Session."""

    session_id: str
    owner_profile_id: str
    room: str
    selected_mood: str
    dj_persona: DJPersona
    locale: str
    music_backend: str
    runtime_state: SessionRuntimeState
    created_at: str
    started_at: str
    session_start_strategy: SessionStartStrategy
    initial_session_mood: str
    interaction_profile: str
    session_direction: SessionDirection
    discover_context: DiscoverContext
    performance_memory: PerformanceMemory
    planner: DJSessionPlanner
    planning_coordinator: PlanningRuntimeCoordinator
    knowledge_engine: DJKnowledgeEngine
    moment_engine: DJMomentEngine
    presentation_composer: PresentationComposer
    broadcast: DJSessionBroadcastEngine
    allowed_capability_intents: frozenset[str] | None = None
    presentation_diagnostics: "PresentationCompositionDiagnostics" = field(
        default_factory=lambda: PresentationCompositionDiagnostics()
    )
    last_accepted_media_identity: str = ""
    published_recording_context: PublishedRecordingContext = field(default_factory=PublishedRecordingContext)

    def as_dict(self) -> dict[str, Any]:
        """Return the public, transport-neutral runtime representation."""
        runtime = {
            "session_id": self.session_id,
            "owner_profile_id": self.owner_profile_id,
            "room": self.room,
            "selected_mood": self.selected_mood,
            "dj_persona": self.dj_persona.value,
            "locale": self.locale,
            "music_backend": self.music_backend,
            "runtime_state": str(self.runtime_state),
            "created_at": self.created_at,
            "started_at": self.started_at,
            "session_start_strategy": self.session_start_strategy.value,
            "initial_session_mood": self.initial_session_mood,
            "interaction_profile": self.interaction_profile,
            "session_direction": self.session_direction.as_dict(),
            "discover_personalization_available": self.discover_context.personal_context_authorized,
            "performance_memory": self.performance_memory.as_dict(),
        }
        runtime["planner"] = self.planner.as_dict()
        runtime["broadcast"] = self.broadcast.as_dict()
        runtime["planner"]["output"]["session_flow"] = runtime["broadcast"]["session_flow"]
        return runtime

    def republish_session_flow(self) -> DJSessionFlow:
        """Coordinate Planner output publication through the Broadcast Engine."""
        if self.planner.discover_narrative_line is not None:
            self.planner.clear_discover_narrative()
        flow = self.planner.republish_session_flow()
        self.broadcast.publish_session_flow(flow)
        return flow

    def submit_audience_signal(self, signal: AudienceSignalType, value: str = "") -> None:
        """Route shared-renderer suggestions through Runtime to its Planner."""
        self.planner.submit_audience_signal(signal, value)
        self.broadcast.publish_audience_state(self.planner.audience_totals, self.planner.recent_audience_activity)

    def publish_moment(
        self, moment: DJMoment, placement: SessionFlowPosition = SessionFlowPosition.NEXT
    ) -> None:
        """Publish a Moment only after Planner placement has been established."""
        if moment.session_id != self.session_id or any(
                previous.moment_id == moment.moment_id for previous in self.broadcast.state.dj_moments):
            return
        composition = self.presentation_composer.compose_with_diagnostics(
            moment=moment,
            context=PresentationContext(
                session_mood=self.selected_mood,
                dj_persona=self.dj_persona.value,
                session_direction=self.session_direction.direction.value,
                session_energy=moment.presentation_intent.energy_level,
                presentation_style=moment.presentation_intent.delivery_style,
                constraints=(
                    ("maximum_duration_seconds", str(moment.presentation_intent.maximum_duration_seconds)),
                    ("visibility", moment.presentation_intent.visibility.value),
                ),
            ),
        )
        self.presentation_diagnostics.record(composition.outcomes)
        self.broadcast.prepare_moment_delivery(moment)
        self.broadcast.publish_session_flow(self.planner.append_moment(moment, placement))
        self.broadcast.publish_moment(moment)
        self.broadcast.publish_presentation(composition.presentation.to_projection())


class SessionRuntimeManager:
    """Own active DJ Session Runtimes for this Home Assistant instance."""

    def __init__(self, persistent_sessions: PersistentSessionRepository | None = None, historical_projections: HistoricalProjectionRepository | None = None, monotonic_source: Callable[[], float] = time.monotonic) -> None:
        self._active_by_profile: dict[str, DJSessionRuntime] = {}
        self._playback_progress_clocks: dict[str, PlaybackProgressClock] = {}
        self._intra_track_opportunities: dict[str, IntraTrackOpportunity] = {}
        self._end_grants: dict[str, tuple[str, str, float, str]] = {}
        self._receiver_entry_generations: dict[str, int] = {}
        self._monotonic_source = monotonic_source
        self._lock = asyncio.Lock()
        self._persistent_sessions = persistent_sessions
        self._historical_projections = historical_projections

    async def async_start(
        self,
        *,
        owner_profile_id: str,
        room: str = "",
        selected_mood: str = "",
        music_backend: str = "",
        dj_persona: DJPersona = DJPersona.HOME_DJ,
        locale: str = "en",
        session_start_strategy: SessionStartStrategy = SessionStartStrategy.MANUAL,
        discover_context: DiscoverContext | None = None,
        elapsed_time_source: Callable[[], float] | None = None,
        allowed_capability_intents: frozenset[str] | None = None,
        history_enabled: bool = True,
    ) -> DJSessionRuntime:
        """Create the one active Runtime allowed for a Profile."""
        async with self._lock:
            if owner_profile_id in self._active_by_profile:
                raise ActiveSessionExistsError(owner_profile_id)
            now = _timestamp()
            session_id = f"session-{uuid4().hex}"
            start_configuration = _session_start_configuration(session_start_strategy)
            initial_session_mood = selected_mood.strip()
            resolved_discover_context = (
                discover_context or DiscoverContext()
                if session_start_strategy is SessionStartStrategy.DISCOVER
                else DiscoverContext()
            )
            session_direction = _initial_session_direction(start_configuration, now)
            if self._persistent_sessions is not None:
                await self._persistent_sessions.async_create(
                    owner_profile_id,
                    session_id=session_id,
                    start_strategy=start_configuration.strategy.value,
                    initial_mood=initial_session_mood,
                    initial_direction=session_direction.direction.value,
                    history_enabled=history_enabled,
                )
            planner = _create_session_planner(
                session_id=session_id,
                created_at=now,
                configuration=start_configuration.planner_configuration,
                elapsed_time_source=elapsed_time_source,
            )
            performance_memory = PerformanceMemory(planner.output.session_flow.flow_id)
            creating = DJSessionRuntime(
                session_id=session_id,
                owner_profile_id=owner_profile_id,
                room=room,
                selected_mood=selected_mood,
                dj_persona=dj_persona,
                locale=_locale_family(locale),
                music_backend=music_backend,
                runtime_state=SessionRuntimeState.CREATING,
                created_at=now,
                started_at="",
                session_start_strategy=start_configuration.strategy,
                initial_session_mood=initial_session_mood,
                interaction_profile=start_configuration.interaction_profile,
                session_direction=session_direction,
                discover_context=resolved_discover_context,
                performance_memory=performance_memory,
                planner=planner,
                planning_coordinator=PlanningRuntimeCoordinator(),
                knowledge_engine=DJKnowledgeEngine(),
                moment_engine=DJMomentEngine(),
                presentation_composer=PresentationComposer(),
                broadcast=_create_broadcast_engine(
                    session_id=session_id,
                    runtime_state=SessionRuntimeState.CREATING,
                    selected_mood=selected_mood,
                    locale=_locale_family(locale),
                    session_direction=session_direction,
                    planner=planner,
                    started_at=now,
                ),
                allowed_capability_intents=allowed_capability_intents,
            )
            creating.broadcast.update_runtime_state(SessionRuntimeState.ACTIVE)
            active = DJSessionRuntime(
                **{
                    **creating.__dict__,
                    "runtime_state": SessionRuntimeState.ACTIVE,
                    "started_at": _timestamp(),
                }
            )
            if self._persistent_sessions is not None:
                try:
                    await self._persistent_sessions.async_transition(
                        owner_profile_id, session_id, PERSISTENT_SESSION_ACTIVE
                    )
                except Exception:
                    await self._persistent_sessions.async_transition(
                        owner_profile_id,
                        session_id,
                        PERSISTENT_SESSION_INTERRUPTED,
                        reason="runtime_activation_failed",
                    )
                    raise
            self._active_by_profile[owner_profile_id] = active
            return active

    async def async_update_playback_projection(
        self,
        *,
        owner_profile_id: str,
        session_id: str,
        state: str,
        media_identity: str = "",
        title: str = "",
        artist: str = "",
        album: str = "",
        artwork_url: str = "",
        target_name: str = "",
        duration_ms: int | None = None,
        position_ms: int | None = None,
        up_next: dict[str, Any] | None = None,
    ) -> bool:
        """Apply one normalized observation to its active Runtime only."""
        projection = RendererSafePlaybackProjection.from_observation(
            state=state, media_identity=media_identity, title=title, artist=artist,
            album=album, artwork_url=artwork_url, target_name=target_name, duration_ms=duration_ms,
            position_ms=position_ms,
            up_next=up_next,
        )
        async with self._lock:
            active = self._active_by_profile.get(owner_profile_id)
            if active is None or active.session_id != session_id:
                return False
            now = self._monotonic_source()
            if projection.item_id and media_identity:
                active.published_recording_context.observe(media_identity, time.monotonic())
            opportunity = self._intra_track_opportunities.get(owner_profile_id)
            if projection.state in {"idle", "stopped"} or not projection.item_id:
                self._intra_track_opportunities.pop(owner_profile_id, None)
            elif opportunity is None or opportunity.session_id != session_id or opportunity.item_id != projection.item_id:
                opportunity = IntraTrackOpportunity(
                    session_id=session_id,
                    media_identity=media_identity,
                    item_id=projection.item_id,
                    source_context=(projection.target_name, projection.title, projection.artist, projection.album),
                )
                self._intra_track_opportunities[owner_profile_id] = opportunity
            if opportunity is not None and self._intra_track_opportunities.get(owner_profile_id) is opportunity:
                context = (projection.target_name, projection.title, projection.artist, projection.album)
                if active.broadcast.state.playback.state == "paused" and projection.state == "playing":
                    opportunity.resume_ready_at = now + 15
                if context != opportunity.source_context or media_identity != opportunity.media_identity:
                    opportunity.blocked = True
                    opportunity.generation += 1
                    opportunity.pending = False
                if projection.state != "playing":
                    opportunity.generation += 1
                    opportunity.pending = False
                if projection.position_ms is not None:
                    old_position = opportunity.last_observed_position_ms
                    elapsed_ms = max(0, (now - opportunity.last_observed_monotonic) * 1000)
                    if old_position is not None and (
                        projection.position_ms < old_position - 5000
                        or projection.position_ms > old_position + max(20_000, elapsed_ms + 15_000)
                    ):
                        opportunity.blocked = True
                        opportunity.generation += 1
                        opportunity.pending = False
                    opportunity.last_observed_position_ms = projection.position_ms
                opportunity.last_observed_monotonic = now
            old_playback = active.broadcast.state.playback
            if up_next is None and projection.state == "playing" and old_playback.item_id == projection.item_id and old_playback.target_name == projection.target_name:
                projection = RendererSafePlaybackProjection(**{**projection.__dict__, "up_next": old_playback.up_next})
            if opportunity is not None and opportunity.blocked:
                active.broadcast.invalidate_current_delivery()
            if (self._historical_projections is not None and projection.state == "playing"
                and projection.item_id and projection.item_id != old_playback.item_id):
                from .session_history_projection import new_observation_reference
                await self._historical_projections.async_append_entries(owner_profile_id,session_id,[{
                    "kind":"playback_observed", "reference_id":new_observation_reference(),
                    "body":{"item_id":projection.item_id,"title":projection.title,"artist":projection.artist,
                            "album":projection.album,"source_url":projection.source_url,
                            "provider":"Spotify" if projection.source_url.startswith("https://open.spotify.com/") else "Music Assistant" if active.music_backend == "music_assistant" else "DJConnect",
                            "coverage":"observed_playing_not_full_listen"},
                }])
            changed = active.broadcast.update_playback(projection)
            self._replace_playback_progress_clock(owner_profile_id, projection, session_id)
            if changed:
                _LOGGER.debug("DJConnect renderer-safe playback projection changed")
            return changed

    async def async_update_next_item_projection(self, *, owner_profile_id: str, session_id: str,
                                                 media_identity: str, target_name: str, up_next: dict[str, Any]) -> bool:
        """Apply optional queue data only to the still-current item/output."""
        async with self._lock:
            active = self._active_by_profile.get(owner_profile_id)
            if active is None or active.session_id != session_id:
                return False
            playback = active.broadcast.state.playback
            expected = hashlib.sha256(media_identity.encode()).hexdigest()[:24] if media_identity else ""
            if playback.item_id != expected or playback.target_name != _bounded_text(target_name, 256) or playback.state != "playing":
                return False
            normalized = RendererSafePlaybackProjection.from_observation(state=playback.state, media_identity=media_identity, up_next=up_next)
            return active.broadcast.update_playback(RendererSafePlaybackProjection(**{**playback.__dict__, "up_next": normalized.up_next}))

    async def async_update_allowed_capability_intents(
        self,
        *,
        owner_profile_id: str,
        session_id: str,
        allowed_capability_intents: frozenset[str],
    ) -> bool:
        """Invalidate disallowed unrealized work without publishing Session state."""
        async with self._lock:
            active = self._active_by_profile.get(owner_profile_id)
            if active is None or active.session_id != session_id:
                return False
            updated = DJSessionRuntime(
                **{
                    **active.__dict__,
                    "allowed_capability_intents": allowed_capability_intents,
                }
            )
            if updated.planner.horizon is not None:
                updated.planner.horizon.replan(allowed_intents=allowed_capability_intents)
            opportunity = self._intra_track_opportunities.get(owner_profile_id)
            if opportunity is not None:
                opportunity.generation += 1
                opportunity.pending = False
            self._active_by_profile[owner_profile_id] = updated
            return True

    async def async_invalidate_intra_track_opportunity(
        self, *, owner_profile_id: str, session_id: str
    ) -> None:
        """Make in-flight later work inert when its playback observer stops."""
        async with self._lock:
            current = self._intra_track_opportunities.get(owner_profile_id)
            if current is not None and current.session_id == session_id:
                current.generation += 1
                current.pending = False
                self._intra_track_opportunities.pop(owner_profile_id, None)

    def _note_initial_track_moment(
        self,
        *,
        owner_profile_id: str,
        active: DJSessionRuntime,
        media_identity: str,
        raw_insight: dict[str, Any],
        moment: DJMoment,
    ) -> None:
        """Keep one safe current-track candidate after its first publication."""
        opportunity = self._intra_track_opportunities.get(owner_profile_id)
        playback = active.broadcast.state.playback
        safe_insight = _safe_intra_track_insight(raw_insight)
        if (
            opportunity is None or opportunity.blocked
            or opportunity.session_id != active.session_id
            or opportunity.media_identity != media_identity
            or opportunity.item_id != playback.item_id
            or moment.moment_type is DJMomentType.SILENCE
            or moment.moment_type not in {
                DJMomentType.TRACK, DJMomentType.GENRE,
                DJMomentType.ARTIST, DJMomentType.ALBUM,
                DJMomentType.RECOMMENDATION,
            }
            or opportunity.first_moment_type is not None
            or safe_insight.get("track", {}).get("title") != playback.title
            or safe_insight.get("track", {}).get("artist") != playback.artist
        ):
            return
        opportunity.safe_insight = safe_insight
        opportunity.first_moment_type = moment.moment_type
        opportunity.first_moment_position_ms = opportunity.last_observed_position_ms
        opportunity.first_read_seconds = moment.presentation_intent.maximum_duration_seconds

    async def async_maybe_publish_intra_track_moment(
        self, *, owner_profile_id: str, session_id: str, media_identity: str
    ) -> DJMoment | None:
        """Realize one later Moment only from fresh observed current playback."""
        async with self._lock:
            active = self._active_by_profile.get(owner_profile_id)
            opportunity = self._intra_track_opportunities.get(owner_profile_id)
            if active is None or active.session_id != session_id or opportunity is None:
                return None
            playback = active.broadcast.state.playback
            position = opportunity.last_observed_position_ms
            duration = playback.duration_ms
            if opportunity.qualified_facts:
                # Fresh provider observations, not the one-second display clock,
                # drive each independent fact opportunity. No backlog or replay.
                if (opportunity.session_id != session_id or opportunity.media_identity != media_identity
                        or opportunity.item_id != playback.item_id or opportunity.blocked
                        or opportunity.fact_count >= 6 or playback.state != "playing"
                        or position is None or duration is None
                        or self._monotonic_source() - opportunity.last_observed_monotonic > 30
                        or self._monotonic_source() < opportunity.resume_ready_at
                        or duration - position < 45_000
                        or (opportunity.last_fact_position_ms is not None and
                            position - opportunity.last_fact_position_ms < max(
                                _qualified_fact_spacing_seconds(active.selected_mood, active.dj_persona, active.session_direction.direction),
                                opportunity.last_fact_read_seconds - 5) * 1000)):
                    return None
                return await self._publish_qualified_current_fact(owner_profile_id, active, opportunity)
            if (
                opportunity.session_id != session_id
                or opportunity.media_identity != media_identity
                or opportunity.item_id != playback.item_id
                or opportunity.blocked or opportunity.spent or opportunity.pending
                or opportunity.first_moment_type is None
                or not opportunity.safe_insight
                or playback.state != "playing"
                or position is None or duration is None
                or opportunity.first_moment_position_ms is None
                or self._monotonic_source() - opportunity.last_observed_monotonic > 30
                or self._monotonic_source() < opportunity.resume_ready_at
            ):
                return None
            intent = active.planner.select_intra_track_intent(
                first_type=opportunity.first_moment_type,
                first_position_ms=opportunity.first_moment_position_ms,
                first_read_seconds=opportunity.first_read_seconds,
                observed_position_ms=position,
                duration_ms=duration,
                safe_insight=opportunity.safe_insight,
                performance_memory=active.performance_memory,
                allowed_intents=active.allowed_capability_intents,
            )
            if intent is None:
                return None
            opportunity.pending = True
            generation = opportunity.generation
            safe_insight = copy.deepcopy(opportunity.safe_insight)
            working_knowledge = copy.deepcopy(active.knowledge_engine)
            working_moments = copy.deepcopy(active.moment_engine)
            direction = active.session_direction
            mood = active.selected_mood
            strategy = active.session_start_strategy
            discover = active.discover_context
            memory = active.performance_memory
            persona = active.dj_persona
            locale = active.locale
        try:
            knowledge = await working_knowledge.async_assemble_track_context(
                intent=intent, raw_insight=safe_insight, session_direction=direction,
                session_start_strategy=strategy, session_mood=mood,
                discover_context=discover, performance_memory=memory,
            )
            moment = working_moments.create_track_context(
                session_id=session_id, knowledge_intent=intent,
                selected_mood=mood, persona=persona, locale=locale,
                insight=knowledge.as_insight(),
            )
        except Exception as exc:  # noqa: BLE001
            _LOGGER.debug("DJConnect later current-track context unavailable: %s", exc.__class__.__name__)
            moment = None
        async with self._lock:
            active = self._active_by_profile.get(owner_profile_id)
            current = self._intra_track_opportunities.get(owner_profile_id)
            if (
                active is None or active.session_id != session_id
                or current is not opportunity or current.generation != generation
                or not current.pending or current.blocked
                or active.broadcast.state.playback.state != "playing"
                or active.broadcast.state.playback.item_id != current.item_id
                or self._monotonic_source() - current.last_observed_monotonic > 30
                or current.last_observed_position_ms is None
                or active.broadcast.state.playback.duration_ms is None
            ):
                if current is opportunity and current.generation == generation:
                    current.pending = False
                return None
            current.pending = False
            current.spent = True
            if moment is None or moment.moment_type is DJMomentType.SILENCE:
                return None
            remaining_ms = active.broadcast.state.playback.duration_ms - current.last_observed_position_ms
            if remaining_ms < (moment.presentation_intent.maximum_duration_seconds + 5) * 1000:
                return None
            active.knowledge_engine.__dict__.update(working_knowledge.__dict__)
            active.moment_engine.__dict__.update(working_moments.__dict__)
            await self._async_persist_moment(active, moment)
            active.publish_moment(moment)
            self._record_performance_memory(owner_profile_id, active)
            return moment

    async def _publish_qualified_current_fact(self, owner_profile_id: str, active: DJSessionRuntime,
                                        opportunity: IntraTrackOpportunity) -> DJMoment | None:
        """Run the canonical Planner→Knowledge→Moment→Flow→Broadcast chain."""
        playback = active.broadcast.state.playback
        if (playback.state != "playing" or opportunity.blocked
                or opportunity.last_observed_position_ms is None or playback.duration_ms is None
                or opportunity.session_id != active.session_id or opportunity.item_id != playback.item_id
                or self._monotonic_source() - opportunity.last_observed_monotonic > 30):
            return None
        facts = opportunity.qualified_facts
        if (active.session_start_strategy is SessionStartStrategy.DISCOVER
                and active.session_direction.direction is SessionDirectionType.EXPLORING):
            relation = active.published_recording_context.candidate(facts, opportunity.media_identity, time.monotonic())
            if relation is not None:
                facts = (relation, *facts)
        remaining_seconds=(playback.duration_ms-opportunity.last_observed_position_ms)/1000
        realizations={id(fact):active.moment_engine.preview_qualified_fact(fact=fact,selected_mood=active.selected_mood,
            persona=active.dj_persona,locale=active.locale,remaining_seconds=remaining_seconds) for fact in facts}
        selected = active.planner.select_qualified_current_fact(
            facts=facts, media_identity=opportunity.media_identity,
            used_keys=opportunity.used_fact_keys | {fact.key for fact in opportunity.qualified_facts
                if f"{fact.source_url}|fact:{fact.key}" in active.moment_engine._track_keys}, locale=active.locale,
            allowed_intents=active.allowed_capability_intents,
            session_start_strategy=active.session_start_strategy,
            session_direction=active.session_direction.direction,
            selected_mood=active.selected_mood, persona=active.dj_persona,
            performance_memory=active.performance_memory,
            remaining_seconds=(playback.duration_ms - opportunity.last_observed_position_ms) / 1000,
            realized_copies={key:((value.summary,value.content) if value else None) for key,value in realizations.items()},
        )
        if selected is None:
            return None
        intent, fact = selected
        knowledge = active.knowledge_engine.assemble_qualified_fact(
            intent=intent, fact=fact, media_identity=opportunity.media_identity, locale=active.locale,
        )
        if knowledge is None:
            return None
        working_moments = copy.deepcopy(active.moment_engine)
        moment = working_moments.create_track_context(
            session_id=active.session_id, knowledge_intent=intent, selected_mood=active.selected_mood,
            persona=active.dj_persona, locale=active.locale, insight=knowledge.as_insight(),
            fact_realization=realizations[id(fact)],
        )
        if moment.moment_type is DJMomentType.SILENCE:
            return None
        playback = active.broadcast.state.playback
        if (playback.state != "playing" or opportunity.blocked
                or opportunity.last_observed_position_ms is None or playback.duration_ms is None
                or self._monotonic_source() - opportunity.last_observed_monotonic > 30
                or playback.duration_ms - opportunity.last_observed_position_ms < (moment.presentation_intent.maximum_duration_seconds + 5) * 1000):
            return None
        await self._async_persist_moment(active, moment)
        active.publish_moment(moment)
        active.published_recording_context.commit(fact, time.monotonic())
        active.moment_engine.__dict__.update(working_moments.__dict__)
        active.moment_engine.commit_expression(moment,active.planner.output.session_flow)
        opportunity.used_fact_keys.add(fact.key)
        opportunity.fact_count += 1
        opportunity.last_fact_position_ms = opportunity.last_observed_position_ms
        opportunity.last_fact_read_seconds = moment.presentation_intent.maximum_duration_seconds
        self._record_performance_memory(owner_profile_id, active)
        return moment

    async def async_advance_playback_progress(
        self, *, owner_profile_id: str, session_id: str
    ) -> bool:
        """Advance one active Runtime's server-owned progress estimate."""
        async with self._lock:
            active = self._active_by_profile.get(owner_profile_id)
            clock = self._playback_progress_clocks.get(owner_profile_id)
            if active is not None and active.session_id == session_id:
                active.broadcast.refresh_native_delivery()
            if (
                active is None
                or active.session_id != session_id
                or clock is None
                or clock.session_id != session_id
            ):
                return False
            playback = active.broadcast.state.playback
            if playback.state != "playing" or playback.item_id != clock.item_id:
                self._playback_progress_clocks.pop(owner_profile_id, None)
                return False
            elapsed_ms = max(0, int((time.monotonic() - clock.anchor_monotonic) * 1000))
            position_ms = min(clock.duration_ms, clock.anchor_position_ms + elapsed_ms)
            if position_ms <= clock.last_published_position_ms:
                return False
            updated = RendererSafePlaybackProjection(
                **{
                    **playback.__dict__,
                    "position_ms": position_ms,
                    "updated_at": _timestamp(),
                }
            )
            changed = active.broadcast.update_playback_progress(updated)
            if changed:
                clock.last_published_position_ms = position_ms
            if position_ms >= clock.duration_ms:
                self._playback_progress_clocks.pop(owner_profile_id, None)
            return changed

    def _replace_playback_progress_clock(
        self,
        owner_profile_id: str,
        playback: RendererSafePlaybackProjection,
        session_id: str,
    ) -> None:
        """Start only a bounded clock based on a reliable backend observation."""
        if (
            playback.state != "playing"
            or not playback.item_id
            or playback.position_ms is None
            or playback.duration_ms is None
            or playback.duration_ms <= 0
        ):
            self._playback_progress_clocks.pop(owner_profile_id, None)
            return
        self._playback_progress_clocks[owner_profile_id] = PlaybackProgressClock(
            session_id=session_id,
            item_id=playback.item_id,
            anchor_position_ms=playback.position_ms,
            duration_ms=playback.duration_ms,
            anchor_monotonic=time.monotonic(),
            last_published_position_ms=playback.position_ms,
        )

    async def async_replan_observed_playback(
        self,
        *,
        owner_profile_id: str,
        session_id: str,
        upcoming_playback: UpcomingPlaybackProjection,
        approve_earliest: bool = False,
    ) -> bool:
        """Apply an observed playback change to the active Planner Horizon only.

        This is the Runtime-owned planning path for observation changes that do
        not constitute Track Started and therefore must not realize a DJMoment.
        It exposes no planning state and never publishes a renderer projection.
        """
        async with self._lock:
            active = self._active_by_profile.get(owner_profile_id)
            if (
                active is None
                or active.session_id != session_id
                or active.planner.horizon is None
            ):
                return False
            window = active.planner.horizon.replan(upcoming_playback=upcoming_playback)
            if approve_earliest:
                window.evaluate_readiness(
                    invalidation_generation=active.planner.horizon.invalidation_generation
                )
                return window.approve_earliest_planned_intent() is not None
            return True

    def _accept_track_started_media(
        self, owner_profile_id: str, session_id: str, media_identity: str, *, allow_initial: bool = False
    ) -> DJSessionRuntime | None:
        """Return an active session after accepting one non-duplicate track identity.

        The caller holds ``_lock``. The first observed identity establishes the
        baseline only; subsequent distinct identities can create a moment.
        """
        active = self._active_by_profile.get(owner_profile_id)
        if active is None or active.session_id != session_id:
            return None
        if not media_identity:
            return active
        if active.last_accepted_media_identity == media_identity:
            return None
        updated = DJSessionRuntime(
            **{**active.__dict__, "last_accepted_media_identity": media_identity}
        )
        self._active_by_profile[owner_profile_id] = updated
        return updated if active.last_accepted_media_identity or allow_initial else None

    async def async_process_track_started(
        self,
        *,
        owner_profile_id: str,
        session_id: str,
        insight_provider: Callable[[], Awaitable[dict[str, Any]]],
        media_identity: str = "",
        upcoming_playback: UpcomingPlaybackProjection | None = None,
        require_current_playback: bool = False,
        allow_initial_facts: bool = False,
    ) -> DJMoment | None:
        """Orchestrate Planner → Knowledge → Moment → Flow → Broadcast."""
        async with self._lock:
            prior = self._active_by_profile.get(owner_profile_id)
            initial = prior is not None and not prior.last_accepted_media_identity
            active = self._accept_track_started_media(owner_profile_id, session_id, media_identity, allow_initial=allow_initial_facts)
            if active is None:
                return None
            started_opportunity = self._intra_track_opportunities.get(owner_profile_id)
            started_generation = started_opportunity.generation if started_opportunity else None
        try:
            raw_insight = await insight_provider()
        except Exception as exc:  # noqa: BLE001
            _LOGGER.debug("DJConnect Track Insight unavailable: %s", exc.__class__.__name__)
            raw_insight = {}
        async with self._lock:
            active = self._active_by_profile.get(owner_profile_id)
            if not self._track_started_result_is_current(
                active,
                session_id=session_id,
                media_identity=media_identity,
                require_current_playback=require_current_playback,
            ):
                return None
            if require_current_playback and (
                started_opportunity is None
                or self._intra_track_opportunities.get(owner_profile_id) is not started_opportunity
                or started_opportunity.generation != started_generation or started_opportunity.blocked
                or self._monotonic_source() - started_opportunity.last_observed_monotonic > 30
            ):
                return None
            facts = raw_insight.get("_qualified_facts")
            opportunity = self._intra_track_opportunities.get(owner_profile_id)
            if isinstance(facts, tuple) and opportunity is not None and opportunity.media_identity == media_identity and not opportunity.blocked:
                opportunity.qualified_facts = tuple(fact for fact in facts[:6] if type(fact) is QualifiedSessionFact
                                                    and fact.eligible(media_identity, time.monotonic()))
                if opportunity.qualified_facts:
                    return await self._publish_qualified_current_fact(owner_profile_id, active, opportunity)
            if initial and allow_initial_facts:
                # Initial metadata establishes the old baseline unless a new
                # qualified source fact exists; never manufacture an intro.
                return None
            working_planner = copy.deepcopy(active.planner)
            working_knowledge_engine = copy.deepcopy(active.knowledge_engine)
            working_moment_engine = copy.deepcopy(active.moment_engine)
            working_coordinator = copy.deepcopy(active.planning_coordinator)
            if active.session_start_strategy is SessionStartStrategy.DISCOVER:
                working_planner.note_discover_track_started()
            planning_input = working_planner.project_track_started_planning_input(
                session_id=active.session_id,
                upcoming_playback=upcoming_playback,
                session_start_strategy=active.session_start_strategy,
                session_direction=active.session_direction,
                selected_mood=active.selected_mood,
                persona=active.dj_persona,
                knowledge_hints=_planner_knowledge_hints(raw_insight),
                performance_memory=active.performance_memory,
                discover_context=active.discover_context,
            )
        _LOGGER.debug("DJConnect Planning Runtime Coordinator lifecycle entered")
        try:
            coordinated = await working_coordinator.async_coordinate_track_started(
                planner=working_planner,
                knowledge_engine=working_knowledge_engine,
                moment_engine=working_moment_engine,
                session_id=active.session_id,
                selected_mood=active.selected_mood,
                persona=active.dj_persona,
                locale=active.locale,
                session_direction=active.session_direction,
                session_start_strategy=active.session_start_strategy,
                performance_memory=active.performance_memory,
                discover_context=active.discover_context,
                raw_insight=raw_insight,
                planning_input=planning_input,
                allowed_intents=active.allowed_capability_intents,
            )
        except Exception as exc:  # noqa: BLE001
            _LOGGER.debug("DJConnect Planning Runtime Coordinator failed: %s", exc.__class__.__name__)
            working_coordinator._fallback("planning_lifecycle_failed")
            coordinated = None
        async with self._lock:
            active = self._active_by_profile.get(owner_profile_id)
            if not self._track_started_result_is_current(
                active,
                session_id=session_id,
                media_identity=media_identity,
                require_current_playback=require_current_playback,
            ):
                return None
            retained_horizon = active.planner.horizon
            active.planner.__dict__.clear()
            active.planner.__dict__.update(working_planner.__dict__)
            if retained_horizon is not None and working_planner.horizon is not None:
                retained_horizon.__dict__.clear()
                retained_horizon.__dict__.update(working_planner.horizon.__dict__)
                active.planner.horizon = retained_horizon
            active.knowledge_engine.__dict__.clear()
            active.knowledge_engine.__dict__.update(working_knowledge_engine.__dict__)
            active.moment_engine.__dict__.clear()
            active.moment_engine.__dict__.update(working_moment_engine.__dict__)
            active.planning_coordinator.__dict__.clear()
            active.planning_coordinator.__dict__.update(working_coordinator.__dict__)
            if coordinated is not None:
                is_session_update = active.planning_coordinator.last_session_direction is not None
                if is_session_update:
                    updated_direction = active.planning_coordinator.last_session_direction
                    assert updated_direction is not None
                    if (active.planner.discover_narrative_line is not None
                            and updated_direction.direction is not active.session_direction.direction):
                        active.planner.clear_discover_narrative()
                    active = DJSessionRuntime(
                        **{**active.__dict__, "session_direction": updated_direction}
                    )
                    self._active_by_profile[owner_profile_id] = active
                    active.broadcast.update_session_direction(updated_direction)
                    active.planner.last_decision = planning_input.planner_decision
                await self._async_persist_moment(active, coordinated)
                active.publish_moment(coordinated)
                active.planning_coordinator.confirm_published(active.planner)
                self._note_initial_track_moment(
                    owner_profile_id=owner_profile_id, active=active,
                    media_identity=media_identity, raw_insight=raw_insight,
                    moment=coordinated,
                )
                if coordinated.moment_type is not DJMomentType.SILENCE:
                    active.planner.record_spoken_moment()
                if coordinated.moment_type is not DJMomentType.SILENCE and not is_session_update:
                    active = self._record_performance_memory(owner_profile_id, active)
                    active = self._publish_discover_transition(
                        owner_profile_id, active, coordinated, raw_insight, media_identity
                    )
                    transition_decision = active.planner.evaluate_transition_after_moment(
                        triggering_intent=coordinated.knowledge_intent,
                        session_direction=active.session_direction,
                        performance_memory=active.performance_memory,
                    )
                    if transition_decision.decision_type is PlannerDecisionType.CREATE_TRANSITION:
                        transition = active.moment_engine.create_transition(
                            session_id=active.session_id,
                            approval=transition_decision,
                            selected_mood=active.selected_mood,
                            persona=active.dj_persona,
                            locale=active.locale,
                        )
                        if transition.moment_type is DJMomentType.TRANSITION:
                            await self._async_persist_moment(active, transition)
                            active.publish_moment(
                                transition,
                                SessionFlowPosition(transition_decision.transition_placement),
                            )
                            active = self._record_performance_memory(owner_profile_id, active)
                else:
                    active = self._record_performance_memory(owner_profile_id, active)
                    self._publish_discover_transition(
                        owner_profile_id, active, coordinated, raw_insight, media_identity
                    )
                _LOGGER.debug(
                    "DJConnect Planning Runtime Coordinator lifecycle completed: approval_source=%s generation=%s",
                    active.planning_coordinator.last_approval_source,
                    active.planning_coordinator.last_planning_generation,
                )
                return coordinated
        _LOGGER.debug(
            "DJConnect Planning Runtime Coordinator fallback invoked: reason=%s generation=%s",
            active.planning_coordinator.last_fallback_reason,
            active.planning_coordinator.last_planning_generation,
        )
        hints = _planner_knowledge_hints(raw_insight)
        async with self._lock:
            active = self._active_by_profile.get(owner_profile_id)
            if not self._track_started_result_is_current(
                active,
                session_id=session_id,
                media_identity=media_identity,
                require_current_playback=require_current_playback,
            ):
                return None
            active, legacy_moment = await self._apply_legacy_initial_track_started_decision(
                owner_profile_id, active
            )
            if legacy_moment is not None:
                if active.planner.discover_narrative_line is not None:
                    active.planner.clear_discover_narrative()
                return legacy_moment
            decision = active.planner.evaluate_track_started(
                session_start_strategy=active.session_start_strategy,
                session_direction=active.session_direction,
                selected_mood=active.selected_mood,
                persona=active.dj_persona,
                knowledge_hints=hints,
                performance_memory=active.performance_memory,
                discover_context=active.discover_context,
                record_track_available=False,
            )
            if decision.decision_type is PlannerDecisionType.SILENCE:
                moment = active.moment_engine.create_silence(
                    session_id=active.session_id,
                    selected_mood=active.selected_mood,
                    persona=active.dj_persona,
                    locale=active.locale,
                    reason=decision.reason,
                )
                await self._async_persist_moment(active, moment)
                active.publish_moment(moment)
                active = self._record_performance_memory(owner_profile_id, active)
                self._publish_discover_transition(
                    owner_profile_id, active, moment, raw_insight, media_identity
                )
                return moment
            intent = decision.knowledge_intent
            if intent is None:
                if active.planner.discover_narrative_line is not None:
                    active.planner.clear_discover_narrative()
                return None
        try:
            knowledge = await active.knowledge_engine.async_assemble_track_context(
                intent=intent,
                raw_insight=raw_insight,
                session_direction=active.session_direction,
                session_start_strategy=active.session_start_strategy,
                session_mood=active.selected_mood,
                discover_context=active.discover_context,
                performance_memory=active.performance_memory,
                personal_context_authorized=False,
            )
        except Exception as exc:  # noqa: BLE001
            _LOGGER.debug("DJConnect Knowledge Engine unavailable: %s", exc.__class__.__name__)
            knowledge = KnowledgeContext(
                (), (), (), session_direction=active.session_direction,
                session_start_strategy=active.session_start_strategy,
                session_mood=active.selected_mood,
                discover_context=active.discover_context,
                performance_memory=active.performance_memory,
            )
        async with self._lock:
            active = self._active_by_profile.get(owner_profile_id)
            if not self._track_started_result_is_current(
                active,
                session_id=session_id,
                media_identity=media_identity,
                require_current_playback=require_current_playback,
            ):
                return None
            moment = active.moment_engine.create_track_context(
                session_id=active.session_id,
                knowledge_intent=intent,
                selected_mood=active.selected_mood,
                persona=active.dj_persona,
                locale=active.locale,
                insight=knowledge.as_insight(),
            )
            if moment.moment_type is not DJMomentType.SILENCE:
                active.planner.record_spoken_moment()
            await self._async_persist_moment(active, moment)
            active.publish_moment(moment)
            self._note_initial_track_moment(
                owner_profile_id=owner_profile_id, active=active,
                media_identity=media_identity, raw_insight=raw_insight,
                moment=moment,
            )
            active = self._record_performance_memory(owner_profile_id, active)
            active = self._publish_discover_transition(
                owner_profile_id, active, moment, raw_insight, media_identity
            )
            transition_decision = active.planner.evaluate_transition_after_moment(
                triggering_intent=intent,
                session_direction=active.session_direction,
                performance_memory=active.performance_memory,
            )
            if transition_decision.decision_type is PlannerDecisionType.CREATE_TRANSITION:
                transition = active.moment_engine.create_transition(
                    session_id=active.session_id,
                    approval=transition_decision,
                    selected_mood=active.selected_mood,
                    persona=active.dj_persona,
                    locale=active.locale,
                )
                if transition.moment_type is DJMomentType.TRANSITION:
                    await self._async_persist_moment(active, transition)
                    active.publish_moment(
                        transition,
                        SessionFlowPosition(transition_decision.transition_placement),
                    )
            self._record_performance_memory(owner_profile_id, active)
            return moment

    async def async_restore_track_started_media(
        self,
        *,
        owner_profile_id: str,
        session_id: str,
        media_identity: str,
        previous_media_identity: str,
    ) -> bool:
        """Restore retryability only when cancelled work is still the newest work."""
        async with self._lock:
            active = self._active_by_profile.get(owner_profile_id)
            if (
                active is None
                or active.session_id != session_id
                or active.last_accepted_media_identity != media_identity
            ):
                return False
            self._active_by_profile[owner_profile_id] = DJSessionRuntime(
                **{
                    **active.__dict__,
                    "last_accepted_media_identity": previous_media_identity,
                }
            )
            return True

    @staticmethod
    def _track_started_result_is_current(
        active: DJSessionRuntime | None,
        *,
        session_id: str,
        media_identity: str,
        require_current_playback: bool,
    ) -> bool:
        """Reject slow enrichment after its Session or playback item changed."""
        if active is None or active.session_id != session_id:
            return False
        if not require_current_playback:
            return True
        if not media_identity or active.last_accepted_media_identity != media_identity:
            return False
        expected_item_id = hashlib.sha256(media_identity.encode()).hexdigest()[:24]
        return (
            active.broadcast.state.playback.item_id == expected_item_id
            and active.broadcast.state.playback.state == "playing"
        )

    def _publish_discover_transition(
        self,
        owner_profile_id: str,
        active: DJSessionRuntime,
        moment: DJMoment,
        raw_insight: dict[str, Any],
        media_identity: str,
    ) -> DJSessionRuntime:
        """Commit one approved Discover relation through the existing Flow path."""
        if (
            active.session_start_strategy is not SessionStartStrategy.DISCOVER
            or active.last_accepted_media_identity != media_identity
        ):
            return active
        evidence = active.knowledge_engine.select_discover_narrative_evidence(
            raw_insight, media_identity
        )
        decision = active.planner.evaluate_discover_narrative_after_moment(
            current_moment=moment,
            strategy=active.session_start_strategy,
            session_direction=active.session_direction,
            selected_mood=active.selected_mood,
            persona=active.dj_persona,
            performance_memory=active.performance_memory,
            evidence=evidence,
        )
        if decision is None:
            return active
        transition = active.moment_engine.create_transition(
            session_id=active.session_id,
            approval=decision,
            selected_mood=active.selected_mood,
            persona=active.dj_persona,
            locale=active.locale,
        )
        if transition.moment_type is DJMomentType.TRANSITION:
            active.publish_moment(transition, SessionFlowPosition(decision.transition_placement))
            active = self._record_performance_memory(owner_profile_id, active)
        return active

    async def _apply_legacy_initial_track_started_decision(
        self, owner_profile_id: str, active: DJSessionRuntime
    ) -> tuple[DJSessionRuntime, DJMoment | None]:
        """Run the established first Track Started decision only for bounded fallback."""
        decision = active.planner.evaluate_track_started(
            session_start_strategy=active.session_start_strategy,
            session_direction=active.session_direction,
            selected_mood=active.selected_mood,
            persona=active.dj_persona,
            performance_memory=active.performance_memory,
            discover_context=active.discover_context,
        )
        if decision.proposed_session_direction is not None:
            updated_direction = SessionDirection(
                direction=decision.proposed_session_direction,
                initialized_at=active.session_direction.initialized_at,
                updated_at=_timestamp(),
                start_strategy=active.session_direction.start_strategy,
            )
            if (active.planner.discover_narrative_line is not None
                    and updated_direction.direction is not active.session_direction.direction):
                active.planner.clear_discover_narrative()
            active = DJSessionRuntime(
                **{**active.__dict__, "session_direction": updated_direction}
            )
            self._active_by_profile[owner_profile_id] = active
            active.broadcast.update_session_direction(updated_direction)
        if decision.decision_type is PlannerDecisionType.CREATE_SESSION_UPDATE:
            knowledge = active.knowledge_engine.assemble_session_direction_context(
                active.session_direction,
                active.session_start_strategy,
                active.selected_mood,
                active.performance_memory,
            )
            moment = active.moment_engine.create_session_update(
                session_id=active.session_id,
                selected_mood=active.selected_mood,
                persona=active.dj_persona,
                locale=active.locale,
                session_direction=active.session_direction,
                knowledge_context=knowledge,
            )
            if moment.moment_type is not DJMomentType.SILENCE:
                active.planner.record_spoken_moment()
                await self._async_persist_moment(active, moment)
                active.publish_moment(moment)
            self._record_performance_memory(owner_profile_id, active)
            return active, moment
        if decision.decision_type is PlannerDecisionType.SILENCE:
            moment = active.moment_engine.create_silence(
                session_id=active.session_id,
                selected_mood=active.selected_mood,
                persona=active.dj_persona,
                locale=active.locale,
                reason=decision.reason,
            )
            await self._async_persist_moment(active, moment)
            active.publish_moment(moment)
            self._record_performance_memory(owner_profile_id, active)
            return active, moment
        return active, None

    def _record_performance_memory(
        self, owner_profile_id: str, active: DJSessionRuntime
    ) -> DJSessionRuntime:
        """Refresh the Runtime-owned projection after its Flow receives a Moment."""
        memory = PerformanceMemory.from_session_flow(
            active.planner.output.session_flow, active.moment_engine.moments
        )
        updated = DJSessionRuntime(**{**active.__dict__, "performance_memory": memory})
        self._active_by_profile[owner_profile_id] = updated
        return updated

    async def async_generate_track_context(
        self,
        *,
        owner_profile_id: str,
        session_id: str,
        insight_provider: Callable[[], Awaitable[dict[str, Any]]],
    ) -> DJMoment | None:
        """Compatibility wrapper for the canonical Track Started orchestration."""
        return await self.async_process_track_started(
            owner_profile_id=owner_profile_id,
            session_id=session_id,
            insight_provider=insight_provider,
        )

    async def async_update_mood(
        self, *, owner_profile_id: str, session_id: str, selected_mood: str
    ) -> DJSessionRuntime | None:
        """Update dynamic Runtime Mood; prior Moment snapshots remain frozen."""
        async with self._lock:
            active = self._active_by_profile.get(owner_profile_id)
            if active is None or active.session_id != session_id:
                return None
            if (active.planner.discover_narrative_line is not None
                    and selected_mood != active.selected_mood):
                active.planner.clear_discover_narrative()
            active.broadcast.state = DJBroadcastState(**{**active.broadcast.state.__dict__, "selected_mood": selected_mood})
            active.broadcast._publish(BroadcastEventType.MOOD_CHANGED, {"session": active.broadcast.as_dict()["session"]})
            updated = DJSessionRuntime(**{**active.__dict__, "selected_mood": selected_mood})
            self._active_by_profile[owner_profile_id] = updated
            return updated

    async def async_update_persona(
        self, *, owner_profile_id: str, session_id: str, dj_persona: DJPersona
    ) -> DJSessionRuntime | None:
        """Change only future Moment behaviour for this active Runtime."""
        async with self._lock:
            active = self._active_by_profile.get(owner_profile_id)
            if active is None or active.session_id != session_id:
                return None
            if (active.planner.discover_narrative_line is not None
                    and dj_persona is not active.dj_persona):
                active.planner.clear_discover_narrative()
            updated = DJSessionRuntime(**{**active.__dict__, "dj_persona": dj_persona})
            self._active_by_profile[owner_profile_id] = updated
            return updated

    async def async_get_active(self, owner_profile_id: str) -> DJSessionRuntime | None:
        """Return the active Runtime for a Profile, if one exists."""
        async with self._lock:
            return self._active_by_profile.get(owner_profile_id)

    async def async_subscribe(
        self,
        *,
        owner_profile_id: str,
        session_id: str,
        callback: Callable[[dict[str, Any]], None],
    ) -> tuple[str, dict[str, Any]] | None:
        """Subscribe an authenticated owner renderer to its active Runtime only."""
        async with self._lock:
            active = self._active_by_profile.get(owner_profile_id)
            if active is None or active.session_id != session_id:
                return None
            return active.broadcast.subscribe(callback)

    async def async_register_subscription(
        self,
        *,
        owner_profile_id: str,
        session_id: str,
        callback: Callable[[dict[str, Any]], None],
    ) -> str | None:
        """Register an authenticated owner renderer without a snapshot."""
        async with self._lock:
            active = self._active_by_profile.get(owner_profile_id)
            if active is None or active.session_id != session_id:
                return None
            return active.broadcast.register_subscription(callback)

    async def async_register_pending_subscription(
        self,
        *,
        owner_profile_id: str,
        session_id: str,
        callback: Callable[[dict[str, Any]], None],
        authorization_entry_id: str = "",
        authorization_entry_generation: int = 0,
    ) -> str | None:
        """Register an owner renderer without delivering events before its snapshot."""
        async with self._lock:
            active = self._active_by_profile.get(owner_profile_id)
            if (active is None or active.session_id != session_id
                    or (authorization_entry_id and authorization_entry_generation != self.receiver_entry_generation(authorization_entry_id))):
                return None
            subscription_id = active.broadcast.register_pending_subscription(callback)
            if authorization_entry_id:
                active.broadcast._owner_subscription_entries[subscription_id] = authorization_entry_id
            return subscription_id

    async def async_recover_owner_subscription(
        self,
        *,
        owner_profile_id: str,
        session_id: str,
        recovery_cursor: str,
        callback: Callable[[dict[str, Any]], None],
        authorization_entry_id: str = "",
        authorization_entry_generation: int = 0,
    ) -> tuple[str, dict[str, Any]] | None:
        """Atomically recover one owner stream and prepare its live delivery."""
        async with self._lock:
            active = self._active_by_profile.get(owner_profile_id)
            if (active is None or active.session_id != session_id
                    or (authorization_entry_id and authorization_entry_generation != self.receiver_entry_generation(authorization_entry_id))):
                return None
            recovery = active.broadcast.recover_owner(recovery_cursor)
            if recovery is None:
                return None
            subscription_id = active.broadcast.register_pending_subscription(callback)
            if authorization_entry_id:
                active.broadcast._owner_subscription_entries[subscription_id] = authorization_entry_id
            return subscription_id, recovery

    async def async_activate_subscription(
        self,
        *,
        owner_profile_id: str,
        session_id: str,
        subscription_id: str,
    ) -> bool:
        """Enable live delivery after the owner renderer received its snapshot."""
        async with self._lock:
            active = self._active_by_profile.get(owner_profile_id)
            if (active is not None and active.session_id == session_id
                    and subscription_id in active.broadcast._subscribers):
                active.broadcast.activate_subscription(subscription_id)
                return True
            return False

    async def async_subscribe_with_broadcast_token(
        self,
        *,
        session_id: str,
        broadcast_token: str,
        callback: Callable[[dict[str, Any]], None],
    ) -> tuple[str, dict[str, Any]] | None:
        """Resolve one exact active Broadcast without exposing its Profile."""
        async with self._lock:
            for active in self._active_by_profile.values():
                if active.session_id == session_id:
                    return active.broadcast.subscribe_with_broadcast_token(broadcast_token, callback)
            return None

    async def async_broadcast_token_for_owner(
        self, *, owner_profile_id: str, session_id: str
    ) -> dict[str, Any] | None:
        """Return an ephemeral token only to the Profile that owns the Runtime."""
        async with self._lock:
            active = self._active_by_profile.get(owner_profile_id)
            if active is None or active.session_id != session_id:
                return None
            return active.broadcast.broadcast_token_contract()

    async def async_unsubscribe_broadcast_token(
        self, *, session_id: str, subscription_id: str
    ) -> None:
        """Release a token Receiver without resolving or exposing its Profile."""
        async with self._lock:
            for active in self._active_by_profile.values():
                if active.session_id == session_id:
                    active.broadcast.unsubscribe(subscription_id)
                    return

    async def async_submit_audience_signal_with_broadcast_token(self, *, session_id: str, broadcast_token: str, signal: str, value: str = "") -> dict[str, Any] | None:
        """Accept an allowed Receiver suggestion; never execute playback."""
        try:
            signal_type = AudienceSignalType(signal)
        except ValueError:
            return None
        async with self._lock:
            for active in self._active_by_profile.values():
                if active.session_id == session_id and secrets.compare_digest(active.broadcast.broadcast_token, broadcast_token):
                    active.submit_audience_signal(signal_type, value)
                    return active.broadcast.as_dict()["audience"]
            return None

    async def async_unsubscribe(
        self, *, owner_profile_id: str, session_id: str, subscription_id: str
    ) -> None:
        """Release an owner renderer subscription when its connection closes."""
        async with self._lock:
            active = self._active_by_profile.get(owner_profile_id)
            if active is not None and active.session_id == session_id:
                active.broadcast.unsubscribe(subscription_id)

    def receiver_entry_generation(self, entry_id: str) -> int:
        """Return the ephemeral entry epoch captured by a loaded owner Runtime."""
        return self._receiver_entry_generations.get(entry_id, 0)

    async def async_issue_receiver_end_grant(self, *, owner_profile_id: str, session_id: str, entry_id: str, entry_generation: int = 0) -> str:
        """Issue a separate end-only credential after explicit owner consent."""
        async with self._lock:
            active = self._active_by_profile.get(owner_profile_id)
            if active is None or active.session_id != session_id or not entry_id:
                return ""
            if entry_generation != self.receiver_entry_generation(entry_id):
                return ""
            now = self._monotonic_source()
            self._end_grants = {key: value for key, value in self._end_grants.items() if value[2] > now}
            if len(self._end_grants) >= 64:
                return ""
            grant = secrets.token_urlsafe(32)
            self._end_grants[grant] = (owner_profile_id, session_id, now + 3600, entry_id)
            return grant

    async def async_revoke_receiver_end_grants(self, *, owner_profile_id: str, session_id: str) -> None:
        """Revoke temporary end authority when its observer unloads/reloads."""
        async with self._lock:
            self._end_grants = {key: value for key, value in self._end_grants.items()
                                if value[:2] != (owner_profile_id, session_id)}

    async def async_revoke_receiver_end_grants_for_entry(self, entry_id: str) -> None:
        """Revoke owner-entry authority even when no playback observer exists."""
        async with self._lock:
            self._receiver_entry_generations[entry_id] = self.receiver_entry_generation(entry_id) + 1
            self._end_grants = {key: value for key, value in self._end_grants.items() if value[3] != entry_id}
            for active in self._active_by_profile.values():
                active.broadcast.revoke_owner_entry_subscriptions(entry_id)

    async def async_end_with_receiver_grant(self, *, session_id: str, grant: str, authorized_entry_ids: frozenset[str] | None = None) -> DJSessionRuntime | None:
        """Consume one exact-session end grant; Broadcast credentials cannot end."""
        async with self._lock:
            authorization = self._end_grants.get(grant)
            if authorization is None or authorization[1] != session_id or authorization[2] <= self._monotonic_source():
                return None
            if authorized_entry_ids is not None and authorization[3] not in authorized_entry_ids:
                del self._end_grants[grant]
                return None
            del self._end_grants[grant]
            profile_id = authorization[0]
        return await self.async_end(owner_profile_id=profile_id, session_id=session_id)

    async def _async_persist_moment(self, active: DJSessionRuntime, moment: DJMoment) -> None:
        """Explicit historical field qualification before actual live publication."""
        if self._historical_projections is None or moment.session_id != active.session_id:
            return
        from .session_facts import QualifiedSessionFact, SharedProducerFact

        source = getattr(moment, "source_fact", None)
        metadata = dict(moment.generation_metadata)
        basis = ""
        if isinstance(source, QualifiedSessionFact):
            expected = {
                "provider": source.provider,
                "url": source.source_url,
                "license": source.license,
            }
            if isinstance(source, SharedProducerFact) and source.previous_evidence is not None:
                expected["url_previous"] = source.previous_evidence.source_url
            if (
                source.provider in {"MusicBrainz", "Wikidata"}
                and source.license == "CC0-1.0"
                and source.eligible(source.media_identity, time.monotonic())
                and dict(moment.source_attribution) == expected
            ):
                basis = "cc0_normalized_fields_v1"
        elif (
            not moment.source_attribution
            and moment.source_references == ("session_direction",)
            and moment.moment_type.value == "session"
            and metadata.get("context_source") == "session_direction"
            and metadata.get("validated") == "true"
        ):
            basis = "runtime_authored_direction_v1"
        if not basis:
            return
        await self._historical_projections.async_append_entries(
            active.owner_profile_id,
            active.session_id,
            [
                {
                    "kind": "dj_moment",
                    "reference_id": moment.moment_id,
                    "occurred_at": moment.created_at,
                    "body": {
                        "moment_id": moment.moment_id,
                        "moment_type": moment.moment_type.value,
                        "text": moment.content,
                        "summary": moment.summary,
                        "source_attribution": dict(moment.source_attribution),
                        "archive_basis": basis,
                        "persona": active.dj_persona.value,
                        "locale": active.locale,
                    },
                }
            ],
        )
    async def async_end(
        self,
        *,
        owner_profile_id: str,
        session_id: str = "",
    ) -> DJSessionRuntime | None:
        """End and dispose of the active Runtime for a Profile."""
        async with self._lock:
            active = self._active_by_profile.get(owner_profile_id)
            if active is None:
                return None
            if session_id and active.session_id != session_id:
                return None
            if self._persistent_sessions is not None:
                persistent = await self._persistent_sessions.async_transition(
                    owner_profile_id, active.session_id, PERSISTENT_SESSION_ENDED
                )
                if self._historical_projections is not None:
                    await self._historical_projections.async_project_session(persistent)
                    for ordering, moment in enumerate(active.moment_engine.moments):
                        if moment.source_attribution:
                            # New source cards are qualified for ephemeral display,
                            # not durable historical reuse without attribution.
                            continue
                        await self._historical_projections.async_project_moment(
                            session_id=active.session_id,
                            moment_id=moment.moment_id,
                            owner_profile_id=owner_profile_id,
                            moment_type=moment.moment_type.value,
                            rendered_text=moment.content,
                            presentation_metadata=json.dumps(moment.presentation_intent.as_dict(), sort_keys=True),
                            visibility=moment.presentation_intent.visibility.value,
                            ordering=ordering,
                            created_at=moment.created_at,
                        )
            self._playback_progress_clocks.pop(owner_profile_id, None)
            self._intra_track_opportunities.pop(owner_profile_id, None)
            active.published_recording_context.clear()
            active.moment_engine._expression_forms=()
            active.moment_engine._expression_moment_ids=()
            active.broadcast.update_runtime_state(SessionRuntimeState.ENDING)
            active.planner.clear_discover_narrative()
            ending = DJSessionRuntime(
                **{**active.__dict__, "runtime_state": SessionRuntimeState.ENDING}
            )
            active.broadcast.update_runtime_state(SessionRuntimeState.ENDED)
            active.planner.dispose_flow_change_journal()
            active.planning_coordinator.dispose()
            ended = DJSessionRuntime(
                **{
                    **ending.__dict__,
                    "runtime_state": SessionRuntimeState.ENDED,
                    "performance_memory": PerformanceMemory(
                        active.performance_memory.source_flow_id
                    ),
                }
            )
            active.broadcast.close()
            self._active_by_profile.pop(owner_profile_id, None)
            self._end_grants = {key: value for key, value in self._end_grants.items() if value[1] != active.session_id}
            return ended


def session_runtime_manager(hass: Any) -> SessionRuntimeManager:
    """Return the integration-wide ephemeral Session Runtime Manager."""
    domain_data = hass.data.setdefault(DOMAIN, {})
    manager = domain_data.get("session_runtime_manager")
    if manager is None:
        try:
            sessions = PersistentSessionRepository(persistence_service(hass))
        except RuntimeError:
            sessions = None
        manager = SessionRuntimeManager(
            sessions,
            HistoricalProjectionRepository(persistence_service(hass)) if sessions is not None else None,
        )
        domain_data["session_runtime_manager"] = manager
    return manager


def _timestamp() -> str:
    return datetime.now(UTC).isoformat()


def _session_start_configuration(
    strategy: SessionStartStrategy,
) -> SessionStartConfiguration:
    """Resolve the bounded, deterministic Runtime initialization contract."""
    configurations = {
        SessionStartStrategy.CONTINUE: SessionStartConfiguration(
            strategy, SessionDirectionType.MAINTAINING_ENERGY,
            PlannerConfiguration(interaction_profile="continuity"), "continuity",
        ),
        SessionStartStrategy.DISCOVER: SessionStartConfiguration(
            strategy, SessionDirectionType.EXPLORING,
            PlannerConfiguration(
                recommendation_preference="prefer",
                exploration_preference="high",
                interaction_profile="curious",
            ), "curious",
        ),
        SessionStartStrategy.MANUAL: SessionStartConfiguration(
            strategy, SessionDirectionType.MAINTAINING_ENERGY,
            PlannerConfiguration(), "balanced",
        ),
    }
    return configurations[strategy]


def _initial_session_direction(
    configuration: SessionStartConfiguration, timestamp: str
) -> SessionDirection:
    """Map bounded Session Start intent to its first Runtime Direction."""
    return SessionDirection(
        configuration.initial_direction,
        timestamp,
        timestamp,
        configuration.strategy,
    )


def _planned_direction(
    *,
    current: SessionDirectionType,
    selected_mood: str,
    persona: DJPersona,
) -> SessionDirectionType:
    """Keep the first Direction adjustment deterministic and playback-neutral."""
    if selected_mood in {"party", "energy", "high_energy"} or persona is DJPersona.FESTIVAL_DJ:
        return SessionDirectionType.BUILDING_ENERGY
    if selected_mood == "chill":
        return SessionDirectionType.COOLING_DOWN
    if selected_mood in {"deep", "focus"}:
        return SessionDirectionType.DEEPENING
    if selected_mood in {"explore", "discovery"}:
        return SessionDirectionType.EXPLORING
    return current


def _prioritized_knowledge_choices(
    *,
    session_start_strategy: SessionStartStrategy,
    selected_mood: str,
    persona: DJPersona,
    session_direction: SessionDirectionType,
    recommendation_preference: str,
) -> tuple[tuple[str, PlannerDecisionType, KnowledgeIntentType, str], ...]:
    """Combine bounded Runtime context into one deterministic Intent ordering."""
    choices = (
        ("related_tracks", PlannerDecisionType.CREATE_RECOMMENDATION, KnowledgeIntentType.RECOMMENDATION, "Recommend one related work when it adds value."),
        ("producer", PlannerDecisionType.CREATE_ARTIST_STORY, KnowledgeIntentType.ARTIST_STORY, "Share relevant artist or production context."),
        ("release_year", PlannerDecisionType.CREATE_ALBUM_STORY, KnowledgeIntentType.ALBUM_STORY, "Share relevant album context."),
        ("genre", PlannerDecisionType.CREATE_GENRE_STORY, KnowledgeIntentType.GENRE_STORY, "Explain relevant genre context."),
    )
    priorities = {
        KnowledgeIntentType.ARTIST_STORY: 0,
        KnowledgeIntentType.ALBUM_STORY: 1,
        KnowledgeIntentType.GENRE_STORY: 2,
        KnowledgeIntentType.RECOMMENDATION: 3,
    }

    def promote(intent_type: KnowledgeIntentType, amount: int) -> None:
        priorities[intent_type] -= amount

    if session_start_strategy is SessionStartStrategy.DISCOVER:
        promote(KnowledgeIntentType.RECOMMENDATION, 4)
        promote(KnowledgeIntentType.ARTIST_STORY, 2)
        promote(KnowledgeIntentType.GENRE_STORY, 1)
    if recommendation_preference == "prefer":
        promote(KnowledgeIntentType.RECOMMENDATION, 2)
    elif recommendation_preference == "deprioritize":
        priorities[KnowledgeIntentType.RECOMMENDATION] += 2

    if selected_mood in {"deep", "focus", "chill"}:
        promote(KnowledgeIntentType.ALBUM_STORY, 2)
        promote(KnowledgeIntentType.GENRE_STORY, 1)
    elif selected_mood in {"party", "energy", "high_energy"}:
        promote(KnowledgeIntentType.RECOMMENDATION, 3)
        promote(KnowledgeIntentType.ARTIST_STORY, 1)

    if persona is DJPersona.RADIO_DJ:
        promote(KnowledgeIntentType.ALBUM_STORY, 3)
        promote(KnowledgeIntentType.ARTIST_STORY, 1)
    elif persona is DJPersona.FESTIVAL_DJ:
        promote(KnowledgeIntentType.RECOMMENDATION, 4)
        promote(KnowledgeIntentType.ARTIST_STORY, 1)

    if session_direction is SessionDirectionType.EXPLORING:
        promote(KnowledgeIntentType.RECOMMENDATION, 2)
        promote(KnowledgeIntentType.GENRE_STORY, 1)
    elif session_direction is SessionDirectionType.DEEPENING:
        promote(KnowledgeIntentType.ALBUM_STORY, 2)
        promote(KnowledgeIntentType.GENRE_STORY, 1)
    elif session_direction is SessionDirectionType.COOLING_DOWN:
        promote(KnowledgeIntentType.GENRE_STORY, 2)
        promote(KnowledgeIntentType.ALBUM_STORY, 1)
    elif session_direction is SessionDirectionType.BUILDING_ENERGY:
        promote(KnowledgeIntentType.RECOMMENDATION, 2)
        promote(KnowledgeIntentType.ARTIST_STORY, 1)

    return tuple(
        sorted(choices, key=lambda choice: priorities[choice[2]])
    )


def _space_recommendation_choices(
    choices: tuple[tuple[str, PlannerDecisionType, KnowledgeIntentType, str], ...],
    *,
    performance_memory: PerformanceMemory,
    discover_context: DiscoverContext,
    hints: dict[str, Any],
) -> tuple[tuple[str, PlannerDecisionType, KnowledgeIntentType, str], ...]:
    """Demote one immediate Recommendation only when a valid alternative exists."""
    if _recent_factual_moment_type(performance_memory) is not DJMomentType.RECOMMENDATION:
        return choices
    alternatives = tuple(
        choice
        for choice in choices
        if choice[2]
        in {
            KnowledgeIntentType.ARTIST_STORY,
            KnowledgeIntentType.ALBUM_STORY,
            KnowledgeIntentType.GENRE_STORY,
        }
    )
    if not any(
        _bounded_text(hints.get(key), 1200)
        and not _performance_memory_repeats(performance_memory, intent_type, hints)
        and not _discover_context_repeats(discover_context, intent_type, hints)
        for key, _, intent_type, _ in alternatives
    ):
        return choices
    return tuple(choice for choice in choices if choice[2] is not KnowledgeIntentType.RECOMMENDATION) + tuple(
        choice for choice in choices if choice[2] is KnowledgeIntentType.RECOMMENDATION
    )


def _space_recent_type_choices(
    choices: tuple[tuple[str, PlannerDecisionType, KnowledgeIntentType, str], ...],
    *,
    performance_memory: PerformanceMemory,
    discover_context: DiscoverContext,
    hints: dict[str, Any],
) -> tuple[tuple[str, PlannerDecisionType, KnowledgeIntentType, str], ...]:
    """Vary the last factual contribution when a distinct safe angle is available."""
    previous = _recent_factual_moment_type(performance_memory)
    if previous is None:
        return choices
    intent_moment_type = {
        KnowledgeIntentType.ARTIST_STORY: DJMomentType.ARTIST,
        KnowledgeIntentType.ALBUM_STORY: DJMomentType.ALBUM,
        KnowledgeIntentType.GENRE_STORY: DJMomentType.GENRE,
        KnowledgeIntentType.RECOMMENDATION: DJMomentType.RECOMMENDATION,
    }
    alternatives = tuple(
        choice
        for choice in choices
        if intent_moment_type.get(choice[2]) is not previous
        and _choice_has_complete_context(choice[2], hints)
        and not _performance_memory_repeats(performance_memory, choice[2], hints)
        and not _discover_context_repeats(discover_context, choice[2], hints)
    )
    if not alternatives:
        return choices
    return alternatives + tuple(choice for choice in choices if choice not in alternatives)


def _recent_factual_moment_type(memory: PerformanceMemory) -> DJMomentType | None:
    """Find the last spoken factual angle across a bounded Flow suffix."""
    factual_types = {
        DJMomentType.TRACK,
        DJMomentType.ARTIST,
        DJMomentType.ALBUM,
        DJMomentType.GENRE,
        DJMomentType.RECOMMENDATION,
    }
    return next(
        (moment_type for moment_type in reversed(memory.recent_moment_types[-4:]) if moment_type in factual_types),
        None,
    )


def _choice_has_complete_context(
    intent_type: KnowledgeIntentType, hints: dict[str, Any]
) -> bool:
    """Promote another angle only when the existing Moment contract can realize it."""
    if not all(_bounded_text(hints.get(key), 1200) for key in ("title", "artist", "summary", "full_text")):
        return False
    if intent_type is KnowledgeIntentType.ARTIST_STORY:
        return bool(_bounded_text(hints.get("producer"), 160))
    if intent_type is KnowledgeIntentType.ALBUM_STORY:
        return bool(
            _bounded_text(hints.get("album"), 160)
            and _bounded_text(hints.get("release_year"), 32)
        )
    if intent_type is KnowledgeIntentType.GENRE_STORY:
        return bool(_bounded_text(hints.get("genre"), 160))
    if intent_type is KnowledgeIntentType.RECOMMENDATION:
        return bool(_bounded_text(hints.get("related_tracks"), 1200))
    return False


def _recent_metadata(
    metadata: tuple[dict[str, str], ...], key: str
) -> tuple[str, ...]:
    """Return unique, non-empty metadata values in chronological order."""
    return tuple(dict.fromkeys(value for item in metadata if (value := item.get(key, ""))))


def _moment_topic(moment: DJMoment) -> tuple[DJMomentType, str] | None:
    """Remember only the subject of the angle actually delivered by this Moment."""
    key = {
        DJMomentType.ARTIST: "artist",
        DJMomentType.ALBUM: "album",
        DJMomentType.GENRE: "genre",
        DJMomentType.RECOMMENDATION: "recommendation",
    }.get(moment.moment_type)
    if key is None:
        return None
    subject = _bounded_text(dict(moment.generation_metadata).get(key), 160).casefold()
    return (moment.moment_type, subject) if subject else None


def _context_fingerprint(artist: Any, summary: Any, content: Any) -> str:
    """Compare bounded already-safe context without retaining another text copy."""
    normalized_artist = _bounded_text(artist, 160).casefold()
    normalized_summary = _bounded_text(summary, 320).casefold()
    normalized_content = _bounded_text(content, 1200).casefold()
    if not normalized_artist or not (normalized_summary or normalized_content):
        return ""
    return hashlib.sha256(
        f"{normalized_artist}|{normalized_summary}|{normalized_content}".encode()
    ).hexdigest()


def _performance_memory_repeats(
    memory: PerformanceMemory, intent_type: KnowledgeIntentType, hints: dict[str, Any]
) -> bool:
    """Reject the same delivered angle and subject within the Runtime window."""
    if intent_type is KnowledgeIntentType.ARTIST_STORY:
        candidate = _bounded_text(hints.get("artist") or hints.get("producer"), 160)
        return (
            (DJMomentType.ARTIST, candidate.casefold()) in memory.recent_topics
            if memory.topics_observed
            else candidate in memory.recent_artists
        )
    if intent_type is KnowledgeIntentType.ALBUM_STORY:
        candidate = _bounded_text(hints.get("album") or hints.get("release_year"), 160)
        return (
            (DJMomentType.ALBUM, candidate.casefold()) in memory.recent_topics
            if memory.topics_observed
            else candidate in memory.recent_albums
        )
    if intent_type is KnowledgeIntentType.GENRE_STORY:
        candidate = _bounded_text(hints.get("genre"), 160)
        return (
            (DJMomentType.GENRE, candidate.casefold()) in memory.recent_topics
            if memory.topics_observed
            else candidate in memory.recent_genres
        )
    if intent_type is KnowledgeIntentType.RECOMMENDATION:
        candidate = _bounded_text(hints.get("artist") or hints.get("related_tracks"), 160)
        return (
            (DJMomentType.RECOMMENDATION, candidate.casefold()) in memory.recent_topics
            if memory.topics_observed
            else candidate in memory.recent_recommendations
        )
    return False


def _discover_context_repeats(
    context: DiscoverContext, intent_type: KnowledgeIntentType, hints: dict[str, Any]
) -> bool:
    """Keep personal Discover guidance opt-in and avoid familiar material."""
    if not context.personal_context_authorized:
        return False
    artist = _bounded_text(hints.get("artist") or hints.get("producer"), 160)
    genre = _bounded_text(hints.get("genre"), 160)
    if intent_type in {KnowledgeIntentType.ARTIST_STORY, KnowledgeIntentType.RECOMMENDATION}:
        return artist in context.familiar_artists
    if intent_type is KnowledgeIntentType.GENRE_STORY:
        return genre in context.familiar_genres
    return False


def _create_session_planner(
    *,
    session_id: str,
    created_at: str,
    configuration: PlannerConfiguration,
    elapsed_time_source: Callable[[], float] | None = None,
) -> DJSessionPlanner:
    """Create the one non-persistent Planner for a newly created Runtime."""
    return DJSessionPlanner(
        planner_state=PlannerState.READY,
        planning_horizon_minutes=15,
        created_at=created_at,
        last_replan_at="",
        current_goal="",
        pending_events=(),
        configuration=configuration,
        output=SessionPlannerOutput(
            session_flow=_create_session_flow(
                session_id=session_id,
                planning_horizon_minutes=15,
                created_at=created_at,
            )
        ),
        horizon=RollingSessionHorizon(window_minutes=15, created_at=created_at),
        elapsed_time_source=elapsed_time_source or time.monotonic,
    )


def _create_broadcast_engine(
    *,
    session_id: str,
    runtime_state: SessionRuntimeState,
    selected_mood: str,
    locale: str = "en",
    session_direction: SessionDirection,
    planner: DJSessionPlanner,
    started_at: str,
) -> DJSessionBroadcastEngine:
    """Create the one non-persistent Broadcast Engine for a new Runtime."""
    return DJSessionBroadcastEngine(
        state=DJBroadcastState(
            session_id=session_id,
            runtime_state=runtime_state,
            selected_mood=selected_mood,
            locale=_locale_family(locale),
            planning_state=planner.planner_state,
            planning_horizon_minutes=planner.planning_horizon_minutes,
            session_direction=session_direction,
            started_at=started_at,
            session_flow=planner.output.session_flow,
        )
    )


def _create_session_flow(
    *,
    session_id: str,
    planning_horizon_minutes: int,
    created_at: str,
) -> DJSessionFlow:
    """Create deterministic current-horizon intent without AI planning."""
    return DJSessionFlow(
        flow_id=f"flow-{session_id}",
        flow_revision=0,
        planning_horizon_minutes=planning_horizon_minutes,
        created_at=created_at,
        items=(
            DJSessionFlowItem(
                item_id="now-current-track",
                item_type=SessionFlowItemType.CURRENT_TRACK,
                position=SessionFlowPosition.NOW,
                label="Current Track",
            ),
            DJSessionFlowItem(
                item_id="next-planning-horizon",
                item_type=SessionFlowItemType.PLANNING_HORIZON,
                position=SessionFlowPosition.NEXT,
                label="Planning Horizon",
            ),
            DJSessionFlowItem(
                item_id="next-maintain-direction",
                item_type=SessionFlowItemType.MAINTAIN_DIRECTION,
                position=SessionFlowPosition.NEXT,
                label="Maintain Direction",
            ),
            DJSessionFlowItem(
                item_id="later-future-direction",
                item_type=SessionFlowItemType.FUTURE_DIRECTION,
                position=SessionFlowPosition.LATER,
                label="Future Direction",
            ),
            DJSessionFlowItem(
                item_id="later-future-placeholder",
                item_type=SessionFlowItemType.FUTURE_PLACEHOLDER,
                position=SessionFlowPosition.LATER,
                label="Future Placeholder",
            ),
        ),
    )


def _qualified_fact_spacing_seconds(mood: str, persona: DJPersona, direction: SessionDirectionType) -> int:
    """Add bounded quiet space without changing truth, read duration or budget."""
    if (mood in {"chill", "party", "energy", "high_energy"}
            or persona in {DJPersona.CLUB_DJ, DJPersona.FESTIVAL_DJ}
            or direction is SessionDirectionType.COOLING_DOWN):
        return 50
    return 35


def _presentation_intent(
    selected_mood: str, persona: DJPersona, *,
    reading_characters: int = 0, minimum_duration_seconds: int = 25,
) -> PresentationIntent:
    """Resolve compact semantic guidance without binding any renderer design."""
    mood = selected_mood.strip() or "neutral"
    tone = {
        DJPersona.HOME_DJ: "warm and conversational",
        DJPersona.RADIO_DJ: "polished and concise",
        DJPersona.CLUB_DJ: "direct and rhythmic",
        DJPersona.FESTIVAL_DJ: "celebratory and expansive",
    }[persona]
    return PresentationIntent(
        source_session_mood=mood,
        dj_persona=persona,
        tone_of_voice=tone,
        energy_level=mood,
        delivery_style="short contextual music story",
        voice_style="persona-guided",
        visual_theme="music-context",
        importance="normal",
        maximum_duration_seconds=min(90, max(minimum_duration_seconds, (reading_characters + 13) // 14)),
        delivery_channels=(DeliveryChannel.BROADCAST, DeliveryChannel.OWNER, DeliveryChannel.SHARED),
        visibility=DJMomentVisibility.SESSION_SHARED,
    )


def _track_actions(track: dict[str, Any], locale: str) -> tuple[DJMomentAction, ...]:
    """Expose only the safe first-slice semantic actions."""
    payload = tuple(
        (key, value)
        for key, value in (("title", _bounded_text(track.get("title"), 160)), ("artist", _bounded_text(track.get("artist"), 160)), ("album", _bounded_text(track.get("album"), 160)))
        if value
    )
    return (
        DJMomentAction("ask_dj", _moment_copy(locale, "ask_dj"), "sparkles", 1, "ask_dj", payload),
        DJMomentAction("tell_me_more", _moment_copy(locale, "tell_me_more"), "info", 2, "ask_dj", payload),
        DJMomentAction("show_artist", _moment_copy(locale, "show_artist"), "person", 3, "music_context", payload),
        DJMomentAction("show_album", _moment_copy(locale, "show_album"), "rectangle.stack", 4, "music_context", payload),
        DJMomentAction("show_track", _moment_copy(locale, "show_track"), "music.note", 5, "music_context", payload),
    )


def _moment_actions(moment_type: DJMomentType, track: dict[str, Any], locale: str) -> tuple[DJMomentAction, ...]:
    actions = _track_actions(track, locale)
    if moment_type is DJMomentType.ARTIST:
        return tuple(action for action in actions if action.action_type in {"ask_dj", "tell_me_more", "show_artist"})
    if moment_type is DJMomentType.ALBUM:
        return tuple(action for action in actions if action.action_type in {"ask_dj", "show_album"})
    if moment_type is DJMomentType.GENRE:
        return (DJMomentAction("explore_genre", "Explore Genre", "music.note.list", 1, "music_context"), *actions[:2])
    if moment_type is DJMomentType.RECOMMENDATION:
        return (DJMomentAction("play_recommendation", "Play Recommendation", "play", 1, "music_context"), DJMomentAction("save_recommendation", "Save Recommendation", "bookmark", 2, "music_context"))
    return actions


def _specialize_track_moment(track: dict[str, Any], analysis: dict[str, Any], title: str, artist: str, summary: str, content: str, intent_type: KnowledgeIntentType, locale: str) -> tuple[DJMomentType, str, str, str] | None:
    if intent_type is KnowledgeIntentType.RECOMMENDATION:
        if not (
            _bounded_text(track.get("related_tracks"), 1200)
            or _bounded_text(track.get("related_artists"), 1200)
            or _bounded_text(analysis.get("similar_tracks"), 1200)
            or _bounded_text(analysis.get("listening_cues"), 1200)
        ):
            return None
        return DJMomentType.RECOMMENDATION, f"Explore beyond {artist}", summary, content
    if intent_type is KnowledgeIntentType.ARTIST_STORY:
        if not (
            _bounded_text(track.get("producer"), 160)
            or _bounded_text(track.get("composer"), 160)
            or _bounded_text(track.get("recording_context"), 600)
            or _bounded_text(track.get("related_artists"), 1200)
            or _bounded_text(analysis.get("production_notes"), 1200)
            or _bounded_text(analysis.get("instrumentation"), 1200)
            or _bounded_text(analysis.get("arrangement_notes"), 1200)
        ):
            return None
        return DJMomentType.ARTIST, artist, summary, content
    if intent_type is KnowledgeIntentType.ALBUM_STORY:
        if not (_bounded_text(track.get("album"), 160) and (_bounded_text(track.get("release_year"), 32) or _bounded_text(track.get("release_date"), 32))):
            return None
        return DJMomentType.ALBUM, _bounded_text(track.get("album"), 160), summary, content
    if intent_type is KnowledgeIntentType.GENRE_STORY:
        genre = _bounded_evidence_value(analysis.get("genre"), 160) or _bounded_evidence_value(track.get("genres"), 160)
        if not genre:
            return None
        genre_summary, genre_content = _genre_moment_copy(locale, genre, title, artist)
        return DJMomentType.GENRE, genre, genre_summary, genre_content
    if intent_type is KnowledgeIntentType.TRACK_CONTEXT:
        return DJMomentType.TRACK, f"{title} — {artist}", summary, content
    return None


def _valid_transition_approval(approval: PlannerDecision | None) -> bool:
    """Require the exact Planner contract before performing a Transition."""
    return bool(
        approval
        and approval.decision_type is PlannerDecisionType.CREATE_TRANSITION
        and approval.knowledge_intent is not None
        and approval.knowledge_intent.intent_type is KnowledgeIntentType.TRANSITION
        and len(approval.transition_moment_ids) == 2
        and all(approval.transition_moment_ids)
        and approval.transition_moment_ids[0] != approval.transition_moment_ids[1]
        and approval.transition_placement == SessionFlowPosition.NEXT.value
        and approval.transition_relation in {"", "discover_same_artist_genre"}
    )


def _valid_discover_transition_context(
    approval: PlannerDecision, source: DJMoment, target: DJMoment
) -> bool:
    """Keep the new relation tied to two real, compatible Moment payloads."""
    if (source.moment_type is not DJMomentType.GENRE
            or target.moment_type is not DJMomentType.TRACK
            or len(approval.transition_context) != 4):
        return False
    context = dict(approval.transition_context)
    if set(context) != {"genre", "artist", "source_track", "target_track"}:
        return False
    if not all(_narrative_label(value, 160) == value for value in context.values()):
        return False
    source_meta = dict(source.generation_metadata)
    target_meta = dict(target.generation_metadata)
    return bool(
        context["genre"] == source.title
        and source_meta.get("genre") == context["genre"]
        and target_meta.get("genre") == context["genre"]
        and source_meta.get("artist") == context["artist"]
        and target_meta.get("artist") == context["artist"]
        and source_meta.get("track_title") == context["source_track"]
        and target_meta.get("track_title") == context["target_track"]
        and context["source_track"] != context["target_track"]
    )


def _valid_session_update_context(
    context: "KnowledgeContext | None",
    session_direction: SessionDirection,
    selected_mood: str,
) -> bool:
    """Accept only the existing safe Session Direction context assembled by Knowledge."""
    return bool(
        context
        and context.sources == ("session_direction",)
        and context.session_direction == session_direction
        and context.session_start_strategy == session_direction.start_strategy
        and context.session_mood == selected_mood
        and context.performance_memory is not None
    )


def _planner_knowledge_hints(raw_insight: dict[str, Any]) -> dict[str, str]:
    """Project only bounded, renderer-safe Track Insight facts into Planner input."""
    track = raw_insight.get("track") if isinstance(raw_insight.get("track"), dict) else {}
    analysis = raw_insight.get("analysis") if isinstance(raw_insight.get("analysis"), dict) else {}
    return {
        "title": _bounded_text(track.get("title"), 160),
        "related_tracks": _bounded_text(track.get("related_tracks") or analysis.get("similar_tracks"), 1200),
        "producer": _bounded_text(track.get("producer") or track.get("recording_context"), 600),
        "release_year": _bounded_text(track.get("release_year") or track.get("release_date"), 32),
        "genre": _bounded_text(analysis.get("genre") or track.get("genres"), 160),
        "artist": _bounded_text(track.get("artist"), 160),
        "album": _bounded_text(track.get("album"), 160),
        "summary": _bounded_text(analysis.get("summary"), 320),
        "full_text": _bounded_text(analysis.get("full_text"), 1200),
    }


def _track_key(track: dict[str, Any]) -> str:
    return "|".join(
        _bounded_text(track.get(field), 160).lower()
        for field in ("title", "artist", "album")
    ).strip("|")


def _bounded_text(value: Any, limit: int) -> str:
    return str(value or "").strip()[:limit]


def _narrative_label(value: Any, limit: int) -> str:
    """Keep an exact, single-line producer label without silently truncating it."""
    if not isinstance(value, str):
        return ""
    label = value.strip()
    if not label or len(label) > limit or any(ord(char) < 32 or ord(char) == 127 for char in label):
        return ""
    return label


def _safe_artwork_url(value: Any) -> str:
    """Keep only URLs served by DJConnect's existing HA image proxy."""
    url = str(value or "").strip()
    return url if url.startswith(f"{API_IMAGE_PROXY_BASE}/") else ""


def _locale_family(value: str) -> str:
    family = str(value or "en").strip().lower().replace("_", "-").split("-", 1)[0]
    return family if family in {"en", "nl", "de", "fr", "es"} else "en"


def _moment_copy(locale: str, key: str) -> str:
    """Return the small canonical five-language Moment copy set."""
    messages = {
        "en": {"silence_title": "Silence", "silence_summary": "The DJ intentionally chose not to interrupt the music.", "ask_dj": "Ask DJ", "tell_me_more": "Tell Me More", "show_artist": "Show Artist", "show_album": "Show Album", "show_track": "Show Track"},
        "nl": {"silence_title": "Stilte", "silence_summary": "De dj kiest er bewust voor de muziek niet te onderbreken.", "ask_dj": "Vraag de dj", "tell_me_more": "Vertel me meer", "show_artist": "Toon artiest", "show_album": "Toon album", "show_track": "Toon nummer"},
        "de": {"silence_title": "Stille", "silence_summary": "Der DJ hat bewusst entschieden, die Musik nicht zu unterbrechen.", "ask_dj": "DJ fragen", "tell_me_more": "Mehr erfahren", "show_artist": "Künstler anzeigen", "show_album": "Album anzeigen", "show_track": "Titel anzeigen"},
        "fr": {"silence_title": "Silence", "silence_summary": "Le DJ a choisi de ne pas interrompre la musique.", "ask_dj": "Demander au DJ", "tell_me_more": "En savoir plus", "show_artist": "Voir l’artiste", "show_album": "Voir l’album", "show_track": "Voir le titre"},
        "es": {"silence_title": "Silencio", "silence_summary": "El DJ ha decidido no interrumpir la música.", "ask_dj": "Preguntar al DJ", "tell_me_more": "Cuéntame más", "show_artist": "Ver artista", "show_album": "Ver álbum", "show_track": "Ver canción"},
    }
    return messages[_locale_family(locale)][key]


def _genre_moment_copy(locale: str, genre: str, title: str, artist: str) -> tuple[str, str]:
    """Present the selected existing genre evidence without added music facts."""
    copy = {
        "en": ("Genre: {genre}", "The genre context for {title} by {artist} is {genre}."),
        "nl": ("Genre: {genre}", "De genrecontext bij {title} van {artist} is {genre}."),
        "de": ("Genre: {genre}", "Der Genrekontext zu {title} von {artist} ist {genre}."),
        "fr": ("Genre : {genre}", "Le contexte de genre de {title} par {artist} est {genre}."),
        "es": ("Género: {genre}", "El contexto de género de {title} de {artist} es {genre}."),
    }
    return tuple(part.format(genre=genre, title=title, artist=artist) for part in copy[_locale_family(locale)])


def _session_direction_copy(
    locale: str, direction: SessionDirectionType, part: str
) -> str:
    """Return five-language, bounded copy for a Direction-driven Session update."""
    labels = {
        "en": {
            SessionDirectionType.BUILDING_ENERGY: ("Building energy", "The session is building energy.", "We are gradually raising the energy."),
            SessionDirectionType.MAINTAINING_ENERGY: ("Maintaining energy", "The session is holding its current energy.", "We are staying with the current musical direction."),
            SessionDirectionType.COOLING_DOWN: ("Cooling down", "The session is easing into a calmer mood.", "We are slowing things down."),
            SessionDirectionType.EXPLORING: ("Exploring", "The session is making room for discovery.", "We are exploring a fresh musical path."),
            SessionDirectionType.DEEPENING: ("Deepening", "The session is moving into deeper focus.", "We are deepening the musical atmosphere."),
            SessionDirectionType.RETURNING: ("Returning", "The session is returning to a familiar direction.", "We are returning to the session's established sound."),
            SessionDirectionType.RESETTING: ("Resetting", "The session is resetting its musical direction.", "We are making space for a new direction."),
        },
        "nl": {
            SessionDirectionType.BUILDING_ENERGY: ("Energie opbouwen", "De sessie bouwt energie op.", "We voeren de energie geleidelijk op."),
            SessionDirectionType.MAINTAINING_ENERGY: ("Energie vasthouden", "De sessie houdt het huidige energieniveau vast.", "We blijven bij de huidige muzikale richting."),
            SessionDirectionType.COOLING_DOWN: ("Rustiger worden", "De sessie beweegt naar een rustiger gevoel.", "We doen het wat rustiger aan."),
            SessionDirectionType.EXPLORING: ("Verkennen", "De sessie maakt ruimte voor ontdekking.", "We verkennen een nieuw muzikaal pad."),
            SessionDirectionType.DEEPENING: ("Verdiepen", "De sessie beweegt naar meer diepgang.", "We verdiepen de muzikale sfeer."),
            SessionDirectionType.RETURNING: ("Terugkeren", "De sessie keert terug naar een vertrouwde richting.", "We keren terug naar het vertrouwde geluid van deze sessie."),
            SessionDirectionType.RESETTING: ("Opnieuw afstemmen", "De sessie stelt de muzikale richting opnieuw af.", "We maken ruimte voor een nieuwe richting."),
        },
        "de": {
            SessionDirectionType.BUILDING_ENERGY: ("Energie aufbauen", "Die Session baut Energie auf.", "Wir steigern die Energie schrittweise."),
            SessionDirectionType.MAINTAINING_ENERGY: ("Energie halten", "Die Session hält ihr aktuelles Energieniveau.", "Wir bleiben bei der aktuellen musikalischen Richtung."),
            SessionDirectionType.COOLING_DOWN: ("Herunterfahren", "Die Session wird ruhiger.", "Wir nehmen das Tempo etwas heraus."),
            SessionDirectionType.EXPLORING: ("Entdecken", "Die Session schafft Raum für Entdeckungen.", "Wir erkunden einen neuen musikalischen Weg."),
            SessionDirectionType.DEEPENING: ("Vertiefen", "Die Session geht in eine tiefere Stimmung über.", "Wir vertiefen die musikalische Atmosphäre."),
            SessionDirectionType.RETURNING: ("Zurückkehren", "Die Session kehrt zu einer vertrauten Richtung zurück.", "Wir kehren zum etablierten Klang der Session zurück."),
            SessionDirectionType.RESETTING: ("Neu ausrichten", "Die Session richtet ihre musikalische Richtung neu aus.", "Wir schaffen Raum für eine neue Richtung."),
        },
        "fr": {
            SessionDirectionType.BUILDING_ENERGY: ("Monter en énergie", "La session monte en énergie.", "Nous augmentons progressivement l'énergie."),
            SessionDirectionType.MAINTAINING_ENERGY: ("Maintenir l'énergie", "La session maintient son niveau d'énergie.", "Nous gardons la direction musicale actuelle."),
            SessionDirectionType.COOLING_DOWN: ("Ralentir", "La session s'oriente vers une ambiance plus calme.", "Nous ralentissons le rythme."),
            SessionDirectionType.EXPLORING: ("Explorer", "La session laisse de la place à la découverte.", "Nous explorons une nouvelle direction musicale."),
            SessionDirectionType.DEEPENING: ("Approfondir", "La session entre dans une ambiance plus profonde.", "Nous approfondissons l'atmosphère musicale."),
            SessionDirectionType.RETURNING: ("Revenir", "La session revient vers une direction familière.", "Nous revenons au son établi de la session."),
            SessionDirectionType.RESETTING: ("Réinitialiser", "La session réinitialise sa direction musicale.", "Nous faisons de la place pour une nouvelle direction."),
        },
        "es": {
            SessionDirectionType.BUILDING_ENERGY: ("Subiendo energía", "La sesión está subiendo energía.", "Estamos aumentando la energía poco a poco."),
            SessionDirectionType.MAINTAINING_ENERGY: ("Manteniendo energía", "La sesión mantiene su nivel de energía.", "Seguimos con la dirección musical actual."),
            SessionDirectionType.COOLING_DOWN: ("Bajando el ritmo", "La sesión se dirige a un ambiente más tranquilo.", "Estamos bajando el ritmo."),
            SessionDirectionType.EXPLORING: ("Explorando", "La sesión abre espacio para descubrir.", "Estamos explorando un nuevo camino musical."),
            SessionDirectionType.DEEPENING: ("Profundizando", "La sesión entra en un enfoque más profundo.", "Estamos profundizando la atmósfera musical."),
            SessionDirectionType.RETURNING: ("Volviendo", "La sesión vuelve a una dirección familiar.", "Volvemos al sonido establecido de la sesión."),
            SessionDirectionType.RESETTING: ("Reiniciando", "La sesión reinicia su dirección musical.", "Estamos dando espacio a una nueva dirección."),
        },
    }
    index = {"title": 0, "summary": 1, "content": 2}[part]
    return labels[_locale_family(locale)][direction][index]


def _transition_copy(locale: str, part: str, source: str, target: str) -> str:
    """Return compact localized copy for one Planner-approved Transition."""
    copy = {
        "en": ("From {source} to {target}", "A bridge into the next discovery.", "The session moves from {source} to {target}."),
        "nl": ("Van {source} naar {target}", "Een brug naar de volgende ontdekking.", "De sessie gaat van {source} naar {target}."),
        "de": ("Von {source} zu {target}", "Eine Brücke zur nächsten Entdeckung.", "Die Session wechselt von {source} zu {target}."),
        "fr": ("De {source} à {target}", "Un passage vers la prochaine découverte.", "La session passe de {source} à {target}."),
        "es": ("De {source} a {target}", "Un puente hacia el próximo descubrimiento.", "La sesión pasa de {source} a {target}."),
    }
    index = {"title": 0, "summary": 1, "content": 2}[part]
    return copy[_locale_family(locale)][index].format(source=source, target=target)


def _discover_transition_copy(locale: str, part: str, context: dict[str, str]) -> str:
    """Describe only the observed same-artist, artist-genre relationship."""
    copy = {
        "en": (
            "More from {artist}",
            "{target_track} continues the {artist} thread opened by {source_track}.",
            "{source_track} brought us to {artist}. Their {genre} side gives us a thread to follow into {target_track}.",
        ),
        "nl": (
            "Meer van {artist}",
            "{target_track} volgt de lijn van {artist} die bij {source_track} begon.",
            "{source_track} bracht ons bij {artist}. De {genre}-kant van die artiest geeft ons een draad om met {target_track} te volgen.",
        ),
        "de": (
            "Mehr von {artist}",
            "{target_track} führt den mit {source_track} begonnenen Faden von {artist} fort.",
            "{source_track} hat uns zu {artist} geführt. Die {genre}-Seite dieses Künstlers gibt uns einen Faden, dem wir mit {target_track} folgen.",
        ),
        "fr": (
            "Encore {artist}",
            "{target_track} poursuit le fil de {artist} ouvert avec {source_track}.",
            "{source_track} nous a menés à {artist}. Sa facette {genre} nous donne un fil à suivre avec {target_track}.",
        ),
        "es": (
            "Más de {artist}",
            "{target_track} sigue el hilo de {artist} iniciado con {source_track}.",
            "{source_track} nos llevó a {artist}. Su faceta {genre} nos da un hilo que seguir con {target_track}.",
        ),
    }
    index = {"title": 0, "summary": 1, "content": 2}[part]
    return copy[_locale_family(locale)][index].format(**context)


def _payload_contains_owner_only_moment(payload: dict[str, Any]) -> bool:
    moment = payload.get("dj_moment")
    if isinstance(moment, dict):
        return moment.get("visibility") == DJMomentVisibility.OWNER_ONLY.value
    presentation = payload.get("presentation")
    if not isinstance(presentation, dict):
        return False
    return presentation.get("visibility") == DJMomentVisibility.OWNER_ONLY.value
