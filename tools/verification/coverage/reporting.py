"""Coverage report renderers."""

from __future__ import annotations

import json
from dataclasses import asdict

from tools.verification.coverage.investigator import CoverageInvestigation, coverage_investigation_to_dict
from tools.verification.coverage.models import CoverageQualification, CoverageStatus


class CoverageJSONReporter:
    def render(self, qualification: CoverageQualification, investigation: CoverageInvestigation | None = None) -> str:
        return json.dumps(_payload(qualification, investigation), indent=2, sort_keys=True)


class CoverageMarkdownReporter:
    def render(self, qualification: CoverageQualification, investigation: CoverageInvestigation | None = None) -> str:
        report = qualification.report
        lines = [
            "# Verification Runtime Coverage Report",
            "",
            f"Qualification: {qualification.status.value}",
            f"Validation: {'PASS' if qualification.validation.ok else 'FAIL'}",
        ]
        if report:
            lines.extend(
                [
                    f"Repository: {report.repository}",
                    f"Commit SHA: {report.commit_sha}",
                    f"Format: {report.coverage_format}",
                    f"Runtime version: {report.runtime_version}",
                    "",
                    "## Summary",
                    "",
                    "| Metric | Status | Covered | Total | Percent |",
                    "| --- | --- | --- | --- | --- |",
                    _metric_row("Line", report.line_coverage),
                    _metric_row("Branch", report.branch_coverage),
                    _metric_row("Function", report.function_coverage),
                    _metric_row("Method", report.method_coverage),
                ]
            )
        if qualification.validation.issues:
            lines.extend(["", "## Validation Issues", ""])
            lines.extend(f"- {issue}" for issue in qualification.validation.issues)
        if investigation:
            lines.extend(["", "## Investigation", "", f"- Classification: {investigation.classification}", f"- Action: {investigation.recommended_action}"])
        return "\n".join(lines) + "\n"


def _payload(qualification: CoverageQualification, investigation: CoverageInvestigation | None) -> dict:
    return {
        "coverage_summary": asdict(qualification.report) if qualification.report else None,
        "coverage_validation": asdict(qualification.validation),
        "coverage_qualification": qualification.status.value,
        "coverage_statistics": qualification.statistics,
        "coverage_investigation": coverage_investigation_to_dict(investigation) if investigation else None,
    }


def _metric_row(name: str, metric) -> str:
    covered = "NOT_REPORTED" if metric.status == CoverageStatus.NOT_REPORTED else str(metric.covered)
    total = "NOT_REPORTED" if metric.status == CoverageStatus.NOT_REPORTED else str(metric.total)
    percent = "NOT_REPORTED" if metric.percent is None else f"{metric.percent:.2f}"
    return f"| {name} | {metric.status.value} | {covered} | {total} | {percent} |"
