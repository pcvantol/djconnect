"""Executable coverage for the canonical server-side Golden Qualification path."""
from __future__ import annotations

import asyncio
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import AsyncMock, patch


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = "golden_qualification_test_package"


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
        "golden_qualification",
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


class GoldenQualificationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        (
            cls.clock,
            cls.runtime,
            cls.bootstrap,
            cls.driver,
            cls.capture,
            cls.validator,
            cls.qualification,
        ) = _load_modules()

    @classmethod
    def tearDownClass(cls) -> None:
        for name in tuple(sys.modules):
            if name == PACKAGE or name.startswith(f"{PACKAGE}."):
                del sys.modules[name]

    def setUp(self) -> None:
        self.hass = types.SimpleNamespace(data={})

    def test_qualification_reuses_one_server_side_path_for_all_executable_scenarios(self) -> None:
        report = asyncio.run(self.qualification.async_run_golden_qualification(self.hass))

        self.assertEqual(report.profile, "golden_qualification_foundation")
        self.assertEqual(report.overall_status, "passed")
        self.assertEqual(
            tuple(item.scenario_id for item in report.scenarios),
            (
                "SI-GOLDEN-001",
                "SI-GOLDEN-002",
                "SI-GOLDEN-003",
                "SI-GOLDEN-004",
                "SI-GOLDEN-005",
                "SI-GOLDEN-006",
            ),
        )
        self.assertTrue(all(item.deterministic for item in report.scenarios))
        self.assertTrue(all(item.session_verification == "passed" for item in report.scenarios))
        self.assertEqual(
            tuple(item.presentation_verification for item in report.scenarios),
            ("passed", "passed", "not_applicable", "not_applicable", "passed", "not_applicable"),
        )

    def test_qualification_stops_every_isolated_runtime(self) -> None:
        asyncio.run(self.qualification.async_run_golden_qualification(self.hass))

        manager = self.runtime.session_runtime_manager(self.hass)
        for profile_id in (
            self.bootstrap.SI_GOLDEN_001_PROFILE_ID,
            self.bootstrap.SI_GOLDEN_002_PROFILE_ID,
            self.bootstrap.SI_GOLDEN_003_PROFILE_ID,
            self.bootstrap.SI_GOLDEN_004_PROFILE_ID,
            self.bootstrap.SI_GOLDEN_005_PROFILE_ID,
            self.bootstrap.SI_GOLDEN_006_PROFILE_ID,
        ):
            self.assertIsNone(asyncio.run(manager.async_get_active(profile_id)))

    def test_bounded_report_does_not_expose_runtime_or_renderer_state(self) -> None:
        result = asyncio.run(self.qualification.async_handle_golden_qualification(self.hass))

        self.assertTrue(result["success"])
        self.assertEqual(result["status"], "passed")
        self.assertNotIn("runtime", result)
        self.assertNotIn("renderer", result)
        self.assertEqual(len(result["scenarios"]), 6)

    def test_golden_smoke_selects_only_the_minimal_approved_scenario(self) -> None:
        report = asyncio.run(self.qualification.async_run_golden_smoke(self.hass))

        self.assertEqual(report.profile, "golden_smoke")
        self.assertEqual(report.overall_status, "passed")
        self.assertEqual(
            tuple(item.scenario_id for item in report.scenarios),
            ("SI-GOLDEN-001",),
        )

    def test_golden_smoke_report_reuses_the_bounded_foundation_shape(self) -> None:
        result = asyncio.run(self.qualification.async_handle_golden_smoke(self.hass))

        self.assertTrue(result["success"])
        self.assertEqual(result["profile"], "golden_smoke")
        self.assertEqual(tuple(item["scenario_id"] for item in result["scenarios"]), ("SI-GOLDEN-001",))
        self.assertNotIn("runtime", result)
        self.assertNotIn("renderer", result)
        self.assertNotIn("profile_version", result)

    def test_golden_regression_uses_the_immutable_canonical_scenario_selection(self) -> None:
        self.assertIsInstance(self.qualification.GOLDEN_REGRESSION_SCENARIOS, tuple)
        self.assertEqual(
            self.qualification.GOLDEN_REGRESSION_SCENARIOS,
            (
                "SI-GOLDEN-001",
                "SI-GOLDEN-002",
                "SI-GOLDEN-003",
                "SI-GOLDEN-004",
                "SI-GOLDEN-005",
                "SI-GOLDEN-006",
            ),
        )

    def test_golden_regression_delegates_to_the_existing_foundation(self) -> None:
        foundation_report = asyncio.run(
            self.qualification.async_run_golden_qualification(self.hass)
        )
        delegated = AsyncMock(return_value=foundation_report)
        with patch.object(
            self.qualification,
            "async_run_golden_qualification",
            delegated,
        ):
            report = asyncio.run(self.qualification.async_run_golden_regression(self.hass))

        delegated.assert_awaited_once_with(
            self.hass,
            scenario_ids=self.qualification.GOLDEN_REGRESSION_SCENARIOS,
        )
        self.assertEqual(report.scenarios, foundation_report.scenarios)
        self.assertEqual(report.overall_status, foundation_report.overall_status)

    def test_golden_regression_executes_the_complete_contract_and_cleans_up(self) -> None:
        report = asyncio.run(self.qualification.async_run_golden_regression(self.hass))

        self.assertEqual(report.profile, "golden_regression")
        self.assertEqual(report.profile_version, 1)
        self.assertEqual(report.overall_status, "passed")
        self.assertEqual(
            tuple(item.scenario_id for item in report.scenarios),
            self.qualification.GOLDEN_REGRESSION_SCENARIOS,
        )
        self.assertTrue(all(item.deterministic for item in report.scenarios))
        manager = self.runtime.session_runtime_manager(self.hass)
        for profile_id in (
            self.bootstrap.SI_GOLDEN_001_PROFILE_ID,
            self.bootstrap.SI_GOLDEN_002_PROFILE_ID,
            self.bootstrap.SI_GOLDEN_003_PROFILE_ID,
            self.bootstrap.SI_GOLDEN_004_PROFILE_ID,
            self.bootstrap.SI_GOLDEN_005_PROFILE_ID,
            self.bootstrap.SI_GOLDEN_006_PROFILE_ID,
        ):
            self.assertIsNone(asyncio.run(manager.async_get_active(profile_id)))

    def test_golden_regression_report_is_bounded_and_has_deterministic_metadata(self) -> None:
        first = asyncio.run(self.qualification.async_handle_golden_regression(self.hass))
        second = asyncio.run(
            self.qualification.async_handle_golden_regression(types.SimpleNamespace(data={}))
        )

        self.assertEqual(first["profile"], "golden_regression")
        self.assertEqual(first["profile_version"], 1)
        self.assertEqual(
            (first["profile"], first["profile_version"], first["scenarios"]),
            (second["profile"], second["profile_version"], second["scenarios"]),
        )
        for key in ("runtime", "renderer", "planner", "knowledge", "provider", "memory", "prompt"):
            self.assertNotIn(key, first)


if __name__ == "__main__":
    unittest.main()
