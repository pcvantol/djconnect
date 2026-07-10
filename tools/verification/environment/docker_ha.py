"""Docker Home Assistant development runtime discovery."""

from __future__ import annotations

import hashlib
import json
import os
import base64
import secrets
import socket
import shutil
import subprocess
import struct
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from tools.verification.models import GateResult, GateState
from tools.verification.lab import LabCatalog


SECRET_KEY_PARTS = ("token", "password", "secret", "proof", "authorization", "key")


@dataclass(frozen=True)
class DockerCommandResult:
    ok: bool
    stdout: str = ""
    stderr: str = ""
    returncode: int = 0


class DockerClient:
    def run(self, *args: str, env: dict[str, str] | None = None, timeout: int = 30) -> DockerCommandResult:
        try:
            result = subprocess.run(
                ("docker", *args),
                check=False,
                text=True,
                capture_output=True,
                timeout=timeout,
                env={**os.environ, **(env or {})},
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
    inspect_error: str = ""


@dataclass(frozen=True)
class HALabConfig:
    name: str
    port: int
    image: str
    compose_file: Path
    compose_files: tuple[Path, ...]
    profile: str
    lab_root: Path
    config_dir: Path
    log_path: Path
    repo_root: Path
    source_sha: str
    source_fingerprint: str

    @classmethod
    def from_root(cls, root: Path) -> "HALabConfig":
        lab_root = Path(os.getenv("DJCONNECT_VERIFICATION_LAB_ROOT", str(root / "artifacts/verification/lab/home_assistant")))
        source_sha = _git_sha(root) or "unknown"
        profile = os.getenv("DJCONNECT_VERIFICATION_LAB_PROFILE", "ha-profile")
        catalog = LabCatalog(root)
        fragments = catalog.profile_compose_fragments(profile)
        compose_files = tuple(root / fragment for fragment in fragments) or (root / "verification/lab/home_assistant/compose.yaml",)
        return cls(
            name=os.getenv("DJCONNECT_VERIFICATION_HA_CONTAINER", "djconnect-verification-ha"),
            port=int(os.getenv("DJCONNECT_VERIFICATION_HA_PORT", "18123")),
            image=os.getenv("DJCONNECT_VERIFICATION_HA_IMAGE", "ghcr.io/home-assistant/home-assistant:stable"),
            compose_file=compose_files[0],
            compose_files=compose_files,
            profile=profile,
            lab_root=lab_root,
            config_dir=lab_root / "config",
            log_path=lab_root / "config/home-assistant.log",
            repo_root=root,
            source_sha=source_sha,
            source_fingerprint=_source_fingerprint(root),
        )


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
            runtime = self._runtime_from_inspect(inspect) if inspect else self._runtime_from_summary(summary, "docker inspect unavailable or timed out")
            if expected_name and runtime.name != expected_name:
                continue
            if not expected_name and not _looks_like_home_assistant(runtime):
                continue
            if expected_port and not expected_name and not _owns_port(runtime, expected_port):
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
        result = self.docker.run("inspect", container_id, timeout=5)
        if not result.ok:
            return None
        data = json.loads(result.stdout)
        if not isinstance(data, list) or not data:
            return None
        return data[0]

    def _runtime_from_summary(self, data: dict[str, Any], inspect_error: str) -> HADockerRuntime:
        name = str(data.get("Names") or data.get("Name") or "").lstrip("/")
        state = str(data.get("State") or data.get("Status") or "unknown").lower()
        return HADockerRuntime(
            container_id=str(data.get("ID") or "")[:12],
            name=name,
            image=str(data.get("Image") or ""),
            image_id=str(data.get("ImageID") or ""),
            status=state,
            state=state,
            health="unknown",
            created=str(data.get("CreatedAt") or ""),
            started_at="",
            network_mode=str(data.get("Networks") or ""),
            labels=_summary_labels(data),
            inspect_error=inspect_error,
        )

    def _runtime_from_inspect(self, data: dict[str, Any]) -> HADockerRuntime:
        config = data.get("Config") or {}
        state = data.get("State") or {}
        host_config = data.get("HostConfig") or {}
        network = data.get("NetworkSettings") or {}
        labels = {str(k): str(v) for k, v in (config.get("Labels") or {}).items()}
        env = _redacted_env(config.get("Env") or [])
        mounts = tuple(data.get("Mounts") or ())
        source_mount = _source_mount(mounts, self.root)
        current_sha = _git_sha(self.root)
        label_sha = labels.get("djconnect.source_sha")
        source_matches = bool(source_mount) and current_sha is not None and label_sha == current_sha
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


class HALocalVerificationLab:
    """Safe lifecycle and qualification helpers for the dedicated HA lab."""

    def __init__(self, root: Path, docker: DockerClient | None = None, config: HALabConfig | None = None) -> None:
        self.root = root
        self.docker = docker or DockerClient()
        self.config = config or HALabConfig.from_root(root)
        self.discovery = HADockerDiscovery(root, self.docker)

    def lifecycle(self, action: str, *, allow_destructive: bool = False) -> GateResult:
        if action not in {"build", "start", "stop", "restart", "recreate", "fresh", "clean", "destroy", "bootstrap-auth"}:
            return GateResult("ha_lab_lifecycle", GateState.FAIL, f"Unsupported lab action: {action}")
        if action == "destroy" and not allow_destructive:
            return GateResult("ha_lab_lifecycle", GateState.FAIL, "Destructive lab destroy requires explicit opt-in")
        if action == "clean":
            return self._clean()
        self._ensure_layout()
        if action == "bootstrap-auth":
            runtime = self._selected_runtime()
            result = self._bootstrap_auth(runtime)
            return GateResult(
                "ha_lab_lifecycle",
                GateState.PASS if result["ok"] else GateState.FAIL,
                "Lab auth bootstrap completed" if result["ok"] else "Lab auth bootstrap failed",
                _redact_mapping(result),
            )
        if action in {"start", "recreate", "fresh"}:
            recovery = self._recover_stale_container()
            if not recovery["ok"]:
                return GateResult("ha_lab_lifecycle", GateState.FAIL, "Lab recovery failed before lifecycle action", recovery)
        env = self._compose_env()
        compose = self._compose_args()
        commands = {
            "build": (*compose, "pull"),
            "start": (*compose, "up", "-d"),
            "stop": (*compose, "stop"),
            "restart": (*compose, "restart"),
            "recreate": (*compose, "up", "-d", "--force-recreate"),
            "fresh": (*compose, "up", "-d", "--force-recreate"),
            "destroy": (*compose, "down", "-v", "--remove-orphans"),
        }
        if action == "fresh":
            self._clean_runtime_state()
            self._ensure_layout()
        result = self.docker.run(*commands[action], env=env, timeout=300)
        state = GateState.PASS if result.ok else GateState.FAIL
        diagnostics = self._container_diagnostics()
        return GateResult(
            "ha_lab_lifecycle",
            state,
            f"Lab {action} {'completed' if result.ok else 'failed'}",
            {"action": action, "stdout": result.stdout[-4000:], "stderr": result.stderr[-4000:], "returncode": result.returncode, "diagnostics": diagnostics},
        )

    def qualify(self) -> GateResult:
        docker_version = self.docker.run("version", "--format", "{{json .}}")
        compose_version = self.docker.run("compose", "version", "--format", "json")
        checks: dict[str, dict[str, Any]] = {}
        checks["docker"] = _check(docker_version.ok, "Docker daemon reachable", docker_version.stderr)
        checks["compose"] = _check(compose_version.ok, "Docker Compose reachable", compose_version.stderr)
        checks["definition"] = _check(self.config.compose_file.exists(), "Lab compose definition exists", str(self.config.compose_file))
        runtimes = self.discovery.discover(expected_port=self.config.port, expected_name=self.config.name)
        checks["container_selection"] = _check(len(runtimes) == 1, "Exactly one intended lab container selected", f"{len(runtimes)} candidates")
        runtime = runtimes[0] if len(runtimes) == 1 else None
        if runtime:
            checks["inspect"] = _check(not runtime.inspect_error, "Docker inspect completed", runtime.inspect_error or "ok")
            checks["container_state"] = _check(runtime.status not in {"created", "exited", "dead", "restarting"}, "Container not stuck before runtime qualification", runtime.status)
            checks["port"] = _check(_owns_port(runtime, self.config.port), "Expected host port belongs to lab container", runtime.ports)
            checks["labels"] = _check(_safe_label(runtime.labels), "Verification labels present", runtime.labels)
            checks["source"] = _check(runtime.source_matches_sha, "Repository source mount matches current tree", runtime.source_mount)
            checks["production_volume"] = _check(not _has_production_mount(runtime), "No production HA volume detected", runtime.mounts)
            checks["safe"] = _check(runtime.safe_for_verification, "Runtime safe for verification", _runtime_metadata(runtime))
            checks["running"] = _check(runtime.status == "running", "Container running", runtime.status)
        else:
            checks["inspect"] = _check(False, "Docker inspect unavailable", "container not selected")
            checks["container_state"] = _check(False, "Container state unavailable", "container not selected")
            checks["port"] = _check(False, "Expected host port unavailable", "container not selected")
            checks["labels"] = _check(False, "Verification labels unavailable", "container not selected")
            checks["source"] = _check(False, "Repository source mount unavailable", "container not selected")
            checks["production_volume"] = _check(False, "Production volume safety unavailable", "container not selected")
            checks["safe"] = _check(False, "Runtime safety unavailable", "container not selected")
            checks["running"] = _check(False, "Container not running", "container not selected")
        token_result = self._resolve_token(runtime)
        token = str(token_result.get("token") or "")
        checks["token"] = _check(bool(token), "HA token available", _redact_mapping(token_result))
        checks["rest"] = self._rest_check("/api/", token, runtime)
        checks["websocket"] = self._websocket_check(token, runtime)
        checks["storage"] = _check(self.config.config_dir.exists(), "Approved lab config/storage path reachable", str(self.config.config_dir))
        checks["logs"] = self._logs_check(runtime)
        passed = all(item["ok"] for item in checks.values())
        return GateResult(
            "ha_local_verification_lab",
            GateState.PASS if passed else GateState.FAIL,
            "LOCAL_VERIFICATION_LAB_QUALIFIED" if passed else "LOCAL_VERIFICATION_LAB_NOT_QUALIFIED",
            {
                "lab": self.metadata(),
                "checks": checks,
                "docker": _safe_json(docker_version.stdout),
                "compose": _safe_json(compose_version.stdout),
                "runtime": _runtime_metadata(runtime) if runtime else None,
                "token": _redact_mapping(token_result),
            },
        )

    def metadata(self) -> dict[str, Any]:
        return {
            "name": self.config.name,
            "port": self.config.port,
            "image": self.config.image,
            "compose_file": str(self.config.compose_file.relative_to(self.root)),
            "compose_files": [
                str(path.relative_to(self.root)) if _is_relative_to(path, self.root) else str(path)
                for path in self.config.compose_files
            ],
            "profile": self.config.profile,
            "lab_root": str(self.config.lab_root.relative_to(self.root)) if _is_relative_to(self.config.lab_root, self.root) else "<external-lab-root>",
            "config_dir": str(self.config.config_dir.relative_to(self.root)) if _is_relative_to(self.config.config_dir, self.root) else "<external-config-dir>",
            "log_path": str(self.config.log_path.relative_to(self.root)) if _is_relative_to(self.config.log_path, self.root) else "<external-log-path>",
            "source_sha": self.config.source_sha,
            "source_fingerprint": self.config.source_fingerprint,
        }

    def _compose_args(self) -> tuple[str, ...]:
        args: list[str] = ["compose"]
        for path in self.config.compose_files:
            args.extend(["-f", str(path)])
        return tuple(args)

    def _ensure_layout(self) -> None:
        self.config.config_dir.mkdir(parents=True, exist_ok=True)
        template = self.root / "verification/lab/home_assistant/configuration.yaml"
        target = self.config.config_dir / "configuration.yaml"
        if template.exists() and not target.exists():
            shutil.copy2(template, target)

    def _clean(self) -> GateResult:
        removed: list[str] = []
        for path in (self.config.log_path, self.config.lab_root / "tmp"):
            if path.exists():
                if path.is_dir():
                    shutil.rmtree(path)
                else:
                    path.unlink()
                removed.append(str(path))
        return GateResult("ha_lab_lifecycle", GateState.PASS, "Lab clean completed", {"removed": removed})

    def _clean_runtime_state(self) -> None:
        if self.config.config_dir.exists():
            shutil.rmtree(self.config.config_dir)

    def _selected_runtime(self) -> HADockerRuntime | None:
        runtimes = self.discovery.discover(expected_port=self.config.port, expected_name=self.config.name)
        return runtimes[0] if len(runtimes) == 1 else None

    def _resolve_token(self, runtime: HADockerRuntime | None) -> dict[str, Any]:
        external = os.getenv("DJCONNECT_VERIFICATION_HA_TOKEN", "")
        if external:
            return {"ok": True, "source": "environment", "token": external}
        if not runtime or runtime.status != "running":
            return {"ok": False, "source": "none", "reason": "lab_runtime_not_running"}
        credentials = self._load_lab_credentials()
        if credentials:
            token = self._request_auth_token(credentials["username"], credentials["password"])
            if token.get("ok"):
                return {**token, "source": "lab_credentials"}
            return {**token, "source": "lab_credentials"}
        return self._bootstrap_auth(runtime)

    def _bootstrap_auth(self, runtime: HADockerRuntime | None) -> dict[str, Any]:
        if not runtime or runtime.status != "running":
            return {"ok": False, "source": "bootstrap", "reason": "lab_runtime_not_running"}
        onboarding = self._onboarding_status()
        if not onboarding.get("ok"):
            return onboarding
        user_step = _onboarding_step(onboarding.get("data"), "user")
        if user_step is None:
            return {"ok": False, "source": "bootstrap", "reason": "onboarding_user_step_unavailable", "onboarding": onboarding.get("data")}
        credentials = self._load_lab_credentials()
        if not user_step.get("done") and not credentials:
            credentials = self._create_lab_credentials()
            created = self._create_onboarding_user(credentials)
            if not created.get("ok"):
                return created
            self._save_lab_credentials(credentials)
        if not credentials:
            return {"ok": False, "source": "bootstrap", "reason": "home_assistant_already_onboarded_without_lab_credentials"}
        token = self._request_auth_token(credentials["username"], credentials["password"])
        return {**token, "source": "bootstrap"}

    def _auth_file(self) -> Path:
        return self.config.lab_root / ".secrets" / "ha_lab_auth.json"

    def _load_lab_credentials(self) -> dict[str, str] | None:
        path = self._auth_file()
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        username = str(data.get("username") or "")
        password = str(data.get("password") or "")
        return {"username": username, "password": password} if username and password else None

    def _save_lab_credentials(self, credentials: dict[str, str]) -> None:
        path = self._auth_file()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(credentials, indent=2, sort_keys=True), encoding="utf-8")
        try:
            path.chmod(0o600)
        except OSError:
            pass

    def _create_lab_credentials(self) -> dict[str, str]:
        return {
            "name": "DJConnect Verification",
            "username": "djconnect_verification",
            "password": secrets.token_urlsafe(32),
        }

    def _onboarding_status(self) -> dict[str, Any]:
        try:
            with urlopen(f"http://127.0.0.1:{self.config.port}/api/onboarding", timeout=5) as response:
                return {"ok": True, "data": json.loads(response.read().decode("utf-8"))}
        except (OSError, URLError, HTTPError, json.JSONDecodeError) as exc:
            return {"ok": False, "source": "bootstrap", "reason": "onboarding_status_failed", "error": str(exc)}

    def _create_onboarding_user(self, credentials: dict[str, str]) -> dict[str, Any]:
        payload = {
            "client_id": f"http://127.0.0.1:{self.config.port}/",
            "name": credentials["name"],
            "username": credentials["username"],
            "password": credentials["password"],
            "language": "en",
        }
        request = Request(
            f"http://127.0.0.1:{self.config.port}/api/onboarding/users",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=10) as response:
                data = response.read().decode("utf-8")
                return {"ok": 200 <= int(response.status) < 300, "source": "bootstrap", "status": int(response.status), "data": _safe_json(data)}
        except (OSError, URLError, HTTPError) as exc:
            return {"ok": False, "source": "bootstrap", "reason": "onboarding_user_create_failed", "error": str(exc)}

    def _request_auth_token(self, username: str, password: str) -> dict[str, Any]:
        body = urlencode(
            {
                "grant_type": "password",
                "client_id": f"http://127.0.0.1:{self.config.port}/",
                "username": username,
                "password": password,
            }
        ).encode("utf-8")
        request = Request(
            f"http://127.0.0.1:{self.config.port}/auth/token",
            data=body,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=10) as response:
                data = json.loads(response.read().decode("utf-8"))
                token = str(data.get("access_token") or "")
                return {
                    "ok": bool(token),
                    "token": token,
                    "token_type": data.get("token_type"),
                    "expires_in": data.get("expires_in"),
                }
        except (OSError, URLError, HTTPError, json.JSONDecodeError) as exc:
            return {"ok": False, "reason": "auth_token_request_failed", "error": str(exc)}

    def _recover_stale_container(self) -> dict[str, Any]:
        summary = self._container_summary()
        if not summary:
            return {"ok": True, "action": "none", "reason": "container_absent"}
        state = str(summary.get("State") or summary.get("Status") or "").lower()
        name = str(summary.get("Names") or summary.get("Name") or "").lstrip("/")
        if name != self.config.name:
            return {"ok": False, "action": "blocked", "reason": "unexpected_container_name", "name": name}
        if state not in {"created", "exited", "dead"}:
            return {"ok": True, "action": "none", "state": state}
        result = self.docker.run("rm", "-f", self.config.name, timeout=30)
        return {
            "ok": result.ok,
            "action": "rm_stale_dedicated_container",
            "state": state,
            "stdout": result.stdout[-1000:],
            "stderr": result.stderr[-1000:],
            "returncode": result.returncode,
        }

    def _container_summary(self) -> dict[str, Any] | None:
        result = self.docker.run("ps", "-a", "--filter", f"name={self.config.name}", "--format", "{{json .}}", timeout=10)
        if not result.ok:
            return None
        for line in result.stdout.splitlines():
            if not line.strip():
                continue
            try:
                summary = json.loads(line)
            except json.JSONDecodeError:
                continue
            if str(summary.get("Names") or summary.get("Name") or "").lstrip("/") == self.config.name:
                return summary
        return None

    def _container_diagnostics(self) -> dict[str, Any]:
        summary = self._container_summary()
        logs = self.docker.run("logs", "--tail", "80", "--timestamps", self.config.name, timeout=5)
        return {
            "summary": summary or {},
            "logs_available": logs.ok,
            "logs_tail": logs.stdout[-4000:] if logs.ok else "",
            "logs_error": logs.stderr[-1000:] if not logs.ok else "",
        }

    def _compose_env(self) -> dict[str, str]:
        return {
            "DJCONNECT_VERIFICATION_HA_CONTAINER": self.config.name,
            "DJCONNECT_VERIFICATION_HA_PORT": str(self.config.port),
            "DJCONNECT_VERIFICATION_HA_IMAGE": self.config.image,
            "DJCONNECT_VERIFICATION_LAB_ROOT": str(self.config.lab_root),
            "DJCONNECT_VERIFICATION_REPO_ROOT": str(self.config.repo_root),
            "DJCONNECT_VERIFICATION_SOURCE_SHA": self.config.source_sha,
            "DJCONNECT_VERIFICATION_SOURCE_FINGERPRINT": self.config.source_fingerprint,
            "DJCONNECT_VERIFICATION_LAB_PROFILE": self.config.profile,
        }

    def _rest_check(self, path: str, token: str, runtime: HADockerRuntime | None) -> dict[str, Any]:
        if not runtime or runtime.status != "running":
            return _check(False, "REST probe blocked until lab container is running", runtime.status if runtime else "container not selected")
        if not token:
            return _check(False, "REST probe blocked until HA token is provided", "missing token")
        url = f"http://127.0.0.1:{self.config.port}{path}"
        request = Request(url, headers={"Authorization": f"Bearer {token}"})
        try:
            with urlopen(request, timeout=5) as response:
                return _check(200 <= int(response.status) < 400, "REST probe completed", {"status": int(response.status)})
        except HTTPError as exc:
            return _check(False, "REST probe failed", {"status": exc.code})
        except (OSError, URLError) as exc:
            return _check(False, "REST probe failed", str(exc))

    def _websocket_check(self, token: str, runtime: HADockerRuntime | None) -> dict[str, Any]:
        if not runtime or runtime.status != "running":
            return _check(False, "WebSocket probe blocked until lab container is running", runtime.status if runtime else "container not selected")
        if not token:
            return _check(False, "WebSocket probe blocked until HA token is provided", "missing token")
        try:
            return _ha_websocket_probe("127.0.0.1", self.config.port, token)
        except OSError as exc:
            return _check(False, "WebSocket probe failed", str(exc))

    def _logs_check(self, runtime: HADockerRuntime | None) -> dict[str, Any]:
        if not self.config.log_path.parent.exists():
            return _check(False, "Dedicated lab log path unavailable", str(self.config.log_path))
        if not runtime:
            return _check(False, "Live HA logs unavailable until lab container is selected", "container not selected")
        result = self.docker.run("logs", "--tail", "80", "--timestamps", self.config.name, timeout=5)
        if not result.ok:
            return _check(False, "Live HA logs unavailable", result.stderr)
        return _check(True, "Live HA logs reachable", {"bytes": len(result.stdout), "tail": result.stdout[-2000:]})

