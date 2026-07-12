"""Coverage evidence persistence."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from tools.verification.coverage.models import CoverageQualification
from tools.verification.evidence import RunStore
from tools.verification.runtime import runtime_metadata


class CoverageEvidenceWriter:
    def __init__(self, evidence_root: Path) -> None:
        self.store = RunStore(evidence_root)

    def write(self, run_id: str, qualification: CoverageQualification) -> Path:
        payload = {
            "coverage_summary": asdict(qualification.report) if qualification.report else None,
            "coverage_validation": asdict(qualification.validation),
            "coverage_qualification": qualification.status.value,
            "coverage_statistics": qualification.statistics,
            "coverage_metadata": {
                "verification_runtime": runtime_metadata(),
                "parser_version": qualification.report.parser_version if qualification.report else None,
                "native_report_reference": qualification.report.native_report_reference if qualification.report else None,
            },
        }
        path = self.store.write_json(run_id, "coverage/coverage-summary.json", payload)
        self.store.write_index(run_id)
        return path
