"""Regression coverage for Presentation Composer architecture navigation."""

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
DOCUMENT = ROOT / "docs/product/PRESENTATION_COMPOSER_ARCHITECTURE.md"


class PresentationComposerArchitectureTest(unittest.TestCase):
    """Keep Presentation composition server-owned and bounded."""

    def _contents(self) -> str:
        return " ".join(DOCUMENT.read_text().split())

    def test_composer_ownership_and_pipeline_are_explicit(self) -> None:
        contents = self._contents()

        for required in (
            "Presentation Composer transforms exactly one approved immutable DJMoment into exactly one immutable, renderer-safe Presentation.",
            "Presentation Composer is a first-class server component of the Presentation Platform.",
            "It is neither a Planner, Knowledge Engine, DJ Moment Engine nor a second Session Runtime.",
            "It never creates a DJMoment or independent knowledge.",
            "Renderer Hosts receive immutable Presentations and render them locally.",
        ):
            self.assertIn(required, contents)

    def test_speech_roles_and_sidekick_boundary_remain_bounded(self) -> None:
        contents = self._contents()

        for required in (
            "Speech Presentation",
            "Speaker Role",
            "`DJ` and `Sidekick`",
            "Primary Only",
            "Primary With Sidekick",
            "not a second DJ, Planner, Knowledge Engine, Runtime or autonomous AI agent",
            "Artist Story",
            "repeats that approved summary verbatim",
            "Every other eligible speech-bearing Moment falls back deterministically to Primary Only.",
        ):
            self.assertIn(required, contents)

    def test_deferred_capabilities_and_canonical_navigation_are_recorded(self) -> None:
        contents = self._contents()

        for required in (
            "DJ–Sidekick–DJ dialogue",
            "Presentation Cast",
            "Presentation Memory",
            "generative dialogue",
            "Ambient Light Presentation",
        ):
            self.assertIn(required, contents)

        for name in (
            "docs/product/README.md",
            "docs/product/DJ_PRESENTATION_ARCHITECTURE.md",
            "PLATFORM_OVERVIEW_ARCHITECTURE.md",
        ):
            self.assertIn("PRESENTATION_COMPOSER_ARCHITECTURE.md", (ROOT / name).read_text())


if __name__ == "__main__":
    unittest.main()
