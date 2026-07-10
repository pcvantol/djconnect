"""Configuration loading for the DJConnect Verification Harness."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import HarnessConfig


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
    overrides: dict[str, str] | None = None,
) -> HarnessConfig:
    """Load local/CI configuration without reading committed secrets."""

    data: dict[str, Any] = {}
    if config_file is not None:
        data = json.loads(config_file.read_text(encoding="utf-8"))

    scenario_paths = tuple(
        root / Path(path) for path in data.get("scenario_paths", DEFAULT_SCENARIO_PATHS)
    )
    evidence_dir = root / Path(data.get("evidence_dir", DEFAULT_EVIDENCE_DIR))
    report_dir = root / Path(data.get("report_dir", DEFAULT_REPORT_DIR))

    return HarnessConfig(
        root=root,
        scenario_paths=scenario_paths,
        evidence_dir=evidence_dir,
        report_dir=report_dir,
        environment_file=environment_file or _optional_path(root, data.get("environment_file")),
        secrets_file=secrets_file or _optional_path(root, data.get("secrets_file")),
        ci=ci or bool(data.get("ci", False)),
        overrides=overrides or {},
    )


def _optional_path(root: Path, value: str | None) -> Path | None:
    if not value:
        return None
    return root / value
