from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import types
import unittest


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = "custom_components.djconnect"


def _load(name: str):
    package = types.ModuleType(PACKAGE)
    package.__path__ = [str(ROOT / "custom_components" / "djconnect")]
    sys.modules.setdefault(PACKAGE, package)
    spec = importlib.util.spec_from_file_location(
        f"{PACKAGE}.{name}", ROOT / "custom_components" / "djconnect" / f"{name}.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader
    spec.loader.exec_module(module)
    return module


class StructuralInvariantValidatorTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        bootstrap = types.ModuleType(f"{PACKAGE}.developer_session_bootstrap")
        bootstrap.GOLDEN_SCENARIO_ID = "SI-GOLDEN-001"
        bootstrap.GOLDEN_SCENARIO_PROFILE_ID = "fixture"
        sys.modules[bootstrap.__name__] = bootstrap
        runtime = types.ModuleType(f"{PACKAGE}.session_runtime")
        runtime.session_runtime_manager = lambda hass: None
        sys.modules[runtime.__name__] = runtime
        cls.capture = _load("developer_session_capture")
        cls.validator = _load("structural_invariant_validator")

    def valid_capture(self):
        return self.capture.SIGolden001SessionCapture(
            "SI-GOLDEN-001",
            "session-1",
            ("runtime_active", "track_started", "runtime_completed"),
            ("track_started",),
            "artist_story",
            self.capture.CapturedMoment("moment-1", "artist", "artist_story"),
            (
                self.capture.CapturedFlowEntry(
                    "moment-1", "dj_moment", "next", "moment-1", "artist"
                ),
            ),
            (self.capture.CapturedBroadcastPublication(1, "dj_moment_published"),),
            "completed",
            "completed",
            1,
            0,
            False,
            True,
        )

    def test_valid_capture_passes_and_is_deterministic(self):
        capture = self.valid_capture()
        self.assertEqual(
            self.validator.validate_si_golden_001(capture),
            self.validator.validate_si_golden_001(capture),
        )
        self.assertEqual(self.validator.validate_si_golden_001(capture).status, "passed")

    def test_invalid_and_missing_evidence_fail_closed(self):
        capture = self.valid_capture()
        self.assertEqual(
            self.validator.validate_si_golden_001(
                capture.__class__(**{**capture.__dict__, "scenario_id": "other"})
            ).status,
            "invalid_capture",
        )
        self.assertEqual(
            self.validator.validate_si_golden_001(
                capture.__class__(**{**capture.__dict__, "approval_count": 2})
            ).status,
            "failed",
        )
