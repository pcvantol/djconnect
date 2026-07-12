"""Coverage-specific investigator."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any

from tools.verification.coverage.models import CoverageQualification, CoverageQualificationStatus


@dataclass(frozen=True)
class CoverageInvestigation:
    classification: str
    confidence: float
    blocking_status: str
    recommended_action: str
    evidence_references: tuple[str, ...]
    trend_ready: bool = True


class CoverageInvestigator:
    def investigate(self, qualification: CoverageQualification) -> CoverageInvestigation:
        issues = set(qualification.validation.issues)
        warnings = set(qualification.validation.warnings)
        status = qualification.status
        if status == CoverageQualificationStatus.COVERAGE_VALID and not warnings:
            return CoverageInvestigation("coverage_valid", 0.95, "non_blocking", "Use coverage as qualification evidence.", ("coverage/coverage-summary.json",))
        if "missing_report" in issues:
            return CoverageInvestigation("missing_reports", 0.95, "blocking", "Configure the repository to produce a native coverage report before ingestion.", ("coverage/coverage-summary.json",))
        if "coverage_sha_mismatch" in issues:
            return CoverageInvestigation("coverage_sha_mismatch", 0.95, "blocking", "Regenerate coverage for the exact commit under verification.", ("coverage/coverage-summary.json",))
        if "unexpected_exclusions" in warnings:
            return CoverageInvestigation("unexpected_exclusions", 0.75, "needs_human_review", "Review excluded files and confirm they are policy-approved.", ("coverage/coverage-summary.json",))
        if any(issue.startswith("invalid_") for issue in issues):
            return CoverageInvestigation("coverage_corruption", 0.85, "blocking", "Inspect the native coverage producer and parser output.", ("coverage/coverage-summary.json",))
        if status == CoverageQualificationStatus.COVERAGE_EMPTY:
            return CoverageInvestigation("coverage_anomaly", 0.8, "blocking", "Regenerate coverage; the report contains no usable coverage data.", ("coverage/coverage-summary.json",))
        if status == CoverageQualificationStatus.COVERAGE_UNSUPPORTED_FORMAT:
            return CoverageInvestigation("unsupported_coverage_format", 0.9, "blocking", "Add a parser plugin or emit a supported coverage format.", ("coverage/coverage-summary.json",))
        return CoverageInvestigation("coverage_anomaly", 0.5, "needs_human_review", "Inspect coverage evidence manually.", ("coverage/coverage-summary.json",))


def coverage_investigation_to_dict(investigation: CoverageInvestigation) -> dict[str, Any]:
    return asdict(investigation)
