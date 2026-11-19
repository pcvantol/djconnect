"""Coverage parser plugins."""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tools.verification.coverage.models import CoverageFile, CoverageMetric, CoverageParseResult, CoverageReport, CoverageStatus
from tools.verification.runtime import RUNTIME_VERSION

PARSER_VERSION = "1"


class CoverageParser(ABC):
    format_id: str

    @abstractmethod
    def parse(self, path: Path, *, repository: str, commit_sha: str, scope: str) -> CoverageParseResult:
        """Parse a native report into the canonical coverage model."""


class CoberturaParser(CoverageParser):
    format_id = "cobertura"

    def parse(self, path: Path, *, repository: str, commit_sha: str, scope: str) -> CoverageParseResult:
        try:
            root = ET.parse(path).getroot()
        except (ET.ParseError, OSError) as exc:
            return CoverageParseResult(False, error="malformed_report", diagnostics={"detail": str(exc)})
        files: list[CoverageFile] = []
        total_lines = covered_lines = 0
        total_branches = covered_branches = 0
        for class_el in root.findall(".//class"):
            filename = class_el.get("filename") or class_el.get("name") or "unknown"
            file_total = file_covered = 0
            file_branch_total = file_branch_covered = 0
            for line_el in class_el.findall("./lines/line"):
                file_total += 1
                hits = int(line_el.get("hits") or "0")
                if hits > 0:
                    file_covered += 1
                branch_text = line_el.get("condition-coverage") or ""
                if "%" in branch_text and "(" in branch_text and "/" in branch_text:
                    try:
                        fraction = branch_text.split("(", 1)[1].split(")", 1)[0]
                        covered, total = (int(item.strip()) for item in fraction.split("/", 1))
                        file_branch_covered += covered
                        file_branch_total += total
                    except ValueError:
                        pass
            total_lines += file_total
            covered_lines += file_covered
            total_branches += file_branch_total
            covered_branches += file_branch_covered
            files.append(
                CoverageFile(
                    path=filename,
                    line=CoverageMetric.reported(file_covered, file_total) if file_total else CoverageMetric.not_reported(),
                    branch=CoverageMetric.reported(file_branch_covered, file_branch_total) if file_branch_total else CoverageMetric.not_reported(),
                )
            )
        line_metric = CoverageMetric.reported(covered_lines, total_lines) if total_lines else _rate_metric(root, "line-rate")
        branch_metric = CoverageMetric.reported(covered_branches, total_branches) if total_branches else _rate_metric(root, "branch-rate")
        return CoverageParseResult(
            True,
            report=_report(
                path,
                repository,
                commit_sha,
                "cobertura",
                scope,
                line=line_metric,
                branch=branch_metric,
                files=tuple(files),
                metadata={"native_root": root.tag},
            ),
        )


class LCOVParser(CoverageParser):
    format_id = "lcov"

    def parse(self, path: Path, *, repository: str, commit_sha: str, scope: str) -> CoverageParseResult:
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError as exc:
            return CoverageParseResult(False, error="missing_report", diagnostics={"detail": str(exc)})
        files: list[CoverageFile] = []
        current: dict[str, Any] | None = None
        for raw in lines:
            if raw.startswith("SF:"):
                current = {"path": raw[3:], "lines": {}, "functions": {}, "branches": []}
            elif current is None:
                continue
            elif raw.startswith("DA:"):
                try:
                    line_no, hits = raw[3:].split(",", 1)
                    hit_count = int(hits)
                except ValueError:
                    return CoverageParseResult(False, error="malformed_report", diagnostics={"line": raw})
                if hit_count < 0:
                    return CoverageParseResult(False, error="invalid_coverage_metric", diagnostics={"line": raw})
                current["lines"][line_no] = hit_count
            elif raw.startswith("FNDA:"):
                try:
                    hits, name = raw[5:].split(",", 1)
                    hit_count = int(hits)
                except ValueError:
                    return CoverageParseResult(False, error="malformed_report", diagnostics={"line": raw})
                if hit_count < 0:
                    return CoverageParseResult(False, error="invalid_coverage_metric", diagnostics={"line": raw})
                current["functions"][name] = hit_count
            elif raw.startswith("BRDA:"):
                parts = raw[5:].split(",")
                taken = parts[3] if len(parts) > 3 else "-"
                try:
                    hit_count = 0 if taken == "-" else int(taken)
                except ValueError:
                    return CoverageParseResult(False, error="malformed_report", diagnostics={"line": raw})
                if hit_count < 0:
                    return CoverageParseResult(False, error="invalid_coverage_metric", diagnostics={"line": raw})
                current["branches"].append(hit_count)
            elif raw == "end_of_record":
                files.append(_lcov_file(current))
                current = None
        if current is not None:
            files.append(_lcov_file(current))
        line = _sum_metric(item.line for item in files)
        branch = _sum_metric(item.branch for item in files)
        function = _sum_metric(item.function for item in files)
        return CoverageParseResult(
            True,
            report=_report(path, repository, commit_sha, "lcov", scope, line=line, branch=branch, function=function, files=tuple(files)),
        )


