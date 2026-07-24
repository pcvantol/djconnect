"""Focused verification for bounded advisory CI qualification reports."""
from __future__ import annotations

import asyncio
import copy
import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


def _load_reporter():
    spec = importlib.util.spec_from_file_location(
        "ci_qualification_report_test", ROOT / "custom_components" / "djconnect" / "ci_qualification_report.py"
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _load_runner():
    spec = importlib.util.spec_from_file_location(
        "run_golden_ci_qualification_test",
        ROOT / "tools" / "verification" / "run_golden_ci_qualification.py",
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class CIQualificationReportTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.reporter = _load_reporter()

    def _report(self, *, status: str = "passed") -> dict[str, object]:
        return {
            "success": status == "passed",
            "status": status,
            "profile": "golden_regression",
            "profile_version": 1,
            "scenarios": [
                {
                    "scenario_id": "SI-GOLDEN-001",
                    "session_verification": "passed",
                    "presentation_verification": "passed",
                    "deterministic": True,
                    "overall_status": status,
                    "failure_identifiers": (),
                }
            ],
            "advisory_metrics": {
                "metric_schema_version": 1,
                "profile": "golden_regression",
                "profile_version": 1,
                "selected_scenarios": 1,
                "executed_scenarios": 1,
                "scenario_coverage": 1.0,
                "session_verification_pass_rate": 1.0,
                "determinism_rate": 1.0,
                "applicable_presentation_verifications": 1,
                "presentation_pass_rate": 1.0,
                "failure_identifier_counts": {},
                "advisory_status": "advisory",
            },
        }

    def test_markdown_is_deterministic_and_does_not_change_qualification(self) -> None:
        report = self._report()
        original = copy.deepcopy(report)

        first = self.reporter.render_ci_qualification_report(report)
        second = self.reporter.render_ci_qualification_report(report)

        self.assertEqual(first, second)
        self.assertEqual(report, original)
        self.assertIn("**PASSED**", first)
        self.assertIn("golden_regression", first)
        self.assertIn("Advisory Intelligence Quality Metrics v1", first)

    def test_existing_failed_status_is_rendered_without_reinterpretation(self) -> None:
        report = self._report(status="failed")
        report["scenarios"][0]["session_verification"] = "failed"  # type: ignore[index]
        report["scenarios"][0]["deterministic"] = False  # type: ignore[index]
        report["scenarios"][0]["failure_identifiers"] = ("SI-FAIL",)  # type: ignore[index]
        report["advisory_metrics"]["session_verification_pass_rate"] = 0.0  # type: ignore[index]
        report["advisory_metrics"]["determinism_rate"] = 0.0  # type: ignore[index]
        report["advisory_metrics"]["failure_identifier_counts"] = {"SI-FAIL": 1}  # type: ignore[index]

        markdown = self.reporter.render_ci_qualification_report(report)

        self.assertIn("**FAILED**", markdown)
        self.assertIn("`SI-FAIL`", markdown)

    def test_prohibited_or_unknown_fields_fail_closed(self) -> None:
        report = self._report()
        report["runtime"] = {"secret": "must-not-publish"}

        with self.assertRaises(self.reporter.CIQualificationReportValidationError):
            self.reporter.render_ci_qualification_report(report)

    def test_prohibited_nested_fields_fail_closed(self) -> None:
        report = self._report()
        report["scenarios"][0]["prompt"] = "must-not-publish"  # type: ignore[index]

        with self.assertRaises(self.reporter.CIQualificationReportValidationError):
            self.reporter.render_ci_qualification_report(report)

    def test_unknown_metrics_schema_fails_closed(self) -> None:
        report = self._report()
        report["advisory_metrics"]["metric_schema_version"] = 2  # type: ignore[index]

        with self.assertRaises(self.reporter.CIQualificationReportValidationError):
            self.reporter.render_ci_qualification_report(report)

    def test_workflow_is_advisory_and_cleans_up_on_pass_and_fail(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "golden-qualification-ci.yml").read_text()

        self.assertIn("continue-on-error: true", workflow)
        self.assertIn("github.event_name == 'pull_request'", workflow)
        self.assertIn("github.event_name != 'pull_request'", workflow)
        self.assertEqual(workflow.count("if: ${{ always() }}"), 2)
        self.assertEqual(workflow.count("rm -f"), 2)
        self.assertNotIn("upload-artifact", workflow)

    def test_ci_runner_executes_the_existing_smoke_and_regression_profiles(self) -> None:
        runner = _load_runner()

        smoke = asyncio.run(runner.async_run_profile("golden_smoke"))
        regression = asyncio.run(runner.async_run_profile("golden_regression"))

        self.assertEqual(smoke["profile"], "golden_smoke")
        self.assertEqual(
            tuple(item["scenario_id"] for item in smoke["scenarios"]),
            ("SI-GOLDEN-001",),
        )
        self.assertEqual(regression["profile"], "golden_regression")
        self.assertEqual(len(regression["scenarios"]), 6)
        self.assertTrue(smoke["success"])
        self.assertTrue(regression["success"])

    def test_browser_observation_keeps_the_existing_bounded_report(self) -> None:
        runner = _load_runner()

        ordinary = asyncio.run(runner.async_run_profile("golden_smoke"))
        observed = asyncio.run(
            runner.async_run_profile("golden_smoke", observe_browser_e2e=True)
        )

        self.assertEqual(observed, ordinary)
        self.assertNotIn("browser", observed)
        self.assertNotIn("token", observed)

    def test_workflow_observes_profiles_without_publishing_browser_evidence(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "golden-qualification-ci.yml").read_text()

        self.assertEqual(workflow.count("--observe-browser-e2e"), 2)
        self.assertNotIn("browser report", workflow.lower())
        self.assertNotIn("upload-artifact", workflow)


if __name__ == "__main__":
    unittest.main()
