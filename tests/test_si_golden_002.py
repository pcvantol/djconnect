from __future__ import annotations

import asyncio
from dataclasses import replace
from dataclasses import FrozenInstanceError
import importlib.util
from pathlib import Path
import sys
import time
import types
import unittest


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = "si_golden_002_test_package"


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


class SIGolden002Test(unittest.TestCase):
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
                self.hass, scenario_id="SI-GOLDEN-002"
            )
        )
        result = asyncio.run(self.driver.async_execute_si_golden_002(self.hass))
        capture = asyncio.run(self.capture.async_capture_si_golden_002(self.hass))
        return started, result, capture

    def test_executes_the_fixed_two_event_scenario(self) -> None:
        started, result, capture = self._execute()
        self.assertEqual(started["scenario_id"], "SI-GOLDEN-002")
        self.assertEqual(result["status"], "executed")
        self.assertEqual(result["session_id"], started["session_id"])
        self.assertIsNotNone(capture)

    def test_clock_advances_deterministically_past_the_interval(self) -> None:
        _, _, capture = self._execute()
        assert capture is not None
        self.assertEqual(capture.verification_clock.elapsed_seconds, 61.0)
        self.assertEqual(capture.verification_clock.advance_count, 1)

    def test_first_eligible_decision_uses_performance_memory_without_repetition(self) -> None:
        _, _, capture = self._execute()
        assert capture is not None
        self.assertEqual(capture.first_realized_moment.knowledge_intent, "artist_story")
        self.assertEqual(capture.second_realized_moment.knowledge_intent, "genre_story")
        self.assertNotEqual(
            capture.first_realized_moment.knowledge_intent,
            capture.second_realized_moment.knowledge_intent,
        )

    def test_second_event_has_one_approval_one_moment_and_ordered_publication(self) -> None:
        _, _, capture = self._execute()
        assert capture is not None
        self.assertEqual(capture.approval_count, 1)
        self.assertNotEqual(
            capture.first_realized_moment.moment_id,
            capture.second_realized_moment.moment_id,
        )
        flow_ids = [entry.moment_id for entry in capture.session_flow]
        self.assertLess(
            flow_ids.index(capture.first_realized_moment.moment_id),
            flow_ids.index(capture.second_realized_moment.moment_id),
        )
        self.assertEqual(
            sum(event.event_type == "dj_moment_published" for event in capture.broadcast_publications),
            2,
        )
        self.assertEqual(
            [presentation.source_moment_id for presentation in capture.presentations],
            [capture.first_realized_moment.moment_id, capture.second_realized_moment.moment_id],
        )
        self.assertEqual(capture.presentations[0].mode, "primary_with_sidekick")
        self.assertEqual(
            [(segment.ordinal, segment.speaker_role, segment.text) for segment in capture.presentations[0].segments],
            [
                (1, "dj", capture.first_realized_moment.content),
                (2, "sidekick", capture.first_realized_moment.summary),
            ],
        )
        self.assertEqual(capture.presentations[1].mode, "primary_only")
        self.assertEqual(
            [(segment.ordinal, segment.speaker_role, segment.text) for segment in capture.presentations[1].segments],
            [(1, "dj", capture.second_realized_moment.content)],
        )

    def test_immutable_capture_passes_structural_validation(self) -> None:
        _, _, capture = self._execute()
        assert capture is not None
        with self.assertRaises(FrozenInstanceError):
            capture.completion_state = "changed"  # type: ignore[misc]
        self.assertEqual(self.validator.validate_si_golden_002(capture).status, "passed")
        repeated = replace(capture, second_realized_moment=capture.first_realized_moment)
        self.assertEqual(self.validator.validate_si_golden_002(repeated).status, "failed")
        missing_presentation = replace(capture, presentations=())
        self.assertEqual(self.validator.validate_si_golden_002(missing_presentation).status, "failed")

    def test_fresh_executions_have_identical_observable_results(self) -> None:
        _, _, first = self._execute()
        assert first is not None
        asyncio.run(
            self.bootstrap.async_handle_developer_session_bootstrap(
                self.hass, action="stop", scenario_id="SI-GOLDEN-002"
            )
        )
        self.hass = types.SimpleNamespace(data={})
        _, _, second = self._execute()
        assert second is not None
        self.assertEqual(
            (
                first.verification_clock,
                first.first_realized_moment.moment_type,
                first.first_realized_moment.knowledge_intent,
                first.second_realized_moment.moment_type,
                first.second_realized_moment.knowledge_intent,
                tuple(item.moment_type for item in first.session_flow),
                tuple(item.event_type for item in first.broadcast_publications),
            ),
            (
                second.verification_clock,
                second.first_realized_moment.moment_type,
                second.first_realized_moment.knowledge_intent,
                second.second_realized_moment.moment_type,
                second.second_realized_moment.knowledge_intent,
                tuple(item.moment_type for item in second.session_flow),
                tuple(item.event_type for item in second.broadcast_publications),
            ),
        )

    def test_clock_is_disposed_with_the_isolated_runtime(self) -> None:
        started, _, _ = self._execute()
        stopped = asyncio.run(
            self.bootstrap.async_handle_developer_session_bootstrap(
                self.hass, action="stop", scenario_id="SI-GOLDEN-002"
            )
        )
        self.assertEqual(stopped["session_id"], started["session_id"])
        self.assertIsNone(self.bootstrap.si_golden_002_clock_evidence(self.hass))
        active = asyncio.run(
            self.runtime.session_runtime_manager(self.hass).async_get_active(
                self.bootstrap.SI_GOLDEN_002_PROFILE_ID
            )
        )
        self.assertIsNone(active)

    def test_normal_runtime_composes_the_existing_monotonic_clock(self) -> None:
        session = asyncio.run(
            self.runtime.session_runtime_manager(self.hass).async_start(owner_profile_id="ordinary")
        )
        self.assertIs(session.planner.elapsed_time_source, time.monotonic)
