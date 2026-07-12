"""Tests for modular verification lab requirements and profile planning."""

from __future__ import annotations

import unittest
from pathlib import Path

from tools.verification.config import load_config
from tools.verification.lab import LabCatalog
from tools.verification.planning import VerificationPlanningEngine
from tools.verification.scenario.loader import ScenarioLoader
from tools.verification.scenario.validator import ScenarioValidator


class LabRequirementTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(__file__).resolve().parents[2]
        self.config = load_config(self.root)
        self.catalog = LabCatalog(self.root)
        self.scenarios = ScenarioLoader(self.config).load()

    def test_catalog_has_no_internal_reference_errors(self) -> None:
        self.assertEqual([], self.catalog.validate_catalog())

    def test_all_canonical_scenarios_have_valid_requirements(self) -> None:
        validator = ScenarioValidator(self.root)
        issues = [issue for scenario in self.scenarios for issue in validator.validate(scenario)]

        self.assertEqual([], [issue.message for issue in issues])
        self.assertEqual(234, len(self.scenarios))

    def test_profile_001_through_005_select_ha_profile(self) -> None:
        scenarios = [scenario for scenario in self.scenarios if scenario.id in {f"PROFILE-00{index}" for index in range(1, 6)}]

        plan = self.catalog.plan_for_scenarios(scenarios)

        self.assertEqual("ha-profile", plan.selected_profile)
        self.assertEqual(("homeassistant",), plan.selected_services)
        self.assertIn("docker/verification/compose.base.yaml", plan.compose_fragments)
        self.assertIn("djconnect.profile_platform", plan.required_capabilities)

    def test_assist_requirements_select_assist_profile(self) -> None:
        scenario = _scenario_with_requirements(
            "ASSIST-PROBE",
            ["ha.runtime", "ha.websocket", "assist.pipeline", "stt.whisper", "tts.piper"],
        )

        plan = self.catalog.plan_for_scenarios([scenario])

        self.assertEqual("ha-assist", plan.selected_profile)
        self.assertIn("whisper", plan.selected_services)
        self.assertIn("piper", plan.selected_services)
        self.assertIn("docker/verification/compose.whisper.yaml", plan.compose_fragments)

    def test_music_requirements_select_music_profile(self) -> None:
        scenario = _scenario_with_requirements(
            "MUSIC-PROBE",
            ["ha.runtime", "ha.websocket", "music.fake_backend", "music.playback_target", "djconnect.playback"],
        )

        plan = self.catalog.plan_for_scenarios([scenario])

        self.assertEqual("ha-music", plan.selected_profile)
        self.assertIn("fake_music_backend", plan.selected_services)
        self.assertNotIn("whisper", plan.selected_services)

    def test_combined_assist_and_music_selects_full_profile(self) -> None:
        scenario = _scenario_with_requirements(
            "FULL-PROBE",
            ["assist.pipeline", "stt.whisper", "tts.piper", "music.fake_backend", "djconnect.playback"],
        )

        plan = self.catalog.plan_for_scenarios([scenario])

        self.assertEqual("ha-full", plan.selected_profile)
        self.assertIn("whisper", plan.selected_services)
        self.assertIn("fake_music_backend", plan.selected_services)

    def test_unknown_capability_fails_scenario_validation(self) -> None:
        scenario = _scenario_with_requirements("BAD-PROBE", ["unknown.capability"])

        errors = self.catalog.validate_scenario(scenario)

        self.assertTrue(any("unknown capability" in error for error in errors))

    def test_planning_engine_includes_lab_execution_plan(self) -> None:
        scenarios = [scenario for scenario in self.scenarios if scenario.id == "PROFILE-001"]

        plan = VerificationPlanningEngine(self.config).plan(scenarios, strategy_id="smoke")

        lab_plan = plan.metadata["lab_execution_plan"]
        self.assertEqual("ha-profile", lab_plan["selected_profile"])
        self.assertIn("docker/verification/compose.base.yaml", lab_plan["compose_fragments"])


def _scenario_with_requirements(identifier: str, capabilities: list[str]):
    from tools.verification.models import Scenario

    return Scenario.from_mapping(
        {
            "id": identifier,
            "title": identifier,
            "description": identifier,
            "category": "Profiles",
            "priority": "P0",
            "verification_level": "V2",
            "automation_level": "ENVIRONMENT_DEPENDENT",
            "required_components": ["HA"],
            "requires": {"capabilities": capabilities},
        }
    )


if __name__ == "__main__":
    unittest.main()
