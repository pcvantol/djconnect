"""Apple runtime qualification gate for Phase 10E verification."""

from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from tools.verification.apple_adapter import AppleAdapterConfig, AppleVerificationAdapter
from tools.verification.evidence import RunStore
from tools.verification.environment.identity import RunIdentityManager
from tools.verification.environment.platforms import CommandRunner


MANDATORY_CHECKS = (
    "release_equivalent_build",
    "apns_entitlements",
    "simulator_target",
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
        if derived_data.state == "PASS":
            checks.append(self._release_equivalent_build())
        else:
            checks.append(
                _check(
                    "release_equivalent_build",
                    "BLOCKED",
                    "Release-equivalent build skipped because clean DerivedData isolation is not available.",
                    {},
                )
            )
        checks.append(self._apns_entitlements())
        checks.append(self._simulator_target())
        checks.append(self._physical_device_target())

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
        checks.append(self._ui_healthcheck())

        state = "PASS" if all(
            check.state == "PASS" or (check.name == "physical_device_target" and check.state == "SKIPPED")
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
                "Latest locally available iOS simulator runtime could not be determined.",
                {
                    "target": target.to_dict(),
                    "recommended_action": "Run `python3 -m tools.verification.cli apple ensure-ios-runtime`, then retry Apple Runtime Qualification.",
                },
            )
        if target.udid not in ios_runtime.get("udids", ()):
            return _check(
                "simulator_target",
                "BLOCKED",
                "Configured simulator target is not on the latest locally available iOS runtime.",
                {
                    "target": target.to_dict(),
                    "latest_ios_runtime": ios_runtime,
                    "recommended_action": "Run `python3 -m tools.verification.cli apple ensure-ios-runtime`, then regenerate DJCONNECT_VERIFICATION_APPLE_TARGET_JSON from the latest iOS simulator runtime.",
                },
            )
        return _check(
            "simulator_target",
            "PASS",
            "Prepared simulator target configured on the latest locally available iOS runtime.",
            {"target": target.to_dict(), "latest_ios_runtime": ios_runtime},
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
            timeout=int(os.getenv("DJCONNECT_VERIFICATION_APPLE_UI_HEALTHCHECK_TIMEOUT", "600")),
        )
        return _check("ui_automation_healthcheck", "PASS" if code == 0 else "FAIL", "UI automation healthcheck executed." if code == 0 else "UI automation healthcheck failed.", {"driver": driver, "returncode": code, "output_tail": output[-4000:]})

    @staticmethod
    def _primitive(name: str, primitive: Any) -> AppleQualificationCheck:
        return _check(name, "PASS" if primitive.ok else "BLOCKED", f"{name} primitive executed." if primitive.ok else f"{name} primitive did not qualify.", {"result": primitive.data, "message": primitive.message})


def _check(name: str, state: str, message: str, data: dict[str, Any]) -> AppleQualificationCheck:
    return AppleQualificationCheck(name=name, state=state, message=message, data=data)


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


def latest_ios_simulator_runtime(runner: CommandRunner | None = None) -> dict[str, Any] | None:
    runner = runner or CommandRunner()
    code, output = runner.run(("xcrun", "simctl", "list", "devices", "available", "--json"), timeout=20)
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
        ios_runtimes.append(
            {
                "runtime": runtime_text,
                "version": version,
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
    latest = sorted(ios_runtimes, key=lambda item: item["version_key"])[-1]
    return {key: value for key, value in latest.items() if key != "version_key"}


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
