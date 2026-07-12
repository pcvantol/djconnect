"""Tests for the canonical Verification Planning Engine."""

from __future__ import annotations

import io
import json
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from tools.verification.cli import main
from tools.verification.config import load_config
from tools.verification.planning import PlanningStrategyRegistry, VerificationPlanningEngine
from tools.verification.scenarios import ScenarioLoader


class VerificationPlanningEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(__file__).resolve().parents[2]
        self.config = load_config(self.root, overrides={"scenario_paths": ["verification/scenarios"]})
        self.scenarios = ScenarioLoader(self.config).load()

    def test_strategy_registry_contains_required_strategies(self) -> None:
        strategies = {strategy.id: strategy for strategy in PlanningStrategyRegistry().all()}

        for strategy_id in (
            "minimal",
            "smoke",
            "regression",
            "release",
            "security",
            "localization",
            "accessibility",
            "performance",
            "hardware",
            "nightly",
            "research",
        ):
            self.assertIn(strategy_id, strategies)
        self.assertEqual("release_candidate", strategies["release"].default_policy)

    def test_smoke_plan_expands_profile_scenario_without_execution(self) -> None:
        scenario = [scenario for scenario in self.scenarios if scenario.id == "PROFILE-001"]

        plan = VerificationPlanningEngine(self.config).plan(scenario, strategy_id="smoke", policy_id="smoke")

        self.assertEqual("smoke", plan.strategy)
        self.assertEqual("smoke", plan.policy)
        self.assertEqual(1, plan.coverage.case_count)
        case = plan.cases[0]
        self.assertEqual("PROFILE-001", case.scenario_id)
        self.assertEqual("functional", case.mode)
        self.assertEqual("Smoke Test Profile", case.matrix_profile)
        self.assertEqual("smoke", case.data_profile)
        self.assertEqual("home_assistant", case.adapter)
        self.assertFalse(plan.metadata["executes"])
        self.assertFalse(plan.metadata["calls_adapters"])

    def test_smoke_plan_selects_first_apple_runtime_scenario(self) -> None:
        plan = VerificationPlanningEngine(self.config).plan(self.scenarios, strategy_id="smoke", policy_id="smoke")

        apple_cases = [case for case in plan.cases if case.adapter == "apple"]

        self.assertEqual(1, len(apple_cases))
        self.assertEqual("APPLE-001", apple_cases[0].scenario_id)
        self.assertEqual("Apple", apple_cases[0].platform)
        self.assertIn("apple_device", plan.resource_plan.required_hardware)
        self.assertEqual(1, plan.coverage.by_platform["Apple"])

    def test_pi_runtime_capability_selects_raspberry_pi_adapter_for_shared_scenario(self) -> None:
        scenarios = [
            scenario
            for scenario in self.scenarios
            if scenario.id in {"CAPABILITIES-005", "PROFILE-010", "ASKDJ-010", "TRACKINSIGHT-005"}
        ]

        plan = VerificationPlanningEngine(self.config).plan(scenarios, strategy_id="smoke", policy_id="smoke")

        pi_cases = {case.scenario_id: case for case in plan.cases}
        self.assertEqual(set(pi_cases), {"CAPABILITIES-005", "PROFILE-010", "ASKDJ-010", "TRACKINSIGHT-005"})
        for case in pi_cases.values():
            self.assertEqual("Raspberry Pi", case.platform)
            self.assertEqual("raspberry_pi", case.adapter)
        self.assertIn("pi", plan.resource_plan.required_hardware)
        self.assertEqual(4, plan.coverage.by_platform["Raspberry Pi"])

    def test_release_policy_includes_release_qualification_mode_for_release_scenario(self) -> None:
        scenario = [scenario for scenario in self.scenarios if scenario.id == "RELEASE-001"]

        plan = VerificationPlanningEngine(self.config).plan(scenario, strategy_id="release")

        self.assertIn("release_qualification", {case.mode for case in plan.cases})
        self.assertIn("Release Qualification Profile", {case.matrix_profile for case in plan.cases})
        self.assertIn("Release-equivalent", plan.resource_plan.required_builds)

    def test_dependency_graph_orders_setup_before_profile(self) -> None:
        scenarios = [
            scenario
            for scenario in self.scenarios
            if scenario.id in {"SETUP-001", "PROFILE-001"}
        ]

        plan = VerificationPlanningEngine(self.config).plan(scenarios, strategy_id="smoke", policy_id="smoke")

        setup_case = next(case for case in plan.cases if case.scenario_id == "SETUP-001")
        profile_case = next(case for case in plan.cases if case.scenario_id == "PROFILE-001")
        self.assertIn((setup_case.case_id, profile_case.case_id), plan.graph.edges)

    def test_cli_plan_outputs_json(self) -> None:
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            exit_code = main(
                [
                    "--root",
                    str(self.root),
                    "plan",
                    "--scenario-id",
                    "PROFILE-001",
                    "--strategy",
                    "smoke",
                    "--policy",
                    "smoke",
                    "--format",
                    "json",
                ]
            )

        payload = json.loads(buffer.getvalue())
        self.assertEqual(0, exit_code)
        self.assertEqual("smoke", payload["policy"])
        self.assertEqual("PROFILE-001", payload["cases"][0]["scenario_id"])


if __name__ == "__main__":
    unittest.main()
