"""Apple runtime qualification gate for Phase 10E verification."""

from __future__ import annotations

import json
import os
import plistlib
import platform
import shutil
import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from tools.verification.apple_adapter import AppleAdapterConfig, AppleRuntimeTarget, AppleVerificationAdapter
from tools.verification.evidence import RunStore
from tools.verification.environment.identity import RunIdentityManager
from tools.verification.environment.platforms import CommandRunner
from tools.verification.runtime_channels import future_beta_enabled, verification_test_mode


MANDATORY_CHECKS = (
    "apns_entitlements",
    "xcode_account",
    "distribution_signing_assets",
    "release_equivalent_build",
    "simulator_target",
    "cross_device_simulator_targets",
    "physical_device_target",
    "derived_data_isolation",
    "install",
    "launch",
    "screenshot",
    "log_collection",
    "ui_automation_healthcheck",
)


@dataclass(frozen=True)
class AppleQualificationCheck:
    name: str
    state: str
    message: str
    data: dict[str, Any]


@dataclass(frozen=True)
class AppleQualificationResult:
    run_id: str
    state: str
    started_at: float
    completed_at: float
    checks: tuple[AppleQualificationCheck, ...]
    evidence_dir: str
    broad_scenario_execution_allowed: bool


class AppleRuntimeQualification:
    """Run the mandatory fail-closed Apple runtime qualification gate."""

    def __init__(self, root: Path, *, apple_repo: Path | None = None) -> None:
        self.root = root
        self.apple_repo = apple_repo or root.parent / "djconnect-app"
        self.evidence_root = root / "artifacts" / "verification" / "evidence"

    def run(self) -> AppleQualificationResult:
        started = time.time()
        run_id = RunIdentityManager().create([], prefix="apple10e").run_id
        store = RunStore(self.evidence_root)
        run_dir = store.ensure(run_id)
        evidence_dir = run_dir / "apple"
        evidence_dir.mkdir(parents=True, exist_ok=True)

        checks: list[AppleQualificationCheck] = []
        derived_data = self._derived_data_isolation()
        checks.append(derived_data)
        checks.append(self._apns_entitlements())
        xcode_account = self._xcode_account()
        checks.append(xcode_account)
        signing_assets = self._distribution_signing_assets()
        checks.append(signing_assets)
        if derived_data.state == "PASS" and xcode_account.state == "PASS" and signing_assets.state in {"PASS", "SKIPPED"}:
            checks.append(self._release_equivalent_build())
        else:
            checks.append(
                _check(
                    "release_equivalent_build",
                    "BLOCKED",
                    "Release-equivalent build skipped because clean DerivedData isolation, Xcode account access or required distribution signing assets are not available.",
                    {},
                )
            )
        checks.append(self._simulator_target())
        checks.append(self._cross_device_simulator_targets())
        checks.append(self._physical_device_target())

        if not _prerequisites_passed(checks):
            checks.extend(
                _blocked_live_primitive(name)
                for name in ("install", "launch", "screenshot", "log_collection", "ui_automation_healthcheck")
            )
            return self._finish_result(
                run_id=run_id,
                started=started,
                run_dir=run_dir,
                store=store,
                checks=checks,
            )

        adapter_config = AppleAdapterConfig.from_environment(self.root)
        if adapter_config.evidence_dir is None:
            adapter_config = AppleAdapterConfig(
                target=adapter_config.target,
                timeout_seconds=adapter_config.timeout_seconds,
                allow_destructive=adapter_config.allow_destructive,
                allow_physical_devices=adapter_config.allow_physical_devices,
                evidence_dir=evidence_dir,
            )
        adapter = AppleVerificationAdapter(adapter_config)

        checks.append(self._primitive("install", adapter.install_app()))
        launch = adapter.launch_app()
        checks.append(self._primitive("launch", launch))
        checks.append(self._primitive("screenshot", adapter.capture_screenshot("phase-10e-runtime-qualification")))
        checks.append(self._logs(adapter))
        if launch.ok:
            adapter.terminate_app()
        checks.append(self._ui_healthcheck())

        return self._finish_result(
            run_id=run_id,
            started=started,
            run_dir=run_dir,
            store=store,
            checks=checks,
        )

    def _finish_result(
        self,
        *,
        run_id: str,
        started: float,
        run_dir: Path,
        store: RunStore,
        checks: list[AppleQualificationCheck],
    ) -> AppleQualificationResult:
        policy_skipped_checks = {
            "cross_device_simulator_targets",
            "distribution_signing_assets",
            "physical_device_target",
        }
        state = "PASS" if all(
            check.state == "PASS" or (check.name in policy_skipped_checks and check.state == "SKIPPED")
            for check in checks
        ) else "BLOCKED"
        result = AppleQualificationResult(
            run_id=run_id,
            state=state,
            started_at=started,
            completed_at=time.time(),
            checks=tuple(checks),
            evidence_dir=str(run_dir),
            broad_scenario_execution_allowed=state == "PASS",
        )
        store.write_json(run_id, "apple/runtime-qualification.json", asdict(result))
        store.finalize(
            run_id,
            state=state,
            summary={
                "phase": "10E",
                "gate": "apple_runtime_qualification",
                "broad_scenario_execution_allowed": result.broad_scenario_execution_allowed,
                "apple_repo": str(self.apple_repo),
                "host": platform.node(),
                "os": platform.platform(),
            },
        )
        return result

    def _release_equivalent_build(self) -> AppleQualificationCheck:
        project = self.apple_repo / "DJConnectApp.xcodeproj"
        release_script = self.apple_repo / "release.sh"
        command = os.getenv("DJCONNECT_VERIFICATION_APPLE_BUILD_COMMAND")
        if not self.apple_repo.exists() or not project.exists():
            return _check("release_equivalent_build", "BLOCKED", "Apple source repository or Xcode project is unavailable.", {"apple_repo": str(self.apple_repo)})
        if not command:
            return _check(
                "release_equivalent_build",
                "BLOCKED",
                "No explicit release-equivalent Apple build command configured.",
                {
                    "apple_repo": str(self.apple_repo),
                    "project": str(project),
                    "release_script": str(release_script),
                    "required_env": "DJCONNECT_VERIFICATION_APPLE_BUILD_COMMAND",
                },
            )
        code, output = _run_shell(command, self.apple_repo, timeout=1800)
        return _check("release_equivalent_build", "PASS" if code == 0 else "FAIL", "Release-equivalent build command executed." if code == 0 else "Release-equivalent build command failed.", {"command": command, "returncode": code, "output_tail": output[-4000:]})

    def _apns_entitlements(self) -> AppleQualificationCheck:
        entitlements = sorted(str(path.relative_to(self.apple_repo)) for path in self.apple_repo.rglob("*.entitlements")) if self.apple_repo.exists() else []
        state = "PASS" if entitlements else "BLOCKED"
        return _check("apns_entitlements", state, "Entitlement files discovered." if entitlements else "No Apple entitlement files found for APNs/signing verification.", {"entitlement_files": entitlements})

    def _xcode_account(self) -> AppleQualificationCheck:
        project = self.apple_repo / "DJConnectApp.xcodeproj"
        if not self.apple_repo.exists() or not project.exists():
            return _check("xcode_account", "BLOCKED", "Apple source repository or Xcode project is unavailable.", {"apple_repo": str(self.apple_repo)})

        runner = CommandRunner()
        command = (
            "xcodebuild",
            "-project",
            str(project),
            "-scheme",
            os.getenv("DJCONNECT_VERIFICATION_APPLE_SCHEME", "DJConnectIOS"),
            "-showBuildSettings",
            "-json",
            "-allowProvisioningUpdates",
        )
        code, output = runner.run(command, cwd=self.apple_repo, timeout=120)
        settings = _extract_xcode_signing_settings(output) if code == 0 else {}
        state = "PASS" if code == 0 else "BLOCKED"
        return _check(
            "xcode_account",
            state,
            "Xcode accepted automatic provisioning access for the Apple project."
            if state == "PASS"
            else "Xcode automatic provisioning is unavailable; sign in to Xcode with an Apple developer account and refresh credentials/profiles.",
            {
                "returncode": code,
                "project": str(project),
                "scheme": command[4],
                "allow_provisioning_updates": True,
                "settings": settings,
                "output_tail": _redacted_output_tail(output),
            },
        )

    def _distribution_signing_assets(self) -> AppleQualificationCheck:
        expected = {
            "DJCONNECT_VERIFICATION_APPLE_DISTRIBUTION_IDENTITY": os.getenv("DJCONNECT_VERIFICATION_APPLE_DISTRIBUTION_IDENTITY", "").strip(),
            "DJCONNECT_VERIFICATION_APPLE_TEAM_ID": os.getenv("DJCONNECT_VERIFICATION_APPLE_TEAM_ID", "").strip(),
            "DJCONNECT_VERIFICATION_APPLE_BUNDLE_ID": os.getenv("DJCONNECT_VERIFICATION_APPLE_BUNDLE_ID", "").strip(),
            "DJCONNECT_VERIFICATION_APPLE_PROVISIONING_PROFILE": os.getenv("DJCONNECT_VERIFICATION_APPLE_PROVISIONING_PROFILE", "").strip(),
        }
        missing = [key for key, value in expected.items() if not value]
        if missing:
            if not _distribution_signing_required():
                return _check(
                    "distribution_signing_assets",
                    "SKIPPED",
                    "App Store/TestFlight distribution signing is deferred for current platform verification.",
                    {
                        "missing": missing,
                        "required_for_current_run": False,
                        "enable_with": "DJCONNECT_VERIFICATION_APPLE_REQUIRE_DISTRIBUTION_SIGNING=1",
                    },
                )
            return _check(
                "distribution_signing_assets",
                "BLOCKED",
                "Distribution signing expectations are not fully configured.",
                {
                    "required_env": [
                        "DJCONNECT_VERIFICATION_APPLE_DISTRIBUTION_IDENTITY",
                        "DJCONNECT_VERIFICATION_APPLE_TEAM_ID",
                        "DJCONNECT_VERIFICATION_APPLE_BUNDLE_ID",
                        "DJCONNECT_VERIFICATION_APPLE_PROVISIONING_PROFILE",
                    ],
                    "missing": missing,
                },
            )

        runner = CommandRunner()
        identity = expected["DJCONNECT_VERIFICATION_APPLE_DISTRIBUTION_IDENTITY"]
        team_id = expected["DJCONNECT_VERIFICATION_APPLE_TEAM_ID"]
        bundle_id = expected["DJCONNECT_VERIFICATION_APPLE_BUNDLE_ID"]
        profile_name = expected["DJCONNECT_VERIFICATION_APPLE_PROVISIONING_PROFILE"]
        identity_code, identities = runner.run(("security", "find-identity", "-v", "-p", "codesigning"), timeout=20)
        identity_ok = identity_code == 0 and identity in identities and team_id in identities
        profile = _find_distribution_profile(
            expected_profile=profile_name,
            expected_team_id=team_id,
            expected_bundle_id=bundle_id,
            runner=runner,
        )
        profile_ok = profile is not None
        state = "PASS" if identity_ok and profile_ok else "BLOCKED"
        return _check(
            "distribution_signing_assets",
            state,
            "Distribution signing identity and provisioning profile matched configured release expectations." if state == "PASS" else "Distribution signing identity or provisioning profile did not match configured release expectations.",
            {
                "identity_expected": identity,
                "team_id_expected": team_id,
                "bundle_id_expected": bundle_id,
                "profile_expected": profile_name,
                "identity_found": identity_ok,
                "profile_found": profile_ok,
                "matched_profile": profile or {},
            },
        )

    def _simulator_target(self) -> AppleQualificationCheck:
        target = AppleAdapterConfig.from_environment(self.root).target
        if target is None:
            return _check("simulator_target", "BLOCKED", "No prepared Apple target JSON configured.", {"required_env": "DJCONNECT_VERIFICATION_APPLE_TARGET_JSON"})
        if target.runtime != "simulator":
            return _check("simulator_target", "BLOCKED", "Configured target is not a simulator.", {"target": target.to_dict()})
        ios_runtime = latest_ios_simulator_runtime()
        if not ios_runtime:
            return _check(
                "simulator_target",
                "BLOCKED",
                "Latest eligible iOS simulator runtime could not be determined.",
                {
                    "target": target.to_dict(),
                    "test_mode": verification_test_mode(),
                    "recommended_action": "Run `python3 -m tools.verification.cli apple ensure-ios-runtime`, then retry Apple Runtime Qualification.",
                },
            )
        if target.udid not in ios_runtime.get("udids", ()):
            return _check(
                "simulator_target",
                "BLOCKED",
                "Configured simulator target is not on the latest eligible iOS runtime for the active verification mode.",
                {
                    "target": target.to_dict(),
                    "latest_ios_runtime": ios_runtime,
                    "test_mode": verification_test_mode(),
                    "recommended_action": "Run `python3 -m tools.verification.cli apple ensure-ios-runtime`, then regenerate DJCONNECT_VERIFICATION_APPLE_TARGET_JSON from the latest eligible iOS simulator runtime.",
                },
            )
        return _check(
            "simulator_target",
            "PASS",
            "Prepared simulator target configured on the latest eligible iOS runtime.",
            {"target": target.to_dict(), "latest_ios_runtime": ios_runtime},
        )

    def _cross_device_simulator_targets(self) -> AppleQualificationCheck:
        targets_json = os.getenv("DJCONNECT_VERIFICATION_APPLE_TARGETS_JSON", "")
        if not targets_json:
            return _check("cross_device_simulator_targets", "SKIPPED", "No cross-device Apple simulator target set configured.", {})
        try:
            raw_targets = json.loads(targets_json)
        except json.JSONDecodeError as exc:
            return _check("cross_device_simulator_targets", "BLOCKED", "Cross-device Apple target set JSON is invalid.", {"error": str(exc)})
        if not isinstance(raw_targets, list) or len(raw_targets) < 2:
            return _check(
                "cross_device_simulator_targets",
                "BLOCKED",
                "Cross-device Apple tests require at least two configured simulator targets.",
                {"target_count": len(raw_targets) if isinstance(raw_targets, list) else 0},
            )
        available = available_ios_simulator_devices()
        if not available:
            return _check("cross_device_simulator_targets", "BLOCKED", "Available iOS simulator devices could not be determined.", {})
        by_udid = {device["udid"]: device for device in available if device.get("udid")}
        resolved: list[dict[str, Any]] = []
        missing: list[dict[str, Any]] = []
        for raw in raw_targets:
            if not isinstance(raw, dict):
                missing.append({"target": raw, "reason": "target is not an object"})
                continue
            target = AppleRuntimeTarget.from_mapping(raw)
            expected_version = str(raw.get("ios_version") or raw.get("runtime_version") or target.metadata.get("ios_version") or target.metadata.get("runtime_version") or "")
            device = by_udid.get(target.udid)
            if not device:
                missing.append({"target": target.to_dict(), "reason": "udid not available"})
                continue
            if expected_version and device.get("version") != expected_version:
                missing.append({"target": target.to_dict(), "reason": "runtime version mismatch", "expected_version": expected_version, "actual_version": device.get("version")})
                continue
            resolved.append({"target": target.to_dict(), "available_device": device})
        if missing:
            return _check(
                "cross_device_simulator_targets",
                "BLOCKED",
                "One or more configured cross-device Apple simulators are unavailable.",
                {"missing": missing, "resolved": resolved},
            )
        return _check(
            "cross_device_simulator_targets",
            "PASS",
            "All configured cross-device Apple simulators are available.",
            {"targets": resolved},
        )

    def _physical_device_target(self) -> AppleQualificationCheck:
        if os.getenv("DJCONNECT_VERIFICATION_APPLE_ALLOW_PHYSICAL", "").lower() not in {"1", "true", "yes", "on"}:
            return _check("physical_device_target", "SKIPPED", "Physical-device qualification is opt-in and was not configured.", {})
        return _check("physical_device_target", "BLOCKED", "Physical-device opt-in is set but no physical-device qualification runner is configured.", {})

    def _derived_data_isolation(self) -> AppleQualificationCheck:
        path = os.getenv("DJCONNECT_VERIFICATION_APPLE_DERIVED_DATA")
        if not path:
            return _check("derived_data_isolation", "BLOCKED", "No isolated DerivedData path configured for Phase 10E.", {"required_env": "DJCONNECT_VERIFICATION_APPLE_DERIVED_DATA"})
        derived_data = Path(path).expanduser()
        if not derived_data.is_absolute():
            return _check("derived_data_isolation", "BLOCKED", "DerivedData path must be absolute.", {"derived_data": path})
        if not _safe_clean_path(derived_data, self.root):
            return _check(
                "derived_data_isolation",
                "BLOCKED",
                "DerivedData cleanup path is outside the approved verification scratch roots.",
                {"derived_data": str(derived_data), "approved_roots": _approved_clean_roots(self.root)},
            )
        existed_before = derived_data.exists()
        shutil.rmtree(derived_data, ignore_errors=True)
        derived_data.mkdir(parents=True, exist_ok=True)
        return _check(
            "derived_data_isolation",
            "PASS",
            "Isolated DerivedData path was cleaned before the release-equivalent build.",
            {"derived_data": str(derived_data), "existed_before_cleanup": existed_before, "cleaned_before_build": True},
        )

    def _logs(self, adapter: AppleVerificationAdapter) -> AppleQualificationCheck:
        logs = adapter.collect_logs()
        ok = bool(logs)
        return _check("log_collection", "PASS" if ok else "BLOCKED", "Scoped Apple runtime logs collected." if ok else "Apple runtime log collection did not produce evidence.", {"log_entries": len(logs), "logs": list(logs)[-3:]})

    def _ui_healthcheck(self) -> AppleQualificationCheck:
        driver = os.getenv("DJCONNECT_VERIFICATION_APPLE_UI_DRIVER")
        command = os.getenv("DJCONNECT_VERIFICATION_APPLE_UI_HEALTHCHECK_COMMAND")
        if not driver or not command:
            return _check(
                "ui_automation_healthcheck",
                "BLOCKED",
                "No XCTest/accessibility UI healthcheck driver and command configured.",
                {
                    "required_env": [
                        "DJCONNECT_VERIFICATION_APPLE_UI_DRIVER",
                        "DJCONNECT_VERIFICATION_APPLE_UI_HEALTHCHECK_COMMAND",
                    ]
                },
            )
        code, output = _run_shell(
            command,
            self.apple_repo,
            timeout=int(os.getenv("DJCONNECT_VERIFICATION_APPLE_UI_HEALTHCHECK_TIMEOUT", "180")),
        )
        return _check("ui_automation_healthcheck", "PASS" if code == 0 else "FAIL", "UI automation healthcheck executed." if code == 0 else "UI automation healthcheck failed.", {"driver": driver, "returncode": code, "output_tail": output[-4000:]})

    @staticmethod
    def _primitive(name: str, primitive: Any) -> AppleQualificationCheck:
        return _check(name, "PASS" if primitive.ok else "BLOCKED", f"{name} primitive executed." if primitive.ok else f"{name} primitive did not qualify.", {"result": primitive.data, "message": primitive.message})


