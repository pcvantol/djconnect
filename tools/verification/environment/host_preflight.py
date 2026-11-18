"""Host preflight checks before starting local verification lab runners."""

from __future__ import annotations

import shutil
import socket
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from tools.verification.models import GateResult, GateState

DEFAULT_MIN_FREE_BYTES = 15 * 1024 * 1024 * 1024


@dataclass(frozen=True)
class HostPreflightConfig:
    ports: tuple[int, ...]
    lab_root: Path
    min_free_bytes: int = DEFAULT_MIN_FREE_BYTES


class HostPreflight:
    def __init__(self, root: Path, config: HostPreflightConfig) -> None:
        self.root = root
        self.config = config

    def check(self) -> GateResult:
        disk = _disk_check(self.config.lab_root, self.config.min_free_bytes)
        ports = [_port_check(port) for port in self.config.ports]
        processes = _process_check()
        blocking_ports = [item for item in ports if item["blocked"]]
        blocking_processes = [item for item in processes if item["blocking"]]
        passed = disk["ok"] and not blocking_ports and not blocking_processes
        return GateResult(
            "host_preflight",
            GateState.PASS if passed else GateState.FAIL,
            "Host preflight passed" if passed else "Host preflight blocked lab runner startup",
            {
                "disk": disk,
                "ports": ports,
                "processes": processes,
                "minimum_free_bytes": self.config.min_free_bytes,
            },
        )


def _disk_check(path: Path, minimum_free_bytes: int) -> dict[str, Any]:
    target = path if path.exists() else _existing_parent(path)
    usage = shutil.disk_usage(target)
    return {
        "path": str(path),
        "checked_path": str(target),
        "free_bytes": usage.free,
        "total_bytes": usage.total,
        "required_free_bytes": minimum_free_bytes,
        "ok": usage.free >= minimum_free_bytes,
    }


def _existing_parent(path: Path) -> Path:
    current = path
    while not current.exists() and current.parent != current:
        current = current.parent
    return current if current.exists() else Path("/")


def _port_check(port: int) -> dict[str, Any]:
    listener = _lsof(port)
    bind_available = _port_bind_available(port)
    return {
        "port": port,
        "bind_available": bind_available,
        "listeners": listener,
        "blocked": bool(listener) or not bind_available,
    }


def _port_bind_available(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(("127.0.0.1", port))
        except OSError:
            return False
    return True


def _lsof(port: int) -> list[dict[str, str]]:
    result = _run(("lsof", "-nP", f"-iTCP:{port}", "-sTCP:LISTEN"))
    if result.returncode != 0:
        return []
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    if len(lines) <= 1:
        return []
    listeners: list[dict[str, str]] = []
    for line in lines[1:]:
        parts = line.split()
        if len(parts) >= 9:
            listeners.append({"command": parts[0], "pid": parts[1], "user": parts[2], "name": parts[-1]})
    return listeners


def _process_check() -> list[dict[str, Any]]:
    result = _run(("pgrep", "-af", "home-assistant|hass|djconnect"))
    if result.returncode != 0:
        return []
    current_pid = str(_current_pid())
    processes: list[dict[str, Any]] = []
    for line in result.stdout.splitlines():
        parts = line.strip().split(maxsplit=1)
        if not parts or parts[0] == current_pid:
            continue
        command = parts[1] if len(parts) > 1 else ""
        lowered = command.lower()
        benign = "tools.verification" in lowered or "codex" in lowered
        processes.append(
            {
                "pid": parts[0],
                "command": command[:500],
                "blocking": not benign and any(token in lowered for token in ("home-assistant", "hass", "djconnect")),
            }
        )
    return processes[:20]


def _current_pid() -> int:
    import os

    return os.getpid()


def _run(command: tuple[str, ...]) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(command, check=False, capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.SubprocessError):
        return subprocess.CompletedProcess(command, 1, "", "")
