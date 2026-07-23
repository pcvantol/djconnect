"""One deterministic, server-side qualification path for executable Golden Scenarios."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .developer_session_bootstrap import (
    SI_GOLDEN_001_ID,
    SI_GOLDEN_002_ID,
    SI_GOLDEN_003_ID,
    SI_GOLDEN_004_ID,
    SI_GOLDEN_005_ID,
    SI_GOLDEN_006_ID,
    async_handle_developer_session_bootstrap,
)
from .developer_session_capture import (
    SIGolden001SessionCapture,
    SIGolden002SessionCapture,
    SIGolden003SessionCapture,
    async_capture_si_golden_001,
    async_capture_si_golden_002,
    async_capture_si_golden_003,
    async_capture_remaining_golden,
    RemainingGoldenSessionCapture,
)
from .developer_session_scenario_driver import (
    async_execute_si_golden_001,
    async_execute_si_golden_002,
    async_execute_si_golden_003,
    async_execute_si_golden_004,
    async_execute_si_golden_005,
    async_execute_si_golden_006,
)
from .structural_invariant_validator import (
    StructuralValidationResult,
    validate_si_golden_001,
    validate_si_golden_002,
    validate_si_golden_003,
    validate_remaining_golden,
)


GOLDEN_QUALIFICATION_PROFILE = "golden_qualification_foundation"
GOLDEN_SMOKE_PROFILE = "golden_smoke"
EXECUTABLE_GOLDEN_SCENARIOS = (
    SI_GOLDEN_001_ID,
    SI_GOLDEN_002_ID,
    SI_GOLDEN_003_ID,
    SI_GOLDEN_004_ID,
    SI_GOLDEN_005_ID,
    SI_GOLDEN_006_ID,
)
GOLDEN_SMOKE_SCENARIOS = (SI_GOLDEN_001_ID,)


@dataclass(frozen=True)
class GoldenScenarioQualification:
    """One immutable server-side qualification result for one approved scenario."""

    scenario_id: str
    session_verification: str
    presentation_verification: str
    deterministic: bool
    overall_status: str
    failure_identifiers: tuple[str, ...] = ()


@dataclass(frozen=True)
class GoldenQualificationReport:
    """One immutable report from the sole Golden Qualification execution path."""

    profile: str
    scenarios: tuple[GoldenScenarioQualification, ...]
    overall_status: str


async def async_run_golden_qualification(
    hass: Any,
    scenario_ids: tuple[str, ...] = EXECUTABLE_GOLDEN_SCENARIOS,
) -> GoldenQualificationReport:
    """Execute each approved scenario twice through the existing Runtime path.

    Bootstrap, Driver, Capture and Validator remain their existing owners. This
    coordinator only composes them, stops every successfully started Session,
    and compares normalized immutable server-owned output. It never reads or
    drives a Renderer Host.
    """
    normalized = tuple(str(item).strip().upper() for item in scenario_ids)
    results_list: list[GoldenScenarioQualification] = []
    for scenario_id in normalized:
        results_list.append(await _qualify_scenario(hass, scenario_id))
    results = tuple(results_list)
    return GoldenQualificationReport(
        profile=GOLDEN_QUALIFICATION_PROFILE,
        scenarios=results,
        overall_status="passed" if results and all(item.overall_status == "passed" for item in results) else "failed",
    )


async def async_handle_golden_qualification(hass: Any) -> dict[str, Any]:
    """Expose bounded qualification metadata without exposing Runtime internals."""
    report = await async_run_golden_qualification(hass)
    return {
        "success": report.overall_status == "passed",
        "status": report.overall_status,
        "profile": report.profile,
        "scenarios": [
            {
                "scenario_id": item.scenario_id,
                "session_verification": item.session_verification,
                "presentation_verification": item.presentation_verification,
                "deterministic": item.deterministic,
                "overall_status": item.overall_status,
                "failure_identifiers": item.failure_identifiers,
            }
            for item in report.scenarios
        ],
    }


async def async_run_golden_smoke(hass: Any) -> GoldenQualificationReport:
    """Run the smallest approved selection through Golden Qualification."""
    foundation_report = await async_run_golden_qualification(
        hass, scenario_ids=GOLDEN_SMOKE_SCENARIOS
    )
    return GoldenQualificationReport(
        profile=GOLDEN_SMOKE_PROFILE,
        scenarios=foundation_report.scenarios,
        overall_status=foundation_report.overall_status,
    )


async def async_handle_golden_smoke(hass: Any) -> dict[str, Any]:
    """Expose the bounded Golden Smoke report from the canonical path."""
    report = await async_run_golden_smoke(hass)
    return {
        "success": report.overall_status == "passed",
        "status": report.overall_status,
        "profile": report.profile,
        "scenarios": [
            {
                "scenario_id": item.scenario_id,
                "session_verification": item.session_verification,
                "presentation_verification": item.presentation_verification,
                "deterministic": item.deterministic,
                "overall_status": item.overall_status,
                "failure_identifiers": item.failure_identifiers,
            }
            for item in report.scenarios
        ],
    }


async def _qualify_scenario(hass: Any, scenario_id: str) -> GoldenScenarioQualification:
    """Run one scenario twice and compare only immutable observable evidence."""
    first, first_validation = await _execute_once(hass, scenario_id)
    second, second_validation = await _execute_once(hass, scenario_id)
    validations = (first_validation, second_validation)
    failures = tuple(
        failure.identifier
        for validation in validations
        for failure in validation.failures
    )
    deterministic = (
        first is not None
        and second is not None
        and _normalized_server_output(first) == _normalized_server_output(second)
    )
    if not deterministic:
        failures = (*failures, "QUALIFICATION-DETERMINISM")
    # GS-004 is deliberately planner-only.  GS-003 and GS-006 produce
    # canonical Silence without requiring narrative Speech Presentation.
    presentation_expected = scenario_id in {
        SI_GOLDEN_001_ID,
        SI_GOLDEN_002_ID,
        SI_GOLDEN_005_ID,
    }
    presentation_failures = tuple(
        identifier
        for identifier in failures
        if "PRESENTATION" in identifier
        or "SIDEKICK" in identifier
        or "PRIMARY" in identifier
        or "DETERMINISM" in identifier
    )
    return GoldenScenarioQualification(
        scenario_id=scenario_id,
        session_verification="passed" if not failures else "failed",
        presentation_verification=(
            "not_applicable"
            if not presentation_expected
            else "passed" if not presentation_failures else "failed"
        ),
        deterministic=deterministic,
        overall_status="passed" if not failures else "failed",
        failure_identifiers=failures,
    )


async def _execute_once(
    hass: Any, scenario_id: str
) -> tuple[
    SIGolden001SessionCapture
    | SIGolden002SessionCapture
    | SIGolden003SessionCapture
    | RemainingGoldenSessionCapture
    | None,
    StructuralValidationResult,
]:
    """Reuse the canonical start -> drive -> capture -> validate -> stop flow."""
    started = await async_handle_developer_session_bootstrap(hass, scenario_id=scenario_id)
    if not started.get("success"):
        return None, StructuralValidationResult("failed")
    try:
        execution = await _driver_for(scenario_id)(hass)
        capture = await _capture_for(scenario_id)(hass)
        if not execution.get("success") or capture is None:
            return capture, StructuralValidationResult("failed")
        return capture, _validator_for(scenario_id)(capture)
    finally:
        await async_handle_developer_session_bootstrap(hass, action="stop", scenario_id=scenario_id)


def _driver_for(scenario_id: str):
    return {
        SI_GOLDEN_001_ID: async_execute_si_golden_001,
        SI_GOLDEN_002_ID: async_execute_si_golden_002,
        SI_GOLDEN_003_ID: async_execute_si_golden_003,
        SI_GOLDEN_004_ID: async_execute_si_golden_004,
        SI_GOLDEN_005_ID: async_execute_si_golden_005,
        SI_GOLDEN_006_ID: async_execute_si_golden_006,
    }.get(scenario_id, _invalid_driver)


def _capture_for(scenario_id: str):
    return {
        SI_GOLDEN_001_ID: async_capture_si_golden_001,
        SI_GOLDEN_002_ID: async_capture_si_golden_002,
        SI_GOLDEN_003_ID: async_capture_si_golden_003,
        SI_GOLDEN_004_ID: lambda hass: async_capture_remaining_golden(hass, SI_GOLDEN_004_ID),
        SI_GOLDEN_005_ID: lambda hass: async_capture_remaining_golden(hass, SI_GOLDEN_005_ID),
        SI_GOLDEN_006_ID: lambda hass: async_capture_remaining_golden(hass, SI_GOLDEN_006_ID),
    }.get(scenario_id, _invalid_capture)


def _validator_for(scenario_id: str):
    return {
        SI_GOLDEN_001_ID: validate_si_golden_001,
        SI_GOLDEN_002_ID: validate_si_golden_002,
        SI_GOLDEN_003_ID: validate_si_golden_003,
        SI_GOLDEN_004_ID: validate_remaining_golden,
        SI_GOLDEN_005_ID: validate_remaining_golden,
        SI_GOLDEN_006_ID: validate_remaining_golden,
    }.get(scenario_id, _invalid_validator)


async def _invalid_driver(_: Any) -> dict[str, Any]:
    return {"success": False, "status": "invalid_scenario"}


async def _invalid_capture(_: Any) -> None:
    return None


def _invalid_validator(_: Any) -> StructuralValidationResult:
    return StructuralValidationResult("invalid_capture")


def _normalized_server_output(
    capture: (
        SIGolden001SessionCapture
        | SIGolden002SessionCapture
        | SIGolden003SessionCapture
        | RemainingGoldenSessionCapture
    ),
) -> tuple[Any, ...]:
    """Compare stable server-owned semantic and Presentation evidence only."""
    moments = (
        (capture.first_realized_moment, capture.second_realized_moment)
        if isinstance(capture, SIGolden002SessionCapture)
        else capture.moments
        if isinstance(capture, RemainingGoldenSessionCapture)
        else (capture.realized_moment,)
    )
    return (
        capture.scenario_id,
        tuple((moment.moment_type, moment.knowledge_intent, moment.summary, moment.content) for moment in moments),
        tuple((item.item_type, item.moment_type) for item in capture.session_flow),
        tuple(item.event_type for item in capture.broadcast_publications),
        tuple(
            (
                presentation.source_moment_type,
                presentation.visibility,
                presentation.mode,
                tuple((segment.ordinal, segment.speaker_role, segment.text) for segment in presentation.segments),
            )
            for presentation in capture.presentations
        ),
    )