def _check(name: str, state: str, message: str, data: dict[str, Any]) -> AppleQualificationCheck:
    return AppleQualificationCheck(name=name, state=state, message=message, data=data)


def _extract_xcode_signing_settings(output: str) -> dict[str, Any]:
    json_start = output.find("\n[")
    if json_start >= 0:
        json_text = output[json_start + 1 :]
    else:
        json_text = output[output.find("[") :]
    try:
        payload = json.loads(json_text)
    except (json.JSONDecodeError, ValueError):
        return {}
    if not isinstance(payload, list):
        return {}
    settings_by_target: dict[str, dict[str, str]] = {}
    interesting_keys = (
        "PRODUCT_BUNDLE_IDENTIFIER",
        "DEVELOPMENT_TEAM",
        "CODE_SIGN_STYLE",
        "CODE_SIGN_IDENTITY",
        "PROVISIONING_PROFILE_SPECIFIER",
    )
    for entry in payload:
        if not isinstance(entry, dict):
            continue
        target = str(entry.get("target") or "unknown")
        build_settings = entry.get("buildSettings")
        if not isinstance(build_settings, dict):
            continue
        settings_by_target[target] = {
            key: str(build_settings.get(key, ""))
            for key in interesting_keys
            if build_settings.get(key) is not None
        }
    return settings_by_target


