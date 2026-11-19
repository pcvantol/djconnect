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
GOLDEN_REGRESSION_PROFILE = "golden_regression"
GOLDEN_REGRESSION_PROFILE_VERSION = 1
ADVISORY_QUALITY_METRICS_SCHEMA_VERSION = 1
EXECUTABLE_GOLDEN_SCENARIOS = (
    SI_GOLDEN_001_ID,
    SI_GOLDEN_002_ID,
    SI_GOLDEN_003_ID,
    SI_GOLDEN_004_ID,
    SI_GOLDEN_005_ID,
    SI_GOLDEN_006_ID,
)
GOLDEN_SMOKE_SCENARIOS = (SI_GOLDEN_001_ID,)
# Regression is deliberately the complete currently approved Session
# Intelligence contract, in the catalogue's canonical order.
GOLDEN_REGRESSION_SCENARIOS = EXECUTABLE_GOLDEN_SCENARIOS


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
    profile_version: int | None = None


async def async_run_golden_qualification(
    hass: Any,
    scenario_ids: tuple[str, ...] = EXECUTABLE_GOLDEN_SCENARIOS,
    *,
    observe_browser_e2e: bool = False,
) -> GoldenQualificationReport:
    """Execute each approved scenario twice through the existing Runtime path.

    Bootstrap, Driver, Capture and Validator remain their existing owners. This
    coordinator only composes them, stops every successfully started Session,
    and compares normalized immutable server-owned output.  An explicitly
    requested Browser E2E observer may subscribe to the existing renderer-safe
    Broadcast view, but cannot alter Capture, validation or this report.
    """
    normalized = tuple(str(item).strip().upper() for item in scenario_ids)
    results_list: list[GoldenScenarioQualification] = []
    for scenario_id in normalized:
        results_list.append(
            await _qualify_scenario(hass, scenario_id, observe_browser_e2e=observe_browser_e2e)
        )
    results = tuple(results_list)
    return GoldenQualificationReport(
        profile=GOLDEN_QUALIFICATION_PROFILE,
        scenarios=results,
        overall_status="passed" if results and all(item.overall_status == "passed" for item in results) else "failed",
    )


def advisory_quality_metrics(report: GoldenQualificationReport) -> dict[str, Any]:
    """Project bounded, read-only advisory metrics from one immutable report.

    This is deliberately a report projection: it neither participates in
    qualification nor retains any evidence after the caller has received it.
    """
    selected_scenarios = len(report.scenarios)
    executed_scenarios = selected_scenarios
    session_passes = sum(
        item.session_verification == "passed" for item in report.scenarios
    )
    deterministic_scenarios = sum(item.deterministic for item in report.scenarios)
    applicable_presentations = tuple(
        item
        for item in report.scenarios
        if item.presentation_verification != "not_applicable"
    )
    presentation_passes = sum(
        item.presentation_verification == "passed"
        for item in applicable_presentations
    )
    failure_identifier_counts: dict[str, int] = {}
    for item in report.scenarios:
        for identifier in item.failure_identifiers:
            failure_identifier_counts[identifier] = (
                failure_identifier_counts.get(identifier, 0) + 1
            )

    return {
        "metric_schema_version": ADVISORY_QUALITY_METRICS_SCHEMA_VERSION,
        "profile": report.profile,
        "profile_version": report.profile_version,
        "selected_scenarios": selected_scenarios,
        "executed_scenarios": executed_scenarios,
        "scenario_coverage": (
            executed_scenarios / selected_scenarios if selected_scenarios else 0.0
        ),
        "session_verification_pass_rate": (
            session_passes / selected_scenarios if selected_scenarios else 0.0
        ),
        "determinism_rate": (
            deterministic_scenarios / selected_scenarios if selected_scenarios else 0.0
        ),
        "applicable_presentation_verifications": len(applicable_presentations),
        "presentation_pass_rate": (
            presentation_passes / len(applicable_presentations)
            if applicable_presentations
            else None
        ),
        "failure_identifier_counts": dict(sorted(failure_identifier_counts.items())),
        "advisory_status": "advisory",
    }


