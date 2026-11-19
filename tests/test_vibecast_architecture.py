"""Regression coverage for the canonical deferred VibeCast product boundary."""

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
DOCUMENT = ROOT / "docs/product/VIBECAST_ARCHITECTURE.md"


class VibeCastArchitectureTest(unittest.TestCase):
    """Keep VibeCast web-rendered, bounded and server-owned."""

    def test_host_model_is_local_web_rendering_not_pixel_streaming(self) -> None:
        contents = DOCUMENT.read_text()

        for required in (
            "ambient-first, minimally interactive web-renderer",
            "Google Cast Custom Web Receiver",
            "Google TV",
            "Universal Receiver Web Platform",
            "DJConnect Broadcast projections",
            "local HTML / CSS / JavaScript rendering on the television",
            "does not continuously render or stream VibeCast pixels",
        ):
            self.assertIn(required, contents)

    def test_runtime_and_playback_ownership_remain_server_and_backend_owned(self) -> None:
        contents = DOCUMENT.read_text()

        for required in (
            "Runtime, Planner, Knowledge Engine, DJ Moment Engine",
            "Session Flow and",
            "Broadcast remain server-owned",
            "VibeCast never mutates Session state locally",
            "DJConnect Session Command",
            "VibeCast never becomes the music playback target",
            "Automatic music-volume ducking is not V1",
        ):
            self.assertIn(required, contents)

    def test_boundaries_and_prerequisite_questions_are_explicit(self) -> None:
        contents = DOCUMENT.read_text()

        for required in (
            "AirPlay mirroring and video streaming are outside VibeCast architecture",
            "not a native Google TV or Android TV application",
            "renderer-to-renderer communication",
            "must not receive permanent DJConnect credentials",
            "Implementation-entry validation",
            "Golden Smoke CI",
            "Custom Web Receiver feasibility",
        ):
            self.assertIn(required, contents)

    def test_canonical_navigation_uses_the_single_definition(self) -> None:
        for name in (
            "PRODUCT_LANGUAGE.md",
            "PRODUCT_ROADMAP.md",
            "ROADMAP_INDEX.md",
            "CLIENT_CAPABILITY_MATRIX.md",
            "docs/product/README.md",
            "docs/technical/UNIVERSAL_RECEIVER_ARCHITECTURE.md",
            "docs/technical/RENDERER_HOST_CLASSIFICATION.md",
        ):
            self.assertIn(
                "VIBECAST_ARCHITECTURE.md",
                (ROOT / name).read_text(),
                name,
            )


if __name__ == "__main__":
    unittest.main()