def _redacted_output_tail(output: str) -> str:
    sensitive_markers = ("token", "password", "secret", "authorization")
    lines = []
    for line in output.splitlines()[-40:]:
        lowered = line.lower()
        if any(marker in lowered for marker in sensitive_markers):
            lines.append("[redacted]")
        else:
            lines.append(line)
    return "\n".join(lines)[-4000:]


def _prerequisites_passed(checks: list[AppleQualificationCheck]) -> bool:
    for check in checks:
        if check.name in {"physical_device_target", "cross_device_simulator_targets", "distribution_signing_assets"} and check.state == "SKIPPED":
            continue
        if check.state != "PASS":
            return False
    return True


def _distribution_signing_required() -> bool:
    return os.getenv("DJCONNECT_VERIFICATION_APPLE_REQUIRE_DISTRIBUTION_SIGNING", "").strip().lower() in {"1", "true", "yes", "on"}


def _blocked_live_primitive(name: str) -> AppleQualificationCheck:
    return _check(
        name,
        "BLOCKED",
        "Live Apple runtime primitive skipped because prerequisite qualification checks did not pass.",
        {},
    )


def _run_shell(command: str, cwd: Path, *, timeout: int) -> tuple[int, str]:
    try:
        output = subprocess.check_output(command, cwd=cwd, shell=True, text=True, stderr=subprocess.STDOUT, timeout=timeout)
        return 0, output.strip()
    except subprocess.CalledProcessError as exc:
        return exc.returncode, str(exc.output).strip()
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 127, str(exc)


