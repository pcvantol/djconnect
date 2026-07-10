"""Durable immutable verification run artifact persistence."""

from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

from tools.verification.evidence.index import redact


RUN_SCHEMA_VERSION = 1


class RunStoreError(RuntimeError):
    """Raised when a run artifact operation is unsafe or invalid."""


class RunStore:
    def __init__(self, root: Path) -> None:
        self.root = root

    def create(self, run_id: str) -> Path:
        path = self.root / run_id
        try:
            path.mkdir(parents=True, exist_ok=False)
        except FileExistsError as exc:
            raise RunStoreError(f"run directory already exists: {run_id}") from exc
        self.write_json(run_id, "summary.json", {"run_id": run_id, "state": "PARTIAL", "schema_version": RUN_SCHEMA_VERSION})
        return path

    def ensure(self, run_id: str) -> Path:
        path = self.root / run_id
        if not path.exists():
            return self.create(run_id)
        return path

    def write_json(self, run_id: str, relative_path: str, data: Any) -> Path:
        path = self.ensure(run_id) / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = redact(json.dumps(_jsonable(data), sort_keys=True))
        tmp = path.with_name(f".{path.name}.{os.getpid()}.{int(time.time() * 1000)}.tmp")
        tmp.write_text(json.dumps(json.loads(payload), indent=2, sort_keys=True), encoding="utf-8")
        tmp.replace(path)
        return path

    def append_jsonl(self, run_id: str, relative_path: str, data: Any) -> Path:
        path = self.ensure(run_id) / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(redact(json.dumps(_jsonable(data), sort_keys=True)) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        return path

    def finalize(self, run_id: str, *, state: str, summary: dict[str, Any] | None = None) -> Path:
        self.write_json(run_id, "summary.json", {"run_id": run_id, "state": state, "schema_version": RUN_SCHEMA_VERSION, **(summary or {})})
        return self.write_index(run_id)

    def write_index(self, run_id: str) -> Path:
        run_dir = self.ensure(run_id)
        items: list[dict[str, Any]] = []
        for path in sorted(run_dir.rglob("*")):
            if path.is_file() and path.name != "evidence-index.json":
                items.append(
                    {
                        "path": str(path.relative_to(run_dir)),
                        "sha256": _checksum(path),
                        "bytes": path.stat().st_size,
                    }
                )
        return self.write_json(run_id, "evidence-index.json", {"run_id": run_id, "items": items})

    def list_runs(self) -> list[str]:
        if not self.root.exists():
            return []
        return sorted(path.name for path in self.root.iterdir() if path.is_dir())

    def show(self, run_id: str) -> dict[str, Any]:
        path = self.root / run_id / "summary.json"
        if not path.exists():
            raise RunStoreError(f"summary missing for run: {run_id}")
        return json.loads(path.read_text(encoding="utf-8"))

    def verify(self, run_id: str) -> dict[str, Any]:
        run_dir = self.root / run_id
        index_path = run_dir / "evidence-index.json"
        if not index_path.exists():
            return {"run_id": run_id, "ok": False, "error": "missing_index"}
        index = json.loads(index_path.read_text(encoding="utf-8"))
        failures: list[str] = []
        for item in index.get("items", []):
            path = run_dir / item.get("path", "")
            if not path.exists() or _checksum(path) != item.get("sha256"):
                failures.append(str(item.get("path")))
        return {"run_id": run_id, "ok": not failures, "failures": failures}


def _checksum(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value
