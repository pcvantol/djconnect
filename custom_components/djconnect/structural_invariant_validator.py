"""Post-execution structural assessment for the sole approved Golden Scenario."""
from __future__ import annotations

from dataclasses import dataclass

from .developer_session_bootstrap import GOLDEN_SCENARIO_ID, SI_GOLDEN_002_ID, SI_GOLDEN_003_ID
from .developer_session_capture import (
    SIGolden001SessionCapture,
    SIGolden002SessionCapture,
    SIGolden003SessionCapture,
)


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


def validate_si_golden_002(capture: SIGolden002SessionCapture) -> StructuralValidationResult:
    """Validate only SI-GOLDEN-002's captured observable product contract."""
    failures: list[InvariantFailure] = []

    def require(identifier: str, condition: bool, expected: str, observed: str, reference: str) -> None:
        if not condition:
            failures.append(
                InvariantFailure(
                    identifier,
                    identifier.replace("SI002-", "").lower().replace("-", " "),
                    expected,
                    observed,
                    reference,
                )
            )

    if capture.scenario_id != SI_GOLDEN_002_ID or not capture.session_id:
        return StructuralValidationResult(
            "invalid_capture",
            (
                InvariantFailure(
                    "SI002-CAPTURE-IDENTITY",
                    "capture identity",
                    SI_GOLDEN_002_ID,
                    capture.scenario_id,
                    "scenario_id",
                ),
            ),
        )
    require(
        "SI002-RUNTIME-LIFECYCLE",
        "runtime_active" in capture.runtime_events and capture.completion_state == "completed",
        "active then completed",
        repr(capture.runtime_events),
        "runtime_events",
    )
    require(
        "SI002-TRACK-STARTED",
        capture.track_started_events == ("track_started", "track_started"),
        "two Track Started events",
        repr(capture.track_started_events),
        "track_started_events",
    )
    require(
        "SI002-CLOCK-ADVANCED",
        capture.verification_clock.advance_count == 1
        and capture.verification_clock.elapsed_seconds > 60.0,
        "one advance beyond 60 seconds",
        repr(capture.verification_clock),
        "verification_clock",
    )
    require(
        "SI002-FIRST-MOMENT",
        bool(capture.first_realized_moment.moment_id)
        and bool(capture.first_realized_moment.knowledge_intent),
        "one knowledge-backed first Moment",
        repr(capture.first_realized_moment),
        "first_realized_moment",
    )
    require(
        "SI002-NO-IMMEDIATE-REPETITION",
        capture.first_realized_moment.knowledge_intent
        != capture.second_realized_moment.knowledge_intent,
        "a different eligible knowledge intent",
        repr((capture.first_realized_moment, capture.second_realized_moment)),
        "first_realized_moment/second_realized_moment",
    )
    require(
        "SI002-SECOND-APPROVAL",
        capture.approval_count == 1
        and bool(capture.second_realized_moment.moment_id)
        and bool(capture.second_realized_moment.knowledge_intent),
        "one approved and realized second Moment",
        str(capture.approval_count),
        "approval_count",
    )
    flow_ids = tuple(item.moment_id for item in capture.session_flow if item.moment_id)
    require(
        "SI002-FLOW-ORDER",
        flow_ids.index(capture.first_realized_moment.moment_id)
        < flow_ids.index(capture.second_realized_moment.moment_id)
        if capture.first_realized_moment.moment_id in flow_ids
        and capture.second_realized_moment.moment_id in flow_ids
        else False,
        "first then second Moment in Flow",
        repr(flow_ids),
        "session_flow",
    )
    publication_count = sum(
        item.event_type == "dj_moment_published" for item in capture.broadcast_publications
    )
    require(
        "SI002-BROADCAST",
        publication_count == 2,
        "two canonical DJMoment publications",
        str(publication_count),
        "broadcast_publications",
    )
    require(
        "SI002-NO-LEGACY-FALLBACK",
        not capture.legacy_fallback_used,
        "no legacy fallback",
        str(capture.legacy_fallback_used),
        "legacy_fallback_used",
    )
    require(
        "SI002-CLEANUP",
        capture.cleanup_completed,
        "completed cleanup",
        str(capture.cleanup_completed),
        "cleanup_completed",
    )
    return StructuralValidationResult("passed" if not failures else "failed", tuple(failures))


def validate_si_golden_003(capture: SIGolden003SessionCapture) -> StructuralValidationResult:
    """Validate only SI-GOLDEN-003's observable safe-degradation contract."""
    failures: list[InvariantFailure] = []

    def require(identifier: str, condition: bool, expected: str, observed: str, reference: str) -> None:
        if not condition:
            failures.append(
                InvariantFailure(
                    identifier,
                    identifier.replace("SI003-", "").lower().replace("-", " "),
                    expected,
                    observed,
                    reference,
                )
            )

    if capture.scenario_id != SI_GOLDEN_003_ID or not capture.session_id:
        return StructuralValidationResult(
            "invalid_capture",
            (
                InvariantFailure(
                    "SI003-CAPTURE-IDENTITY",
                    "capture identity",
                    SI_GOLDEN_003_ID,
                    capture.scenario_id,
                    "scenario_id",
                ),
            ),
        )
    require(
        "SI003-RUNTIME-LIFECYCLE",
        "runtime_active" in capture.runtime_events and capture.completion_state == "completed",
        "active then completed",
        repr(capture.runtime_events),
        "runtime_events",
    )
    require(
        "SI003-TRACK-STARTED",
        capture.track_started_events == ("track_started",),
        "one Track Started",
        repr(capture.track_started_events),
        "track_started_events",
    )
    require(
        "SI003-KNOWLEDGE-FAILURE",
        capture.knowledge_failure_observed,
        "approved unavailable knowledge outcome",
        str(capture.knowledge_failure_observed),
        "knowledge_failure_observed",
    )
    require(
        "SI003-NO-FABRICATION",
        capture.no_fabricated_knowledge,
        "no fabricated knowledge content or sources",
        str(capture.no_fabricated_knowledge),
        "no_fabricated_knowledge",
    )
    require(
        "SI003-SILENCE",
        capture.realized_moment.moment_type == "silence"
        and capture.realized_moment.knowledge_intent == "silence",
        "one approved Silence outcome",
        repr(capture.realized_moment),
        "realized_moment",
    )
    require(
        "SI003-PLANNER-APPROVAL",
        capture.approval_count == 1 and capture.planning_lifecycle == "completed",
        "one completed Planner approval",
        f"approval_count={capture.approval_count}, lifecycle={capture.planning_lifecycle}",
        "approval_count/planning_lifecycle",
    )
    require(
        "SI003-FLOW",
        any(item.moment_id == capture.realized_moment.moment_id for item in capture.session_flow),
        "Silence in Session Flow",
        repr(capture.session_flow),
        "session_flow",
    )
    require(
        "SI003-BROADCAST",
        capture.broadcast_contains_realized_moment
        and not any(item.event_type == "dj_moment_published" for item in capture.broadcast_publications),
        "Silence retained in Broadcast projection without narrative publication",
        repr(capture.broadcast_publications),
        "broadcast_publications",
    )
    require(
        "SI003-NO-LEGACY-FALLBACK",
        not capture.legacy_fallback_used,
        "no legacy fallback",
        str(capture.legacy_fallback_used),
        "legacy_fallback_used",
    )
    require(
        "SI003-CLEANUP",
        capture.cleanup_completed,
        "completed cleanup",
        str(capture.cleanup_completed),
        "cleanup_completed",
    )
    return StructuralValidationResult("passed" if not failures else "failed", tuple(failures))
