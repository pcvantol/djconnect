"""Thin Raspberry Pi runtime adapter for verification execution."""

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


class RaspberryPiCommandRunner:
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
class RaspberryPiRuntimeTarget:
    target_id: str
    runtime: str = "local"
    host: str = ""
    port: int = 22
    user: str = ""
    app_path: Path | None = None
    launch_command: str = ""
    stop_command: str = ""
    restart_command: str = ""
    log_command: str = ""
    screenshot_command: str = ""
    metadata_command: str = ""
    metadata: dict[str, Any] | None = None

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "RaspberryPiRuntimeTarget":
        app_path = data.get("app_path")
        return cls(
            target_id=str(data.get("target_id") or data.get("id") or data.get("host") or ""),
            runtime=str(data.get("runtime") or "local").lower(),
            host=str(data.get("host") or ""),
            port=int(data.get("port") or 22),
            user=str(data.get("user") or ""),
            app_path=Path(str(app_path)).expanduser() if app_path else None,
            launch_command=str(data.get("launch_command") or ""),
            stop_command=str(data.get("stop_command") or ""),
            restart_command=str(data.get("restart_command") or ""),
            log_command=str(data.get("log_command") or ""),
            screenshot_command=str(data.get("screenshot_command") or ""),
            metadata_command=str(data.get("metadata_command") or ""),
            metadata=dict(data.get("metadata") or {}),
        )

    def to_dict(self) -> dict[str, Any]:
        return _redact(
            {
                "target_id": self.target_id,
                "runtime": self.runtime,
                "host": self.host,
                "port": self.port,
                "user": self.user,
                "app_path": str(self.app_path) if self.app_path else None,
                "launch_command": self.launch_command,
                "stop_command": self.stop_command,
                "restart_command": self.restart_command,
                "log_command": self.log_command,
                "screenshot_command": self.screenshot_command,
                "metadata_command": self.metadata_command,
                "metadata": self.metadata or {},
            }
        )


@dataclass(frozen=True)
class RaspberryPiAdapterConfig:
    target: RaspberryPiRuntimeTarget | None = None
    timeout_seconds: float = 30.0
    allow_destructive: bool = False
    allow_live_ssh: bool = False
    evidence_dir: Path | None = None

    @classmethod
    def from_environment(cls, root: Path | None = None) -> "RaspberryPiAdapterConfig":
        target_json = os.getenv("DJCONNECT_VERIFICATION_PI_TARGET_JSON", "")
        target = RaspberryPiRuntimeTarget.from_mapping(json.loads(target_json)) if target_json else None
        evidence_dir = _resolve_optional(root, os.getenv("DJCONNECT_VERIFICATION_PI_EVIDENCE_DIR"))
        return cls(
            target=target,
            timeout_seconds=float(os.getenv("DJCONNECT_VERIFICATION_PI_TIMEOUT", "30")),
            allow_destructive=_truthy(os.getenv("DJCONNECT_VERIFICATION_ALLOW_DESTRUCTIVE")),
            allow_live_ssh=_truthy(os.getenv("DJCONNECT_VERIFICATION_PI_ALLOW_SSH")),
            evidence_dir=evidence_dir,
        )


