"""Coverage validation and qualification."""

from __future__ import annotations

from pathlib import Path

from tools.verification.coverage.models import (
    CoverageMetric,
    CoverageParseResult,
    CoverageQualification,
    CoverageQualificationStatus,
    CoverageReport,
    CoverageStatus,
    CoverageValidation,
)


class CoverageValidator:
    def validate(
        self,
        parse_result: CoverageParseResult,
        *,
        path: Path,
        expected_commit_sha: str | None = None,
        seen_reports: set[str] | None = None,
    ) -> CoverageValidation:
        issues: list[str] = []
        warnings: list[str] = []
        if not path.exists():
            issues.append("missing_report")
        elif path.stat().st_size == 0:
            issues.append("empty_report")
        if seen_reports is not None:
            key = str(path.resolve())
            if key in seen_reports:
                issues.append("duplicate_report")
            seen_reports.add(key)
        if not parse_result.ok:
            issues.append(parse_result.error or "coverage_parser_failure")
            return CoverageValidation(False, tuple(sorted(set(issues))), tuple(warnings))
        report = parse_result.report
        if report is None:
            issues.append("coverage_parser_failure")
            return CoverageValidation(False, tuple(sorted(set(issues))), tuple(warnings))
        if expected_commit_sha and report.commit_sha and report.commit_sha != expected_commit_sha:
            issues.append("coverage_sha_mismatch")
        if not report.native_report_reference:
            issues.append("broken_provenance")
        if not report.covered_files and report.line_coverage.status != CoverageStatus.REPORTED:
            issues.append("empty_report")
        for name, metric in {
            "line": report.line_coverage,
            "branch": report.branch_coverage,
            "function": report.function_coverage,
            "method": report.method_coverage,
        }.items():
            issue = _metric_issue(name, metric)
            if issue:
                issues.append(issue)
        if report.excluded_files and len(report.excluded_files) > len(report.covered_files):
            warnings.append("unexpected_exclusions")
        return CoverageValidation(not issues, tuple(sorted(set(issues))), tuple(sorted(set(warnings))))


class CoverageQualifier:
    def qualify(self, validation: CoverageValidation, parse_result: CoverageParseResult) -> CoverageQualification:
        report = parse_result.report
        issues = set(validation.issues)
        if "missing_report" in issues:
            status = CoverageQualificationStatus.COVERAGE_NOT_AVAILABLE
        elif "unsupported_format" in issues:
            status = CoverageQualificationStatus.COVERAGE_UNSUPPORTED_FORMAT
        elif "empty_report" in issues:
            status = CoverageQualificationStatus.COVERAGE_EMPTY
        elif "coverage_sha_mismatch" in issues:
            status = CoverageQualificationStatus.COVERAGE_SHA_MISMATCH
        elif "stale_coverage" in issues:
            status = CoverageQualificationStatus.COVERAGE_STALE
        elif validation.ok:
            status = CoverageQualificationStatus.COVERAGE_VALID
        else:
            status = CoverageQualificationStatus.COVERAGE_INVALID
        return CoverageQualification(status=status, validation=validation, report=report, statistics=_statistics(report))


def _metric_issue(name: str, metric: CoverageMetric) -> str | None:
    if metric.status == CoverageStatus.NOT_REPORTED:
        return None
    if metric.total is not None and metric.total < 0:
        return f"invalid_{name}_coverage_total"
    if metric.covered is not None and metric.covered < 0:
        return f"invalid_{name}_coverage_covered"
    if metric.covered is not None and metric.total is not None and metric.covered > metric.total:
        return f"invalid_{name}_coverage_totals"
    if metric.percent is not None and not 0.0 <= metric.percent <= 100.0:
        return f"invalid_{name}_coverage_percent"
    return None


def _statistics(report: CoverageReport | None) -> dict[str, object]:
    if report is None:
        return {}
    return {
        "covered_file_count": len(report.covered_files),
        "excluded_file_count": len(report.excluded_files),
        "line_percent": report.line_coverage.percent,
        "branch_percent": report.branch_coverage.percent,
        "function_percent": report.function_coverage.percent,
        "method_percent": report.method_coverage.percent,
    }
