"""Typed execution selection resolved before lifecycle admission."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ExecutionContext:
    execution_mode: str
    host_repository: Path
    target_repository: Path | None
    lifecycle_policy: str
    selected_preflight: str
    run_id: str | None = None