def _looks_like_home_assistant(runtime: HADockerRuntime) -> bool:
    text = f"{runtime.name} {runtime.image}".lower()
    return "homeassistant" in text or "home-assistant" in text or "home-assistant" in runtime.image.lower()


def _owns_port(runtime: HADockerRuntime, port: int) -> bool:
    return any(str(item.get("HostPort")) == str(port) or str(item.get("PrivatePort")) == str(port) for item in runtime.ports)


def _summary_labels(data: dict[str, Any]) -> dict[str, str]:
    labels = data.get("Labels")
    if isinstance(labels, dict):
        return {str(k): str(v) for k, v in labels.items()}
    result: dict[str, str] = {}
    for item in str(labels or "").split(","):
        key, sep, value = item.partition("=")
        if sep and key:
            result[key] = value
    return result


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
        if source and (root_text.startswith(source) or source.startswith(root_text)):
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


def _redact_mapping(value: Any) -> Any:
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for key, item in value.items():
            if any(part in str(key).lower() for part in SECRET_KEY_PARTS):
                result[str(key)] = "<redacted>"
            else:
                result[str(key)] = _redact_mapping(item)
        return result
    if isinstance(value, list):
        return [_redact_mapping(item) for item in value]
    return value


def _onboarding_step(data: Any, step: str) -> dict[str, Any] | None:
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict) and item.get("step") == step:
                return item
    if isinstance(data, dict):
        for item in data.get("data") or data.get("steps") or []:
            if isinstance(item, dict) and item.get("step") == step:
                return item
    return None


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
        "inspect_error": runtime.inspect_error,
    }


