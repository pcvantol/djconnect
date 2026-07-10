"""Docker Home Assistant development runtime discovery."""

from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from tools.verification.models import GateResult, GateState


SECRET_KEY_PARTS = ("token", "password", "secret", "proof", "authorization", "key")


@dataclass(frozen=True)
class DockerCommandResult:
    ok: bool
    stdout: str = ""
    stderr: str = ""
    returncode: int = 0


class DockerClient:
    def run(self, *args: str) -> DockerCommandResult:
        try:
            result = subprocess.run(
                ("docker", *args),
                check=False,
                text=True,
                capture_output=True,
                timeout=30,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            return DockerCommandResult(False, stderr=str(exc), returncode=1)
        return DockerCommandResult(
            result.returncode == 0,
            stdout=result.stdout.strip(),
            stderr=result.stderr.strip(),
            returncode=result.returncode,
        )


@dataclass(frozen=True)
class HADockerRuntime:
    container_id: str
    name: str
    image: str
    image_id: str
    status: str
    state: str
    health: str
    created: str
    started_at: str
    network_mode: str
    ports: tuple[dict[str, Any], ...] = ()
    mounts: tuple[dict[str, Any], ...] = ()
    labels: dict[str, str] = field(default_factory=dict)
    environment_fingerprint: str = ""
    config_path: str = "/config"
    storage_path: str = "/config/.storage"
    source_mount: str = ""
    source_matches_sha: bool = False
    safe_for_verification: bool = False


class HADockerDiscovery:
    def __init__(self, root: Path, docker: DockerClient | None = None) -> None:
        self.root = root
        self.docker = docker or DockerClient()

    def discover(self, *, expected_port: int = 8123, expected_name: str | None = None) -> tuple[HADockerRuntime, ...]:
        result = self.docker.run("ps", "-a", "--format", "{{json .}}")
        if not result.ok:
            return ()
        runtimes: list[HADockerRuntime] = []
        for line in result.stdout.splitlines():
            if not line.strip():
                continue
            summary = json.loads(line)
            container_id = str(summary.get("ID") or "")
            inspect = self._inspect(container_id)
            if not inspect:
                continue
            runtime = self._runtime_from_inspect(inspect)
            if expected_name and runtime.name != expected_name:
                continue
            if not expected_name and not _looks_like_home_assistant(runtime):
                continue
            if expected_port and not _owns_port(runtime, expected_port):
                continue
            runtimes.append(runtime)
        return tuple(runtimes)

    def qualify(self, *, expected_port: int = 8123, expected_name: str | None = None) -> GateResult:
        docker_version = self.docker.run("version", "--format", "{{json .}}")
        if not docker_version.ok:
            return GateResult(
                "ha_docker_discovery",
                GateState.FAIL,
                "Docker daemon unavailable",
                {"error": docker_version.stderr},
            )
        runtimes = self.discover(expected_port=expected_port, expected_name=expected_name)
        if not runtimes:
            return GateResult(
                "ha_docker_discovery",
                GateState.FAIL,
                "No intended Docker Home Assistant development container found",
                {"expected_port": expected_port, "expected_name": expected_name},
            )
        if len(runtimes) > 1:
            return GateResult(
                "ha_docker_discovery",
                GateState.FAIL,
                "Multiple candidate Home Assistant containers found",
                {"containers": [runtime.name for runtime in runtimes]},
            )
        runtime = runtimes[0]
        state = GateState.PASS if runtime.safe_for_verification else GateState.FAIL
        return GateResult(
            "ha_docker_discovery",
            state,
            "Docker Home Assistant runtime qualified" if state == GateState.PASS else "Docker Home Assistant runtime is not proven safe",
            {"runtime": _runtime_metadata(runtime), "docker": _safe_json(docker_version.stdout)},
        )

    def _inspect(self, container_id: str) -> dict[str, Any] | None:
        result = self.docker.run("inspect", container_id)
        if not result.ok:
            return None
        data = json.loads(result.stdout)
        if not isinstance(data, list) or not data:
            return None
        return data[0]

    def _runtime_from_inspect(self, data: dict[str, Any]) -> HADockerRuntime:
        config = data.get("Config") or {}
        state = data.get("State") or {}
        host_config = data.get("HostConfig") or {}
        network = data.get("NetworkSettings") or {}
        labels = {str(k): str(v) for k, v in (config.get("Labels") or {}).items()}
        env = _redacted_env(config.get("Env") or [])
        mounts = tuple(data.get("Mounts") or ())
        source_mount = _source_mount(mounts, self.root)
        source_matches = bool(source_mount) and _git_sha(self.root) is not None
        safe = _safe_label(labels) or _safe_name(str(data.get("Name") or ""))
        return HADockerRuntime(
            container_id=str(data.get("Id") or "")[:12],
            name=str(data.get("Name") or "").lstrip("/"),
            image=str(config.get("Image") or ""),
            image_id=str(data.get("Image") or ""),
            status=str(state.get("Status") or ""),
            state=str(state.get("Status") or ""),
            health=str((state.get("Health") or {}).get("Status") or "unknown"),
            created=str(data.get("Created") or ""),
            started_at=str(state.get("StartedAt") or ""),
            network_mode=str(host_config.get("NetworkMode") or ""),
            ports=tuple(_ports(network.get("Ports") or {})),
            mounts=mounts,
            labels=labels,
            environment_fingerprint=_fingerprint(env),
            source_mount=source_mount,
            source_matches_sha=source_matches,
            safe_for_verification=safe and source_matches,
        )


def _looks_like_home_assistant(runtime: HADockerRuntime) -> bool:
    text = f"{runtime.name} {runtime.image}".lower()
    return "homeassistant" in text or "home-assistant" in text or "home-assistant" in runtime.image.lower()


def _owns_port(runtime: HADockerRuntime, port: int) -> bool:
    return any(str(item.get("HostPort")) == str(port) or str(item.get("PrivatePort")) == str(port) for item in runtime.ports)


def _safe_label(labels: dict[str, str]) -> bool:
    values = {key.lower(): value.lower() for key, value in labels.items()}
    return values.get("djconnect.verification") in {"1", "true", "yes"} or values.get("com.docker.compose.project", "").startswith("djconnect")


def _safe_name(name: str) -> bool:
    return any(token in name.lower() for token in ("djconnect", "verification", "dev"))


def _ports(ports: dict[str, Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for container_port, mappings in ports.items():
        private = container_port.split("/", 1)[0]
        for mapping in mappings or []:
            result.append({"PrivatePort": private, **mapping})
    return result


def _source_mount(mounts: tuple[dict[str, Any], ...], root: Path) -> str:
    root_text = str(root.resolve())
    for mount in mounts:
        source = str(mount.get("Source") or "")
        destination = str(mount.get("Destination") or "")
        if source and (root_text.startswith(source) or source == root_text):
            return destination
    return ""


def _redacted_env(items: list[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for item in items:
        key, _, value = item.partition("=")
        if any(part in key.lower() for part in SECRET_KEY_PARTS):
            result[key] = "<redacted>"
        else:
            result[key] = value
    return result


def _fingerprint(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode("utf-8")).hexdigest()


def _git_sha(root: Path) -> str | None:
    try:
        return subprocess.check_output(("git", "rev-parse", "HEAD"), cwd=root, text=True, stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def _runtime_metadata(runtime: HADockerRuntime) -> dict[str, Any]:
    return {
        "container_id": runtime.container_id,
        "name": runtime.name,
        "image": runtime.image,
        "image_id": runtime.image_id,
        "status": runtime.status,
        "health": runtime.health,
        "created": runtime.created,
        "started_at": runtime.started_at,
        "network_mode": runtime.network_mode,
        "ports": list(runtime.ports),
        "mounts": [
            {"Source": item.get("Source"), "Destination": item.get("Destination"), "Type": item.get("Type")}
            for item in runtime.mounts
        ],
        "labels": runtime.labels,
        "environment_fingerprint": runtime.environment_fingerprint,
        "config_path": runtime.config_path,
        "storage_path": runtime.storage_path,
        "source_mount": runtime.source_mount,
        "source_matches_sha": runtime.source_matches_sha,
        "safe_for_verification": runtime.safe_for_verification,
    }


def _safe_json(text: str) -> dict[str, Any]:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {}
