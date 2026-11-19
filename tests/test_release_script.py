"""Regression tests for the DJConnect release helper."""

from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "release.sh"


class ReleaseScriptTest(unittest.TestCase):
    """Validate release helper safety checks that are easy to regress."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.text = SCRIPT.read_text()

    def test_pushes_current_release_commit_to_main(self) -> None:
        self.assertIn('run git push origin HEAD:main', self.text)
        self.assertNotIn('run git push origin main', self.text)

    def test_checks_head_is_based_on_origin_main(self) -> None:
        self.assertIn('git fetch origin main --tags', self.text)
        self.assertIn('git merge-base --is-ancestor origin/main HEAD', self.text)
        self.assertIn('Current HEAD is not based on origin/main', self.text)

    def test_release_notes_use_current_changelog_section(self) -> None:
        self.assertIn('write_release_notes()', self.text)
        self.assertIn('extract CHANGELOG.md section for ${VERSION}', self.text)
        self.assertIn('--notes-file "$RELEASE_NOTES_FILE"', self.text)
        self.assertNotIn('--notes-file CHANGELOG.md', self.text)

    def test_release_notes_dry_run_does_not_require_mutated_changelog(self) -> None:
        self.assertIn('dry_run = os.environ["DRY_RUN"] == "true"', self.text)
        self.assertIn("Dry-run release notes", self.text)

    def test_release_updates_version_sensitive_context_docs(self) -> None:
        for path in ("CHAT_BOOTSTRAP.md", "HANDOFF.md", "SYNC_PROMPTS.md"):
            with self.subTest(path=path):
                self.assertIn(f'"{path}"', self.text)
        self.assertIn("Laatste release", self.text)
        self.assertIn("Current integration release", self.text)
        self.assertIn("aligned after Home Assistant integration release", self.text)


if __name__ == "__main__":
    unittest.main()
