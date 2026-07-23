"""Regression coverage for Presentation Verification architecture boundaries."""

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
DOCUMENT = ROOT / "docs" / "verification" / "PRESENTATION_VERIFICATION_ARCHITECTURE.md"


class PresentationVerificationArchitectureTest(unittest.TestCase):
    """Keep Presentation Verification server-side, bounded and non-rendering."""

    def _contents(self) -> str:
        return " ".join(DOCUMENT.read_text().split())

    def test_canonical_projection_path_and_scope_are_explicit(self) -> None:
        contents = self._contents()

        for required in (
            "approved immutable DJMoment -> Presentation Composer -> immutable Presentation",
            "-> renderer-safe Presentation Projection -> Broadcast publication",
            "It ends at the renderer-safe Broadcast projection.",
            "Existing renderer-safe visual Presentation remains authoritative",
        ):
            self.assertIn(required, contents)

    def test_session_and_presentation_verification_are_separate(self) -> None:
        contents = self._contents()

        for required in (
            "Session Intelligence Verification and Presentation Verification protect different contracts",
            "Planner, Knowledge Engine, DJ Moment Engine and Session Flow",
            "Presentation Composer, immutable Presentation structure and renderer-safe Broadcast projection",
            "Neither creates a second Runtime, Scenario Driver, Session Flow or Broadcast path.",
        ):
            self.assertIn(required, contents)

    def test_assertions_are_deterministic_and_renderer_safe(self) -> None:
        contents = self._contents()

        for required in (
            "Presentation identity and source DJMoment identity are present and linked",
            "Speech segment order and semantic speaker roles are preserved",
            "Primary Only is retained as the safe fallback",
            "projection exposes neither Presentation Context nor Planner",
            "equivalent immutable DJMoment + equivalent Presentation Context + equivalent policy",
        ):
            self.assertIn(required, contents)

    def test_renderer_audio_ci_and_implementation_work_remain_excluded(self) -> None:
        contents = self._contents()

        for required in (
            "rendered pixels, DOM structure, animation, generated audio, voice quality, TTS provider behavior",
            "does not authorize renderer tests, browser tests, visual assertions, audio assertions",
            "Golden Smoke changes, Golden Regression changes",
            "Presentation Golden Scenarios are a separate future family",
        ):
            self.assertIn(required, contents)


if __name__ == "__main__":
    unittest.main()