def _ha_websocket_probe(host: str, port: int, token: str) -> dict[str, Any]:
    key = base64.b64encode(os.urandom(16)).decode("ascii")
    with socket.create_connection((host, port), timeout=5) as sock:
        sock.settimeout(5)
        request = (
            "GET /api/websocket HTTP/1.1\r\n"
            f"Host: {host}:{port}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            "Sec-WebSocket-Version: 13\r\n"
            "\r\n"
        )
        sock.sendall(request.encode("ascii"))
        response = _recv_until(sock, b"\r\n\r\n")
        if b" 101 " not in response.split(b"\r\n", 1)[0]:
            return _check(False, "WebSocket handshake failed", response.decode("utf-8", errors="replace")[:500])
        auth_required = _read_ws_json(sock)
        _send_ws_json(sock, {"type": "auth", "access_token": token})
        auth = _read_ws_json(sock)
        if auth.get("type") != "auth_ok":
            return _check(False, "WebSocket authentication failed", {"auth_required": auth_required, "auth": auth})
        _send_ws_json(sock, {"id": 1, "type": "get_config"})
        config = _read_ws_json(sock)
        ok = config.get("id") == 1 and config.get("type") == "result" and bool(config.get("success"))
        return _check(ok, "WebSocket probe completed", {"auth_required": auth_required, "auth": auth, "result": config})


