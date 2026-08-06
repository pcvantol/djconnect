from __future__ import annotations

import json
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "custom_components" / "djconnect" / "manifest.json"
CONSTANTS = ROOT / "custom_components" / "djconnect" / "const.py"
CHANGELOG = ROOT / "CHANGELOG.md"


class HacsReleaseMetadataTest(unittest.TestCase):
    """Keep the public HACS release metadata internally consistent."""

    def test_manifest_const_and_changelog_agree_on_current_release(self) -> None:
        manifest_version = json.loads(MANIFEST.read_text(encoding="utf-8"))["version"]
        constants = CONSTANTS.read_text(encoding="utf-8")
        version_match = re.search(r'^VERSION = "(?P<version>[^\"]+)"$', constants, re.M)

        self.assertIsNotNone(version_match)
        self.assertEqual(version_match["version"], manifest_version)
        self.assertRegex(
            manifest_version,
            r"^\d+\.\d+\.\d+(?:-[0-9A-Za-z]+(?:\.[0-9A-Za-z]+)*)?$",
        )
        self.assertIn(f"## {manifest_version}\n", CHANGELOG.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
