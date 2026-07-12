"""Tests for Verification Runtime coverage capability."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.verification.cli import build_parser, main
from tools.verification.coverage import CoveragePipeline
from tools.verification.coverage.investigator import CoverageInvestigator
from tools.verification.coverage.models import CoverageQualificationStatus, CoverageStatus
from tools.verification.coverage.registry import default_registry
from tools.verification.coverage.validation import CoverageValidator
from tools.verification.docker_release import _tags
from tools.verification.runtime import runtime_metadata


class CoverageRuntimeTests(unittest.TestCase):
    def test_runtime_metadata_advertises_coverage_capability(self) -> None:
        metadata = runtime_metadata()

        self.assertEqual("1.1.0", metadata["version"])
        self.assertEqual("Verification Runtime", metadata["product"])
        self.assertIn("coverage", metadata["capabilities"])

    def test_parser_registry_supports_initial_formats(self) -> None:
        self.assertEqual(("apple-xccov", "cobertura", "lcov"), default_registry().available_formats())

    def test_cobertura_ingestion_normalizes_line_and_branch_coverage(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            report = Path(temp_dir) / "coverage.xml"
            report.write_text(
                """<?xml version="1.0" ?>
<coverage line-rate="0.5" branch-rate="0.5">
  <packages><package><classes>
    <class filename="src/a.py"><lines>
      <line number="1" hits="1" branch="false" />
      <line number="2" hits="0" branch="true" condition-coverage="50% (1/2)" />
    </lines></class>
  </classes></package></packages>
</coverage>
""",
                encoding="utf-8",
            )

            qualification = CoveragePipeline().ingest(
                report,
                coverage_format="cobertura",
                repository="pcvantol/djconnect",
                commit_sha="abc123",
                expected_commit_sha="abc123",
            )

        self.assertEqual(CoverageQualificationStatus.COVERAGE_VALID, qualification.status)
        self.assertEqual(50.0, qualification.report.line_coverage.percent)
        self.assertEqual(50.0, qualification.report.branch_coverage.percent)
        self.assertEqual("cobertura", qualification.report.coverage_format)

    def test_lcov_ingestion_keeps_missing_method_metric_not_reported(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            report = Path(temp_dir) / "lcov.info"
            report.write_text(
                "\n".join(
                    [
                        "TN:",
                        "SF:src/app.ts",
                        "DA:1,1",
                        "DA:2,0",
                        "FN:1,run",
                        "FNDA:1,run",
                        "BRDA:1,0,0,1",
                        "BRDA:2,0,1,-",
                        "end_of_record",
                    ]
                ),
                encoding="utf-8",
            )

            qualification = CoveragePipeline().ingest(report, coverage_format="lcov", repository="repo", commit_sha="abc")

        self.assertEqual(CoverageQualificationStatus.COVERAGE_VALID, qualification.status)
        self.assertEqual(50.0, qualification.report.line_coverage.percent)
        self.assertEqual(50.0, qualification.report.branch_coverage.percent)
        self.assertEqual(100.0, qualification.report.function_coverage.percent)
        self.assertEqual(CoverageStatus.NOT_REPORTED, qualification.report.method_coverage.status)

    def test_apple_xccov_json_ingestion(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            report = Path(temp_dir) / "xccov.json"
            report.write_text(
                json.dumps(
                    {
                        "targets": [
                            {
                                "name": "DJConnect",
                                "files": [
                                    {"path": "App.swift", "coveredLines": 8, "executableLines": 10},
                                    {"path": "Player.swift", "coveredLines": 5, "executableLines": 5},
                                ],
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            qualification = CoveragePipeline().ingest(report, coverage_format="apple-xccov", repository="repo", commit_sha="abc")

        self.assertEqual(CoverageQualificationStatus.COVERAGE_VALID, qualification.status)
        self.assertEqual(86.67, qualification.report.line_coverage.percent)
        self.assertEqual("apple-xccov", qualification.report.coverage_format)

    def test_validation_fails_closed_for_missing_unsupported_empty_and_sha_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            missing = root / "missing.xml"
            missing_result = CoveragePipeline().ingest(missing, coverage_format="cobertura", repository="repo", commit_sha="abc")
            self.assertEqual(CoverageQualificationStatus.COVERAGE_NOT_AVAILABLE, missing_result.status)

            empty = root / "empty.info"
            empty.write_text("", encoding="utf-8")
            empty_result = CoveragePipeline().ingest(empty, coverage_format="lcov", repository="repo", commit_sha="abc")
            self.assertEqual(CoverageQualificationStatus.COVERAGE_EMPTY, empty_result.status)

            unsupported = default_registry().parse(empty, coverage_format="istanbul", repository="repo", commit_sha="abc", scope="repository")
            validation = CoverageValidator().validate(unsupported, path=empty)
            self.assertIn("unsupported_format", validation.issues)

            report = root / "lcov.info"
            report.write_text("SF:a.py\nDA:1,1\nend_of_record\n", encoding="utf-8")
            mismatch = CoveragePipeline().ingest(
                report,
                coverage_format="lcov",
                repository="repo",
                commit_sha="old",
                expected_commit_sha="new",
            )
            self.assertEqual(CoverageQualificationStatus.COVERAGE_SHA_MISMATCH, mismatch.status)

    def test_coverage_evidence_and_investigator(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            report = root / "lcov.info"
            report.write_text("SF:a.py\nDA:1,0\nend_of_record\n", encoding="utf-8")
            pipeline = CoveragePipeline()
            qualification = pipeline.ingest(report, coverage_format="lcov", repository="repo", commit_sha="abc")
            evidence_path = pipeline.write_evidence(root / "evidence", "run-coverage", qualification)
            investigation = CoverageInvestigator().investigate(qualification)

            payload = json.loads(evidence_path.read_text(encoding="utf-8"))

        self.assertEqual("COVERAGE_VALID", payload["coverage_qualification"])
        self.assertEqual("coverage_valid", investigation.classification)

    def test_cli_coverage_ingest_and_docker_tags(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["coverage", "ingest", "coverage.xml", "--format", "cobertura"])

        self.assertEqual("coverage", args.command)
        self.assertIn("image:1.1", _tags("image", "abcdef1234567890"))
        self.assertIn("image:latest", _tags("image", "abcdef1234567890"))

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            report = root / "lcov.info"
            report.write_text("SF:a.py\nDA:1,1\nend_of_record\n", encoding="utf-8")

            self.assertEqual(0, main(["--root", str(root), "coverage", "ingest", str(report), "--format", "lcov"]))


if __name__ == "__main__":
    unittest.main()
