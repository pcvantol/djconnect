from __future__ import annotations

import asyncio
import importlib.util
from pathlib import Path
import sys
import types
import unittest


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = "custom_components.djconnect"


def _load_bootstrap_modules():
    package = types.ModuleType(PACKAGE)
    package.__path__ = [str(ROOT / "custom_components" / "djconnect")]
    sys.modules.setdefault(PACKAGE, package)
    const = types.ModuleType(f"{PACKAGE}.const")
    const.DOMAIN = "djconnect"
    const.API_IMAGE_PROXY_BASE = "/api/djconnect/v1/image_proxy"
    previous_const = sys.modules.get(f"{PACKAGE}.const")
    sys.modules[f"{PACKAGE}.const"] = const

    modules = []
    for module_name in ("session_runtime", "developer_session_bootstrap"):
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


class DeveloperSessionBootstrapTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.runtime, cls.bootstrap, cls.previous_const = _load_bootstrap_modules()

    @classmethod
    def tearDownClass(cls) -> None:
        sys.modules.pop(f"{PACKAGE}.developer_session_bootstrap", None)
        sys.modules.pop(f"{PACKAGE}.session_runtime", None)
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

    def test_start_creates_one_isolated_runtime_with_a_bounded_result(self) -> None:
        result = self._bootstrap()

        self.assertEqual(
            set(result),
            {"success", "status", "scenario_id", "session_id", "lifecycle_state"},
        )
        self.assertEqual(
            result,
            {
                "success": True,
                "status": "ready",
                "scenario_id": "SI-GOLDEN-001",
                "session_id": result["session_id"],
                "lifecycle_state": "active",
            },
        )
        active = asyncio.run(
            self.runtime.session_runtime_manager(self.hass).async_get_active(
                "e2e-session-intelligence-golden-001"
            )
        )
        self.assertIsNotNone(active)
        assert active is not None
        self.assertEqual(active.session_id, result["session_id"])
        self.assertEqual(active.runtime_state, self.runtime.SessionRuntimeState.ACTIVE)

    def test_start_is_non_interactive_and_does_not_execute_the_scenario(self) -> None:
        self._bootstrap()

        active = asyncio.run(
            self.runtime.session_runtime_manager(self.hass).async_get_active(
                "e2e-session-intelligence-golden-001"
            )
        )
        assert active is not None
        self.assertEqual(active.moment_engine.moments, ())
        self.assertEqual(active.broadcast.state.dj_moments, ())
        self.assertTrue(
            all(not item.moment_id for item in active.planner.output.session_flow.items)
        )

    def test_only_the_existing_runtime_manager_owns_the_bootstrapped_session(self) -> None:
        self._bootstrap()

        manager = self.runtime.session_runtime_manager(self.hass)
        active = asyncio.run(
            manager.async_get_active("e2e-session-intelligence-golden-001")
        )
        self.assertIsNotNone(active)
        self.assertFalse(hasattr(self.bootstrap, "_active_session"))
        self.assertFalse(hasattr(self.bootstrap, "_runtime"))

    def test_second_start_does_not_create_a_second_runtime(self) -> None:
        first = self._bootstrap()
        second = self._bootstrap()

        self.assertTrue(first["success"])
        self.assertEqual(
            second,
            {
                "success": False,
                "status": "already_active",
                "scenario_id": "SI-GOLDEN-001",
            },
        )

    def test_stop_terminates_and_releases_runtime_scoped_state(self) -> None:
        started = self._bootstrap()
        stopped = self._bootstrap("stop")

        self.assertEqual(
            stopped,
            {
                "success": True,
                "status": "stopped",
                "scenario_id": "SI-GOLDEN-001",
                "session_id": started["session_id"],
                "lifecycle_state": "ended",
            },
        )
        active = asyncio.run(
            self.runtime.session_runtime_manager(self.hass).async_get_active(
                "e2e-session-intelligence-golden-001"
            )
        )
        self.assertIsNone(active)

    def test_invalid_action_does_not_create_a_runtime(self) -> None:
        result = self._bootstrap("run")

        self.assertEqual(
            result,
            {
                "success": False,
                "status": "invalid_action",
                "scenario_id": "SI-GOLDEN-001",
            },
        )
        active = asyncio.run(
            self.runtime.session_runtime_manager(self.hass).async_get_active(
                "e2e-session-intelligence-golden-001"
            )
        )
        self.assertIsNone(active)
