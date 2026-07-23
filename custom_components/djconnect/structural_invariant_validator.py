"""Post-execution structural assessment for the sole approved Golden Scenario."""
from __future__ import annotations

from dataclasses import dataclass

from .developer_session_bootstrap import (
    GOLDEN_SCENARIO_ID,
    SI_GOLDEN_002_ID,
    SI_GOLDEN_003_ID,
    SI_GOLDEN_004_ID,
    SI_GOLDEN_005_ID,
    SI_GOLDEN_006_ID,
)
from .developer_session_capture import (
    SIGolden001SessionCapture,
    SIGolden002SessionCapture,
    SIGolden003SessionCapture,
    RemainingGoldenSessionCapture,
)


def validate_remaining_golden(capture: RemainingGoldenSessionCapture) -> StructuralValidationResult:
    """Validate the distinct product semantics of GS-004 through GS-006."""
    failures: list[InvariantFailure] = []
    def require(identifier: str, condition: bool, expected: str, observed: str) -> None:
        if not condition:
            failures.append(InvariantFailure(identifier, identifier.lower(), expected, observed, "capture"))
    if capture.scenario_id == SI_GOLDEN_004_ID:
        require("SI004-REPLAN", capture.planning_generation > 0, "replacement generation", str(capture.planning_generation))
        require("SI004-SUPERSESSION", capture.superseded_intent_count > 0, "superseded provisional intent", str(capture.superseded_intent_count))
        require("SI004-ONE-APPROVAL", sum(status == "approved" for _, _, status in capture.planned_intents) == 1, "one stable approved intent", repr(capture.planned_intents))
        require("SI004-NO-MOMENT", not capture.moments, "no DJMoment", repr(capture.moments))
        require("SI004-NO-PRESENTATION", not capture.presentations, "no Presentation", repr(capture.presentations))
        require("SI004-NO-FLOW-REWRITE", not any(item.moment_id for item in capture.session_flow), "no realized Flow Moment", repr(capture.session_flow))
        require("SI004-NO-BROADCAST-LEAK", not any(item.event_type in {"dj_moment_published", "presentation_published"} for item in capture.broadcast_publications), "no planning internals or Moment publication", repr(capture.broadcast_publications))
    elif capture.scenario_id == SI_GOLDEN_005_ID:
        require("SI005-THREE-MOMENTS", tuple(item.moment_type for item in capture.moments) == ("silence", "silence", "session"), "two Silence then Session Update", repr(capture.moments))
        require("SI005-ONE-UPDATE", sum(item.moment_type == "session" for item in capture.moments) == 1, "one Session Update", repr(capture.moments))
        require("SI005-PRESENTATION", bool(capture.presentations) and capture.presentations[-1].source_moment_id == capture.moments[-1].moment_id, "Session Update Presentation", repr(capture.presentations))
    elif capture.scenario_id == SI_GOLDEN_006_ID:
        require("SI006-SILENCE", len(capture.moments) == 1 and capture.moments[0].moment_type == "silence", "one canonical Silence", repr(capture.moments))
        require("SI006-INTENTIONAL", bool(capture.moments) and capture.moments[0].reason == "planned_silence", "planned intentional Silence", repr(capture.moments))
        require("SI006-NO-NARRATIVE", bool(capture.moments) and not capture.moments[0].content, "no narrative content", repr(capture.moments))
        require("SI006-NO-SPEECH", not capture.presentations or not capture.presentations[0].segments, "no narrative Speech", repr(capture.presentations))
    else:
        failures.append(InvariantFailure("SI-UNKNOWN", "scenario", "known scenario", capture.scenario_id, "scenario_id"))
    return StructuralValidationResult("passed" if not failures else "failed", tuple(failures))


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
    presentation = next(
        (
            item
            for item in capture.presentations
            if getattr(item, "source_moment_id", "") == capture.realized_moment.moment_id
        ),
        None,
    )
    require("SI001-PRESENTATION-PROJECTION", presentation is not None and bool(presentation.presentation_id), "one Presentation for realized Moment", repr(presentation), "presentations")
    require(
        "SI001-PRESENTATION-STRUCTURE",
        presentation is not None
        and presentation.presentation_id == f"presentation-{capture.realized_moment.moment_id}"
        and presentation.source_moment_type == capture.realized_moment.moment_type
        and presentation.visibility == "session_shared"
        and presentation.mode in {"primary_only", "primary_with_sidekick"}
        and _valid_speech_structure(presentation.mode, presentation.segments),
        "safe source-linked Presentation with ordered semantic Speech roles",
        repr(presentation),
        "presentations",
    )
    require("SI001-FLOW-UNCHANGED", not any(item.item_type == "presentation" for item in capture.session_flow), "no Presentation Flow item", repr(capture.session_flow), "session_flow")
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
    presentations_by_source = {
        item.source_moment_id: item
        for item in capture.presentations
        if hasattr(item, "source_moment_id")
    }
    first_presentation = presentations_by_source.get(capture.first_realized_moment.moment_id)
    second_presentation = presentations_by_source.get(capture.second_realized_moment.moment_id)
    require(
        "SI002-PRESENTATION-PUBLICATION",
        sum(item.event_type == "presentation_published" for item in capture.broadcast_publications) == 2,
        "two canonical Presentation publications",
        repr(capture.broadcast_publications),
        "broadcast_publications",
    )
    require(
        "SI002-ARTIST-SIDEKICK-PROJECTION",
        first_presentation is not None
        and first_presentation.presentation_id
        and first_presentation.mode == "primary_with_sidekick"
        and tuple(segment.ordinal for segment in first_presentation.segments) == (1, 2)
        and tuple(segment.speaker_role for segment in first_presentation.segments) == ("dj", "sidekick")
        and tuple(segment.text for segment in first_presentation.segments)
        == (capture.first_realized_moment.content, capture.first_realized_moment.summary),
        "Artist Story Presentation with ordered approved DJ and Sidekick text",
        repr(first_presentation),
        "presentations",
    )
    require(
        "SI002-PRESENTATION-COMPATIBILITY",
        first_presentation is not None
        and second_presentation is not None
        and first_presentation.visibility == "session_shared"
        and second_presentation.visibility == "session_shared"
        and _valid_speech_structure(first_presentation.mode, first_presentation.segments)
        and _valid_speech_structure(second_presentation.mode, second_presentation.segments),
        "renderer-safe compatible Presentation projections",
        repr((first_presentation, second_presentation)),
        "presentations",
    )
    require(
        "SI002-NONELIGIBLE-PRIMARY-PROJECTION",
        second_presentation is not None
        and second_presentation.presentation_id
        and second_presentation.mode == "primary_only"
        and tuple((segment.ordinal, segment.speaker_role, segment.text) for segment in second_presentation.segments)
        == ((1, "dj", capture.second_realized_moment.content),),
        "non-eligible Moment Presentation with one approved DJ segment",
        repr(second_presentation),
        "presentations",
    )
    require(
        "SI002-FLOW-UNCHANGED",
        not any(item.item_type == "presentation" for item in capture.session_flow),
        "no Presentation Flow item",
        repr(capture.session_flow),
        "session_flow",
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


def _valid_speech_structure(mode: str, segments: tuple[object, ...]) -> bool:
    """Validate only immutable segment ordering and semantic roles."""
    ordinals = tuple(getattr(segment, "ordinal", None) for segment in segments)
    roles = tuple(getattr(segment, "speaker_role", None) for segment in segments)
    texts = tuple(getattr(segment, "text", None) for segment in segments)
    if not all(isinstance(text, str) and text for text in texts):
        return False
    if mode == "primary_only":
        return ordinals == (1,) and roles == ("dj",)
    if mode == "primary_with_sidekick":
        return ordinals == (1, 2) and roles == ("dj", "sidekick")
    return False


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
