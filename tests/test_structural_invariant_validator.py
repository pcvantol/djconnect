from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import types
import unittest


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = "structural_invariant_validator_test_package"


def _load(name: str):
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
        """Load fixtures in a private package, never in the integration package."""
        package = types.ModuleType(PACKAGE)
        package.__path__ = [str(ROOT / "custom_components" / "djconnect")]
        sys.modules[PACKAGE] = package
        bootstrap = types.ModuleType(f"{PACKAGE}.developer_session_bootstrap")
        bootstrap.GOLDEN_SCENARIO_ID = "SI-GOLDEN-001"
        bootstrap.GOLDEN_SCENARIO_PROFILE_ID = "fixture"
        bootstrap.SI_GOLDEN_002_ID = "SI-GOLDEN-002"
        bootstrap.SI_GOLDEN_002_PROFILE_ID = "fixture-002"
        bootstrap.SI_GOLDEN_003_ID = "SI-GOLDEN-003"
        bootstrap.SI_GOLDEN_003_PROFILE_ID = "fixture-003"
        bootstrap.SI_GOLDEN_004_ID = "SI-GOLDEN-004"
        bootstrap.SI_GOLDEN_004_PROFILE_ID = "fixture-004"
        bootstrap.SI_GOLDEN_005_ID = "SI-GOLDEN-005"
        bootstrap.SI_GOLDEN_005_PROFILE_ID = "fixture-005"
        bootstrap.SI_GOLDEN_006_ID = "SI-GOLDEN-006"
        bootstrap.SI_GOLDEN_006_PROFILE_ID = "fixture-006"
        bootstrap.si_golden_002_clock_evidence = lambda hass: None
        sys.modules[bootstrap.__name__] = bootstrap
        runtime = types.ModuleType(f"{PACKAGE}.session_runtime")
        runtime.session_runtime_manager = lambda hass: None
        sys.modules[runtime.__name__] = runtime
        cls.capture = _load("developer_session_capture")
        cls.validator = _load("structural_invariant_validator")

    @classmethod
    def tearDownClass(cls):
        for name in tuple(sys.modules):
            if name == PACKAGE or name.startswith(f"{PACKAGE}."):
                del sys.modules[name]

    def valid_capture(self):
        return self.capture.SIGolden001SessionCapture(
            "SI-GOLDEN-001",
            "session-1",
            ("runtime_active", "track_started", "runtime_completed"),
            ("track_started",),
            "artist_story",
            self.capture.CapturedMoment(
                "moment-1", "artist", "artist_story", "Approved summary.", "Approved artist story."
            ),
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
            (
                self.capture.CapturedPresentation(
                    "presentation-moment-1",
                    "moment-1",
                    "artist",
                "primary_with_sidekick",
                (
                    self.capture.CapturedSpeechSegment(1, "dj", "Approved artist story."),
                    self.capture.CapturedSpeechSegment(2, "sidekick", "Approved summary."),
                ),
                "session_shared",
            ),
            ),
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
