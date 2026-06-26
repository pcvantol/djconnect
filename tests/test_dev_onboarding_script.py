"""Contract tests for the macOS developer onboarding helper."""

from __future__ import annotations

import os
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "dev_onboarding_macos.sh"


def run_script(*args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["NO_COLOR"] = "1"
    return subprocess.run(
        [str(SCRIPT), *args],
        cwd=ROOT,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )


class DevOnboardingScriptTests(unittest.TestCase):
    def test_help_documents_testability_flags(self) -> None:
        result = run_script("--help")

        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("--dry-run", result.stdout)
        self.assertIn("--plan", result.stdout)
        self.assertIn("--no-color", result.stdout)
        self.assertIn("--windows-vm-name", result.stdout)
        self.assertIn("--windows-iso", result.stdout)

    def test_all_plan_includes_preflight_and_excludes_apply_upgrades(self) -> None:
        result = run_script("--all", "--plan", "--no-color")

        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("PLAN  0. Preflight", result.stdout)
        self.assertIn("PLAN 23. Check package manager upgrades", result.stdout)
        self.assertNotIn("PLAN 24. Apply package manager upgrades", result.stdout)

    def test_core_plan_uses_shifted_core_steps(self) -> None:
        result = run_script("--core", "--plan", "--no-color")

        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("PLAN  3. Xcode Command Line Tools + Homebrew", result.stdout)
        self.assertIn("PLAN 12. GitHub/Codex auth checks and summary", result.stdout)
        self.assertNotIn("PLAN  1. Download/bootstrap", result.stdout)

    def test_apply_upgrades_requires_explicit_flag(self) -> None:
        result = run_script("--steps", "24", "--no-log-file", "--no-color")

        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn("Step 24 requires --apply-upgrades", result.stdout)

    def test_apply_upgrades_dry_run_prints_mutating_commands(self) -> None:
        result = run_script(
            "--steps",
            "24",
            "--apply-upgrades",
            "--dry-run",
            "--no-log-file",
            "--no-color",
        )

        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("DRY brew update", result.stdout)
        self.assertIn("DRY brew upgrade", result.stdout)

    def test_vm_bootstrap_dry_run_prints_macos_commands(self) -> None:
        result = run_script(
            "--steps",
            "1",
            "--macos-version",
            "15.5",
            "--dry-run",
            "--no-log-file",
            "--no-color",
        )

        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("DRY softwareupdate --fetch-full-installer", result.stdout)
        self.assertIn("DRY open -a", result.stdout)
        self.assertIn("DRY prlctl create", result.stdout)

    def test_vm_bootstrap_dry_run_prints_windows_commands(self) -> None:
        result = run_script(
            "--steps",
            "2",
            "--windows-vm-name",
            "DJConnect Windows Test",
            "--dry-run",
            "--no-log-file",
            "--no-color",
        )

        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("Preparing Parallels Windows 11 ARM VM bootstrap", result.stdout)
        self.assertIn("DRY open -a", result.stdout)
        self.assertIn("DRY prlctl create", result.stdout)

    def test_ci_smoke_requires_explicit_push_flag(self) -> None:
        result = run_script("--steps", "26", "--no-log-file", "--no-color")

        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn("Step 26 requires --run-ci-push", result.stdout)

    def test_ci_smoke_dry_run_prints_git_push_commands(self) -> None:
        result = run_script(
            "--steps",
            "26",
            "--run-ci-push",
            "--dry-run",
            "--ci-branch",
            "codex/test-ci-smoke",
            "--no-log-file",
            "--no-color",
        )

        if result.returncode != 0 and "GitHub CLI is not authenticated" in result.stdout:
            self.skipTest("GitHub CLI is not authenticated in this environment")
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("DRY cd", result.stdout)
        self.assertIn("git switch -c codex/test-ci-smoke", result.stdout)
        self.assertIn("git push -u origin codex/test-ci-smoke", result.stdout)

    def test_e2e_local_dry_run_is_plan_addressable(self) -> None:
        result = run_script("--steps", "25", "--plan", "--no-color")

        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("PLAN 25. Local E2E release/build smoke checks", result.stdout)


if __name__ == "__main__":
    unittest.main()
