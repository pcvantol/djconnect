from __future__ import annotations

import asyncio
import importlib.util
from pathlib import Path
import sys
import types
import unittest


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = "custom_components.djconnect"


def _load_modules():
    package = types.ModuleType(PACKAGE)
    package.__path__ = [str(ROOT / "custom_components" / "djconnect")]
    sys.modules.setdefault(PACKAGE, package)
    const = types.ModuleType(f"{PACKAGE}.const")
    const.DOMAIN = "djconnect"
    const.API_IMAGE_PROXY_BASE = "/api/djconnect/v1/image_proxy"
    previous_const = sys.modules.get(f"{PACKAGE}.const")
    sys.modules[f"{PACKAGE}.const"] = const

    modules = []
    for module_name in (
        "session_runtime",
        "developer_session_bootstrap",
        "developer_session_scenario_driver",
    ):
        spec = importlib.util.spec_from_file_location(
            f"{PACKAGE}.{module_name}",
            ROOT / "custom_components" / "djconnect" / f"{module_name}.py",
        )
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        assert spec.loader is not None
        spec.loader.exec_module(module)
        modules.append(module)
    return *modules, previous_const


class DeterministicScenarioDriverTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.runtime, cls.bootstrap, cls.driver, cls.previous_const = _load_modules()

    @classmethod
    def tearDownClass(cls) -> None:
        for module_name in (
            "developer_session_scenario_driver",
            "developer_session_bootstrap",
            "session_runtime",
        ):
            sys.modules.pop(f"{PACKAGE}.{module_name}", None)
        if cls.previous_const is None:
            sys.modules.pop(f"{PACKAGE}.const", None)
        else:
            sys.modules[f"{PACKAGE}.const"] = cls.previous_const

    def setUp(self) -> None:
        self.hass = types.SimpleNamespace(data={})

    def _bootstrap(self, action: str = "start") -> dict:
        return asyncio.run(
            self.bootstrap.async_handle_developer_session_bootstrap(self.hass, action)
        )

    def _run(self) -> dict:
        return asyncio.run(self.driver.async_execute_si_golden_001(self.hass))

    def test_executes_si_golden_001_through_the_existing_runtime(self) -> None:
        started = self._bootstrap()
        result = self._run()

        self.assertEqual(
            set(result),
            {"success", "status", "scenario_id", "session_id", "moment_id"},
        )
        self.assertTrue(result["success"])
        self.assertEqual(result["status"], "executed")
        self.assertEqual(result["scenario_id"], "SI-GOLDEN-001")
        self.assertEqual(result["session_id"], started["session_id"])
        active = asyncio.run(
            self.runtime.session_runtime_manager(self.hass).async_get_active(
                self.bootstrap.GOLDEN_SCENARIO_PROFILE_ID
            )
        )
        assert active is not None
        self.assertEqual(len(active.moment_engine.moments), 1)
        self.assertEqual(active.moment_engine.moments[0].moment_id, result["moment_id"])
        self.assertEqual(active.planning_coordinator.last_lifecycle_state, "completed")
        self.assertEqual(active.planning_coordinator.last_approval_source, "planned_intent")

    def test_runtime_receives_the_fixed_observable_input(self) -> None:
        self._bootstrap()
        manager = self.runtime.session_runtime_manager(self.hass)
        original = manager.async_process_track_started
        observed: list[dict] = []

        async def observe(**kwargs):
            insight = await kwargs["insight_provider"]()
            observed.append(insight)

            async def same_insight() -> dict:
                return insight

            kwargs["insight_provider"] = same_insight
            return await original(**kwargs)

        manager.async_process_track_started = observe
        result = self._run()

        self.assertTrue(result["success"])
        self.assertEqual(observed, [self.driver.SI_GOLDEN_001_FIXTURE.as_track_insight()])

    def test_driver_reaches_planner_knowledge_and_moment_only_via_runtime(self) -> None:
        self._bootstrap()
        result = self._run()

        self.assertTrue(result["success"])
        source = (
            ROOT
            / "custom_components"
            / "djconnect"
            / "developer_session_scenario_driver.py"
        ).read_text()
        self.assertIn("manager.async_process_track_started", source)
        self.assertNotIn(".planner", source)
        self.assertNotIn(".knowledge_engine", source)
        self.assertNotIn(".moment_engine", source)

    def test_repeated_runs_from_fresh_bootstraps_receive_identical_inputs(self) -> None:
        def execute_and_observe() -> tuple[dict, list[dict]]:
            manager = self.runtime.session_runtime_manager(self.hass)
            original = manager.async_process_track_started
            observed: list[dict] = []

            async def observe(**kwargs):
                insight = await kwargs["insight_provider"]()
                observed.append(insight)

                async def same_insight() -> dict:
                    return insight

                kwargs["insight_provider"] = same_insight
                return await original(**kwargs)

            manager.async_process_track_started = observe
            return self._run(), observed

        self._bootstrap()
        first, first_inputs = execute_and_observe()
        self._bootstrap("stop")
        self.hass = types.SimpleNamespace(data={})
        self._bootstrap()
        second, second_inputs = execute_and_observe()

        self.assertTrue(first["success"])
        self.assertTrue(second["success"])
        self.assertEqual(first_inputs, second_inputs)
        self.assertEqual(first_inputs, [self.driver.SI_GOLDEN_001_FIXTURE.as_track_insight()])

    def test_driver_requires_existing_bootstrap_and_preserves_cleanup(self) -> None:
        missing = self._run()
        started = self._bootstrap()
        executed = self._run()
        stopped = self._bootstrap("stop")

        self.assertEqual(
            missing,
            {
                "success": False,
                "status": "bootstrap_required",
                "scenario_id": "SI-GOLDEN-001",
            },
        )
        self.assertTrue(executed["success"])
        self.assertEqual(stopped["session_id"], started["session_id"])
        self.assertEqual(stopped["lifecycle_state"], "ended")
        active = asyncio.run(
            self.runtime.session_runtime_manager(self.hass).async_get_active(
                self.bootstrap.GOLDEN_SCENARIO_PROFILE_ID
            )
        )
        self.assertIsNone(active)
