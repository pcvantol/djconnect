"""Thin Voice Assistant runtime adapter for verification execution."""

from __future__ import annotations

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
from tools.verification.models import ArtifactMetadata
from tools.verification.models import PrimitiveAction, PrimitiveResult


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


class VoiceAssistantCommandRunner:
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
class VoiceAssistantRuntimeTarget:
    target_id: str
    runtime: str = "local"
    ha_url: str = ""
    endpoint_id: str = ""
    assist_pipeline_id: str = ""
    metadata_command: str = ""
    health_command: str = ""
    log_command: str = ""
    metadata: dict[str, Any] | None = None

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "VoiceAssistantRuntimeTarget":
        return cls(
            target_id=str(data.get("target_id") or data.get("id") or data.get("endpoint_id") or ""),
            runtime=str(data.get("runtime") or "local").lower(),
            ha_url=str(data.get("ha_url") or data.get("home_assistant_url") or ""),
            endpoint_id=str(data.get("endpoint_id") or ""),
            assist_pipeline_id=str(data.get("assist_pipeline_id") or data.get("pipeline_id") or ""),
            metadata_command=str(data.get("metadata_command") or ""),
            health_command=str(data.get("health_command") or ""),
            log_command=str(data.get("log_command") or ""),
            metadata=dict(data.get("metadata") or {}),
        )

    def to_dict(self) -> dict[str, Any]:
        return _redact(
            {
                "target_id": self.target_id,
                "runtime": self.runtime,
                "ha_url": self.ha_url,
                "endpoint_id": self.endpoint_id,
                "assist_pipeline_id": self.assist_pipeline_id,
                "metadata_command": self.metadata_command,
                "health_command": self.health_command,
                "log_command": self.log_command,
                "metadata": self.metadata or {},
            }
        )


@dataclass(frozen=True)
class VoiceAssistantAdapterConfig:
    target: VoiceAssistantRuntimeTarget | None = None
    timeout_seconds: float = 30.0
    allow_live_runtime: bool = False

    @classmethod
    def from_environment(cls, root: Path | None = None) -> "VoiceAssistantAdapterConfig":
        target_json = os.getenv("DJCONNECT_VERIFICATION_VOICE_ASSISTANT_TARGET_JSON", "")
        target = VoiceAssistantRuntimeTarget.from_mapping(json.loads(target_json)) if target_json else None
        return cls(
            target=target,
            timeout_seconds=float(os.getenv("DJCONNECT_VERIFICATION_VOICE_ASSISTANT_TIMEOUT", "30")),
            allow_live_runtime=_truthy(os.getenv("DJCONNECT_VERIFICATION_VOICE_ASSISTANT_ALLOW_LIVE")),
        )


