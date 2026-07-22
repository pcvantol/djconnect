"""Immutable read-only observation capture for SI-GOLDEN-001."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .developer_session_bootstrap import GOLDEN_SCENARIO_ID, GOLDEN_SCENARIO_PROFILE_ID
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


async def async_handle_developer_session_capture(hass: Any) -> dict[str, Any]:
    """Expose only bounded capture metadata; the artifact stays in-process."""
    capture = await async_capture_si_golden_001(hass)
    if capture is None:
        return {"success": False, "status": "execution_required", "scenario_id": GOLDEN_SCENARIO_ID}
    return {
        "success": True,
        "status": "captured",
        "scenario_id": capture.scenario_id,
        "session_id": capture.session_id,
        "moment_id": capture.realized_moment.moment_id,
        "completion_state": capture.completion_state,
    }
