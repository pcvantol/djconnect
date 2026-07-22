"""Regression coverage for Audio Renderer Host terminology boundaries."""

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
DOCUMENT = ROOT / "docs/technical/AUDIO_RENDERER_HOST_ARCHITECTURE.md"


class AudioRendererHostArchitectureTest(unittest.TestCase):
    """Keep internal audio presentation distinct from Home Assistant terminology."""

    def test_voice_satellite_and_audio_renderer_host_have_distinct_contexts(self) -> None:
        contents = DOCUMENT.read_text()

        for required in (
            "Voice Satellite",
            "Audio Renderer Host",
            "Home Assistant documentation, entities, configuration and UI",
            "internal,\nplatform-neutral presentation abstraction",
            "one current\nimplementation of an Audio Renderer Host",
        ):
            self.assertIn(required, contents)

    def test_audio_role_preserves_renderer_and_runtime_boundaries(self) -> None:
        contents = DOCUMENT.read_text()

        for required in (
            "same immutable DJMoment and",
            "Presentation Intent",
            "Session Runtime, Planner, Knowledge Engine, DJ Moment",
            "Ambient is an\nexperience mode, not a third host role",
            "must not autonomously route\nspeech to an arbitrary room",
        ):
            self.assertIn(required, contents)

    def test_canonical_navigation_and_cross_references_are_present(self) -> None:
        for name in (
            "PRODUCT_LANGUAGE.md",
            "PRODUCT_ROADMAP.md",
            "ROADMAP_INDEX.md",
            "CLIENT_CAPABILITY_MATRIX.md",
            "docs/product/DJ_PRESENTATION_ARCHITECTURE.md",
            "docs/technical/RENDERER_HOST_CLASSIFICATION.md",
            "docs/technical/ROOM_PRESENTATION_ROUTING_ARCHITECTURE.md",
        ):
            self.assertIn(
                "AUDIO_RENDERER_HOST_ARCHITECTURE.md",
                (ROOT / name).read_text(),
                name,
            )


if __name__ == "__main__":
    unittest.main()