class AppleXccovParser(CoverageParser):
    format_id = "apple-xccov"

    def parse(self, path: Path, *, repository: str, commit_sha: str, scope: str) -> CoverageParseResult:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            return CoverageParseResult(False, error="malformed_report", diagnostics={"detail": str(exc)})
        files: list[CoverageFile] = []
        for target in data.get("targets") or []:
            for file_item in target.get("files") or []:
                name = str(file_item.get("path") or file_item.get("name") or "unknown")
                covered = _int_or_none(file_item.get("coveredLines"))
                total = _int_or_none(file_item.get("executableLines") or file_item.get("lineCount"))
                metric = CoverageMetric.reported(covered, total) if covered is not None and total is not None else CoverageMetric.not_reported()
                files.append(CoverageFile(path=name, line=metric, metadata={"target": target.get("name")}))
        line = _sum_metric(item.line for item in files)
        return CoverageParseResult(
            True,
            report=_report(path, repository, commit_sha, "apple-xccov", scope, line=line, files=tuple(files), metadata={"producer": "xccov"}),
        )


def _lcov_file(current: dict[str, Any]) -> CoverageFile:
    line_hits = current["lines"]
    function_hits = current["functions"]
    branch_hits = current["branches"]
    return CoverageFile(
        path=str(current["path"]),
        line=CoverageMetric.reported(sum(1 for hits in line_hits.values() if hits > 0), len(line_hits)) if line_hits else CoverageMetric.not_reported(),
        branch=CoverageMetric.reported(sum(1 for hits in branch_hits if hits > 0), len(branch_hits)) if branch_hits else CoverageMetric.not_reported(),
        function=CoverageMetric.reported(sum(1 for hits in function_hits.values() if hits > 0), len(function_hits)) if function_hits else CoverageMetric.not_reported(),
    )


def _report(
    path: Path,
    repository: str,
    commit_sha: str,
    fmt: str,
    scope: str,
    *,
    line: CoverageMetric = CoverageMetric.not_reported(),
    branch: CoverageMetric = CoverageMetric.not_reported(),
    function: CoverageMetric = CoverageMetric.not_reported(),
    method: CoverageMetric = CoverageMetric.not_reported(),
    files: tuple[CoverageFile, ...] = (),
    metadata: dict[str, Any] | None = None,
) -> CoverageReport:
    return CoverageReport(
        repository=repository,
        commit_sha=commit_sha,
        runtime_version=RUNTIME_VERSION,
        coverage_producer=str((metadata or {}).get("producer") or fmt),
        coverage_format=fmt,
        coverage_scope=scope,
        coverage_timestamp=datetime.now(timezone.utc).isoformat(),
        coverage_version="1",
        parser_version=PARSER_VERSION,
        line_coverage=line,
        branch_coverage=branch,
        function_coverage=function,
        method_coverage=method,
        covered_files=files,
        coverage_metadata=metadata or {},
        native_report_reference=str(path),
    )


def _rate_metric(root: ET.Element, attr: str) -> CoverageMetric:
    value = root.get(attr)
    if value is None:
        return CoverageMetric.not_reported()
    try:
        percent = round(float(value) * 100.0, 2)
    except ValueError:
        return CoverageMetric.not_reported()
    return CoverageMetric(covered=None, total=None, percent=percent, status=CoverageStatus.REPORTED)


def _sum_metric(metrics) -> CoverageMetric:
    covered = total = 0
    reported = False
    for metric in metrics:
        if metric.status != "REPORTED" or metric.covered is None or metric.total is None:
            continue
        reported = True
        covered += metric.covered
        total += metric.total
    return CoverageMetric.reported(covered, total) if reported else CoverageMetric.not_reported()


def _int_or_none(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
