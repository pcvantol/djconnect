"""Thin ESP32 runtime adapter for verification execution."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import shlex
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


class ESP32CommandRunner:
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
class ESP32RuntimeTarget:
    target_id: str
    runtime: str = "local"
    host: str = ""
    serial_port: str = ""
    app_path: Path | None = None
    build_command: str = ""
    flash_command: str = ""
    reset_command: str = ""
    log_command: str = ""
    serial_command: str = ""
    metadata_command: str = ""
    metadata: dict[str, Any] | None = None

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "ESP32RuntimeTarget":
        app_path = data.get("app_path") or data.get("firmware_path") or data.get("repo_path")
        return cls(
            target_id=str(data.get("target_id") or data.get("id") or data.get("device_id") or data.get("host") or ""),
            runtime=str(data.get("runtime") or "local").lower(),
            host=str(data.get("host") or ""),
            serial_port=str(data.get("serial_port") or data.get("port") or ""),
            app_path=Path(str(app_path)).expanduser() if app_path else None,
            build_command=str(data.get("build_command") or ""),
            flash_command=str(data.get("flash_command") or ""),
            reset_command=str(data.get("reset_command") or ""),
            log_command=str(data.get("log_command") or ""),
            serial_command=str(data.get("serial_command") or ""),
            metadata_command=str(data.get("metadata_command") or ""),
            metadata=dict(data.get("metadata") or {}),
        )

    def to_dict(self) -> dict[str, Any]:
        return _redact(
            {
                "target_id": self.target_id,
                "runtime": self.runtime,
                "host": self.host,
                "serial_port": self.serial_port,
                "app_path": str(self.app_path) if self.app_path else None,
                "build_command": self.build_command,
                "flash_command": self.flash_command,
                "reset_command": self.reset_command,
                "log_command": self.log_command,
                "serial_command": self.serial_command,
                "metadata_command": self.metadata_command,
                "metadata": self.metadata or {},
            }
        )


@dataclass(frozen=True)
class ESP32AdapterConfig:
    target: ESP32RuntimeTarget | None = None
    timeout_seconds: float = 30.0
    allow_destructive: bool = False
    allow_live_serial: bool = False
    evidence_dir: Path | None = None

    @classmethod
    def from_environment(cls, root: Path | None = None) -> "ESP32AdapterConfig":
        target_json = os.getenv("DJCONNECT_VERIFICATION_ESP32_TARGET_JSON", "")
        target = ESP32RuntimeTarget.from_mapping(json.loads(target_json)) if target_json else None
        evidence_dir = _resolve_optional(root, os.getenv("DJCONNECT_VERIFICATION_ESP32_EVIDENCE_DIR"))
        return cls(
            target=target,
            timeout_seconds=float(os.getenv("DJCONNECT_VERIFICATION_ESP32_TIMEOUT", "30")),
            allow_destructive=_truthy(os.getenv("DJCONNECT_VERIFICATION_ALLOW_DESTRUCTIVE")),
            allow_live_serial=_truthy(os.getenv("DJCONNECT_VERIFICATION_ESP32_ALLOW_SERIAL")),
            evidence_dir=evidence_dir,
        )


class ESP32VerificationAdapter(VerificationAdapter):
    """Execute ESP32 runtime primitives without scenario assertions."""

    name = "esp32"

    def __init__(self, config: ESP32AdapterConfig | None = None, *, runner: Any | None = None) -> None:
        self.config = config or ESP32AdapterConfig.from_environment()
        self.runner = runner or ESP32CommandRunner()
        self._logs: list[dict[str, Any]] = []
        self._connected = False

    def initialize(self) -> None:
        self._connected = True
        self._record("initialize", True, {"target": self._target_dict()})

    def shutdown(self) -> None:
        self._connected = False
        self._record("shutdown", True, {"target": self._target_dict()})

    def health(self) -> dict[str, Any]:
        target = self.validate_target_identity()
        metadata = self.collect_runtime_metadata()
        return {"ok": target.ok and metadata.ok, "target_configured": self.config.target is not None, "target": self._target_dict()}

    def prepare_environment(self) -> None:
        self._record("prepare_environment", True, {"source": "execution_environment"})

    def launch(self, target: str | None = None) -> PrimitiveResult:
        return self.build_firmware()

    def stop(self) -> PrimitiveResult:
        return self.reset_device()

    def restart(self) -> PrimitiveResult:
        return self.reset_device()

    def click(self, target: str, **kwargs: Any) -> PrimitiveResult:
        return PrimitiveResult("ui_input", False, {"error": "CapabilityUnavailable", "input": "click", "target": target, "arguments": _redact(kwargs)})

    def type(self, text: str, **kwargs: Any) -> PrimitiveResult:
        return PrimitiveResult("ui_input", False, {"error": "CapabilityUnavailable", "input": "type", "arguments": _redact(kwargs)})

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
        if name in {"collect_environment", "collect_runtime_metadata"}:
            return PrimitiveResult(name, True, self.collect_environment())
        if name in {"collect_app_metadata", "app_metadata", "collect_firmware_metadata"}:
            return self.collect_app_metadata()
        if name in {"build_firmware", "build_app", "launch_app", "launch"}:
            return self.build_firmware()
        if name in {"flash_firmware", "flash_app", "install_app", "install"}:
            return self.flash_firmware()
        if name in {"reset_device", "stop_app", "terminate_app", "terminate", "stop", "restart"}:
            return self.reset_device()
        if name in {"collect_logs", "serial_logs", "collect_serial"}:
            return PrimitiveResult("collect_logs", True, {"logs": list(self.collect_logs())})
        if name in {"capture_screenshot", "screenshot"}:
            return self.capture_screenshot(str(parameters.get("name") or "") or None)
        return PrimitiveResult(name, False, {"error": "CapabilityUnavailable", "action": action.name, "arguments": _redact(parameters)})

    def cleanup(self) -> None:
        self._record("cleanup", True, {"target": self._target_dict()})

    def collect_logs(self) -> tuple:
        logs = list(self._logs)
        target = self.config.target
        command = target.serial_command or target.log_command if target else ""
        if command:
            result = self._run_target_command(command, "collect_serial_logs", timeout=15)
            logs.append({"source": "esp32_serial_log_command", "ok": result.ok, "data": result.data})
        return tuple(_redact(logs))

    def collect_artifacts(self) -> tuple:
        return tuple(item for item in (self.config.target.app_path if self.config.target else None,) if item)

    def capture_screenshot(self, name: str | None = None) -> PrimitiveResult:
        return PrimitiveResult("capture_screenshot", False, {"error": "ScreenshotUnavailable", "target": self._target_dict()}, message="ESP32 screenshot capture requires a configured display capture tool.")

    def capture_serial(self) -> tuple:
        return self.collect_logs()

    def collect_environment(self) -> dict[str, Any]:
        metadata = self.collect_runtime_metadata()
        return {
            "adapter": self.name,
            "host": platform.node(),
            "os": platform.platform(),
            "architecture": platform.machine(),
            "target": self._target_dict(),
            "target_metadata": metadata.data,
            "capabilities": {
                "target_configured": self.config.target is not None,
                "local_runtime": self.config.target is not None and self.config.target.runtime == "local",
                "serial_runtime": self.config.target is not None and self.config.allow_live_serial,
                "build": bool(self.config.target and self.config.target.build_command),
                "flash": bool(self.config.target and self.config.target.flash_command and self.config.allow_destructive),
                "reset": bool(self.config.target and self.config.target.reset_command),
                "serial_logs": True,
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
                configuration={"runtime": self.config.target.runtime if self.config.target else "unknown"},
                instrumented=True,
            ),
        )

    def reset(self) -> None:
        self._logs.clear()
        self._connected = False

    def validate_target_identity(self, expected: dict[str, Any] | None = None) -> PrimitiveResult:
        target = self.config.target
        if target is None:
            return PrimitiveResult("validate_target_identity", False, {"error": "ESP32TargetUnavailable"})
        if target.runtime == "serial" and not self.config.allow_live_serial:
            return PrimitiveResult("validate_target_identity", False, {"error": "LiveSerialExecutionNotConfigured", "target": target.to_dict()})
        if target.runtime == "serial" and not target.serial_port:
            return PrimitiveResult("validate_target_identity", False, {"error": "SerialTargetIncomplete", "target": target.to_dict()})
        if target.runtime not in {"local", "serial"}:
            return PrimitiveResult("validate_target_identity", False, {"error": "UnsupportedRuntime", "target": target.to_dict()})
        expected = expected or {}
        mismatches = {}
        for key in ("target_id", "runtime", "host", "serial_port"):
            value = expected.get(key)
            if value and str(getattr(target, key)) != str(value):
                mismatches[key] = {"expected": value, "actual": getattr(target, key)}
        return PrimitiveResult("validate_target_identity", not mismatches, {"target": target.to_dict(), "mismatches": _redact(mismatches)})

    def collect_runtime_metadata(self) -> PrimitiveResult:
        target = self.config.target
        if target is None:
            return PrimitiveResult("collect_runtime_metadata", False, {"error": "ESP32TargetUnavailable"})
        if target.metadata_command:
            return self._run_target_command(target.metadata_command, "collect_runtime_metadata", timeout=10)
        return PrimitiveResult("collect_runtime_metadata", True, {"target": target.to_dict()})

    def build_firmware(self) -> PrimitiveResult:
        target = self.config.target
        if target is None:
            return PrimitiveResult("build_firmware", False, {"error": "ESP32TargetUnavailable"})
        if not target.build_command:
            return PrimitiveResult("build_firmware", False, {"error": "BuildCommandUnavailable"})
        return self._run_target_command(target.build_command, "build_firmware")

    def flash_firmware(self) -> PrimitiveResult:
        target = self.config.target
        if target is None:
            return PrimitiveResult("flash_firmware", False, {"error": "ESP32TargetUnavailable"})
        if not self.config.allow_destructive:
            return PrimitiveResult("flash_firmware", False, {"error": "DestructiveExecutionNotConfigured", "target": target.to_dict()})
        if not target.flash_command:
            return PrimitiveResult("flash_firmware", False, {"error": "FlashCommandUnavailable"})
        return self._run_target_command(target.flash_command, "flash_firmware")

    def reset_device(self) -> PrimitiveResult:
        target = self.config.target
        if target is None:
            return PrimitiveResult("reset_device", False, {"error": "ESP32TargetUnavailable"})
        if not target.reset_command:
            return PrimitiveResult("reset_device", False, {"error": "ResetCommandUnavailable"})
        return self._run_target_command(target.reset_command, "reset_device")

    def collect_app_metadata(self) -> PrimitiveResult:
        target = self.config.target
        if target is None or target.app_path is None:
            return PrimitiveResult("collect_app_metadata", False, {"error": "FirmwareArtifactUnavailable"})
        path = target.app_path
        if not path.exists():
            return PrimitiveResult("collect_app_metadata", False, {"error": "FirmwareArtifactUnavailable", "path": str(path)})
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

    def _run_target_command(self, command: str, operation: str, *, timeout: int | None = None) -> PrimitiveResult:
        validation = self.validate_target_identity()
        if not validation.ok:
            return PrimitiveResult(operation, False, validation.data, message=validation.message)
        return self._run(tuple(shlex.split(command)), operation, timeout=timeout)

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
                "runtime": self.config.target.runtime if self.config.target else None,
                "data": _redact(data),
            }
        )

    def _target_dict(self) -> dict[str, Any] | None:
        return self.config.target.to_dict() if self.config.target else None


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


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
