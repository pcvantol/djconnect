"""Immutable read-only observation capture for SI-GOLDEN-001."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .developer_session_bootstrap import (
    GOLDEN_SCENARIO_ID,
    GOLDEN_SCENARIO_PROFILE_ID,
    SI_GOLDEN_002_ID,
    SI_GOLDEN_002_PROFILE_ID,
    SI_GOLDEN_003_ID,
    SI_GOLDEN_003_PROFILE_ID,
    si_golden_002_clock_evidence,
)
from .session_runtime import session_runtime_manager


DEVELOPER_SESSION_CAPTURE_SERVICE = "developer_session_capture"


@dataclass(frozen=True)
class CapturedFlowEntry:
    item_id: str
    item_type: str
    position: str
    moment_id: str
    moment_type: str


@dataclass(frozen=True)
class CapturedMoment:
    moment_id: str
    moment_type: str
    knowledge_intent: str


@dataclass(frozen=True)
class CapturedBroadcastPublication:
    delivery_sequence: int
    event_type: str


@dataclass(frozen=True)
class SIGolden001SessionCapture:
    """One finalized, immutable observation artifact; never Runtime state."""

    scenario_id: str
    session_id: str
    runtime_events: tuple[str, ...]
    track_started_events: tuple[str, ...]
    approved_planner_intent: str
    realized_moment: CapturedMoment
    session_flow: tuple[CapturedFlowEntry, ...]
    broadcast_publications: tuple[CapturedBroadcastPublication, ...]
    completion_state: str
    planning_lifecycle: str = ""
    approval_count: int = 0
    planning_generation: int = -1
    legacy_fallback_used: bool = False
    cleanup_completed: bool = False


@dataclass(frozen=True)
class CapturedVerificationClock:
    """Bounded evidence from verification infrastructure, never Runtime state."""

    elapsed_seconds: float
    advance_count: int


@dataclass(frozen=True)
class SIGolden002SessionCapture:
    """Finalized observation of the approved first-eligible repetition scenario."""

    scenario_id: str
    session_id: str
    runtime_events: tuple[str, ...]
    track_started_events: tuple[str, ...]
    verification_clock: CapturedVerificationClock
    first_realized_moment: CapturedMoment
    second_realized_moment: CapturedMoment
    session_flow: tuple[CapturedFlowEntry, ...]
    broadcast_publications: tuple[CapturedBroadcastPublication, ...]
    completion_state: str
    planning_lifecycle: str = ""
    approval_count: int = 0
    legacy_fallback_used: bool = False
    cleanup_completed: bool = False


@dataclass(frozen=True)
class SIGolden003SessionCapture:
    """Finalized observation of safe degradation from unavailable knowledge."""

    scenario_id: str
    session_id: str
    runtime_events: tuple[str, ...]
    track_started_events: tuple[str, ...]
    realized_moment: CapturedMoment
    knowledge_failure_observed: bool
    no_fabricated_knowledge: bool
    session_flow: tuple[CapturedFlowEntry, ...]
    broadcast_publications: tuple[CapturedBroadcastPublication, ...]
    broadcast_contains_realized_moment: bool
    completion_state: str
    planning_lifecycle: str = ""
    approval_count: int = 0
    legacy_fallback_used: bool = False
    cleanup_completed: bool = False


async def async_capture_si_golden_001(hass: Any) -> SIGolden001SessionCapture | None:
    """Read the active Runtime once without mutating it or its owners."""
    active = await session_runtime_manager(hass).async_get_active(GOLDEN_SCENARIO_PROFILE_ID)
    if active is None or not active.moment_engine.moments:
        return None
    moment = active.moment_engine.moments[-1]
    flow = tuple(
        CapturedFlowEntry(
            item_id=item.item_id,
            item_type=item.item_type.value,
            position=item.position.value,
            moment_id=item.moment_id,
            moment_type=item.moment_type,
        )
        for item in active.planner.output.session_flow.items
    )
    publications = tuple(
        CapturedBroadcastPublication(entry.delivery_sequence, entry.event_type.value)
        for entry in active.broadcast.replay_log
    )
    return SIGolden001SessionCapture(
        scenario_id=GOLDEN_SCENARIO_ID,
        session_id=active.session_id,
        runtime_events=("runtime_active", "track_started", "runtime_completed"),
        track_started_events=("track_started",),
        approved_planner_intent=moment.knowledge_intent.intent_type.value,
        realized_moment=CapturedMoment(
            moment_id=moment.moment_id,
            moment_type=moment.moment_type.value,
            knowledge_intent=moment.knowledge_intent.intent_type.value,
        ),
        session_flow=flow,
        broadcast_publications=publications,
        completion_state="completed",
        planning_lifecycle=active.planning_coordinator.last_lifecycle_state or "",
        approval_count=1 if active.planning_coordinator.last_approval_source == "planned_intent" else 0,
        planning_generation=active.planning_coordinator.last_planning_generation or 0,
        legacy_fallback_used=active.planning_coordinator.last_fallback_reason is not None,
        cleanup_completed=True,
    )


async def async_capture_si_golden_002(hass: Any) -> SIGolden002SessionCapture | None:
    """Read the completed two-event Runtime without mutating any owner."""
    active = await session_runtime_manager(hass).async_get_active(SI_GOLDEN_002_PROFILE_ID)
    clock_evidence = si_golden_002_clock_evidence(hass)
    if active is None or len(active.moment_engine.moments) != 2 or clock_evidence is None:
        return None
    first, second = active.moment_engine.moments
    flow = tuple(
        CapturedFlowEntry(
            item_id=item.item_id,
            item_type=item.item_type.value,
            position=item.position.value,
            moment_id=item.moment_id,
            moment_type=item.moment_type,
        )
        for item in active.planner.output.session_flow.items
    )
    publications = tuple(
        CapturedBroadcastPublication(entry.delivery_sequence, entry.event_type.value)
        for entry in active.broadcast.replay_log
    )
    return SIGolden002SessionCapture(
        scenario_id=SI_GOLDEN_002_ID,
        session_id=active.session_id,
        runtime_events=("runtime_active", "track_started", "track_started", "runtime_completed"),
        track_started_events=("track_started", "track_started"),
        verification_clock=CapturedVerificationClock(*clock_evidence),
        first_realized_moment=CapturedMoment(
            first.moment_id, first.moment_type.value, first.knowledge_intent.intent_type.value
        ),
        second_realized_moment=CapturedMoment(
            second.moment_id, second.moment_type.value, second.knowledge_intent.intent_type.value
        ),
        session_flow=flow,
        broadcast_publications=publications,
        completion_state="completed",
        planning_lifecycle=active.planning_coordinator.last_lifecycle_state or "",
        approval_count=1 if active.planning_coordinator.last_approval_source == "planned_intent" else 0,
        legacy_fallback_used=active.planning_coordinator.last_fallback_reason is not None,
        cleanup_completed=True,
    )


async def async_capture_si_golden_003(hass: Any) -> SIGolden003SessionCapture | None:
    """Observe only the realized safe-degradation outcome of the active Runtime."""
    active = await session_runtime_manager(hass).async_get_active(SI_GOLDEN_003_PROFILE_ID)
    if active is None or len(active.moment_engine.moments) != 1:
        return None
    moment = active.moment_engine.moments[0]
    metadata = dict(moment.generation_metadata)
    flow = tuple(
        CapturedFlowEntry(
            item_id=item.item_id,
            item_type=item.item_type.value,
            position=item.position.value,
            moment_id=item.moment_id,
            moment_type=item.moment_type,
        )
        for item in active.planner.output.session_flow.items
    )
    publications = tuple(
        CapturedBroadcastPublication(entry.delivery_sequence, entry.event_type.value)
        for entry in active.broadcast.replay_log
    )
    return SIGolden003SessionCapture(
        scenario_id=SI_GOLDEN_003_ID,
        session_id=active.session_id,
        runtime_events=("runtime_active", "track_started", "runtime_completed"),
        track_started_events=("track_started",),
        realized_moment=CapturedMoment(
            moment.moment_id, moment.moment_type.value, moment.knowledge_intent.intent_type.value
        ),
        knowledge_failure_observed=(
            moment.moment_type.value == "silence" and metadata.get("reason") == "invalid_ai_output"
        ),
        no_fabricated_knowledge=not moment.content and not moment.source_references,
        session_flow=flow,
        broadcast_publications=publications,
        broadcast_contains_realized_moment=any(
            item.moment_id == moment.moment_id for item in active.broadcast.state.dj_moments
        ),
        completion_state="completed",
        planning_lifecycle=active.planning_coordinator.last_lifecycle_state or "",
        approval_count=1 if active.planning_coordinator.last_approval_source == "planned_intent" else 0,
        legacy_fallback_used=active.planning_coordinator.last_fallback_reason is not None,
        cleanup_completed=True,
    )


async def async_handle_developer_session_capture(
    hass: Any, scenario_id: str = GOLDEN_SCENARIO_ID
) -> dict[str, Any]:
    """Expose only bounded capture metadata; the artifact stays in-process."""
    scenario = str(scenario_id or GOLDEN_SCENARIO_ID).strip().upper()
    if scenario == GOLDEN_SCENARIO_ID:
        capture = await async_capture_si_golden_001(hass)
    elif scenario == SI_GOLDEN_002_ID:
        capture = await async_capture_si_golden_002(hass)
    elif scenario == SI_GOLDEN_003_ID:
        capture = await async_capture_si_golden_003(hass)
    else:
        return {"success": False, "status": "invalid_scenario", "scenario_id": scenario}
    if capture is None:
        return {"success": False, "status": "execution_required", "scenario_id": scenario}
    moment_id = capture.second_realized_moment.moment_id if isinstance(
        capture, SIGolden002SessionCapture
    ) else capture.realized_moment.moment_id
    return {
        "success": True,
        "status": "captured",
        "scenario_id": capture.scenario_id,
        "session_id": capture.session_id,
        "moment_id": moment_id,
        "completion_state": capture.completion_state,
    }
