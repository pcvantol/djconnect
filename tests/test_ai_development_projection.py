"""Regression coverage for the committed generic AI-development projection."""

from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
AI_DEVELOPMENT = ROOT / "docs" / "ai-development"
VALIDATOR = AI_DEVELOPMENT / "validate_projection.py"
SOURCE_SHA = "ec070e399ff4dbd92e760370002995fe4f4d52d6"


class AiDevelopmentProjectionTests(unittest.TestCase):
    def _validate(self, directory: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(directory / "validate_projection.py"),
                "--profile",
                "djconnect",
                "--source-commit",
                SOURCE_SHA,
                "--extension-identity",
                "DJCONNECT_DEVELOPMENT_EXTENSION",
            ],
            text=True,
            capture_output=True,
            check=False,
        )

    def test_projection_and_semantic_receipt_are_committed(self) -> None:
        result = self._validate(AI_DEVELOPMENT)
        self.assertEqual(result.returncode, 0, result.stderr)
        receipt = (ROOT / "docs/governance/AI_DEVELOPMENT_CONTRACT_SEMANTIC_EQUIVALENCE_RECEIPT.md").read_text()
        self.assertIn("Unresolved semantic units: `0`", receipt)
        self.assertIn("Central-contract gaps: `0`", receipt)
        self.assertIn("ZERO-LOSS PASS", receipt)

    def test_generated_projection_drift_fails_but_extension_is_not_projection_input(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            copied = Path(temporary) / "ai-development"
            shutil.copytree(AI_DEVELOPMENT, copied)
            self.assertEqual(self._validate(copied).returncode, 0)
            extension = copied / "DJCONNECT_DEVELOPMENT_EXTENSION.md"
            extension.write_text(extension.read_text() + "\nLocal extension can change.\n")
            self.assertEqual(self._validate(copied).returncode, 0)
            projection = copied / "GENERATED_PROJECTION.md"
            projection.write_text(projection.read_text() + "\nmanual change\n")
            self.assertNotEqual(self._validate(copied).returncode, 0)