def _recv_until(sock: socket.socket, marker: bytes) -> bytes:
    data = b""
    while marker not in data:
        chunk = sock.recv(4096)
        if not chunk:
            break
        data += chunk
    return data


def _read_ws_json(sock: socket.socket) -> dict[str, Any]:
    header = sock.recv(2)
    if len(header) != 2:
        raise OSError("incomplete websocket frame")
    first, second = header
    length = second & 0x7F
    if length == 126:
        length = struct.unpack("!H", _recv_exact(sock, 2))[0]
    elif length == 127:
        length = struct.unpack("!Q", _recv_exact(sock, 8))[0]
    masked = bool(second & 0x80)
    mask = _recv_exact(sock, 4) if masked else b""
    payload = bytearray(_recv_exact(sock, length))
    if masked:
        for index, value in enumerate(payload):
            payload[index] = value ^ mask[index % 4]
    if first & 0x0F == 8:
        raise OSError("websocket closed")
    return json.loads(payload.decode("utf-8"))


def _send_ws_json(sock: socket.socket, payload: dict[str, Any]) -> None:
    data = json.dumps(payload).encode("utf-8")
    mask = os.urandom(4)
    if len(data) < 126:
        header = bytes([0x81, 0x80 | len(data)])
    elif len(data) < 65536:
        header = bytes([0x81, 0x80 | 126]) + struct.pack("!H", len(data))
    else:
        header = bytes([0x81, 0x80 | 127]) + struct.pack("!Q", len(data))
    masked = bytes(value ^ mask[index % 4] for index, value in enumerate(data))
    sock.sendall(header + mask + masked)


