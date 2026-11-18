"""Verification artifact directories and cleanup."""

from __future__ import annotations

import shutil
from pathlib import Path


class ArtifactManager:
    def __init__(self, root: Path) -> None:
        self.root = root

    def ensure_run_dir(self, run_id: str) -> Path:
        path = self.root / run_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def clean(self, *, dry_run: bool = False) -> list[Path]:
        if not self.root.exists():
            return []
        paths = sorted(self.root.iterdir())
        if not dry_run:
            for path in paths:
                if path.is_dir():
                    shutil.rmtree(path)
                else:
                    path.unlink()
        return paths