class RaspberryPiVerificationAdapter(VerificationAdapter):
    """Execute Raspberry Pi runtime primitives without scenario assertions."""

    name = "raspberry_pi"

    def __init__(
        self,
        config: RaspberryPiAdapterConfig | None = None,
        *,
        runner: Any | None = None,
    ) -> None:
        self.config = config or RaspberryPiAdapterConfig.from_environment()
        self.runner = runner or RaspberryPiCommandRunner()
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
        return {
            "ok": target.ok and metadata.ok,
            "target_configured": self.config.target is not None,
            "target": self._target_dict(),
        }

    def prepare_environment(self) -> None:
        self._record("prepare_environment", True, {"source": "execution_environment"})

    def launch(self, target: str | None = None) -> PrimitiveResult:
        return self.launch_app()

    def stop(self) -> PrimitiveResult:
        return self.stop_app()

    def restart(self) -> PrimitiveResult:
        target = self.config.target
        if target and target.restart_command:
            return self._run_target_command(target.restart_command, "restart_app")
        stopped = self.stop_app()
        launched = self.launch_app()
        return PrimitiveResult("restart_app", stopped.ok and launched.ok, {"stop": stopped.data, "launch": launched.data})

    def click(self, target: str, **kwargs: Any) -> PrimitiveResult:
        return PrimitiveResult(
            "ui_input",
            False,
            {"error": "CapabilityUnavailable", "input": "click", "target": target, "arguments": _redact(kwargs)},
            message="Raspberry Pi UI input requires a configured UI driver.",
        )

    def type(self, text: str, **kwargs: Any) -> PrimitiveResult:
        return PrimitiveResult(
            "ui_input",
            False,
            {"error": "CapabilityUnavailable", "input": "type", "arguments": _redact(kwargs)},
            message="Raspberry Pi UI text input requires a configured UI driver.",
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
        if name in {"collect_environment", "collect_runtime_metadata"}:
            return PrimitiveResult(name, True, self.collect_environment())
        if name in {"collect_app_metadata", "app_metadata"}:
            return self.collect_app_metadata()
        if name in {"launch_app", "launch"}:
            return self.launch_app()
        if name in {"stop_app", "terminate_app", "terminate", "stop"}:
            return self.stop_app()
        if name in {"restart_app", "restart"}:
            return self.restart()
        if name in {"collect_logs", "system_logs"}:
            return PrimitiveResult("collect_logs", True, {"logs": list(self.collect_logs())})
        if name in {"capture_screenshot", "screenshot"}:
            return self.capture_screenshot(str(parameters.get("name") or "") or None)
        return PrimitiveResult(name, False, {"error": "CapabilityUnavailable", "action": action.name})

    def cleanup(self) -> None:
        self._record("cleanup", True, {"target": self._target_dict()})

    def collect_logs(self) -> tuple:
        logs = list(self._logs)
        target = self.config.target
        if target and target.log_command:
            result = self._run_target_command(target.log_command, "collect_system_logs", timeout=15)
            logs.append({"source": "raspberry_pi_log_command", "ok": result.ok, "data": result.data})
        return tuple(_redact(logs))

    def collect_artifacts(self) -> tuple:
        return tuple(item for item in (self.config.target.app_path if self.config.target else None,) if item)

    def capture_screenshot(self, name: str | None = None) -> PrimitiveResult:
        target = self.config.target
        if target is None or not target.screenshot_command:
            return PrimitiveResult("capture_screenshot", False, {"error": "ScreenshotCommandUnavailable", "target": self._target_dict()})
        evidence_dir = self.config.evidence_dir
        if evidence_dir is None:
            return PrimitiveResult("capture_screenshot", False, {"error": "EvidenceDirectoryUnavailable"})
        evidence_dir.mkdir(parents=True, exist_ok=True)
        path = evidence_dir / f"{_safe_name(name or target.target_id or 'raspberry-pi-target')}.png"
        command = target.screenshot_command.format(path=str(path))
        result = self._run_target_command(command, "capture_screenshot")
        evidence = (EvidenceItem("screenshot", path, {"target_id": target.target_id, "runtime": target.runtime}),) if result.ok else ()
        return PrimitiveResult("capture_screenshot", result.ok, {**result.data, "path": str(path)}, evidence=evidence, message=result.message)

    def capture_serial(self) -> tuple:
        return ()

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
                "ssh_runtime": self.config.target is not None and self.config.target.runtime == "ssh" and self.config.allow_live_ssh,
                "launch": bool(self.config.target and self.config.target.launch_command),
                "stop": bool(self.config.target and self.config.target.stop_command),
                "screenshots": bool(self.config.target and self.config.target.screenshot_command),
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
            return PrimitiveResult("validate_target_identity", False, {"error": "RaspberryPiTargetUnavailable"})
        if target.runtime == "ssh" and not self.config.allow_live_ssh:
            return PrimitiveResult("validate_target_identity", False, {"error": "LiveSshExecutionNotConfigured", "target": target.to_dict()})
        if target.runtime == "ssh" and (not target.host or not target.user):
            return PrimitiveResult("validate_target_identity", False, {"error": "SshTargetIncomplete", "target": target.to_dict()})
        if target.runtime not in {"local", "ssh"}:
            return PrimitiveResult("validate_target_identity", False, {"error": "UnsupportedRuntime", "target": target.to_dict()})
        expected = expected or {}
        mismatches = {}
        for key in ("target_id", "runtime", "host", "user"):
            value = expected.get(key)
            if value and str(getattr(target, key)) != str(value):
                mismatches[key] = {"expected": value, "actual": getattr(target, key)}
        return PrimitiveResult("validate_target_identity", not mismatches, {"target": target.to_dict(), "mismatches": _redact(mismatches)})

    def collect_runtime_metadata(self) -> PrimitiveResult:
        target = self.config.target
        if target is None:
            return PrimitiveResult("collect_runtime_metadata", False, {"error": "RaspberryPiTargetUnavailable"})
        if target.metadata_command:
            return self._run_target_command(target.metadata_command, "collect_runtime_metadata", timeout=10)
        return PrimitiveResult("collect_runtime_metadata", True, {"target": target.to_dict()})

    def launch_app(self) -> PrimitiveResult:
        target = self.config.target
        if target is None:
            return PrimitiveResult("launch_app", False, {"error": "RaspberryPiTargetUnavailable"})
        if not target.launch_command:
            return PrimitiveResult("launch_app", False, {"error": "LaunchCommandUnavailable"})
        return self._run_target_command(target.launch_command, "launch_app")

    def stop_app(self) -> PrimitiveResult:
        target = self.config.target
        if target is None:
            return PrimitiveResult("stop_app", False, {"error": "RaspberryPiTargetUnavailable"})
        if not target.stop_command:
            return PrimitiveResult("stop_app", False, {"error": "StopCommandUnavailable"})
        return self._run_target_command(target.stop_command, "stop_app")

    def collect_app_metadata(self) -> PrimitiveResult:
        target = self.config.target
        if target is None or target.app_path is None:
            return PrimitiveResult("collect_app_metadata", False, {"error": "AppArtifactUnavailable"})
        if target.runtime == "ssh":
            return PrimitiveResult("collect_app_metadata", True, {"path": str(target.app_path), "target": target.to_dict(), "remote": True})
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

    def _run_target_command(self, command: str, operation: str, *, timeout: int | None = None) -> PrimitiveResult:
        target = self.config.target
        if target is None:
            return PrimitiveResult(operation, False, {"error": "RaspberryPiTargetUnavailable"})
        validation = self.validate_target_identity()
        if not validation.ok:
            return PrimitiveResult(operation, False, validation.data, message=validation.message)
        if target.runtime == "ssh":
            argv = ("ssh", "-p", str(target.port), f"{target.user}@{target.host}", command)
        else:
            argv = tuple(shlex.split(command))
        return self._run(argv, operation, timeout=timeout)

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


def _safe_name(value: str) -> str:
    cleaned = "".join(character if character.isalnum() or character in {"-", "_"} else "-" for character in value)
    return cleaned.strip("-") or "raspberry-pi-target"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