class VoiceAssistantVerificationAdapter(VerificationAdapter):
    """Execute Voice Assistant runtime primitives without scenario assertions."""

    name = "voice_endpoint"

    def __init__(
        self,
        config: VoiceAssistantAdapterConfig | None = None,
        *,
        runner: Any | None = None,
    ) -> None:
        self.config = config or VoiceAssistantAdapterConfig.from_environment()
        self.runner = runner or VoiceAssistantCommandRunner()
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
        metadata = self.collect_assist_metadata()
        return {"ok": target.ok and metadata.ok, "target_configured": self.config.target is not None, "target": self._target_dict()}

    def prepare_environment(self) -> None:
        self._record("prepare_environment", True, {"source": "execution_environment"})

    def launch(self, target: str | None = None) -> PrimitiveResult:
        return self.probe_voice_endpoint()

    def stop(self) -> PrimitiveResult:
        return PrimitiveResult("stop_voice_endpoint", True, {"noop": True})

    def restart(self) -> PrimitiveResult:
        return self.probe_voice_endpoint()

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
        if name in {"connect", "validate_target", "validate_target_identity"}:
            return self.validate_target_identity(action.parameters)
        if name in {"collect_environment", "collect_runtime_metadata"}:
            return PrimitiveResult(name, True, self.collect_environment())
        if name in {"collect_assist_metadata", "collect_endpoint_metadata", "assist_metadata"}:
            return self.collect_assist_metadata()
        if name in {"probe_voice_endpoint", "launch_app", "launch", "health"}:
            return self.probe_voice_endpoint()
        if name in {"collect_logs", "system_logs"}:
            return PrimitiveResult("collect_logs", True, {"logs": list(self.collect_logs())})
        return PrimitiveResult(name, False, {"error": "CapabilityUnavailable", "action": action.name, "arguments": _redact(action.parameters)})

    def cleanup(self) -> None:
        self._record("cleanup", True, {"target": self._target_dict()})

    def collect_logs(self) -> tuple:
        logs = list(self._logs)
        target = self.config.target
        if target and target.log_command:
            result = self._run_target_command(target.log_command, "collect_voice_assistant_logs", timeout=15)
            logs.append({"source": "voice_assistant_log_command", "ok": result.ok, "data": result.data})
        return tuple(_redact(logs))

    def collect_artifacts(self) -> tuple:
        return ()

    def capture_screenshot(self, name: str | None = None) -> PrimitiveResult:
        return PrimitiveResult("capture_screenshot", False, {"error": "ScreenshotUnavailable", "target": self._target_dict()}, message="Voice Assistant endpoint verification has no visual screenshot surface.")

    def capture_serial(self) -> tuple:
        return ()

    def collect_artifact_metadata(self) -> tuple[ArtifactMetadata, ...]:
        return ()

    def collect_environment(self) -> dict[str, Any]:
        metadata = self.collect_assist_metadata()
        target = self.config.target
        return {
            "adapter": self.name,
            "host": platform.node(),
            "os": platform.platform(),
            "architecture": platform.machine(),
            "runtime_owner": "Home Assistant Assist / DJConnect conversation agent",
            "target": self._target_dict(),
            "target_metadata": metadata.data,
            "capabilities": {
                "target_configured": target is not None,
                "local_runtime": target is not None and target.runtime == "local",
                "live_runtime": target is not None and target.runtime == "live" and self.config.allow_live_runtime,
                "assist_pipeline": bool(target and target.assist_pipeline_id),
                "endpoint_mapping": bool(target and target.endpoint_id),
                "logs": True,
            },
        }

    def reset(self) -> None:
        self._logs.clear()
        self._connected = False

    def validate_target_identity(self, expected: dict[str, Any] | None = None) -> PrimitiveResult:
        target = self.config.target
        if target is None:
            return PrimitiveResult("validate_target_identity", False, {"error": "VoiceAssistantTargetUnavailable"})
        if target.runtime == "live" and not self.config.allow_live_runtime:
            return PrimitiveResult("validate_target_identity", False, {"error": "LiveVoiceAssistantExecutionNotConfigured", "target": target.to_dict()})
        if target.runtime not in {"local", "live"}:
            return PrimitiveResult("validate_target_identity", False, {"error": "UnsupportedRuntime", "target": target.to_dict()})
        expected = expected or {}
        mismatches = {}
        for key in ("target_id", "runtime", "ha_url", "endpoint_id", "assist_pipeline_id"):
            value = expected.get(key)
            if value and str(getattr(target, key)) != str(value):
                mismatches[key] = {"expected": value, "actual": getattr(target, key)}
        if mismatches:
            return PrimitiveResult("validate_target_identity", False, {"error": "TargetMismatch", "mismatches": _redact(mismatches), "target": target.to_dict()})
        self._record("validate_target_identity", True, {"target": target.to_dict()})
        return PrimitiveResult("validate_target_identity", True, {"target": target.to_dict()})

    def collect_assist_metadata(self) -> PrimitiveResult:
        target = self.config.target
        if target is None:
            return PrimitiveResult("collect_assist_metadata", False, {"error": "VoiceAssistantTargetUnavailable"})
        data: dict[str, Any] = {
            "target": target.to_dict(),
            "metadata": _redact(target.metadata or {}),
        }
        if target.metadata_command:
            command_result = self._run_target_command(target.metadata_command, "collect_assist_metadata")
            data["command"] = command_result.data
            ok = command_result.ok
            message = command_result.message
        else:
            ok = True
            message = ""
        self._record("collect_assist_metadata", ok, data)
        return PrimitiveResult("collect_assist_metadata", ok, data, message=message)

    def probe_voice_endpoint(self) -> PrimitiveResult:
        target = self.config.target
        if target is None:
            return PrimitiveResult("probe_voice_endpoint", False, {"error": "VoiceAssistantTargetUnavailable"})
        identity = self.validate_target_identity()
        if not identity.ok:
            return PrimitiveResult("probe_voice_endpoint", False, identity.data, message=identity.message)
        if target.health_command:
            return self._run_target_command(target.health_command, "probe_voice_endpoint")
        data = {"target": target.to_dict(), "probe": "configured_target_only", "mutates_runtime": False}
        self._record("probe_voice_endpoint", True, data)
        return PrimitiveResult("probe_voice_endpoint", True, data)

    def _run_target_command(self, command: str, action: str, *, timeout: int | None = None) -> PrimitiveResult:
        started = time.monotonic()
        argv = tuple(shlex.split(command))
        code, output = self.runner.run(argv, timeout=timeout or int(self.config.timeout_seconds))
        data = {"command": argv[:1] + ("<args-redacted>",) if _looks_sensitive(command) else argv, "exit_code": code, "output": output, "duration_seconds": time.monotonic() - started}
        data = _redact(data)
        self._record(action, code == 0, data)
        return PrimitiveResult(action, code == 0, data, message="" if code == 0 else output)

    def _record(self, action: str, ok: bool, data: dict[str, Any]) -> None:
        self._logs.append({"action": action, "ok": ok, "data": _redact(data), "timestamp": time.time()})

    def _target_dict(self) -> dict[str, Any] | None:
        return self.config.target.to_dict() if self.config.target else None


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: ("<redacted>" if _is_sensitive_key(str(key)) else _redact(item)) for key, item in value.items()}
    if isinstance(value, list):
        return [_redact(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_redact(item) for item in value)
    return value


def _is_sensitive_key(key: str) -> bool:
    lowered = key.lower()
    return any(token in lowered for token in SENSITIVE_KEY_TOKENS)


def _looks_sensitive(command: str) -> bool:
    lowered = command.lower()
    return any(token in lowered for token in SENSITIVE_KEY_TOKENS)


def _truthy(value: str | None) -> bool:
    return str(value or "").lower() in {"1", "true", "yes", "on"}
