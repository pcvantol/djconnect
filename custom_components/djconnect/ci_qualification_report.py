"""Bounded CI presentation for existing Golden Qualification reports."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any


CI_QUALIFICATION_REPORT_FORMAT_VERSION = 1

_TOP_LEVEL_FIELDS = frozenset(
    {
        "success",
        "status",
        "profile",
        "profile_version",
        "scenarios",
        "advisory_metrics",
    }
)
_SCENARIO_FIELDS = frozenset(
    {
        "scenario_id",
        "session_verification",
        "presentation_verification",
        "deterministic",
        "overall_status",
        "failure_identifiers",
    }
)
_METRIC_FIELDS = frozenset(
    {
        "metric_schema_version",
        "profile",
        "profile_version",
        "selected_scenarios",
        "executed_scenarios",
        "scenario_coverage",
        "session_verification_pass_rate",
        "determinism_rate",
        "applicable_presentation_verifications",
        "presentation_pass_rate",
        "failure_identifier_counts",
        "advisory_status",
    }
)
_STATUS_VALUES = frozenset({"passed", "failed", "not_applicable"})


class CIQualificationReportValidationError(ValueError):
    """Raised when a report cannot safely be published in CI."""


def validate_ci_qualification_report(report: Mapping[str, Any]) -> None:
    """Fail closed unless a bounded existing qualification payload is safe.

    This validates publication shape only. It never derives, changes, or
    authorizes the Foundation's qualification status.
    """
    _require_exact_fields(report, _TOP_LEVEL_FIELDS, "report", optional={"profile_version", "advisory_metrics"})
    _require_type(report.get("success"), bool, "report.success")
    _require_status(report.get("status"), "report.status")
    _require_type(report.get("profile"), str, "report.profile")
    if report["success"] != (report["status"] == "passed"):
        raise CIQualificationReportValidationError("report.success must match report.status")
    if "profile_version" in report:
        _require_type(report["profile_version"], int, "report.profile_version")
    scenarios = report.get("scenarios")
    _require_type(scenarios, list, "report.scenarios")
    for index, scenario in enumerate(scenarios):
        _validate_scenario(scenario, index)
    if "advisory_metrics" in report:
        _validate_metrics(report["advisory_metrics"], report)


def render_ci_qualification_report(report: Mapping[str, Any]) -> str:
    """Render one deterministic Markdown summary from approved evidence only."""
    validate_ci_qualification_report(report)
    lines = [
        "## Golden Qualification",
        "",
        f"- Report format version: `{CI_QUALIFICATION_REPORT_FORMAT_VERSION}`",
        f"- Profile: `{report['profile']}`",
    ]
    if "profile_version" in report:
        lines.append(f"- Profile version: `{report['profile_version']}`")
    lines.extend((f"- Overall qualification: **{report['status'].upper()}**", ""))
    lines.extend(
        (
            "| Scenario | Session | Presentation | Deterministic | Overall |",
            "| --- | --- | --- | --- | --- |",
        )
    )
    for scenario in report["scenarios"]:
        lines.append(
            "| {scenario_id} | {session} | {presentation} | {deterministic} | {overall} |".format(
                scenario_id=scenario["scenario_id"],
                session=scenario["session_verification"],
                presentation=scenario["presentation_verification"],
                deterministic="passed" if scenario["deterministic"] else "failed",
                overall=scenario["overall_status"],
            )
        )
    _append_failure_identifiers(lines, report["scenarios"])
    if "advisory_metrics" in report:
        _append_advisory_metrics(lines, report["advisory_metrics"])
    return "\n".join(lines) + "\n"


def _validate_scenario(value: Any, index: int) -> None:
    name = f"report.scenarios[{index}]"
    _require_mapping(value, name)
    _require_exact_fields(value, _SCENARIO_FIELDS, name)
    _require_type(value["scenario_id"], str, f"{name}.scenario_id")
    _require_status(value["session_verification"], f"{name}.session_verification")
    _require_status(value["presentation_verification"], f"{name}.presentation_verification")
    _require_type(value["deterministic"], bool, f"{name}.deterministic")
    _require_status(value["overall_status"], f"{name}.overall_status")
    identifiers = value["failure_identifiers"]
    _require_type(identifiers, tuple, f"{name}.failure_identifiers")
    for identifier in identifiers:
        _require_type(identifier, str, f"{name}.failure_identifiers[]")


def _validate_metrics(value: Any, report: Mapping[str, Any]) -> None:
    _require_mapping(value, "report.advisory_metrics")
    _require_exact_fields(value, _METRIC_FIELDS, "report.advisory_metrics")
    _require_type(value["metric_schema_version"], int, "report.advisory_metrics.metric_schema_version")
    if value["metric_schema_version"] != 1:
        raise CIQualificationReportValidationError("metrics schema version is not supported")
    _require_type(value["profile"], str, "report.advisory_metrics.profile")
    if value["profile"] != report["profile"]:
        raise CIQualificationReportValidationError("metrics profile must match report profile")
    if value["profile_version"] != report.get("profile_version"):
        raise CIQualificationReportValidationError("metrics profile version must match report")
    for field in (
        "selected_scenarios",
        "executed_scenarios",
        "applicable_presentation_verifications",
    ):
        _require_type(value[field], int, f"report.advisory_metrics.{field}")
    for field in (
        "scenario_coverage",
        "session_verification_pass_rate",
        "determinism_rate",
    ):
        _require_type(value[field], (int, float), f"report.advisory_metrics.{field}")
    if value["presentation_pass_rate"] is not None:
        _require_type(value["presentation_pass_rate"], (int, float), "report.advisory_metrics.presentation_pass_rate")
    _require_mapping(value["failure_identifier_counts"], "report.advisory_metrics.failure_identifier_counts")
    for identifier, count in value["failure_identifier_counts"].items():
        _require_type(identifier, str, "report.advisory_metrics.failure_identifier_counts key")
        _require_type(count, int, "report.advisory_metrics.failure_identifier_counts value")
    if value["advisory_status"] != "advisory":
        raise CIQualificationReportValidationError("metrics must remain advisory")


def _append_failure_identifiers(lines: list[str], scenarios: list[Mapping[str, Any]]) -> None:
    identifiers = tuple(
        identifier for scenario in scenarios for identifier in scenario["failure_identifiers"]
    )
    if identifiers:
        lines.extend(("", "### Invariant failure identifiers", ""))
        lines.extend(f"- `{identifier}`" for identifier in identifiers)


def _append_advisory_metrics(lines: list[str], metrics: Mapping[str, Any]) -> None:
    lines.extend(("", "### Advisory Intelligence Quality Metrics v1", ""))
    for field in (
        "selected_scenarios",
        "executed_scenarios",
        "scenario_coverage",
        "session_verification_pass_rate",
        "determinism_rate",
        "applicable_presentation_verifications",
        "presentation_pass_rate",
        "advisory_status",
    ):
        lines.append(f"- {field}: `{metrics[field]}`")
    counts = metrics["failure_identifier_counts"]
    if counts:
        lines.append("- failure_identifier_counts:")
        lines.extend(f"  - `{identifier}`: `{count}`" for identifier, count in counts.items())


def _require_exact_fields(
    value: Mapping[str, Any],
    allowed: frozenset[str],
    name: str,
    *,
    optional: set[str] | None = None,
) -> None:
    _require_mapping(value, name)
    fields = set(value)
    unknown = fields - allowed
    missing = (allowed - (optional or set())) - fields
    if unknown or missing:
        raise CIQualificationReportValidationError(
            f"{name} has prohibited or missing fields: unknown={sorted(unknown)}, missing={sorted(missing)}"
        )


def _require_mapping(value: Any, name: str) -> None:
    if not isinstance(value, Mapping):
        raise CIQualificationReportValidationError(f"{name} must be a mapping")


def _require_type(value: Any, expected: type | tuple[type, ...], name: str) -> None:
    if not isinstance(value, expected):
        raise CIQualificationReportValidationError(f"{name} has an invalid type")


def _require_status(value: Any, name: str) -> None:
    _require_type(value, str, name)
    if value not in _STATUS_VALUES:
        raise CIQualificationReportValidationError(f"{name} has an invalid status")