def result_to_json(result: AppleQualificationResult) -> str:
    return json.dumps(asdict(result), indent=2, sort_keys=True)


def _approved_clean_roots(root: Path) -> list[str]:
    return [
        "/private/tmp",
        "/tmp",
        str((root / "artifacts" / "verification").resolve()),
    ]


def _safe_clean_path(path: Path, root: Path) -> bool:
    try:
        resolved = path.resolve()
    except OSError:
        resolved = path.absolute()
    for approved in _approved_clean_roots(root):
        approved_path = Path(approved).resolve()
        if resolved == approved_path:
            return False
        if approved_path in resolved.parents:
            return True
    return False


def _find_distribution_profile(
    *,
    expected_profile: str,
    expected_team_id: str,
    expected_bundle_id: str,
    runner: CommandRunner,
) -> dict[str, Any] | None:
    for profiles_dir in _profile_search_dirs():
        if not profiles_dir.exists():
            continue
        for path in sorted(profiles_dir.glob("*")):
            if path.suffix not in {".mobileprovision", ".provisionprofile", ".plist"}:
                continue
            profile = _read_profile(path, runner)
            if not profile:
                continue
            name = str(profile.get("Name", ""))
            uuid = str(profile.get("UUID", ""))
            team_ids = tuple(str(item) for item in profile.get("TeamIdentifier", []) if item)
            entitlements = profile.get("Entitlements", {})
            application_identifier = str(entitlements.get("application-identifier", "")) if isinstance(entitlements, dict) else ""
            aps_environment = str(entitlements.get("aps-environment", "")) if isinstance(entitlements, dict) else ""
            profile_type = _profile_type(profile)
            profile_matches = expected_profile in {name, uuid}
            team_matches = expected_team_id in team_ids or application_identifier.startswith(f"{expected_team_id}.")
            bundle_matches = application_identifier == f"{expected_team_id}.{expected_bundle_id}"
            if profile_matches and team_matches and bundle_matches:
                return {
                    "name": name,
                    "uuid": uuid,
                    "team_ids": list(team_ids),
                    "application_identifier": application_identifier,
                    "profile_type": profile_type,
                    "aps_environment": aps_environment,
                    "path_name": path.name,
                    "profiles_dir": str(profiles_dir),
                }
    return None