def _bounded_report_payload(
    report: GoldenQualificationReport,
    *,
    include_advisory_metrics: bool = False,
) -> dict[str, Any]:
    """Return the existing bounded report, optionally with its advisory view."""
    payload = {
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
    if report.profile_version is not None:
        payload["profile_version"] = report.profile_version
    if include_advisory_metrics:
        payload["advisory_metrics"] = advisory_quality_metrics(report)
    return payload


async def async_handle_golden_qualification(
    hass: Any, *, include_advisory_metrics: bool = False
) -> dict[str, Any]:
    """Expose bounded qualification metadata without exposing Runtime internals."""
    report = await async_run_golden_qualification(hass)
    return _bounded_report_payload(
        report, include_advisory_metrics=include_advisory_metrics
    )


async def async_run_golden_smoke(
    hass: Any, *, observe_browser_e2e: bool = False
) -> GoldenQualificationReport:
    """Run the smallest approved selection through Golden Qualification."""
    foundation_report = await async_run_golden_qualification(
        hass,
        scenario_ids=GOLDEN_SMOKE_SCENARIOS,
        **({"observe_browser_e2e": True} if observe_browser_e2e else {}),
    )
    return GoldenQualificationReport(
        profile=GOLDEN_SMOKE_PROFILE,
        scenarios=foundation_report.scenarios,
        overall_status=foundation_report.overall_status,
    )


async def async_handle_golden_smoke(
    hass: Any, *, include_advisory_metrics: bool = False
) -> dict[str, Any]:
    """Expose the bounded Golden Smoke report from the canonical path."""
    report = await async_run_golden_smoke(hass)
    return _bounded_report_payload(
        report, include_advisory_metrics=include_advisory_metrics
    )


async def async_run_golden_regression(
    hass: Any, *, observe_browser_e2e: bool = False
) -> GoldenQualificationReport:
    """Run the complete approved contract through Golden Qualification only."""
    foundation_report = await async_run_golden_qualification(
        hass,
        scenario_ids=GOLDEN_REGRESSION_SCENARIOS,
        **({"observe_browser_e2e": True} if observe_browser_e2e else {}),
    )
    return GoldenQualificationReport(
        profile=GOLDEN_REGRESSION_PROFILE,
        scenarios=foundation_report.scenarios,
        overall_status=foundation_report.overall_status,
        profile_version=GOLDEN_REGRESSION_PROFILE_VERSION,
    )


async def async_handle_golden_regression(
    hass: Any, *, include_advisory_metrics: bool = False
) -> dict[str, Any]:
    """Expose the bounded Golden Regression report from the canonical path."""
    report = await async_run_golden_regression(hass)
    return _bounded_report_payload(
        report, include_advisory_metrics=include_advisory_metrics
    )


async def _qualify_scenario(
    hass: Any, scenario_id: str, *, observe_browser_e2e: bool = False
) -> GoldenScenarioQualification:
    """Run one scenario twice and compare only immutable observable evidence."""
    first, first_validation = await _execute_once(
        hass, scenario_id, observe_browser_e2e=observe_browser_e2e
    )
    second, second_validation = await _execute_once(
        hass, scenario_id, observe_browser_e2e=observe_browser_e2e
    )
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
    hass: Any, scenario_id: str, *, observe_browser_e2e: bool = False
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
    observer = None
    try:
        if observe_browser_e2e:
            from .universal_receiver_browser_e2e import UniversalReceiverBrowserObserver

            observer = UniversalReceiverBrowserObserver(hass, scenario_id, started["session_id"])
            await observer.async_attach()
        execution = await _driver_for(scenario_id)(hass)
        capture = await _capture_for(scenario_id)(hass)
        if not execution.get("success") or capture is None:
            return capture, StructuralValidationResult("failed")
        return capture, _validator_for(scenario_id)(capture)
    finally:
        await async_handle_developer_session_bootstrap(hass, action="stop", scenario_id=scenario_id)
        if observer is not None:
            await observer.async_assert_and_release()


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
