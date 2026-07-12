"""Normalized coverage runtime models."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any


class CoverageStatus(StrEnum):
    REPORTED = "REPORTED"
    NOT_REPORTED = "NOT_REPORTED"
    INVALID = "INVALID"


class CoverageQualificationStatus(StrEnum):
    COVERAGE_VALID = "COVERAGE_VALID"
    COVERAGE_INVALID = "COVERAGE_INVALID"
    COVERAGE_NOT_AVAILABLE = "COVERAGE_NOT_AVAILABLE"
    COVERAGE_STALE = "COVERAGE_STALE"
    COVERAGE_SHA_MISMATCH = "COVERAGE_SHA_MISMATCH"
    COVERAGE_UNSUPPORTED_FORMAT = "COVERAGE_UNSUPPORTED_FORMAT"
    COVERAGE_EMPTY = "COVERAGE_EMPTY"


@dataclass(frozen=True)
class CoverageMetric:
    covered: int | None = None
    total: int | None = None
    percent: float | None = None
    status: CoverageStatus = CoverageStatus.NOT_REPORTED

    @classmethod
    def not_reported(cls) -> "CoverageMetric":
        return cls()

    @classmethod
    def reported(cls, covered: int, total: int) -> "CoverageMetric":
        percent = round((covered / total * 100.0), 2) if total else 0.0
        return cls(covered=covered, total=total, percent=percent, status=CoverageStatus.REPORTED)


@dataclass(frozen=True)
class CoverageFile:
    path: str
    line: CoverageMetric = field(default_factory=CoverageMetric.not_reported)
    branch: CoverageMetric = field(default_factory=CoverageMetric.not_reported)
    function: CoverageMetric = field(default_factory=CoverageMetric.not_reported)
    method: CoverageMetric = field(default_factory=CoverageMetric.not_reported)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CoverageReport:
    repository: str
    commit_sha: str
    runtime_version: str
    coverage_producer: str
    coverage_format: str
    coverage_scope: str
    coverage_timestamp: str
    coverage_version: str
    parser_version: str
    line_coverage: CoverageMetric = field(default_factory=CoverageMetric.not_reported)
    branch_coverage: CoverageMetric = field(default_factory=CoverageMetric.not_reported)
    function_coverage: CoverageMetric = field(default_factory=CoverageMetric.not_reported)
    method_coverage: CoverageMetric = field(default_factory=CoverageMetric.not_reported)
    covered_files: tuple[CoverageFile, ...] = ()
    excluded_files: tuple[str, ...] = ()
    coverage_status: str = "parsed"
    coverage_metadata: dict[str, Any] = field(default_factory=dict)
    native_report_reference: str = ""


@dataclass(frozen=True)
class CoverageParseResult:
    ok: bool
    report: CoverageReport | None = None
    error: str = ""
    diagnostics: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CoverageValidation:
    ok: bool
    issues: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class CoverageQualification:
    status: CoverageQualificationStatus
    validation: CoverageValidation
    report: CoverageReport | None = None
    evidence_path: Path | None = None
    statistics: dict[str, Any] = field(default_factory=dict)
