"""Post-execution structural assessment for the sole approved Golden Scenario."""
from __future__ import annotations

from dataclasses import dataclass

from .developer_session_bootstrap import GOLDEN_SCENARIO_ID
from .developer_session_capture import SIGolden001SessionCapture


@dataclass(frozen=True)
class InvariantFailure:
    identifier: str
    description: str
    expected: str
    observed: str
    capture_reference: str


@dataclass(frozen=True)
class StructuralValidationResult:
    status: str
    failures: tuple[InvariantFailure, ...] = ()


def validate_si_golden_001(capture: SIGolden001SessionCapture) -> StructuralValidationResult:
    """Validate only approved SI-GOLDEN-001 structural capture evidence."""
    failures: list[InvariantFailure] = []

    def require(identifier: str, condition: bool, expected: str, observed: str, reference: str) -> None:
        if not condition:
            failures.append(InvariantFailure(identifier, identifier.replace("SI001-", "").lower().replace("-", " "), expected, observed, reference))

    invalid = capture.scenario_id != GOLDEN_SCENARIO_ID or not capture.session_id
    if invalid:
        return StructuralValidationResult("invalid_capture", (InvariantFailure("SI001-CAPTURE-IDENTITY", "capture identity", GOLDEN_SCENARIO_ID, capture.scenario_id, "scenario_id"),))
    require("SI001-RUNTIME-LIFECYCLE", "runtime_active" in capture.runtime_events and capture.completion_state == "completed", "active then completed", repr(capture.runtime_events), "runtime_events")
    require("SI001-TRACK-STARTED", capture.track_started_events == ("track_started",), "one Track Started", repr(capture.track_started_events), "track_started_events")
    require("SI001-PLANNING-LIFECYCLE", capture.planning_lifecycle == "completed", "canonical completed lifecycle", capture.planning_lifecycle, "planning_lifecycle")
    require("SI001-PLANNER-APPROVAL", capture.approval_count == 1 and bool(capture.approved_planner_intent), "one approval", str(capture.approval_count), "approval_count")
    require("SI001-MOMENT", bool(capture.realized_moment.moment_id) and capture.realized_moment.knowledge_intent == capture.approved_planner_intent, "one matching Moment", repr(capture.realized_moment), "realized_moment")
    flow_index = next((i for i, item in enumerate(capture.session_flow) if item.moment_id == capture.realized_moment.moment_id), -1)
    broadcast_index = next((i for i, item in enumerate(capture.broadcast_publications) if item.event_type == "dj_moment_published"), -1)
    require("SI001-FLOW-BEFORE-BROADCAST", flow_index >= 0 and broadcast_index >= 0, "Moment in Flow and Broadcast", f"flow={flow_index}, broadcast={broadcast_index}", "session_flow/broadcast_publications")
    require("SI001-NO-LEGACY-FALLBACK", not capture.legacy_fallback_used, "no legacy fallback", str(capture.legacy_fallback_used), "legacy_fallback_used")
    require("SI001-PLANNING-GENERATION", capture.planning_generation >= 0, "valid planning generation", str(capture.planning_generation), "planning_generation")
    require("SI001-CLEANUP", capture.cleanup_completed, "completed cleanup", str(capture.cleanup_completed), "cleanup_completed")
    return StructuralValidationResult("passed" if not failures else "failed", tuple(failures))
