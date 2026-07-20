"""Ephemeral server-owned DJ Session Runtime lifecycle."""

from __future__ import annotations

import asyncio
import logging
import secrets
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Awaitable, Callable
from uuid import uuid4

from .const import DOMAIN

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
    planning_horizon_minutes: int
    created_at: str
    items: tuple[DJSessionFlowItem, ...]

    def as_dict(self) -> dict[str, Any]:
        """Return the canonical current-horizon Session Flow."""
        return {
            "flow_id": self.flow_id,
            "planning_horizon_minutes": self.planning_horizon_minutes,
            "created_at": self.created_at,
            "items": [item.as_dict() for item in self.items],
        }


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
                for value in _recent_metadata(metadata, "direction")
                if value in SessionDirectionType._value2member_map_
            ),
            recent_silence_count=sum(
                moment.moment_type is DJMomentType.SILENCE for moment in ordered
            ),
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
    audience_totals: dict[str, int] = field(default_factory=dict)
    recent_audience_activity: tuple[str, ...] = ()
    configuration: PlannerConfiguration = field(default_factory=PlannerConfiguration)
    last_spoken_moment_at: float = 0.0
    last_decision: PlannerDecision | None = None

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
        self.output = SessionPlannerOutput(session_flow=flow)
        self.last_replan_at = flow.created_at
        return flow

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
        now = time.monotonic()
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
        ):
            proposed_direction = SessionDirectionType.RESETTING
            direction_change_reason = "recent_silence_recovery"
        if proposed_direction is not session_direction.direction:
            if performance_memory.recent_moment_types[-1:] == (DJMomentType.SESSION,):
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
        choices = _prioritized_knowledge_choices(
            session_start_strategy=session_start_strategy,
            selected_mood=mood,
            persona=persona,
            session_direction=session_direction.direction,
            recommendation_preference=self.configuration.recommendation_preference,
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
        self.last_spoken_moment_at = time.monotonic()

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
            planning_horizon_minutes=current.planning_horizon_minutes,
            created_at=_timestamp(),
            items=(*current.items, item),
        )
        self.output = SessionPlannerOutput(session_flow=flow)
        self.last_replan_at = flow.created_at
        return flow

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
            or performance_memory.recent_moment_types[-1:] == (DJMomentType.TRANSITION,)
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


