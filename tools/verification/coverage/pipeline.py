"""Coverage ingestion pipeline."""

from __future__ import annotations

from pathlib import Path

from tools.verification.coverage.evidence import CoverageEvidenceWriter
from tools.verification.coverage.investigator import CoverageInvestigator
from tools.verification.coverage.models import CoverageQualification
from tools.verification.coverage.registry import CoverageParserRegistry, default_registry
from tools.verification.coverage.validation import CoverageQualifier, CoverageValidator


class CoveragePipeline:
    def __init__(self, registry: CoverageParserRegistry | None = None) -> None:
        self.registry = registry or default_registry()
        self.validator = CoverageValidator()
        self.qualifier = CoverageQualifier()
        self.investigator = CoverageInvestigator()

    def ingest(
        self,
        path: Path,
        *,
        coverage_format: str,
        repository: str,
        commit_sha: str,
        scope: str = "repository",
        expected_commit_sha: str | None = None,
    ) -> CoverageQualification:
        parse_result = self.registry.parse(path, coverage_format=coverage_format, repository=repository, commit_sha=commit_sha, scope=scope)
        validation = self.validator.validate(parse_result, path=path, expected_commit_sha=expected_commit_sha)
        return self.qualifier.qualify(validation, parse_result)

    def write_evidence(self, evidence_root: Path, run_id: str, qualification: CoverageQualification) -> Path:
        return CoverageEvidenceWriter(evidence_root).write(run_id, qualification)
