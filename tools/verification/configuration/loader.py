"""Configuration loading with environment and CLI override support."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from tools.verification.models import HarnessConfig

DEFAULT_SCENARIO_PATHS = (Path("verification/schema/examples"),)
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
    return data


def _optional_path(root: Path, value: str | Path | None) -> Path | None:
    if not value:
        return None
    return _resolve(root, Path(value))


def _resolve(root: Path, path: Path) -> Path:
    return path if path.is_absolute() else root / path


def _truthy(value: Any) -> bool:
    return str(value).lower() in {"1", "true", "yes", "on"}