@dataclass
class DJMomentEngine:
    """Runtime-owned creative execution for a bounded first Moment slice."""

    moments: tuple[DJMoment, ...] = ()
    _track_keys: set[str] = field(default_factory=set, repr=False)

    def create_track_context(
        self,
        *,
        session_id: str,
        knowledge_intent: KnowledgeIntent,
        selected_mood: str,
        persona: DJPersona,
        locale: str,
        insight: dict[str, Any],
    ) -> DJMoment:
        """Translate one selected Knowledge Context into one frozen Moment."""
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
        if track_key in self._track_keys:
            return self.create_silence(
                session_id=session_id,
                selected_mood=selected_mood,
                persona=persona,
                locale=locale,
                reason="duplicate_track_context",
            )
        self._track_keys.add(track_key)
        specialized = _specialize_track_moment(
            track, analysis, title, artist, summary, content, knowledge_intent.intent_type
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
        moment = DJMoment(
            moment_id=f"moment-{uuid4().hex}",
            session_id=session_id,
            created_at=_timestamp(),
            moment_type=moment_type,
            knowledge_intent=KnowledgeIntent(
                knowledge_intent.intent_type, knowledge_intent.goal, track_key
            ),
            presentation_intent=_presentation_intent(selected_mood, persona),
            title=title,
            summary=summary,
            content=content,
            artwork_url=_bounded_text(track.get("artwork_url"), 2048) or None,
            actions=_moment_actions(moment_type, track, locale),
            source_references=("track_insight",),
            generation_metadata=(
                ("provider", "track_insight"),
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
        if (
            source is None
            or target is None
            or source.session_id != session_id
            or target.session_id != session_id
            or source.moment_type
            not in {
                DJMomentType.TRACK,
                DJMomentType.ARTIST,
                DJMomentType.ALBUM,
                DJMomentType.GENRE,
            }
            or target.moment_type is not DJMomentType.RECOMMENDATION
        ):
            return self.create_silence(
                session_id=session_id,
                selected_mood=selected_mood,
                persona=persona,
                locale=locale,
                reason="invalid_transition_context",
            )
        moment = DJMoment(
            moment_id=f"moment-{uuid4().hex}",
            session_id=session_id,
            created_at=_timestamp(),
            moment_type=DJMomentType.TRANSITION,
            knowledge_intent=approval.knowledge_intent,
            presentation_intent=_presentation_intent(selected_mood, persona),
            title=_transition_copy(locale, "title", source.title, target.title),
            summary=_transition_copy(locale, "summary", source.title, target.title),
            content=_transition_copy(locale, "content", source.title, target.title),
            artwork_url=None,
            actions=(),
            source_references=("session_flow",),
            generation_metadata=(
                ("transition_from_moment_id", source.moment_id),
                ("transition_to_moment_id", target.moment_id),
                ("placement", approval.transition_placement),
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

    def as_insight(self) -> dict[str, Any]:
        """Adapt the safe context to the existing Moment Engine contract."""
        insight = {"track": dict(self.track), "analysis": dict(self.analysis)}
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

    def _record(self, context: KnowledgeContext) -> KnowledgeContext:
        self.assembled_contexts = (*self.assembled_contexts, context)
        return context


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
    audience_totals: dict[str, int] = field(default_factory=dict)
    recent_audience_activity: tuple[str, ...] = ()
    dj_moments: tuple[DJMoment, ...] = ()

    def as_dict(self, *, include_owner_only: bool = True) -> dict[str, Any]:
        """Return canonical state with its Planner-produced Session Flow."""
        return {
            "session": {
                "session_id": self.session_id,
                "runtime_state": str(self.runtime_state),
                "selected_mood": self.selected_mood,
            },
            "playback": {"current_track": None, "playback_progress": None},
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
            "broadcast": {"started_at": self.started_at},
        }


@dataclass
class DJSessionBroadcastEngine:
    """One ephemeral distribution owner for one active Session Runtime.

    The Engine publishes only canonical Broadcast State. It never plans,
    executes playback or renders a presentation; future renderers consume this
    state and the stable Broadcast Event vocabulary through the Runtime.
    """

    state: DJBroadcastState
    pending_events: tuple[BroadcastEventType, ...] = ()
    broadcast_token: str = field(default_factory=lambda: secrets.token_urlsafe(32), repr=False)
    _subscribers: dict[str, tuple[Callable[[dict[str, Any]], None], bool]] = field(
        default_factory=dict, init=False, repr=False
    )

    def subscribe(
        self, callback: Callable[[dict[str, Any]], None]
    ) -> tuple[str, dict[str, Any]]:
        """Register one renderer and return its required initial snapshot."""
        subscription_id = f"broadcast-subscription-{uuid4().hex}"
        self._subscribers[subscription_id] = (callback, True)
        return subscription_id, self.as_dict()

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

    def publish_audience_state(self, totals: dict[str, int], recent_activity: tuple[str, ...]) -> None:
        self.state = DJBroadcastState(**{**self.state.__dict__, "audience_totals": dict(totals), "recent_audience_activity": recent_activity})
        self._publish(BroadcastEventType.AUDIENCE_UPDATED, {"audience": self.as_dict()["audience"]})

    def publish_moment(self, moment: DJMoment) -> None:
        """Project a validated Moment without exposing private projections."""
        self.state = DJBroadcastState(**{**self.state.__dict__, "dj_moments": (*self.state.dj_moments, moment)})
        if moment.moment_type is not DJMomentType.SILENCE:
            self._publish(BroadcastEventType.DJ_MOMENT_PUBLISHED, {"dj_moment": moment.as_dict()})

    def close(self) -> None:
        """Notify renderers of Runtime termination, then release every subscription."""
        state = self.as_dict()
        self._publish(BroadcastEventType.RUNTIME_ENDED, {"session": state["session"]})
        self._publish(BroadcastEventType.BROADCAST_STOPPED, {"broadcast": state["broadcast"]})
        self._subscribers.clear()

    def _publish(self, event_type: BroadcastEventType, payload: dict[str, Any]) -> None:
        """Deliver one incremental, renderer-safe event to active subscribers."""
        event = {
            "event_type": str(event_type),
            "session_id": self.state.session_id,
            "payload": payload,
        }
        for callback, include_owner_only in tuple(self._subscribers.values()):
            if not include_owner_only and _payload_contains_owner_only_moment(payload):
                continue
            callback(event)

    def as_dict(self, *, include_owner_only: bool = True) -> dict[str, Any]:
        """Expose only canonical Broadcast State to future renderers."""
        return self.state.as_dict(include_owner_only=include_owner_only)


class ActiveSessionExistsError(RuntimeError):
    """Raised when a Profile already owns an active DJ Session."""

    def __init__(self, profile_id: str) -> None:
        self.profile_id = profile_id
        super().__init__(f"Profile already has an active DJ Session: {profile_id}")


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
    knowledge_engine: DJKnowledgeEngine
    moment_engine: DJMomentEngine
    broadcast: DJSessionBroadcastEngine

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
        return runtime

    def republish_session_flow(self) -> DJSessionFlow:
        """Coordinate Planner output publication through the Broadcast Engine."""
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
        self.broadcast.publish_session_flow(self.planner.append_moment(moment, placement))
        self.broadcast.publish_moment(moment)


class SessionRuntimeManager:
    """Own active DJ Session Runtimes for this Home Assistant instance."""

    def __init__(self) -> None:
        self._active_by_profile: dict[str, DJSessionRuntime] = {}
        self._lock = asyncio.Lock()

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
            planner = _create_session_planner(
                session_id=session_id,
                created_at=now,
                configuration=start_configuration.planner_configuration,
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
                knowledge_engine=DJKnowledgeEngine(),
                moment_engine=DJMomentEngine(),
                broadcast=_create_broadcast_engine(
                    session_id=session_id,
                    runtime_state=SessionRuntimeState.CREATING,
                    selected_mood=selected_mood,
                    session_direction=session_direction,
                    planner=planner,
                    started_at=now,
                ),
            )
            creating.broadcast.update_runtime_state(SessionRuntimeState.ACTIVE)
            active = DJSessionRuntime(
                **{
                    **creating.__dict__,
                    "runtime_state": SessionRuntimeState.ACTIVE,
                    "started_at": _timestamp(),
                }
            )
            self._active_by_profile[owner_profile_id] = active
            return active

    async def async_process_track_started(
        self,
        *,
        owner_profile_id: str,
        session_id: str,
        insight_provider: Callable[[], Awaitable[dict[str, Any]]],
    ) -> DJMoment | None:
        """Orchestrate Planner → Knowledge → Moment → Flow → Broadcast."""
        async with self._lock:
            active = self._active_by_profile.get(owner_profile_id)
            if active is None or active.session_id != session_id:
                return None
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
                    active.publish_moment(moment)
                self._record_performance_memory(owner_profile_id, active)
                return moment
            if decision.decision_type is PlannerDecisionType.SILENCE:
                moment = active.moment_engine.create_silence(
                    session_id=active.session_id,
                    selected_mood=active.selected_mood,
                    persona=active.dj_persona,
                    locale=active.locale,
                    reason=decision.reason,
                )
                active.publish_moment(moment)
                self._record_performance_memory(owner_profile_id, active)
                return moment
            intent = decision.knowledge_intent
            if intent is None:
                return None
        try:
            raw_insight = await insight_provider()
        except Exception as exc:  # noqa: BLE001
            _LOGGER.debug("DJConnect Track Insight unavailable: %s", exc.__class__.__name__)
            raw_insight = {}
        hints = _planner_knowledge_hints(raw_insight)
        async with self._lock:
            active = self._active_by_profile.get(owner_profile_id)
            if active is None or active.session_id != session_id:
                return None
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
                active.publish_moment(moment)
                self._record_performance_memory(owner_profile_id, active)
                return moment
            intent = decision.knowledge_intent
            if intent is None:
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
            if active is None or active.session_id != session_id:
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
            active.publish_moment(moment)
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
                    active.publish_moment(
                        transition,
                        SessionFlowPosition(transition_decision.transition_placement),
                    )
            self._record_performance_memory(owner_profile_id, active)
            return moment

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
            active.broadcast.update_runtime_state(SessionRuntimeState.ENDING)
            ending = DJSessionRuntime(
                **{**active.__dict__, "runtime_state": SessionRuntimeState.ENDING}
            )
            active.broadcast.update_runtime_state(SessionRuntimeState.ENDED)
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
            return ended


def session_runtime_manager(hass: Any) -> SessionRuntimeManager:
    """Return the integration-wide ephemeral Session Runtime Manager."""
    domain_data = hass.data.setdefault(DOMAIN, {})
    manager = domain_data.get("session_runtime_manager")
    if manager is None:
        manager = SessionRuntimeManager()
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


def _recent_metadata(
    metadata: tuple[dict[str, str], ...], key: str
) -> tuple[str, ...]:
    """Return unique, non-empty metadata values in chronological order."""
    return tuple(dict.fromkeys(value for item in metadata if (value := item.get(key, ""))))


def _performance_memory_repeats(
    memory: PerformanceMemory, intent_type: KnowledgeIntentType, hints: dict[str, Any]
) -> bool:
    """Reject only deterministic repeats from the bounded Runtime projection."""
    if intent_type is KnowledgeIntentType.ARTIST_STORY:
        candidate = _bounded_text(hints.get("artist") or hints.get("producer"), 160)
        return candidate in memory.recent_artists
    if intent_type is KnowledgeIntentType.ALBUM_STORY:
        candidate = _bounded_text(hints.get("album") or hints.get("release_year"), 160)
        return candidate in memory.recent_albums
    if intent_type is KnowledgeIntentType.GENRE_STORY:
        candidate = _bounded_text(hints.get("genre"), 160)
        return candidate in memory.recent_genres
    if intent_type is KnowledgeIntentType.RECOMMENDATION:
        candidate = _bounded_text(hints.get("artist") or hints.get("related_tracks"), 160)
        return candidate in memory.recent_recommendations
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
    *, session_id: str, created_at: str, configuration: PlannerConfiguration
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
    )


def _create_broadcast_engine(
    *,
    session_id: str,
    runtime_state: SessionRuntimeState,
    selected_mood: str,
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


def _presentation_intent(selected_mood: str, persona: DJPersona) -> PresentationIntent:
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
        maximum_duration_seconds=25,
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


def _specialize_track_moment(track: dict[str, Any], analysis: dict[str, Any], title: str, artist: str, summary: str, content: str, intent_type: KnowledgeIntentType) -> tuple[DJMomentType, str, str, str] | None:
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
        if not (_bounded_text(analysis.get("genre"), 160) or _bounded_text(track.get("genres"), 160)):
            return None
        return DJMomentType.GENRE, _bounded_text(analysis.get("genre"), 160) or _bounded_text(track.get("genres"), 160), summary, content
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
        "related_tracks": _bounded_text(track.get("related_tracks") or analysis.get("similar_tracks"), 1200),
        "producer": _bounded_text(track.get("producer") or track.get("recording_context"), 600),
        "release_year": _bounded_text(track.get("release_year") or track.get("release_date"), 32),
        "genre": _bounded_text(analysis.get("genre") or track.get("genres"), 160),
        "artist": _bounded_text(track.get("artist"), 160),
        "album": _bounded_text(track.get("album"), 160),
    }


def _track_key(track: dict[str, Any]) -> str:
    return "|".join(
        _bounded_text(track.get(field), 160).lower()
        for field in ("title", "artist", "album")
    ).strip("|")


def _bounded_text(value: Any, limit: int) -> str:
    return str(value or "").strip()[:limit]


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
        "en": ("From {source} to {target}", "A bridge into the next discovery.", "This connection carries the session from {source} into {target}."),
        "nl": ("Van {source} naar {target}", "Een brug naar de volgende ontdekking.", "Deze verbinding brengt de sessie van {source} naar {target}."),
        "de": ("Von {source} zu {target}", "Eine Brücke zur nächsten Entdeckung.", "Diese Verbindung führt die Session von {source} zu {target}."),
        "fr": ("De {source} à {target}", "Un passage vers la prochaine découverte.", "Cette transition mène la session de {source} à {target}."),
        "es": ("De {source} a {target}", "Un puente hacia el próximo descubrimiento.", "Esta transición lleva la sesión de {source} a {target}."),
    }
    index = {"title": 0, "summary": 1, "content": 2}[part]
    return copy[_locale_family(locale)][index].format(source=source, target=target)


def _payload_contains_owner_only_moment(payload: dict[str, Any]) -> bool:
    moment = payload.get("dj_moment")
    if not isinstance(moment, dict):
        return False
    return moment.get("visibility") == DJMomentVisibility.OWNER_ONLY.value
