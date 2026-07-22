from __future__ import annotations

import asyncio
from dataclasses import FrozenInstanceError, replace
import importlib.util
from pathlib import Path
import sys
import types
import unittest


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = "si_golden_003_test_package"


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


class SIGolden003Test(unittest.TestCase):
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

    def _execute(self):
        started = asyncio.run(
            self.bootstrap.async_handle_developer_session_bootstrap(
                self.hass, scenario_id="SI-GOLDEN-003"
            )
        )
        result = asyncio.run(self.driver.async_execute_si_golden_003(self.hass))
        capture = asyncio.run(self.capture.async_capture_si_golden_003(self.hass))
        return started, result, capture

    def test_executes_the_approved_unavailable_knowledge_scenario(self) -> None:
        started, result, capture = self._execute()
        self.assertEqual(started["scenario_id"], "SI-GOLDEN-003")
        self.assertEqual(result["status"], "executed")
        self.assertEqual(result["session_id"], started["session_id"])
        self.assertIsNotNone(capture)

    def test_failure_degrades_to_one_silence_without_fabricated_knowledge(self) -> None:
        _, _, capture = self._execute()
        assert capture is not None
        self.assertTrue(capture.knowledge_failure_observed)
        self.assertTrue(capture.no_fabricated_knowledge)
        self.assertEqual(capture.realized_moment.moment_type, "silence")
        self.assertEqual(capture.realized_moment.knowledge_intent, "silence")
        self.assertEqual(capture.approval_count, 1)

    def test_flow_and_broadcast_remain_valid_for_the_silence_outcome(self) -> None:
        _, _, capture = self._execute()
        assert capture is not None
        self.assertTrue(
            any(entry.moment_id == capture.realized_moment.moment_id for entry in capture.session_flow)
        )
        self.assertTrue(capture.broadcast_contains_realized_moment)
        self.assertFalse(
            any(entry.event_type == "dj_moment_published" for entry in capture.broadcast_publications)
        )

    def test_immutable_capture_passes_structural_validation(self) -> None:
        _, _, capture = self._execute()
        assert capture is not None
        with self.assertRaises(FrozenInstanceError):
            capture.completion_state = "changed"  # type: ignore[misc]
        self.assertEqual(self.validator.validate_si_golden_003(capture).status, "passed")
        invalid = replace(capture, no_fabricated_knowledge=False)
        self.assertEqual(self.validator.validate_si_golden_003(invalid).status, "failed")

    def test_repeated_executions_have_identical_observable_results(self) -> None:
        _, _, first = self._execute()
        assert first is not None
        asyncio.run(
            self.bootstrap.async_handle_developer_session_bootstrap(
                self.hass, action="stop", scenario_id="SI-GOLDEN-003"
            )
        )
        self.hass = types.SimpleNamespace(data={})
        _, _, second = self._execute()
        assert second is not None
        self.assertEqual(
            (
                first.realized_moment.moment_type,
                first.realized_moment.knowledge_intent,
                first.knowledge_failure_observed,
                first.no_fabricated_knowledge,
                tuple(item.moment_type for item in first.session_flow),
                tuple(item.event_type for item in first.broadcast_publications),
                first.broadcast_contains_realized_moment,
            ),
            (
                second.realized_moment.moment_type,
                second.realized_moment.knowledge_intent,
                second.knowledge_failure_observed,
                second.no_fabricated_knowledge,
                tuple(item.moment_type for item in second.session_flow),
                tuple(item.event_type for item in second.broadcast_publications),
                second.broadcast_contains_realized_moment,
            ),
        )

    def test_runtime_destruction_removes_the_isolated_session(self) -> None:
        started, _, _ = self._execute()
        stopped = asyncio.run(
            self.bootstrap.async_handle_developer_session_bootstrap(
                self.hass, action="stop", scenario_id="SI-GOLDEN-003"
            )
        )
        self.assertEqual(stopped["session_id"], started["session_id"])
        active = asyncio.run(
            self.runtime.session_runtime_manager(self.hass).async_get_active(
                self.bootstrap.SI_GOLDEN_003_PROFILE_ID
            )
        )
        self.assertIsNone(active)


if __name__ == "__main__":
    unittest.main()
