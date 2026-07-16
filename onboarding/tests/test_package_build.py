from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

from onboarding import build_package


class OnboardingPackageBuildTests(unittest.TestCase):
    def test_manifest_declares_versioned_runtime_and_test_components(self) -> None:
        self.assertEqual(build_package.manifest_value("package.name"), "djconnect-developer-onboarding")
        self.assertEqual(build_package.manifest_value("package.version"), "1.1.1")
        self.assertEqual(build_package.manifest_value("component.tests.path"), "tests/test_onboarding_scripts.py")
        self.assertEqual(build_package.manifest_value("component.changelog.path"), "CHANGELOG.md")

    def test_package_file_selection_excludes_generated_output(self) -> None:
        names = {path.relative_to(build_package.PACKAGE_ROOT).as_posix() for path in build_package.package_files()}
        self.assertIn("dev_onboarding_macos.sh", names)
        self.assertIn("tests/test_package_build.py", names)
        self.assertFalse(any(name.startswith("dist/") or "__pycache__" in name for name in names))

    def test_build_emits_deterministic_versioned_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            first_artifacts = build_package.build(Path(first))
            second_artifacts = build_package.build(Path(second))
            self.assertEqual([item.name for item in first_artifacts], [item.name for item in second_artifacts])
            self.assertEqual(first_artifacts[0].read_bytes(), second_artifacts[0].read_bytes())
            metadata = json.loads(first_artifacts[2].read_text(encoding="utf-8"))
            self.assertEqual(metadata["version"], "1.1.1")
            self.assertEqual(metadata["sha256"], hashlib.sha256(first_artifacts[0].read_bytes()).hexdigest())
            with zipfile.ZipFile(first_artifacts[0]) as archive:
                self.assertIn("onboarding/dev_onboarding_macos.sh", archive.namelist())
                self.assertIn("onboarding/dev_onboarding_windows.ps1", archive.namelist())
                self.assertIn("onboarding/tests/test_onboarding_scripts.py", archive.namelist())
                self.assertIn("onboarding/CHANGELOG.md", archive.namelist())

    def test_macos_preflight_requires_current_major_security_patches(self) -> None:
        source = (build_package.PACKAGE_ROOT / "dev_onboarding_macos.sh").read_text(encoding="utf-8")

        self.assertIn("preflight_macos_security_patches()", source)
        self.assertIn("softwareupdate --list", source)
        self.assertIn("macOS[^0-9]*${macos_major}", source)
        self.assertIn("System Settings > General > Software Update", source)

    def test_check_mode_rejects_stale_distribution_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            build_package.build(output)
            checksum = next(output.glob("*.sha256"))
            checksum.write_text("stale\n", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(build_package.PACKAGE_ROOT / "build_package.py"), "--output", str(output), "--check"],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False,
            )
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn("missing or stale", result.stdout)
