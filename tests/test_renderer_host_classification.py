"""Regression coverage for the canonical Renderer Host classification."""

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class RendererHostClassificationTest(unittest.TestCase):
    """Keep renderer lifecycle and experience axes independent."""

    def test_canonical_model_has_two_independent_axes(self) -> None:
        contents = (ROOT / "docs/technical/RENDERER_HOST_CLASSIFICATION.md").read_text()

        for required in (
            "Device Lifecycle",
            "Guest",
            "Registered",
            "Experience Mode",
            "Interactive",
            "Ambient",
            "Pairing therefore belongs solely to Device Lifecycle",
            "Runtime, Planner, Knowledge, Session Flow or Session pipeline",
        ):
            self.assertIn(required, contents)

    def test_canonical_positioning_preserves_renderer_boundaries(self) -> None:
        contents = (ROOT / "docs/technical/RENDERER_HOST_CLASSIFICATION.md").read_text()

        for required in (
            "VibeCast is the canonical DJConnect Ambient Renderer experience",
            "Guest + Ambient",
            "Raspberry Pi Wall Panel is a Registered + Interactive Renderer by default",
            "replace its QML",
            "local-first",
        ):
            self.assertIn(required, contents)

    def test_canonical_navigation_links_the_classification(self) -> None:
        for name in (
            "ROADMAP_INDEX.md",
            "PRODUCT_ROADMAP.md",
            "CLIENT_CAPABILITY_MATRIX.md",
            "docs/technical/UNIVERSAL_RECEIVER_ARCHITECTURE.md",
            "docs/technical/PLATFORM_AMBIENT_EXPERIENCE.md",
            "docs/product/DJ_PRESENTATION_ARCHITECTURE.md",
        ):
            self.assertIn(
                "RENDERER_HOST_CLASSIFICATION.md", (ROOT / name).read_text(), name
            )


if __name__ == "__main__":
    unittest.main()
