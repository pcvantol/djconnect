"""Regression coverage for the canonical Presentation capability model."""

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
DOCUMENT = ROOT / "docs" / "product" / "PRESENTATION_CAPABILITY_ARCHITECTURE.md"


class PresentationCapabilityArchitectureTest(unittest.TestCase):
    """Keep capability ownership independent and renderer-neutral."""

    def _contents(self) -> str:
        return " ".join(DOCUMENT.read_text().split())

    def test_presentation_hierarchy_and_current_capability_are_explicit(self) -> None:
        contents = self._contents()

        for required in (
            "DJMoment -> Presentation -> Presentation Capabilities",
            "Presentation represents exactly one approved DJMoment.",
            "Speech Presentation CURRENT",
            "Speech is not the Presentation; it is the first implemented Presentation Capability.",
        ):
            self.assertIn(required, contents)

    def test_deferred_capabilities_are_independent(self) -> None:
        contents = self._contents()

        for required in (
            "Visual Presentation DEFERRED",
            "Ambient Presentation DEFERRED",
            "Audience Presentation DEFERRED",
            "Ambient Light Presentation DEFERRED",
            "Capabilities are orthogonal. No capability owns another capability",
        ):
            self.assertIn(required, contents)

    def test_ownership_and_renderer_consumption_remain_bounded(self) -> None:
        contents = self._contents()

        for required in (
            "Composes the complete immutable Presentation from one approved DJMoment.",
            "Distributes renderer-safe Presentation Projections.",
            "Independently consumes the capabilities it supports and renders locally.",
            "not a server-side negotiation protocol",
            "No Renderer Host changes the supplied capability",
            "Presentation Composer never selects a Renderer Host, device or Home Assistant Area.",
        ):
            self.assertIn(required, contents)

    def test_capability_independence_and_deferred_evolution_are_recorded(self) -> None:
        contents = self._contents()

        for required in (
            "Speech unavailable -> Visual Presentation remains valid",
            "Visual unavailable -> Speech Presentation remains valid",
            "Ambient unavailable -> Speech and Visual Presentation remain valid",
            "Speech -> Visual -> Ambient -> Audience -> Ambient Light",
            "does not authorize any future implementation",
        ):
            self.assertIn(required, contents)


if __name__ == "__main__":
    unittest.main()
