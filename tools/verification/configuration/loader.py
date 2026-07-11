"""Configuration loading with environment and CLI override support."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any

from tools.verification.models import HarnessConfig

DEFAULT_SCENARIO_PATHS = (Path("verification/scenarios"),)
DEFAULT_EVIDENCE_DIR = Path("artifacts/verification/evidence")
DEFAULT_REPORT_DIR = Path("artifacts/verification/reports")


def load_config(
    root: Path,
    config_file: Path | None = None,
    *,
    environment_file: Path | None = None,
    secrets_file: Path | None = None,
    ci: bool = False,
    dry_run: bool = False,
    overrides: dict[str, str] | None = None,
) -> HarnessConfig:
    data: dict[str, Any] = {}
    if config_file is not None and config_file.exists():
        data = json.loads(config_file.read_text(encoding="utf-8"))

    merged = dict(data)
    merged.update(_env_config())
    merged.update(overrides or {})

    scenario_paths = tuple(
        _resolve(root, Path(path)) for path in merged.get("scenario_paths", DEFAULT_SCENARIO_PATHS)
    )
    return HarnessConfig(
        root=root,
        scenario_paths=scenario_paths,
        evidence_dir=_resolve(root, Path(merged.get("evidence_dir", DEFAULT_EVIDENCE_DIR))),
        report_dir=_resolve(root, Path(merged.get("report_dir", DEFAULT_REPORT_DIR))),
        environment_file=environment_file or _optional_path(root, merged.get("environment_file")),
        secrets_file=secrets_file or _optional_path(root, merged.get("secrets_file")),
        ci=ci or _truthy(merged.get("ci")),
        dry_run=dry_run,
        test_mode=str(merged.get("test_mode") or "stable"),
        parallel_execution=_parallel_enabled(merged.get("parallel_execution")),
        parallel_workers=_bounded_workers(
            merged.get("parallel_workers"),
            parallel_enabled=_parallel_enabled(merged.get("parallel_execution")),
        ),
        overrides=overrides or {},
    )


def _env_config() -> dict[str, Any]:
    data: dict[str, Any] = {}
    prefix = "DJCONNECT_VERIFICATION_"
    if value := os.getenv(prefix + "SCENARIO_PATHS"):
        data["scenario_paths"] = [item for item in value.split(os.pathsep) if item]
    if value := os.getenv(prefix + "EVIDENCE_DIR"):
        data["evidence_dir"] = value
    if value := os.getenv(prefix + "REPORT_DIR"):
        data["report_dir"] = value
    if value := os.getenv(prefix + "CI"):
        data["ci"] = value
    if value := os.getenv(prefix + "TEST_MODE"):
        data["test_mode"] = value
    if value := os.getenv(prefix + "PARALLEL"):
        data["parallel_execution"] = value
    if value := os.getenv(prefix + "PARALLEL_WORKERS"):
        data["parallel_workers"] = value
    return data


def _optional_path(root: Path, value: str | Path | None) -> Path | None:
    if not value:
        return None
    return _resolve(root, Path(value))


def _resolve(root: Path, path: Path) -> Path:
    return path if path.is_absolute() else root / path


def _truthy(value: Any) -> bool:
    return str(value).lower() in {"1", "true", "yes", "on"}


def _parallel_enabled(value: Any) -> bool:
    if value is None:
        return True
    return _truthy(value)


def _bounded_workers(value: Any, *, parallel_enabled: bool = False) -> int:
    try:
        workers = int(value)
    except (TypeError, ValueError):
        return _dynamic_worker_count() if parallel_enabled else 1
    return max(1, min(workers, 32))


def _dynamic_worker_count() -> int:
    logical = os.cpu_count() or 8
    performance_cores = _sysctl_int("hw.perflevel0.physicalcpu")
    efficiency_cores = _sysctl_int("hw.perflevel1.physicalcpu")
    if performance_cores or efficiency_cores:
        workers = (performance_cores * 2) + efficiency_cores
    else:
        workers = max(logical - 2, 2)
    return max(2, min(workers, max(logical, 2), 32))


def _sysctl_int(name: str) -> int:
    try:
        result = subprocess.run(
            ("sysctl", "-n", name),
            check=False,
            capture_output=True,
            text=True,
            timeout=2,
        )
    except (OSError, subprocess.SubprocessError):
        return 0
    if result.returncode != 0:
        return 0
    try:
        return max(0, int(result.stdout.strip()))
    except ValueError:
        return 0