def _profile_search_dirs() -> tuple[Path, ...]:
    configured = os.getenv("DJCONNECT_VERIFICATION_APPLE_PROFILES_DIR", "").strip()
    if configured:
        return (Path(configured).expanduser(),)
    return (
        Path("~/Library/MobileDevice/Provisioning Profiles").expanduser(),
        Path("~/Library/Developer/Xcode/UserData/Provisioning Profiles").expanduser(),
    )


def _read_profile(path: Path, runner: CommandRunner) -> dict[str, Any] | None:
    if path.suffix == ".plist":
        try:
            data = plistlib.loads(path.read_bytes())
            return data if isinstance(data, dict) else None
        except (OSError, plistlib.InvalidFileException):
            return None
    code, output = runner.run(("security", "cms", "-D", "-i", str(path)), timeout=20)
    if code != 0:
        return None
    try:
        data = plistlib.loads(output.encode("utf-8"))
    except plistlib.InvalidFileException:
        return None
    return data if isinstance(data, dict) else None


def _profile_type(profile: dict[str, Any]) -> str:
    entitlements = profile.get("Entitlements", {})
    get_task_allow = bool(entitlements.get("get-task-allow")) if isinstance(entitlements, dict) else False
    provisions_all_devices = bool(profile.get("ProvisionsAllDevices"))
    provisioned_devices = profile.get("ProvisionedDevices")
    if get_task_allow:
        return "development"
    if provisions_all_devices:
        return "enterprise"
    if provisioned_devices:
        return "ad_hoc"
    return "app_store"


