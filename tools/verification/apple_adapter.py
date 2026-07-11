"""Thin Apple runtime adapter for verification execution."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from tools.verification.adapters import VerificationAdapter
from tools.verification.evidence import LogManager
from tools.verification.models import ArtifactMetadata, EvidenceItem, PrimitiveAction, PrimitiveResult


SENSITIVE_KEY_TOKENS = (
    "token",
    "password",
    "secret",
    "proof",
    "authorization",
    "prompt",
    "history",
    "memory",
    "raw_audio",
)


class AppleAdapterError(RuntimeError):
    """Base Apple adapter error."""


class AppleCommandRunner:
    def run(self, command: tuple[str, ...], *, cwd: Path | None = None, timeout: int = 30) -> tuple[int, str]:
        try:
            output = subprocess.check_output(
                command,
                cwd=cwd,
                text=True,
                stderr=subprocess.STDOUT,
                timeout=timeout,
            )
            return 0, output.strip()
        except subprocess.CalledProcessError as exc:
            return exc.returncode, str(exc.output).strip()
        except (OSError, subprocess.TimeoutExpired) as exc:
            return 127, str(exc)


@dataclass(frozen=True)
class AppleRuntimeTarget:
    target_id: str
    variant: str = "ios"
    runtime: str = "simulator"
    name: str = ""
    udid: str = ""
    bundle_id: str = ""
    app_path: Path | None = None
    booted: bool = False
    metadata: dict[str, Any] | None = None

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "AppleRuntimeTarget":
        app_path = data.get("app_path")
        return cls(
            target_id=str(data.get("target_id") or data.get("id") or data.get("udid") or ""),
            variant=str(data.get("variant") or "ios").lower(),
            runtime=str(data.get("runtime") or "simulator").lower(),
            name=str(data.get("name") or ""),
            udid=str(data.get("udid") or data.get("target_id") or ""),
            bundle_id=str(data.get("bundle_id") or ""),
            app_path=Path(str(app_path)).expanduser() if app_path else None,
            booted=bool(data.get("booted")),
            metadata=dict(data.get("metadata") or {}),
        )

    def to_dict(self) -> dict[str, Any]:
        return _redact(
            {
                "target_id": self.target_id,
                "variant": self.variant,
                "runtime": self.runtime,
                "name": self.name,
                "udid": self.udid,
                "bundle_id": self.bundle_id,
                "app_path": str(self.app_path) if self.app_path else None,
                "booted": self.booted,
                "metadata": self.metadata or {},
            }
        )


@dataclass(frozen=True)
class AppleAdapterConfig:
    target: AppleRuntimeTarget | None = None
    timeout_seconds: float = 30.0
    allow_destructive: bool = False
    allow_physical_devices: bool = False
    evidence_dir: Path | None = None

    @classmethod
    def from_environment(cls, root: Path | None = None) -> "AppleAdapterConfig":
        target_json = os.getenv("DJCONNECT_VERIFICATION_APPLE_TARGET_JSON", "")
        target = AppleRuntimeTarget.from_mapping(json.loads(target_json)) if target_json else None
        evidence_dir = _resolve_optional(root, os.getenv("DJCONNECT_VERIFICATION_APPLE_EVIDENCE_DIR"))
        return cls(
            target=target,
            timeout_seconds=float(os.getenv("DJCONNECT_VERIFICATION_APPLE_TIMEOUT", "30")),
            allow_destructive=_truthy(os.getenv("DJCONNECT_VERIFICATION_ALLOW_DESTRUCTIVE")),
            allow_physical_devices=_truthy(os.getenv("DJCONNECT_VERIFICATION_APPLE_ALLOW_PHYSICAL")),
            evidence_dir=evidence_dir,
        )


class AppleVerificationAdapter(VerificationAdapter):
    """Execute Apple runtime primitives without scenario assertions."""

    name = "apple"

    def __init__(
        self,
        config: AppleAdapterConfig | None = None,
        *,
        runner: Any | None = None,
    ) -> None:
        self.config = config or AppleAdapterConfig.from_environment()
        self.runner = runner or AppleCommandRunner()
        self._logs: list[dict[str, Any]] = []
        self._connected = False

    def initialize(self) -> None:
        self._connected = True
        self._record("initialize", True, {"target": self._target_dict()})

    def shutdown(self) -> None:
        self._connected = False
        self._record("shutdown", True, {"target": self._target_dict()})

    def health(self) -> dict[str, Any]:
        simulators = self.discover_simulators()
        target = self.validate_target_identity()
        return {
            "ok": simulators.ok and (target.ok if self.config.target else True),
            "target_configured": self.config.target is not None,
            "simulator_discovery": simulators.ok,
            "target": self._target_dict(),
        }

    def prepare_environment(self) -> None:
        self._record("prepare_environment", True, {"source": "execution_environment"})

    def launch(self, target: str | None = None) -> PrimitiveResult:
        return self.launch_app(bundle_id=target)

    def stop(self) -> PrimitiveResult:
        return self.terminate_app()

    def restart(self) -> PrimitiveResult:
        stopped = self.terminate_app()
        launched = self.launch_app()
        return PrimitiveResult(
            "restart_app",
            stopped.ok and launched.ok,
            {"terminate": stopped.data, "launch": launched.data},
        )

    def click(self, target: str, **kwargs: Any) -> PrimitiveResult:
        return PrimitiveResult(
            "ui_input",
            False,
            {"error": "CapabilityUnavailable", "input": "click", "target": target, "arguments": _redact(kwargs)},
            message="Apple UI input requires a configured XCTest or accessibility driver.",
        )

    def type(self, text: str, **kwargs: Any) -> PrimitiveResult:
        return PrimitiveResult(
            "ui_input",
            False,
            {"error": "CapabilityUnavailable", "input": "type", "arguments": _redact(kwargs)},
            message="Apple UI text input requires a configured XCTest or accessibility driver.",
        )

    def execute_service(self, name: str, payload: dict[str, Any] | None = None) -> PrimitiveResult:
        return PrimitiveResult("execute_service", False, {"error": "CapabilityUnavailable", "service": name, "payload": _redact(payload or {})})

    def execute_rest(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> PrimitiveResult:
        return PrimitiveResult("http_request", False, {"error": "CapabilityUnavailable", "method": method, "path": path, "payload": _redact(payload or {}), "headers": _redact(headers or {})})

    def execute_websocket(self, message: dict[str, Any]) -> PrimitiveResult:
        return PrimitiveResult("websocket_request", False, {"error": "CapabilityUnavailable", "message": _redact(message)})

    def execute_action(self, action: PrimitiveAction) -> PrimitiveResult:
        name = action.name.lower().replace(" ", "_")
        parameters = action.parameters
        if name in {"connect", "validate_target", "validate_target_identity"}:
            return self.validate_target_identity(parameters)
        if name in {"discover_simulators", "list_simulators"}:
            return self.discover_simulators()
        if name in {"discover_physical_devices", "list_physical_devices"}:
            return self.discover_physical_devices()
        if name in {"collect_environment", "collect_runtime_metadata"}:
            return PrimitiveResult(name, True, self.collect_environment())
        if name in {"collect_app_metadata", "app_metadata"}:
            return self.collect_app_metadata()
        if name == "install_app":
            return self.install_app(_path_parameter(parameters, "app_path"))
        if name == "uninstall_app":
            return self.uninstall_app(str(parameters.get("bundle_id") or ""))
        if name in {"launch_app", "launch"}:
            return self.launch_app(str(parameters.get("bundle_id") or "") or None)
        if name in {"terminate_app", "terminate", "stop"}:
            return self.terminate_app(str(parameters.get("bundle_id") or "") or None)
        if name == "reset_app_state":
            return self.reset_app_state(str(parameters.get("bundle_id") or "") or None)
        if name in {"collect_logs", "system_logs"}:
            return PrimitiveResult("collect_logs", True, {"logs": list(self.collect_logs())})
        if name in {"capture_screenshot", "screenshot"}:
            return self.capture_screenshot(str(parameters.get("name") or "") or None)
        return PrimitiveResult(name, False, {"error": "CapabilityUnavailable", "action": action.name})

    def cleanup(self) -> None:
        self._record("cleanup", True, {"target": self._target_dict()})

    def collect_logs(self) -> tuple:
        logs = list(self._logs)
        if self.config.target and self.config.target.runtime == "simulator" and self.config.target.udid:
            result = self._run(("xcrun", "simctl", "spawn", self.config.target.udid, "log", "show", "--style", "json", "--last", "2m"), "collect_system_logs", timeout=15)
            logs.append({"source": "simulator_system_log", "ok": result.ok, "data": result.data})
        return tuple(_redact(logs))

    def collect_artifacts(self) -> tuple:
        return tuple(item for item in (self.config.target.app_path if self.config.target else None,) if item)

    def capture_screenshot(self, name: str | None = None) -> PrimitiveResult:
        target = self.config.target
        if not target or target.runtime != "simulator" or not target.udid:
            return PrimitiveResult("capture_screenshot", False, {"error": "UnsupportedTarget", "target": self._target_dict()})
        evidence_dir = self.config.evidence_dir
        if evidence_dir is None:
            return PrimitiveResult("capture_screenshot", False, {"error": "EvidenceDirectoryUnavailable"})
        evidence_dir.mkdir(parents=True, exist_ok=True)
        path = evidence_dir / f"{_safe_name(name or target.target_id or 'apple-target')}.png"
        result = self._run(("xcrun", "simctl", "io", target.udid, "screenshot", str(path)), "capture_screenshot")
        evidence = (EvidenceItem("screenshot", path, {"target_id": target.target_id, "client_variant": target.variant}),) if result.ok else ()
        return PrimitiveResult("capture_screenshot", result.ok, {**result.data, "path": str(path)}, evidence=evidence, message=result.message)

    def capture_serial(self) -> tuple:
        return ()

    def collect_environment(self) -> dict[str, Any]:
        xcode = self._run(("xcodebuild", "-version"), "xcode_version", timeout=10)
        return {
            "adapter": self.name,
            "host": platform.node(),
            "os": platform.platform(),
            "architecture": platform.machine(),
            "target": self._target_dict(),
            "xcode": xcode.data,
            "capabilities": {
                "simulator_discovery": True,
                "physical_discovery": self.config.allow_physical_devices,
                "install": self.config.target is not None,
                "launch": self.config.target is not None,
                "terminate": self.config.target is not None,
                "screenshots": self.config.target is not None and self.config.target.runtime == "simulator",
                "logs": True,
            },
        }

    def collect_artifact_metadata(self) -> tuple[ArtifactMetadata, ...]:
        result = self.collect_app_metadata()
        if not result.ok:
            return ()
        app_path = self.config.target.app_path if self.config.target else None
        if app_path is None:
            return ()
        return (
            ArtifactMetadata(
                path=app_path,
                name=app_path.name,
                sha256=result.data.get("sha256"),
                configuration={"client_variant": self.config.target.variant if self.config.target else "unknown"},
                instrumented=True,
            ),
        )

    def reset(self) -> None:
        self._logs.clear()
        self._connected = False

    def discover_simulators(self) -> PrimitiveResult:
        result = self._run(("xcrun", "simctl", "list", "devices", "available", "--json"), "discover_simulators", timeout=20)
        if not result.ok:
            return result
        devices = parse_simctl_devices(str(result.data.get("stdout") or "{}"))
        return PrimitiveResult("discover_simulators", True, {"devices": [_redact(device) for device in devices]})

    def discover_physical_devices(self) -> PrimitiveResult:
        if not self.config.allow_physical_devices:
            return PrimitiveResult("discover_physical_devices", False, {"error": "PhysicalDeviceExecutionNotConfigured"})
        return self._run(("xcrun", "devicectl", "list", "devices", "--json-output", "-"), "discover_physical_devices", timeout=20)

    def validate_target_identity(self, expected: dict[str, Any] | None = None) -> PrimitiveResult:
        target = self.config.target
        if target is None:
            return PrimitiveResult("validate_target_identity", False, {"error": "AppleTargetUnavailable"})
        if target.runtime == "physical" and not self.config.allow_physical_devices:
            return PrimitiveResult("validate_target_identity", False, {"error": "PhysicalDeviceExecutionNotConfigured", "target": target.to_dict()})
        expected = expected or {}
        mismatches = {}
        for key in ("target_id", "variant", "runtime", "bundle_id"):
            value = expected.get(key)
            if value and str(getattr(target, key)) != str(value):
                mismatches[key] = {"expected": value, "actual": getattr(target, key)}
        return PrimitiveResult("validate_target_identity", not mismatches, {"target": target.to_dict(), "mismatches": _redact(mismatches)})

    def install_app(self, app_path: Path | None = None) -> PrimitiveResult:
        target = self.config.target
        if target is None:
            return PrimitiveResult("install_app", False, {"error": "AppleTargetUnavailable"})
        path = app_path or target.app_path
        if path is None:
            return PrimitiveResult("install_app", False, {"error": "AppArtifactUnavailable"})
        if target.runtime != "simulator":
            return PrimitiveResult("install_app", False, {"error": "UnsupportedTarget", "runtime": target.runtime})
        return self._run(("xcrun", "simctl", "install", target.udid, str(path)), "install_app")

    def uninstall_app(self, bundle_id: str = "") -> PrimitiveResult:
        target = self.config.target
        bundle_id = bundle_id or (target.bundle_id if target else "")
        if target is None or not bundle_id:
            return PrimitiveResult("uninstall_app", False, {"error": "AppleTargetUnavailable" if target is None else "BundleIdUnavailable"})
        if target.runtime != "simulator":
            return PrimitiveResult("uninstall_app", False, {"error": "UnsupportedTarget", "runtime": target.runtime})
        return self._run(("xcrun", "simctl", "uninstall", target.udid, bundle_id), "uninstall_app")

    def launch_app(self, bundle_id: str | None = None) -> PrimitiveResult:
        target = self.config.target
        bundle_id = bundle_id or (target.bundle_id if target else "")
        if target is None or not bundle_id:
            return PrimitiveResult("launch_app", False, {"error": "AppleTargetUnavailable" if target is None else "BundleIdUnavailable"})
        if target.runtime != "simulator":
            return PrimitiveResult("launch_app", False, {"error": "UnsupportedTarget", "runtime": target.runtime})
        return self._run(("xcrun", "simctl", "launch", target.udid, bundle_id), "launch_app")

    def terminate_app(self, bundle_id: str | None = None) -> PrimitiveResult:
        target = self.config.target
        bundle_id = bundle_id or (target.bundle_id if target else "")
        if target is None or not bundle_id:
            return PrimitiveResult("terminate_app", False, {"error": "AppleTargetUnavailable" if target is None else "BundleIdUnavailable"})
        if target.runtime != "simulator":
            return PrimitiveResult("terminate_app", False, {"error": "UnsupportedTarget", "runtime": target.runtime})
        return self._run(("xcrun", "simctl", "terminate", target.udid, bundle_id), "terminate_app")

    def reset_app_state(self, bundle_id: str | None = None) -> PrimitiveResult:
        if not self.config.allow_destructive:
            return PrimitiveResult("reset_app_state", False, {"error": "DestructiveOperationNotAllowed"})
        target = self.config.target
        bundle_id = bundle_id or (target.bundle_id if target else "")
        if target is None or not bundle_id:
            return PrimitiveResult("reset_app_state", False, {"error": "AppleTargetUnavailable" if target is None else "BundleIdUnavailable"})
        if target.runtime != "simulator":
            return PrimitiveResult("reset_app_state", False, {"error": "UnsupportedTarget", "runtime": target.runtime})
        return self._run(("xcrun", "simctl", "uninstall", target.udid, bundle_id), "reset_app_state")

    def collect_app_metadata(self) -> PrimitiveResult:
        target = self.config.target
        if target is None or target.app_path is None:
            return PrimitiveResult("collect_app_metadata", False, {"error": "AppArtifactUnavailable"})
        path = target.app_path
        if not path.exists():
            return PrimitiveResult("collect_app_metadata", False, {"error": "AppArtifactUnavailable", "path": str(path)})
        digest = _sha256_file(path) if path.is_file() else None
        return PrimitiveResult(
            "collect_app_metadata",
            True,
            {
                "path": str(path),
                "name": path.name,
                "is_dir": path.is_dir(),
                "size": path.stat().st_size if path.is_file() else None,
                "sha256": digest,
                "target": target.to_dict(),
            },
        )

    def _run(self, command: tuple[str, ...], operation: str, *, timeout: int | None = None) -> PrimitiveResult:
        started = time.perf_counter()
        code, output = self.runner.run(command, timeout=timeout or int(self.config.timeout_seconds))
        ok = code == 0
        data = {
            "command": _redact_command(command),
            "returncode": code,
            "stdout": LogManager().redact(output[-8000:]),
            "duration_seconds": time.perf_counter() - started,
        }
        self._record(operation, ok, data, started=started)
        return PrimitiveResult(operation, ok, _redact(data), message="" if ok else "CommandFailed")

    def _record(self, operation: str, ok: bool, data: dict[str, Any], *, started: float | None = None) -> None:
        self._logs.append(
            {
                "timestamp": time.time(),
                "operation": operation,
                "ok": ok,
                "duration_seconds": (time.perf_counter() - started) if started else 0.0,
                "target_id": self.config.target.target_id if self.config.target else None,
                "client_variant": self.config.target.variant if self.config.target else None,
                "data": _redact(data),
            }
        )

    def _target_dict(self) -> dict[str, Any] | None:
        return self.config.target.to_dict() if self.config.target else None


def parse_simctl_devices(payload: str) -> list[dict[str, Any]]:
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return []
    devices_by_runtime = data.get("devices") if isinstance(data, dict) else None
    if not isinstance(devices_by_runtime, dict):
        return []
    devices: list[dict[str, Any]] = []
    for runtime, runtime_devices in devices_by_runtime.items():
        if not isinstance(runtime_devices, list):
            continue
        for device in runtime_devices:
            if not isinstance(device, dict):
                continue
            devices.append(
                {
                    "runtime": runtime,
                    "name": device.get("name"),
                    "udid": device.get("udid"),
                    "state": device.get("state"),
                    "is_available": device.get("isAvailable", device.get("is_available")),
                    "variant": _variant_from_runtime(runtime),
                    "booted": str(device.get("state") or "").lower() == "booted",
                }
            )
    return devices


def _variant_from_runtime(runtime: str) -> str:
    lowered = runtime.lower()
    if "watch" in lowered:
        return "watchos"
    if "tvos" in lowered:
        return "tvos"
    if "ios" in lowered:
        return "ios"
    return "apple"


def _path_parameter(parameters: dict[str, Any], key: str) -> Path | None:
    value = parameters.get(key)
    return Path(str(value)).expanduser() if value else None


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: ("<redacted>" if any(token in str(key).lower() for token in SENSITIVE_KEY_TOKENS) else _redact(item)) for key, item in value.items()}
    if isinstance(value, list):
        return [_redact(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_redact(item) for item in value)
    if isinstance(value, str):
        return LogManager().redact(value)
    return value


def _redact_command(command: tuple[str, ...]) -> tuple[str, ...]:
    redacted: list[str] = []
    redact_next = False
    for item in command:
        lowered = item.lower()
        if redact_next or any(token in lowered for token in SENSITIVE_KEY_TOKENS):
            redacted.append("<redacted>")
            redact_next = False
            continue
        redacted.append(item)
        if lowered in {"--token", "--password", "--secret", "--authorization"}:
            redact_next = True
    return tuple(redacted)


def _resolve_optional(root: Path | None, value: str | None) -> Path | None:
    if not value:
        return None
    path = Path(value).expanduser()
    return path if path.is_absolute() or root is None else root / path


def _truthy(value: Any) -> bool:
    return str(value).lower() in {"1", "true", "yes", "on"}


def _safe_name(value: str) -> str:
    cleaned = "".join(character if character.isalnum() or character in {"-", "_"} else "-" for character in value)
    return cleaned.strip("-") or "apple-target"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
