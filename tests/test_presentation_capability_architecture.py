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
            "approved immutable DJMoment -> Presentation Composer -> Presentation",
            "Presentation represents exactly one approved DJMoment.",
            "existing renderer-safe visual Presentation CURRENT, AUTHORITATIVE",
            "Speech Presentation CURRENT, STRUCTURED",
            "first newly formalized structured Presentation Capability introduced by Presentation Composer.",
        ):
            self.assertIn(required, contents)

    def test_deferred_capabilities_are_independent(self) -> None:
        contents = self._contents()

        for required in (
            "Existing visual Presentation | Current",
            "Richer visual composition | Deferred",
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
            "Speech unavailable -> existing visual Presentation remains valid",
            "Future richer visual composition unavailable -> Speech and existing visual Presentation remain valid",
            "Ambient unavailable -> Speech and existing visual Presentation remain valid",
            "Speech -> richer visual composition -> Ambient -> Audience -> Ambient Light",
            "does not replace existing visual Presentation",
        ):
            self.assertIn(required, contents)

    def test_existing_visual_presentation_is_not_remodelled_or_deferred(self) -> None:
        contents = self._contents()

        for required in (
            "Existing renderer-safe visual Presentation remains authoritative",
            "Existing visual Presentation is not remodelled as a new capability",
            "It neither replaces nor supersedes existing visual Presentation.",
            "existing visual Presentation remains unchanged.",
        ):
            self.assertIn(required, contents)


if __name__ == "__main__":
    unittest.main()
