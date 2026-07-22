"""Regression coverage for the deferred Ambient Light Renderer Host boundary."""

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
DOCUMENT = ROOT / "docs/technical/AMBIENT_LIGHT_RENDERER_HOST_ARCHITECTURE.md"


class AmbientLightRendererHostArchitectureTest(unittest.TestCase):
    """Keep lighting presentation intent-driven and outside Runtime ownership."""

    def test_renderer_role_consumes_existing_semantic_presentation(self) -> None:
        contents = DOCUMENT.read_text()

        for required in (
            "Ambient Light Renderer Host",
            "same immutable DJMoment and",
            "Presentation Intent",
            "Visual Renderer Host, Audio Renderer Host and Ambient Light Renderer Host",
            "Device Lifecycle (Guest/Registered)",
            "Experience Mode (Interactive/Ambient)",
        ):
            self.assertIn(required, contents)

    def test_raw_audio_and_lighting_implementations_remain_out_of_scope(self) -> None:
        contents = DOCUMENT.read_text()

        for required in (
            "do not synchronize to raw audio",
            "beat detection",
            "FFT",
            "raw-audio synchronization",
            "WLED, Philips Hue, ESPHome light devices",
            "does not implement or authorize WLED, Hue, ESPHome",
        ):
            self.assertIn(required, contents)

    def test_mood_routing_and_deferred_navigation_are_preserved(self) -> None:
        contents = DOCUMENT.read_text()

        for required in (
            "Mood remains the dominant influence",
            "Room Presentation Context",
            "never communicate directly with another Renderer Host",
            "Universal Receiver product experience has matured",
            "Room Presentation Routing is operational",
            "practical evaluation on real hardware is possible",
        ):
            self.assertIn(required, contents)

        for name in (
            "PRODUCT_LANGUAGE.md",
            "PRODUCT_ROADMAP.md",
            "ROADMAP_INDEX.md",
            "docs/product/DJ_PRESENTATION_ARCHITECTURE.md",
            "docs/technical/RENDERER_HOST_CLASSIFICATION.md",
            "docs/technical/ROOM_PRESENTATION_ROUTING_ARCHITECTURE.md",
            "docs/technical/PLATFORM_AMBIENT_EXPERIENCE.md",
        ):
            self.assertIn(
                "AMBIENT_LIGHT_RENDERER_HOST_ARCHITECTURE.md",
                (ROOT / name).read_text(),
                name,
            )


if __name__ == "__main__":
    unittest.main()
