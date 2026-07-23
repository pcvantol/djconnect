"""Regression coverage for the descriptive Platform Overview Architecture."""

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
DOCUMENT = ROOT / "PLATFORM_OVERVIEW_ARCHITECTURE.md"


class PlatformOverviewArchitectureTest(unittest.TestCase):
    """Keep the overview descriptive and its platform boundaries explicit."""

    def _contents(self) -> str:
        return " ".join(DOCUMENT.read_text().split())

    def test_all_existing_platforms_and_responsibilities_are_present(self) -> None:
        contents = self._contents()

        for required in (
            "Profile Platform",
            "Playback Platform",
            "Session Intelligence Platform",
            "Presentation Platform",
            "Verification Platform",
            "Session Intelligence Platform determines **what should happen**",
            "Presentation Platform determines **how Session Intelligence is experienced**",
            "Verification Platform determines **whether implementation conforms to approved behaviour**",
        ):
            self.assertIn(required, contents)

    def test_ownership_and_execution_separation_remain_explicit(self) -> None:
        contents = self._contents()

        for required in (
            "Playback ownership never migrates into Session Intelligence or Renderer Hosts.",
            "does not own backend playback, Renderer Host presentation or persistent Profile state.",
            "none owns the Runtime, Planner, Knowledge Engine, DJ Moment Engine, Session Flow or playback.",
            "never becomes the Session Runtime",
            "does not participate in Runtime execution.",
        ):
            self.assertIn(required, contents)

    def test_conceptual_relationship_keeps_verification_orthogonal(self) -> None:
        contents = self._contents()

        for required in (
            "Profile Platform ↓ Playback Platform ↓ Session Intelligence Platform ↓ Broadcast ↓ Presentation Platform",
            "Verification Platform — orthogonal behavioural proof",
            "without joining this Runtime path.",
        ):
            self.assertIn(required, contents)

    def test_overview_stays_descriptive_and_uses_canonical_navigation(self) -> None:
        contents = self._contents()

        for required in (
            "introduces no implementation work or new architecture",
            "linked canonical documents remain authoritative",
            "This history provides orientation only",
            "not additional principles.",
        ):
            self.assertIn(required, contents)

        for name in ("FOUNDATION_INDEX.md", "CANONICAL_REFERENCES.md"):
            self.assertIn("PLATFORM_OVERVIEW_ARCHITECTURE.md", (ROOT / name).read_text())


if __name__ == "__main__":
    unittest.main()
