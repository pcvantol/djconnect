"""Tests for the DJConnect Verification Harness scaffold."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.verification.cli import build_parser, main
from tools.verification.config import load_config
from tools.verification.models import ResultState, ScenarioResult
from tools.verification.reporters import JSONReporter, MarkdownReporter, SummaryReporter
from tools.verification.results import ResultManager
from tools.verification.scenarios import ScenarioLoader, ScenarioValidator


class VerificationHarnessTests(unittest.TestCase):
    def test_config_defaults_point_at_canonical_scenarios(self) -> None:
        root = Path(__file__).resolve().parents[2]

        config = load_config(root)

        self.assertIn(root / "verification/scenarios", config.scenario_paths)
        self.assertEqual(config.evidence_dir, root / "artifacts/verification/evidence")

    def test_scenario_loader_reads_existing_catalog(self) -> None:
        root = Path(__file__).resolve().parents[2]
        scenarios = ScenarioLoader(load_config(root)).load()

        self.assertGreaterEqual(len(scenarios), 1)
        self.assertIn("PROFILE-001", {scenario.id for scenario in scenarios})

    def test_validator_accepts_catalog_example_shape(self) -> None:
        root = Path(__file__).resolve().parents[2]
        scenario = next(
            scenario for scenario in ScenarioLoader(load_config(root)).load() if scenario.id == "PROFILE-001"
        )

        issues = ScenarioValidator().validate(scenario)

        self.assertEqual([], [issue for issue in issues if issue.severity == "error"])

    def test_validator_rejects_invalid_scenario_id(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            scenario_dir = root / "scenarios"
            scenario_dir.mkdir()
            scenario_file = scenario_dir / "bad.json"
            scenario_file.write_text(
                json.dumps(
                    {
                        "id": "bad",
                        "title": "Bad",
                        "description": "Bad",
                        "required_components": ["HA"],
                    }
                ),
                encoding="utf-8",
            )
            config_file = root / "config.json"
            config_file.write_text(json.dumps({"scenario_paths": ["scenarios"]}), encoding="utf-8")

            scenario = ScenarioLoader(load_config(root, config_file)).load()[0]
            issues = ScenarioValidator().validate(scenario)

            self.assertTrue(any("Invalid scenario id" in issue.message for issue in issues))
            self.assertTrue(any("Missing required field" in issue.message for issue in issues))

    def test_cli_parses_registered_commands_and_filters(self) -> None:
        args = build_parser().parse_args(["dry-run", "--scenario-id", "PROFILE-001", "--tag", "profile"])

        self.assertEqual(args.command, "dry-run")
        self.assertEqual(args.scenario_id, ["PROFILE-001"])
        self.assertEqual(args.tag, ["profile"])

    def test_result_generation_and_reporters(self) -> None:
        result = ResultManager().aggregate(
            "unit",
            [
                ScenarioResult("PROFILE-001", ResultState.PASS, "ok"),
                ScenarioResult("ASKDJ-001", ResultState.WARNING, "caveat"),
            ],
        )

        self.assertEqual(ResultState.WARNING, result.state)
        self.assertIn("PROFILE-001", MarkdownReporter().render(result))
        rendered = json.loads(JSONReporter().render(result))
        self.assertEqual("WARNING", rendered["state"])
        self.assertEqual(2, rendered["execution_summary"]["executed_scenarios"])
        self.assertIn("2 of 2 tests executed, status WARNING", SummaryReporter().render(result))

    def test_cli_validate_catalog(self) -> None:
        root = Path(__file__).resolve().parents[2]

        exit_code = main(["--root", str(root), "validate"])

        self.assertEqual(0, exit_code)


if __name__ == "__main__":
    unittest.main()