def latest_ios_simulator_runtime(runner: CommandRunner | None = None, *, xcrun: str = "xcrun") -> dict[str, Any] | None:
    runner = runner or CommandRunner()
    code, output = runner.run((xcrun, "simctl", "list", "devices", "available", "--json"), timeout=20)
    if code != 0:
        return None
    try:
        data = json.loads(output)
    except json.JSONDecodeError:
        return None
    devices_by_runtime = data.get("devices")
    if not isinstance(devices_by_runtime, dict):
        return None
    ios_runtimes: list[dict[str, Any]] = []
    for runtime, devices in devices_by_runtime.items():
        runtime_text = str(runtime)
        if "SimRuntime.iOS-" not in runtime_text or not isinstance(devices, list):
            continue
        available_devices = [device for device in devices if isinstance(device, dict) and device.get("isAvailable", device.get("is_available"))]
        if not available_devices:
            continue
        version = _runtime_version(runtime_text)
        channel = _ios_runtime_channel(version)
        ios_runtimes.append(
            {
                "runtime": runtime_text,
                "version": version,
                "channel": channel,
                "version_key": _version_key(version),
                "devices": [
                    {
                        "name": device.get("name"),
                        "udid": device.get("udid"),
                        "state": device.get("state"),
                    }
                    for device in available_devices
                ],
                "udids": [str(device.get("udid")) for device in available_devices if device.get("udid")],
            }
        )
    if not ios_runtimes:
        return None
    eligible = ios_runtimes if future_beta_enabled() else [runtime for runtime in ios_runtimes if runtime["channel"] == "stable"]
    if not eligible:
        return None
    latest = sorted(eligible, key=lambda item: item["version_key"])[-1]
    return {key: value for key, value in latest.items() if key != "version_key"}


