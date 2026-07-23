"""Executable coverage for the remaining original Golden Scenario contracts."""
from __future__ import annotations

import asyncio
import importlib.util
from pathlib import Path
import sys
import types
import unittest


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = "si_golden_remaining_test_package"


def _load_modules():
    package = types.ModuleType(PACKAGE)
    package.__path__ = [str(ROOT / "custom_components" / "djconnect")]
    sys.modules[PACKAGE] = package
    const = types.ModuleType(f"{PACKAGE}.const")
    const.DOMAIN = "djconnect"
    const.API_IMAGE_PROXY_BASE = "/api/djconnect/v1/image_proxy"
    sys.modules[const.__name__] = const
    modules = []
    for name in (
        "verification_clock",
        "session_runtime",
        "developer_session_bootstrap",
        "developer_session_scenario_driver",
        "developer_session_capture",
        "structural_invariant_validator",
    ):
        spec = importlib.util.spec_from_file_location(
            f"{PACKAGE}.{name}", ROOT / "custom_components" / "djconnect" / f"{name}.py"
        )
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        assert spec.loader is not None
        spec.loader.exec_module(module)
        modules.append(module)
    return modules


class RemainingGoldenScenariosTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        (
            cls.clock,
            cls.runtime,
            cls.bootstrap,
            cls.driver,
            cls.capture,
            cls.validator,
        ) = _load_modules()

    @classmethod
    def tearDownClass(cls) -> None:
        for name in tuple(sys.modules):
            if name == PACKAGE or name.startswith(f"{PACKAGE}."):
                del sys.modules[name]

    def setUp(self) -> None:
        self.hass = types.SimpleNamespace(data={})

    def _run(self, scenario_id: str):
        started = asyncio.run(
            self.bootstrap.async_handle_developer_session_bootstrap(
                self.hass, scenario_id=scenario_id
            )
        )
        result = asyncio.run(getattr(self.driver, f"async_execute_si_golden_{scenario_id[-3:]}")(self.hass))
        capture = asyncio.run(self.capture.async_capture_remaining_golden(self.hass, scenario_id))
        stopped = asyncio.run(
            self.bootstrap.async_handle_developer_session_bootstrap(
                self.hass, action="stop", scenario_id=scenario_id
            )
        )
        return started, result, capture, stopped

    def test_golden_004_replans_without_realizing_or_publishing_a_moment(self) -> None:
        _, result, capture, _ = self._run("SI-GOLDEN-004")
        assert capture is not None
        self.assertTrue(result["success"])
        self.assertGreater(capture.planning_generation, 0)
        self.assertGreater(capture.superseded_intent_count, 0)
        self.assertEqual(sum(status == "approved" for _, _, status in capture.planned_intents), 1)
        self.assertEqual(capture.moments, ())
        self.assertEqual(capture.presentations, ())
        self.assertEqual(self.validator.validate_remaining_golden(capture).status, "passed")

    def test_remaining_capture_service_keeps_planner_only_scenario_bounded(self) -> None:
        asyncio.run(
            self.bootstrap.async_handle_developer_session_bootstrap(
                self.hass, scenario_id="SI-GOLDEN-004"
            )
        )
        asyncio.run(self.driver.async_execute_si_golden_004(self.hass))
        result = asyncio.run(
            self.capture.async_handle_developer_session_capture(self.hass, "SI-GOLDEN-004")
        )
        self.assertEqual(result["status"], "captured")
        self.assertEqual(result["moment_id"], "")
        asyncio.run(
            self.bootstrap.async_handle_developer_session_bootstrap(
                self.hass, action="stop", scenario_id="SI-GOLDEN-004"
            )
        )

    def test_golden_005_produces_two_silences_then_one_session_update_presentation(self) -> None:
        _, result, capture, _ = self._run("SI-GOLDEN-005")
        assert capture is not None
        self.assertTrue(result["success"])
        self.assertEqual(tuple(moment.moment_type for moment in capture.moments), ("silence", "silence", "session"))
        self.assertEqual(capture.presentations[-1].source_moment_id, capture.moments[-1].moment_id)
        self.assertTrue(capture.presentations[-1].segments)
        self.assertEqual(self.validator.validate_remaining_golden(capture).status, "passed")

    def test_golden_006_is_intentional_non_narrative_silence(self) -> None:
        _, result, capture, _ = self._run("SI-GOLDEN-006")
        assert capture is not None
        self.assertTrue(result["success"])
        self.assertEqual(tuple(moment.moment_type for moment in capture.moments), ("silence",))
        self.assertEqual(capture.moments[0].reason, "planned_silence")
        self.assertEqual(capture.moments[0].content, "")
        self.assertTrue(all(not presentation.segments for presentation in capture.presentations))
        self.assertEqual(self.validator.validate_remaining_golden(capture).status, "passed")


if __name__ == "__main__":
    unittest.main()
