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
RECOVERY_REDACTION_RULES = ROOT / "scripts" / "runner" / "redact_recovery_output.sed"
MACOS_RUNNER_DESIRED_STATE = ROOT / "scripts" / "runner" / "macos_runner_host_desired_state.yml"
MACOS_RUNNER_RECOVERY_CHANGELOG = ROOT / "scripts" / "runner" / "BOOTSTRAP_MACOS_RUNNER_HOST_CHANGELOG.md"
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
        self.assertIn("profile.$profile.runner_name", source)
        self.assertIn("RUNNER_ARCHIVE_DIGEST", source)
        self.assertIn("--xcode-version", source)
        self.assertIn("set-key-partition-list", source)
        self.assertIn("--install-parallels", source)
        self.assertIn("brew install --cask parallels", source)
        self.assertIn("dev_onboarding_macos.sh --all --yes --warm-sudo", source)
        self.assertIn("--ngrok-domain", source)
        self.assertIn("--prompt-ngrok-auth", source)
        self.assertIn("NGROK_AUTHTOKEN", source)
        self.assertIn("docker login", source)
        self.assertIn("gh auth login --hostname github.com --git-protocol https --web", source)
        self.assertIn("--configure-apple-internal-release", source)
        self.assertIn("DJCONNECT_APPLE_MACBOOK_HARDWARE_UUID", source)
        self.assertIn("DJCONNECT_APPLE_DEVELOPMENT_SIGNING_IDENTITY", source)
        self.assertIn("verify_apple_internal_release_readiness.py", source)
        self.assertIn("warm_sudo", source)
        self.assertIn("dseditgroup -o checkmember", source)
        self.assertIn("verify_launchd_services", source)
        self.assertIn("run_in_dir \"$install_dir\" sudo ./svc.sh install", source)
        self.assertIn("audit_apple_github_configuration", source)
        self.assertIn("gh secret list --repo", source)
        self.assertIn("gh variable list --repo", source)
        self.assertIn("refresh_host_tooling", source)
        self.assertIn("check_reboot_required", source)
        self.assertIn("run_initial_verification", source)
        self.assertIn("softwareupdate --list", source)
        self.assertIn("tools/dev_onboarding_macos.sh --steps 21,22", source)
        self.assertIn("actions/runners", source)
        self.assertIn("onboarding_args+=(--dry-run)", source)
        self.assertIn("verification_args+=(--dry-run)", source)
        self.assertIn("onboarding_args=(tools/dev_onboarding_macos.sh --all --yes --warm-sudo --no-log-file)", source)
        self.assertIn("start_logging", source)
        self.assertIn("start_report", source)
        self.assertIn("complete_report", source)
        self.assertIn("run_phase", source)
        self.assertIn("--report-file", source)
        self.assertIn("--no-report-file", source)
        self.assertIn("Final status", source)
        self.assertIn("Retry this phase?", source)
        self.assertIn("--no-step-retry", source)
        self.assertIn("RETRYING", source)
        self.assertIn("--skip-phases", source)
        self.assertIn("COMPLETED WITH SKIPPED PHASES", source)
        self.assertIn("phase_is_skipped", source)
        self.assertIn("Verification-run verdict", source)
        self.assertIn("HOST QUALIFIED FOR THE REQUESTED DJCONNECT RECOVERY SCOPE", source)
        self.assertIn("INITIAL_VERIFICATION_PASSED", source)
        self.assertIn("machdep.cpu.brand_string", source)
        self.assertIn("DESIRED_MINIMUM_FREE_DISK_GB", source)
        self.assertIn("Development host qualification", source)
        self.assertIn("macos-preflight is mandatory and cannot be skipped", source)
        self.assertIn("Precheck: $step", source)
        self.assertIn("phase_dependencies", source)
        self.assertIn("phase_runtime_conditions", source)
        self.assertIn("PASSED is required", source)
        self.assertIn("--force-phases", source)
        self.assertIn("phase_is_forced", source)
        self.assertIn("without destructive recreation", source)
        self.assertIn("redact_recovery_output.sed", source)
        self.assertIn("--desired-state", source)
        self.assertIn("load_desired_state", source)
        self.assertIn("validate_profile_selection", source)
        self.assertIn("--verify", source)
        self.assertIn("run_desired_state_verification", source)
        self.assertIn("Desired-State Delta", source)
        self.assertIn("DRIFT DETECTED", source)
        self.assertIn("--resume", source)
        self.assertIn("write_resume_checkpoint", source)
        self.assertIn("load_resume_checkpoint", source)
        self.assertIn("PAUSED FOR REBOOT", source)
        self.assertIn("macos_runner_host_desired_state.yml", source)
        self.assertTrue(MACOS_RUNNER_DESIRED_STATE.is_file())
        desired_state = MACOS_RUNNER_DESIRED_STATE.read_text()
        self.assertIn("schema_version: 1", desired_state)
        self.assertIn("host.minimum_free_disk_gb: 80", desired_state)
        self.assertIn("runner.profiles: apple,private-network,esp32,pi", desired_state)
        self.assertTrue(RECOVERY_REDACTION_RULES.is_file())
        self.assertIn("[REDACTED]", RECOVERY_REDACTION_RULES.read_text())
        self.assertIn("/dev/tty", source)
        self.assertIn("run_interactive", source)
        self.assertIn("install_macos_ci_tooling_maintenance.sh --run-now", source)

    def test_macos_runner_recovery_bootstrap_reports_its_semantic_version(self) -> None:
        result = subprocess.run(
            [str(RUNNER_RECOVERY_SCRIPT), "--version"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertEqual(
            result.stdout,
            "DJConnect macOS Runner Host Recovery Bootstrap 1.0.0\n",
        )
        self.assertTrue(MACOS_RUNNER_RECOVERY_CHANGELOG.is_file())
        changelog = MACOS_RUNNER_RECOVERY_CHANGELOG.read_text(encoding="utf-8")
        self.assertIn("Semantic Versioning", changelog)
        self.assertIn("## [1.0.0] - 2026-07-16", changelog)
        self.assertIn("--version", changelog)

    def test_macos_runner_recovery_bootstrap_accepts_help_subcommand(self) -> None:
        result = subprocess.run(
            [str(RUNNER_RECOVERY_SCRIPT), "help"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("Usage: bootstrap_macos_runner_host.sh [options]", result.stdout)
        self.assertIn("--version", result.stdout)
        self.assertIn("help                   Show this help and exit.", result.stdout)

    def test_macos_runner_recovery_bootstrap_validates_log_levels(self) -> None:
        help_result = subprocess.run(
            [str(RUNNER_RECOVERY_SCRIPT), "--help"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        invalid_level = subprocess.run(
            [str(RUNNER_RECOVERY_SCRIPT), "--log-level", "invalid", "--version"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )

        self.assertEqual(help_result.returncode, 0, help_result.stdout)
        self.assertIn("--log-level LEVEL", help_result.stdout)
        self.assertIn("debug, verbose, info,", help_result.stdout)
        self.assertIn("warning or error", help_result.stdout)
        self.assertEqual(invalid_level.returncode, 2, invalid_level.stdout)
        self.assertIn("Invalid log level", invalid_level.stdout)
        source = RUNNER_RECOVERY_SCRIPT.read_text(encoding="utf-8")
        self.assertIn('LOG_LEVEL="${LOG_LEVEL:-info}"', source)
        self.assertIn("log_level_rank", source)
        self.assertIn("VERBOSE", source)

    def test_macos_runner_recovery_bootstrap_marks_parallel_safe_phases(self) -> None:
        result = subprocess.run(
            [str(RUNNER_RECOVERY_SCRIPT), "--list-phases"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("EXECUTION CAPABILITY", result.stdout)
        self.assertIn("runner-apple", result.stdout)
        self.assertIn("runner-private-network", result.stdout)
        self.assertIn("runner-esp32", result.stdout)
        self.assertIn("runner-pi", result.stdout)
        self.assertIn("apple-github-audit", result.stdout)
        self.assertIn("HEADLESS + PARALLEL SAFE", result.stdout)
        source = RUNNER_RECOVERY_SCRIPT.read_text(encoding="utf-8")
        self.assertIn("phase_execution_capability", source)
        self.assertIn("Execution capability: $step", source)

    def test_macos_runner_recovery_bootstrap_cpu_bounds_parallel_work(self) -> None:
        help_result = subprocess.run(
            [str(RUNNER_RECOVERY_SCRIPT), "--help"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        invalid_jobs = subprocess.run(
            [str(RUNNER_RECOVERY_SCRIPT), "--parallel-jobs", "invalid", "--version"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )

        self.assertEqual(help_result.returncode, 0, help_result.stdout)
        self.assertIn("--parallel-jobs COUNT", help_result.stdout)
        self.assertEqual(invalid_jobs.returncode, 2, invalid_jobs.stdout)
        self.assertIn("Parallel job count must be a non-negative integer", invalid_jobs.stdout)
        source = RUNNER_RECOVERY_SCRIPT.read_text(encoding="utf-8")
        self.assertIn("run_parallel_runner_profiles", source)
        self.assertIn("parallel_worker_limit", source)
        self.assertIn("worker_limit <= cpu_count", source)
        self.assertIn("run_apple_audit_alongside_services", source)

    def test_macos_runner_recovery_bootstrap_gates_low_recommended_memory(self) -> None:
        result = subprocess.run(
            [str(RUNNER_RECOVERY_SCRIPT), "--help"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("--confirm-memory-override", result.stdout)
        source = RUNNER_RECOVERY_SCRIPT.read_text(encoding="utf-8")
        self.assertIn("confirm_recommended_memory_override", source)
        self.assertIn("DESIRED_MINIMUM_RAM_GB", source)
        self.assertIn("DESIRED_RECOMMENDED_RAM_GB", source)
        self.assertIn("INTERACTIVELY APPROVED", source)
        self.assertIn("EXPLICITLY APPROVED", source)
        self.assertIn("CONFIRMATION REQUIRED", source)

    def test_macos_runner_recovery_bootstrap_has_unattended_repair_mode(self) -> None:
        result = subprocess.run(
            [str(RUNNER_RECOVERY_SCRIPT), "--help"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        incompatible_result = subprocess.run(
            [str(RUNNER_RECOVERY_SCRIPT), "--repair", "--verify"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("--repair", result.stdout)
        self.assertIn("baseline verify, then run verify again", result.stdout)
        self.assertNotEqual(incompatible_result.returncode, 0, incompatible_result.stdout)
        self.assertIn("--repair and --verify cannot be combined", incompatible_result.stdout)
        source = RUNNER_RECOVERY_SCRIPT.read_text(encoding="utf-8")
        self.assertIn("run_unattended_repair", source)
        self.assertIn("run_unattended_repair_runners", source)
        self.assertIn("record_repair_manual_requirement", source)
        self.assertIn("Post-repair desired-state verification", source)
        self.assertIn("--repair and --verify cannot be combined", source)
        self.assertIn("Desired-state repair verdict", source)
        recovery_guide = (ROOT / "docs" / "release" / "MACOS_RUNNER_HOST_RECOVERY.md").read_text(encoding="utf-8")
        self.assertIn("never opens a browser, GUI, `sudo` password prompt", recovery_guide)
        session_bootstrap = (ROOT / "BOOTSTRAP_CODEX_SESSION.md").read_text(encoding="utf-8")
        self.assertIn("prompt-free desired-state repair pass", session_bootstrap)

    def test_macos_runner_recovery_bootstrap_refuses_repository_output_paths(self) -> None:
        result = subprocess.run(
            [str(RUNNER_RECOVERY_SCRIPT), "--verify", "--log-file", "recovery.log"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )

        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn("absolute path outside the repository", result.stdout)
        source = RUNNER_RECOVERY_SCRIPT.read_text(encoding="utf-8")
        self.assertIn("require_external_output_path", source)
        self.assertIn("recovery output is never written into Git working tree", source)
        gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
        self.assertIn("macos-runner-recovery-*.log", gitignore)
        self.assertIn("macos-runner-recovery-*.md", gitignore)

    def test_macos_runner_recovery_bootstrap_groups_installation_sections(self) -> None:
        source = RUNNER_RECOVERY_SCRIPT.read_text(encoding="utf-8")

        self.assertIn("phase_section_id", source)
        self.assertIn("begin_report_section", source)
        self.assertIn("SECTION", source)
        self.assertIn("append_section_summary", source)
        self.assertIn("Installation section summary", source)
        self.assertIn("ATTENTION REQUIRED", source)
        self.assertIn("GitHub Actions runner provisioning", source)

    def test_macos_runner_recovery_bootstrap_reports_indicative_progress(self) -> None:
        source = RUNNER_RECOVERY_SCRIPT.read_text(encoding="utf-8")

        self.assertIn("phase_progress_snapshot", source)
        self.assertIn("emit_phase_progress", source)
        self.assertIn("PROGRESS", source)
        self.assertIn("completed * 100 / total", source)
        self.assertIn("emit_repair_progress", source)
        self.assertIn("REPAIR_PROGRESS_TOTAL=6", source)

    def test_macos_runner_recovery_bootstrap_audits_least_privilege(self) -> None:
        source = RUNNER_RECOVERY_SCRIPT.read_text(encoding="utf-8")

        self.assertIn("permissions-audit", source)
        self.assertIn("audit_least_privilege", source)
        self.assertIn("LEAST-PRIVILEGE WARNING", source)
        self.assertIn("Do not run DJConnect recovery as root", source)
        self.assertIn("path_is_group_or_world_writable", source)
        self.assertIn(".permissions.admin", source)
        self.assertIn("classic repo scope", source)

    def test_macos_runner_recovery_bootstrap_audits_credential_expiry(self) -> None:
        result = subprocess.run(
            [str(RUNNER_RECOVERY_SCRIPT), "--help"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("--expiry-warning-days DAYS", result.stdout)
        source = RUNNER_RECOVERY_SCRIPT.read_text(encoding="utf-8")
        self.assertIn("credential-expiry-audit", source)
        self.assertIn("audit_credential_expiry", source)
        self.assertIn("Apple Development", source)
        self.assertIn("Developer ID Application", source)
        self.assertIn("TOKEN EXPIRY UNVERIFIED", source)
        self.assertIn("CREDENTIAL EXPIRY WARNING", source)

    def test_macos_runner_recovery_bootstrap_opens_terminal_after_reboot(self) -> None:
        source = RUNNER_RECOVERY_SCRIPT.read_text(encoding="utf-8")

        self.assertIn("install_resume_terminal_continuation", source)
        self.assertIn("com.djconnect.macos-runner-recovery-resume", source)
        self.assertIn("/usr/bin/open", source)
        self.assertIn("Terminal", source)
        self.assertIn("RunAtLoad", source)
        self.assertIn("RESUME_CONTINUATION_COMMAND", source)
        self.assertIn("Sensitive passwords and token values remain outside the checkpoint", source)

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
        self.assertIn("Waiting for Docker Desktop", SCRIPT.read_text())
        self.assertIn("Docker Desktop daemon is ready.", SCRIPT.read_text())

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
