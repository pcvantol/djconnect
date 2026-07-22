from __future__ import annotations

import asyncio
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from dataclasses import FrozenInstanceError


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = "custom_components.djconnect"


def _load_modules():
    package = types.ModuleType(PACKAGE)
    package.__path__ = [str(ROOT / "custom_components" / "djconnect")]
    sys.modules.setdefault(PACKAGE, package)
    const = types.ModuleType(f"{PACKAGE}.const")
    const.DOMAIN, const.API_IMAGE_PROXY_BASE = "djconnect", "/api/djconnect/v1/image_proxy"
    previous = sys.modules.get(f"{PACKAGE}.const")
    sys.modules[f"{PACKAGE}.const"] = const
    modules = []
    for name in ("session_runtime", "developer_session_bootstrap", "developer_session_scenario_driver", "developer_session_capture"):
        spec = importlib.util.spec_from_file_location(f"{PACKAGE}.{name}", ROOT / "custom_components" / "djconnect" / f"{name}.py")
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        assert spec.loader is not None
        spec.loader.exec_module(module)
        modules.append(module)
    return *modules, previous


class ImmutableSessionCaptureTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.runtime, cls.bootstrap, cls.driver, cls.capture, cls.previous = _load_modules()

    @classmethod
    def tearDownClass(cls) -> None:
        for name in ("developer_session_capture", "developer_session_scenario_driver", "developer_session_bootstrap", "session_runtime"):
            sys.modules.pop(f"{PACKAGE}.{name}", None)
        if cls.previous is None:
            sys.modules.pop(f"{PACKAGE}.const", None)
        else:
            sys.modules[f"{PACKAGE}.const"] = cls.previous

    def setUp(self) -> None:
        self.hass = types.SimpleNamespace(data={})

    def _capture_after_execution(self):
        asyncio.run(self.bootstrap.async_handle_developer_session_bootstrap(self.hass))
        asyncio.run(self.driver.async_execute_si_golden_001(self.hass))
        return asyncio.run(self.capture.async_capture_si_golden_001(self.hass))

    def test_si_golden_001_produces_one_immutable_observation_capture(self) -> None:
        capture = self._capture_after_execution()
        assert capture is not None
        self.assertEqual(capture.scenario_id, "SI-GOLDEN-001")
        self.assertEqual(capture.completion_state, "completed")
        with self.assertRaises(FrozenInstanceError):
            capture.completion_state = "changed"  # type: ignore[misc]

    def test_capture_contains_observable_runtime_moment_flow_and_broadcast(self) -> None:
        capture = self._capture_after_execution()
        assert capture is not None
        self.assertEqual(capture.runtime_events, ("runtime_active", "track_started", "runtime_completed"))
        self.assertEqual(capture.track_started_events, ("track_started",))
        self.assertTrue(capture.approved_planner_intent)
        self.assertTrue(capture.realized_moment.moment_id)
        self.assertTrue(any(item.moment_id == capture.realized_moment.moment_id for item in capture.session_flow))
        self.assertTrue(any(item.event_type == "dj_moment_published" for item in capture.broadcast_publications))

    def test_capture_is_read_only_and_runtime_remains_unchanged(self) -> None:
        capture = self._capture_after_execution()
        active = asyncio.run(self.runtime.session_runtime_manager(self.hass).async_get_active(self.bootstrap.GOLDEN_SCENARIO_PROFILE_ID))
        assert capture is not None and active is not None
        self.assertEqual(len(active.moment_engine.moments), 1)
        self.assertEqual(active.moment_engine.moments[0].moment_id, capture.realized_moment.moment_id)
        self.assertTrue(asyncio.run(self.capture.async_handle_developer_session_capture(self.hass))["success"])
