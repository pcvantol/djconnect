"""Regression coverage for the deferred Room Presentation Routing boundary."""

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
ROUTING_DOCUMENT = ROOT / "docs/technical/ROOM_PRESENTATION_ROUTING_ARCHITECTURE.md"


class RoomPresentationRoutingArchitectureTest(unittest.TestCase):
    """Keep room delivery distinct from Runtime ownership and host behavior."""

    def test_routing_is_area_scoped_and_runtime_ephemeral(self) -> None:
        contents = ROUTING_DOCUMENT.read_text()

        for required in (
            "Room Presentation Context",
            "Runtime-scoped",
            "ephemeral",
            "destroyed with that Session",
            "Home Assistant entity",
            "Device Registry",
            "Area Registry",
            "Active Home Assistant Area",
        ):
            self.assertIn(required, contents)

    def test_routing_preserves_independent_renderer_and_moment_ownership(self) -> None:
        contents = ROUTING_DOCUMENT.read_text()

        for required in (
            "same immutable DJMoment",
            "Visual Renderer Host",
            "Audio Renderer Host",
            "Renderer-to-Renderer coordination",
            "does not create a master Renderer Host",
            "Session Runtime / DJ Moment Engine",
            "Broadcast",
        ):
            self.assertIn(required, contents)

    def test_unresolved_area_disables_speech_and_navigation_is_canonical(self) -> None:
        contents = ROUTING_DOCUMENT.read_text()

        self.assertIn("must not autonomously present speech in an arbitrary room", contents)
        self.assertIn("Speech routing stays\ndisabled", contents)

        for name in (
            "ROADMAP_INDEX.md",
            "PRODUCT_ROADMAP.md",
            "CLIENT_CAPABILITY_MATRIX.md",
            "docs/product/DJ_PRESENTATION_ARCHITECTURE.md",
            "docs/technical/RENDERER_HOST_CLASSIFICATION.md",
            "docs/technical/PLATFORM_AMBIENT_EXPERIENCE.md",
        ):
            self.assertIn(
                "ROOM_PRESENTATION_ROUTING_ARCHITECTURE.md",
                (ROOT / name).read_text(),
                name,
            )


if __name__ == "__main__":
    unittest.main()
