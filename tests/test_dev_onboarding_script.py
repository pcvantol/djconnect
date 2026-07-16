"""Contract tests for developer onboarding helpers."""

from __future__ import annotations

import os
import shutil
import sys
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "dev_onboarding_macos.sh"
WINDOWS_SCRIPT = ROOT / "tools" / "dev_onboarding_windows.ps1"
RUNNER_RECOVERY_SCRIPT = ROOT / "scripts" / "runner" / "bootstrap_macos_runner_host.sh"
WINDOWS_RUNNER_RECOVERY_SCRIPT = ROOT / "scripts" / "runner" / "bootstrap_windows_arm64_runner.ps1"


def run_script(*args: str, stdin: str | None = None) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["NO_COLOR"] = "1"
    return subprocess.run(
        [str(SCRIPT), *args],
        cwd=ROOT,
        env=env,
        text=True,
        input=stdin,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )


def run_script_with_env(
    extra_env: dict[str, str],
    *args: str,
    stdin: str | None = None,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.update(extra_env)
    env["NO_COLOR"] = "1"
    return subprocess.run(
        [str(SCRIPT), *args],
        cwd=ROOT,
        env=env,
        text=True,
        input=stdin,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )


def run_windows_script(*args: str, stdin: str | None = None) -> subprocess.CompletedProcess[str]:
    executable = "pwsh"
    env = os.environ.copy()
    env["NO_COLOR"] = "1"
    return subprocess.run(
        [executable, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(WINDOWS_SCRIPT), *args],
        cwd=ROOT,
        env=env,
        text=True,
        input=stdin,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )


def run_windows_script_with_env(
    extra_env: dict[str, str],
    *args: str,
    stdin: str | None = None,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.update(extra_env)
    env["NO_COLOR"] = "1"
    return subprocess.run(
        ["pwsh", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(WINDOWS_SCRIPT), *args],
        cwd=ROOT,
        env=env,
        text=True,
        input=stdin,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )


@unittest.skipUnless(sys.platform == "darwin", "macOS onboarding script tests require Darwin")
class DevOnboardingScriptTests(unittest.TestCase):
    def test_macos_runner_recovery_bootstrap_has_no_token_argument(self) -> None:
        result = subprocess.run(
            [str(RUNNER_RECOVERY_SCRIPT), "--help"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("short-lived token per repository", result.stdout)
        self.assertNotIn("--token", result.stdout)
        source = RUNNER_RECOVERY_SCRIPT.read_text()
        self.assertIn("registration-token", source)
        self.assertIn("djconnect-apple-macos", source)
        self.assertIn("RUNNER_ARCHIVE_DIGEST", source)
        self.assertIn("--xcode-version", source)
        self.assertIn("set-key-partition-list", source)
        self.assertIn("--install-parallels", source)
        self.assertIn("brew install --cask parallels", source)
        self.assertIn("dev_onboarding_macos.sh --all --yes --warm-sudo", source)
        self.assertIn("install_macos_ci_tooling_maintenance.sh --run-now", source)

    def test_windows_runner_recovery_bootstrap_keeps_tokens_off_the_cli(self) -> None:
        source = WINDOWS_RUNNER_RECOVERY_SCRIPT.read_text()

        self.assertIn("actions-runner-win-arm64", source)
        self.assertIn("registration-token", source)
        self.assertIn("Get-FileHash -Algorithm SHA256", source)
        self.assertIn("--runasservice", source)
        self.assertIn("NT AUTHORITY\\NETWORK SERVICE", source)
        self.assertIn("Git.Git", source)
        self.assertIn("Python.Python.3.12", source)
        self.assertIn("OpenJS.NodeJS.LTS", source)
        self.assertIn("workload restore", source)
        self.assertNotIn("[string] $RegistrationToken", source)

    def test_help_documents_testability_flags(self) -> None:
        result = run_script("--help")

        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("--dry-run", result.stdout)
        self.assertIn("--plan", result.stdout)
        self.assertIn("--no-color", result.stdout)
        self.assertIn("--ha-compose-file", result.stdout)
        self.assertNotIn("--windows-vm-name", result.stdout)
        self.assertNotIn("--windows-iso", result.stdout)
        self.assertNotIn("--macos-version", result.stdout)
        self.assertIn("--ma-data-dir", result.stdout)
        self.assertIn("--ngrok-domain", result.stdout)
        self.assertIn("DJCONNECT_HA_WS_URL", result.stdout)
        self.assertIn("DJCONNECT_HA_TOKEN", result.stdout)
        self.assertIn("NGROK_AUTHTOKEN", result.stdout)
        self.assertIn("@openai/codex", SCRIPT.read_text())
        self.assertIn("npm bin -g", SCRIPT.read_text())

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
        self.assertNotIn("PLAN  2. Download/bootstrap", result.stdout)

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

    def test_removed_vm_bootstrap_steps_are_rejected(self) -> None:
        for step in ("1", "2"):
            with self.subTest(step=step):
                result = run_script("--steps", step, "--no-log-file", "--no-color")

                self.assertNotEqual(result.returncode, 0, result.stdout)
                self.assertIn(
                    f"Step {step} was removed. VM bootstrap is intentionally outside the onboarding script.",
                    result.stdout,
                )

    def test_home_assistant_dry_run_uses_docker_compose(self) -> None:
        result = run_script(
            "--steps",
            "9",
            "--dry-run",
            "--ha-compose-file",
            "/tmp/djconnect-ha-compose.yml",
            "--no-log-file",
            "--no-color",
        )

        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("Using Docker Compose file: /tmp/djconnect-ha-compose.yml", result.stdout)
        self.assertIn("DRY add homeassistant service to /tmp/djconnect-ha-compose.yml", result.stdout)
        self.assertIn("DRY docker compose -f /tmp/djconnect-ha-compose.yml up -d homeassistant", result.stdout)
        self.assertNotIn("docker run -d", result.stdout)

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

    def test_e2e_local_dry_run_can_print_websocket_capability_smoke(self) -> None:
        result = run_script_with_env(
            {
                "DJCONNECT_HA_WS_URL": "ws://localhost:8123/api/websocket",
                "DJCONNECT_HA_TOKEN": "secret-token",
            },
            "--steps",
            "25",
            "--dry-run",
            "--no-log-file",
            "--no-color",
        )

        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("DJCONNECT_HA_WS_URL=ws://localhost:8123/api/websocket", result.stdout)
        self.assertIn("DJCONNECT_HA_TOKEN=\\<redacted\\>", result.stdout)
        self.assertNotIn("secret-token", result.stdout)

    def test_music_assistant_step_is_plan_addressable(self) -> None:
        result = run_script("--steps", "27", "--plan", "--no-color")

        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn(
            "PLAN 27. Install/start local HA voice/backend Docker Compose stack",
            result.stdout,
        )

    def test_music_assistant_dry_run_prints_docker_commands(self) -> None:
        result = run_script(
            "--steps",
            "27",
            "--dry-run",
            "--ha-compose-file",
            "/tmp/djconnect-ha-compose.yml",
            "--ma-data-dir",
            "/tmp/djconnect-mass-test",
            "--no-log-file",
            "--no-color",
        )

        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("Using Docker Compose file: /tmp/djconnect-ha-compose.yml", result.stdout)
        self.assertIn(
            "DRY add missing homeassistant, whisper, piper and music-assistant services to /tmp/djconnect-ha-compose.yml",
            result.stdout,
        )
        self.assertIn("data dir /tmp/djconnect-mass-test", result.stdout)
        self.assertIn("whisper image rhasspy/wyoming-whisper", result.stdout)
        self.assertIn("piper image rhasspy/wyoming-piper", result.stdout)
        self.assertIn(
            "DRY docker compose -f /tmp/djconnect-ha-compose.yml up -d homeassistant whisper piper music-assistant",
            result.stdout,
        )
        self.assertIn("ghcr.io/music-assistant/server:latest", result.stdout)
        self.assertIn("DRY curl -fsS http://localhost:8095", result.stdout)

    def test_ngrok_step_is_plan_addressable(self) -> None:
        result = run_script("--steps", "28", "--plan", "--no-color")

        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn(
            "PLAN 28. Install/start persistent ngrok tunnel for local Home Assistant",
            result.stdout,
        )

    def test_ngrok_dry_run_prints_launchagent_and_ha_config(self) -> None:
        result = run_script_with_env(
            {"NGROK_AUTHTOKEN": "secret-ngrok-token"},
            "--steps",
            "28",
            "--ngrok-domain",
            "victory-curvy-refold.ngrok-free.dev",
            "--dry-run",
            "--no-log-file",
            "--no-color",
        )

        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("DRY ngrok config add-authtoken \\<redacted\\>", result.stdout)
        self.assertNotIn("secret-ngrok-token", result.stdout)
        self.assertIn("dev.djconnect.homeassistant.ngrok.plist", result.stdout)
        self.assertIn(
            "ngrok http --url=victory-curvy-refold.ngrok-free.dev 8123",
            result.stdout,
        )
        self.assertIn(
            "configure Home Assistant external/internal URL and trusted proxy settings as https://victory-curvy-refold.ngrok-free.dev",
            result.stdout,
        )


class WindowsDevOnboardingScriptTests(unittest.TestCase):
    def test_windows_script_exists_and_documents_core_flags(self) -> None:
        text = WINDOWS_SCRIPT.read_text()

        self.assertIn("Automates DJConnect developer onboarding on a Windows 11", text)
        self.assertIn("-DryRun", text)
        self.assertIn("-Plan", text)
        self.assertIn("-HaComposeFile", text)
        self.assertIn("-HaHostUrl", text)
        self.assertIn("-MaHostUrl", text)
        self.assertIn("-NgrokDomain", text)
        self.assertIn("Available steps:", text)
        self.assertIn("Write-StepMenu", text)
        self.assertIn("Invoke-InteractiveMenu", text)
        self.assertIn("Choose a step number, comma-separated steps, core/all, or q to quit", text)
        self.assertIn("Write-Styled", text)
        self.assertIn("Write-StatusLine", text)
        self.assertIn("Write-Dry", text)
        self.assertIn("Refresh-ProcessPath", text)
        self.assertIn("Get-GitCommandExpression", text)
        self.assertIn("Install-WingetPackage", text)
        self.assertIn("already installed", text)
        self.assertNotIn('Invoke-StepCommand "winget install --id Git.Git', text)
        self.assertIn("Invoke-PythonInDirectory", text)
        self.assertIn("Get-PythonCommandExpression", text)
        self.assertIn("py -3.11", text)
        self.assertIn("WindowsApps\\python.exe", text)
        self.assertIn("Microsoft Store python.exe alias", text)
        self.assertIn("PYTHONUTF8", text)
        self.assertIn("PYTHONIOENCODING", text)
        self.assertIn("python -X utf8", text)
        self.assertIn("npm install -g @openai/codex", text)
        self.assertIn("Enable-CurrentUserPowerShellScripts", text)
        self.assertIn("Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned -Force", text)
        self.assertIn("-ErrorAction SilentlyContinue", text)
        self.assertIn("open a new normal PowerShell terminal", text)
        self.assertIn("Test-CodexLaunchable", text)
        self.assertIn("codex.cmd", text)
        self.assertIn("codex available after npm install", text)
        self.assertIn("Add-GitSafeDirectory", text)
        self.assertIn("%(prefix)$slashPath", text)
        self.assertIn("Test-GitRepository", text)
        self.assertIn("Move-NonGitDirectoryAside", text)
        self.assertIn("New-CheckoutRootFallback", text)
        self.assertIn("Using fresh checkout root", text)
        self.assertIn("Get-CheckoutRootCandidates", text)
        self.assertIn("Resolve-CheckoutRepoPath", text)
        self.assertIn("Resolve-DjconnectRepoRoot", text)
        self.assertIn('Resolve-CheckoutRepoPath -RepoName "djconnect-windows"', text)
        self.assertIn("Command failed with exit code", text)
        self.assertIn('dotnet workload restore `"DJConnect.Windows.sln`"', text)
        self.assertIn("run step 3 first, then rerun step 6", text)
        self.assertNotIn('Invoke-StepCommand "dotnet workload restore"', text)
        self.assertIn("Get-DotNetSdkVersionFromGlobalJson", text)
        self.assertIn("Install-DotNetSdkVersion", text)
        self.assertIn("Microsoft.DotNet.SDK.10", text)
        self.assertIn("$HOME\\.dotnet", text)
        self.assertIn("dotnet-install.ps1", text)
        self.assertIn("Test-IsAdministrator", text)
        self.assertIn("Do not run this onboarding script as Administrator", text)
        self.assertIn("C:\\Program Files\\Git\\cmd\\git.exe", text)
        self.assertIn("Windows-local checkout root", text)
        self.assertIn("Use a local Windows path", text)
        self.assertIn("LocalDocuments\\GitHub\\djconnect", text)
        self.assertIn("GitHubRoot must be under the current user's home directory", text)
        self.assertNotIn('"C:\\Mac\\Home\\Documents\\GitHub\\djconnect"', text)
        self.assertIn("Running Windows machine, hardware, filesystem and network preflight.", text)
        self.assertIn("Test-WritableDirectory", text)
        self.assertIn("Test-DiskFree", text)
        self.assertIn("Test-PortStatus", text)
        self.assertIn("Test-NetworkEndpoint", text)
        self.assertIn("Test-HttpService", text)
        self.assertIn("https://registry-1.docker.io/v2/", text)
        self.assertNotIn('"Docker.DockerDesktop"', text)
        self.assertIn("NGROK_AUTHTOKEN", text)
        self.assertIn("DJCONNECT_HA_WS_URL", text)
        self.assertIn("DJCONNECT_HA_TOKEN", text)

    def test_macos_script_documents_interactive_menu(self) -> None:
        text = SCRIPT.read_text()

        self.assertIn("interactive_menu", text)
        self.assertIn("resolve_step_selection", text)
        self.assertIn("Choose a step number, comma-separated steps, core/all, or q to quit", text)
        self.assertIn("Omit --all/--core/--steps to open an interactive step menu.", text)

    def test_development_docs_cover_windows_onboarding_constraints(self) -> None:
        text = (ROOT / "DEVELOPMENT_ENVIRONMENT.md").read_text()

        self.assertIn("C:\\Users\\<user>\\LocalDocuments\\GitHub", text)
        self.assertIn("Windows 11 ARM in Parallels on Apple Silicon should not run Docker Desktop", text)
        self.assertIn("do not run it from an\nAdministrator terminal", text)
        self.assertIn("npm install -g @openai/codex", text)
        self.assertIn("RemoteSigned", text)
        self.assertIn("global.json", text)
        self.assertIn("C:\\Users\\<user>\\.dotnet", text)
        self.assertIn("idempotent around `winget` packages", text)

    @unittest.skipUnless(
        shutil.which("pwsh"),
        "PowerShell 7 is required to execute Windows onboarding script tests",
    )
    def test_windows_help_documents_testability_flags(self) -> None:
        result = run_windows_script("-Help")

        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("-DryRun", result.stdout)
        self.assertIn("-Plan", result.stdout)
        self.assertIn("-HaComposeFile", result.stdout)
        self.assertIn("-HaHostUrl", result.stdout)
        self.assertIn("-MaHostUrl", result.stdout)
        self.assertIn("-NgrokDomain", result.stdout)
        self.assertIn("Available steps:", result.stdout)
        self.assertIn("  0. Preflight", result.stdout)
        self.assertIn(" 14. CI smoke push", result.stdout)

    @unittest.skipUnless(
        shutil.which("pwsh"),
        "PowerShell 7 is required to execute Windows onboarding script tests",
    )
    def test_windows_default_start_shows_steps_without_running_preflight(self) -> None:
        result = run_windows_script("-NoLogFile", stdin="q\n")

        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("Available steps:", result.stdout)
        self.assertIn("  0. Preflight", result.stdout)
        self.assertIn("Examples:", result.stdout)
        self.assertIn("Exiting onboarding menu.", result.stdout)
        self.assertNotIn("Running Windows preflight checks", result.stdout)

    @unittest.skipUnless(
        shutil.which("pwsh"),
        "PowerShell 7 is required to execute Windows onboarding script tests",
    )
    def test_windows_interactive_menu_runs_selected_step_and_returns(self) -> None:
        result = run_windows_script("-DryRun", "-NoLogFile", "-Yes", stdin="8\nq\n")

        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("Checking Home Assistant published by the macOS host.", result.stdout)
        self.assertRegex(result.stdout, r"DRY\s+curl\.exe -fsS http://10\.211\.55\.2:8123")
        self.assertNotIn("Run step 8.", result.stdout)
        self.assertGreaterEqual(result.stdout.count("Available steps:"), 2)
        self.assertIn("Exiting onboarding menu.", result.stdout)

    @unittest.skipUnless(
        shutil.which("pwsh"),
        "PowerShell 7 is required to execute Windows onboarding script tests",
    )
    def test_windows_core_plan_is_addressable(self) -> None:
        result = run_windows_script("-Core", "-Plan")

        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("PLAN  0. Preflight", result.stdout)
        self.assertIn("PLAN  5. Run Home Assistant integration tests", result.stdout)
        self.assertIn("PLAN 11. Check voice/backend services on macOS host", result.stdout)
        self.assertNotIn("PLAN 14. CI smoke push", result.stdout)

    @unittest.skipUnless(
        shutil.which("pwsh"),
        "PowerShell 7 is required to execute Windows onboarding script tests",
    )
    def test_windows_ha_stack_dry_run_uses_macos_host_url(self) -> None:
        result = run_windows_script(
            "-Steps",
            "8",
            "-DryRun",
            "-HaHostUrl",
            "http://10.211.55.2:8123",
            "-NoLogFile",
            "-Yes",
        )

        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("Windows ARM in Parallels cannot run Docker Desktop nested virtualization reliably.", result.stdout)
        self.assertIn("Home Assistant host URL: http://10.211.55.2:8123", result.stdout)
        self.assertRegex(result.stdout, r"DRY\s+curl\.exe -fsS http://10\.211\.55\.2:8123")
        self.assertNotIn("docker compose", result.stdout)

    @unittest.skipUnless(
        shutil.which("pwsh"),
        "PowerShell 7 is required to execute Windows onboarding script tests",
    )
    def test_windows_ngrok_dry_run_redacts_token(self) -> None:
        result = run_windows_script_with_env(
            {"NGROK_AUTHTOKEN": "secret-ngrok-token"},
            "-Steps",
            "12",
            "-NgrokDomain",
            "victory-curvy-refold.ngrok-free.dev",
            "-DryRun",
            "-NoLogFile",
            "-Yes",
        )

        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertRegex(result.stdout, r"DRY\s+ngrok config add-authtoken <redacted>")
        self.assertNotIn("secret-ngrok-token", result.stdout)
        self.assertIn("schtasks /Create", result.stdout)
        self.assertIn("ngrok http --url=victory-curvy-refold.ngrok-free.dev 8123", result.stdout)


if __name__ == "__main__":
    unittest.main()