def available_ios_simulator_devices(runner: CommandRunner | None = None, *, xcrun: str = "xcrun") -> list[dict[str, Any]]:
    runner = runner or CommandRunner()
    code, output = runner.run((xcrun, "simctl", "list", "devices", "available", "--json"), timeout=20)
    if code != 0:
        return []
    try:
        data = json.loads(output)
    except json.JSONDecodeError:
        return []
    devices_by_runtime = data.get("devices")
    if not isinstance(devices_by_runtime, dict):
        return []
    devices: list[dict[str, Any]] = []
    for runtime, runtime_devices in devices_by_runtime.items():
        runtime_text = str(runtime)
        if "SimRuntime.iOS-" not in runtime_text or not isinstance(runtime_devices, list):
            continue
        version = _runtime_version(runtime_text)
        for device in runtime_devices:
            if not isinstance(device, dict) or not device.get("isAvailable", device.get("is_available")):
                continue
            devices.append(
                {
                    "runtime": runtime_text,
                    "version": version,
                    "name": device.get("name"),
                    "udid": device.get("udid"),
                    "state": device.get("state"),
                }
            )
    return devices


def _runtime_version(runtime: str) -> str:
    marker = "SimRuntime.iOS-"
    if marker not in runtime:
        return ""
    return runtime.split(marker, 1)[1].replace("-", ".")


def _version_key(version: str) -> tuple[int, ...]:
    parts: list[int] = []
    for item in version.split("."):
        try:
            parts.append(int(item))
        except ValueError:
            parts.append(0)
    return tuple(parts)


def _ios_runtime_channel(version: str) -> str:
    return "stable" if _ios_runtime_major(version) <= _stable_ios_major_version() else "beta"


def _ios_runtime_major(version: str) -> int:
    try:
        return int(version.split(".", 1)[0])
    except (TypeError, ValueError):
        return 0


def _stable_ios_major_version() -> int:
    value = os.getenv("DJCONNECT_VERIFICATION_STABLE_IOS_MAJOR_VERSION", "26")
    try:
        return max(1, int(value))
    except ValueError:
        return 26
