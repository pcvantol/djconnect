"""Evidence collection and indexing."""

from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import asdict
from pathlib import Path

from tools.verification.artifacts import ArtifactManager
from tools.verification.models import EvidenceIndex, EvidenceItem, EvidenceKind


class EvidenceCollector:
    def __init__(self, evidence_dir: Path) -> None:
        self.artifacts = ArtifactManager(evidence_dir)

    def store_text(
        self,
        run_id: str,
        kind: EvidenceKind,
        name: str,
        content: str,
        metadata: dict | None = None,
    ) -> EvidenceItem:
        path = self.artifacts.ensure_run_dir(run_id) / name
        path.write_text(redact(content), encoding="utf-8")
        item = EvidenceItem(kind.value, path, {"sha256": checksum(path), **(metadata or {})})
        return item

    def store_file(
        self,
        run_id: str,
        kind: EvidenceKind,
        source: Path,
        metadata: dict | None = None,
    ) -> EvidenceItem:
        target = self.artifacts.ensure_run_dir(run_id) / source.name
        shutil.copy2(source, target)
        return EvidenceItem(kind.value, target, {"sha256": checksum(target), **(metadata or {})})

    def write_index(self, index: EvidenceIndex) -> Path:
        run_dir = self.artifacts.ensure_run_dir(index.run_id)
        path = run_dir / "evidence-index.json"
        data = {
            "run_id": index.run_id,
            "items": [_jsonable_item(item) for item in index.items],
        }
        path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
        return path


def checksum(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def redact(value: str) -> str:
    redacted = value
    for token in ("token", "password", "secret", "proof", "authorization", "prompt", "history", "memory", "raw_audio"):
        redacted = redacted.replace(token, "[redacted-key]")
        redacted = redacted.replace(token.upper(), "[redacted-key]")
    return redacted


def _jsonable_item(item: EvidenceItem) -> dict:
    data = asdict(item)
    if item.path is not None:
        data["path"] = str(item.path)
    return data
