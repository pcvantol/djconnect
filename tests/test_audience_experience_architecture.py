"""Regression coverage for the deferred Audience Experience boundary."""

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
DOCUMENT = ROOT / "docs/product/AUDIENCE_EXPERIENCE_ARCHITECTURE.md"


class AudienceExperienceArchitectureTest(unittest.TestCase):
    """Keep participant reactions separate from Session Intelligence."""

    def _contents(self) -> str:
        return " ".join(DOCUMENT.read_text().split())

    def test_events_are_ephemeral_participant_context_not_dj_moments(self) -> None:
        contents = self._contents()

        for required in (
            "Audience Experience",
            "immutable, ephemeral, participant-originated",
            "independent of DJMoment identity",
            "Heart;",
            "Love;",
            "Applause; and",
            "Cheer.",
            "Audience Events are not DJMoments",
        ):
            self.assertIn(required, contents)

    def test_projection_and_audience_layer_are_renderer_safe_and_non_authoritative(self) -> None:
        contents = self._contents()

        for required in (
            "Audience Projection",
            "privacy-filtered and renderer-safe",
            "Audience Layer",
            "never replaces, dismisses or obscures the DJMoment Layer",
            "Audience Presentation Pressure",
            "never rewrite the underlying immutable",
        ):
            self.assertIn(required, contents)

    def test_planner_and_persistent_preference_boundaries_remain_deferred(self) -> None:
        contents = self._contents()

        for required in (
            "does not authorize the Planner to consume Audience Events",
            "Planner must never receive individual reactions",
            "a Spotify Like",
            "Music DNA preference",
            "must not automatically enter Performance Memory",
            "No Planner integration is authorized here",
        ):
            self.assertIn(required, contents)

    def test_ambient_and_vibecast_examples_do_not_add_implementation(self) -> None:
        contents = self._contents()

        for required in (
            "VibeCast is an illustrative future Ambient presentation",
            "social-feed wall",
            "Ambient Light Renderer",
            "No lighting work is authorized",
            "This definition does not authorize reaction submission",
        ):
            self.assertIn(required, contents)

    def test_canonical_navigation_links_the_single_definition(self) -> None:
        for name in (
            "PRODUCT_LANGUAGE.md",
            "PRODUCT_ROADMAP.md",
            "ROADMAP_INDEX.md",
            "INNOVATION_BACKLOG.md",
            "docs/product/README.md",
            "docs/product/DJ_PRESENTATION_ARCHITECTURE.md",
            "docs/product/VIBECAST_ARCHITECTURE.md",
            "docs/technical/AMBIENT_LIGHT_RENDERER_HOST_ARCHITECTURE.md",
            "DJ_SESSION_RUNTIME_CONTRACTS.md",
        ):
            self.assertIn(
                "AUDIENCE_EXPERIENCE_ARCHITECTURE.md",
                (ROOT / name).read_text(),
                name,
            )


if __name__ == "__main__":
    unittest.main()