def _recv_exact(sock: socket.socket, size: int) -> bytes:
    data = b""
    while len(data) < size:
        chunk = sock.recv(size - len(data))
        if not chunk:
            raise OSError("unexpected websocket EOF")
        data += chunk
    return data


def _safe_json(text: str) -> dict[str, Any]:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {}


def _source_fingerprint(root: Path) -> str:
    parts: list[str] = []
    for path in sorted((root / "custom_components/djconnect").rglob("*.py")):
        try:
            parts.append(f"{path.relative_to(root)}:{hashlib.sha256(path.read_bytes()).hexdigest()}")
        except OSError:
            continue
    return hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()


def _has_production_mount(runtime: HADockerRuntime) -> bool:
    for mount in runtime.mounts:
        source = str(mount.get("Source") or "").lower()
        if "/docker/homeassistant" in source or source.endswith("/homeassistant/config"):
            return True
    return False


def _check(ok: bool, message: str, detail: Any = None) -> dict[str, Any]:
    return {"ok": ok, "message": message, "detail": _redact_detail(detail)}


def _redact_detail(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: ("<redacted>" if any(part in str(key).lower() for part in SECRET_KEY_PARTS) else _redact_detail(item)) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_redact_detail(item) for item in value]
    if isinstance(value, str):
        redacted = value
        for part in SECRET_KEY_PARTS:
            redacted = redacted.replace(part, "[redacted-key]")
        return redacted
    return value


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False
