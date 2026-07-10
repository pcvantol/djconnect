"""Evidence and artifact management for verification runs."""

from __future__ import annotations

import hashlib
from pathlib import Path

from .models import EvidenceItem


class ArtifactManager:
    def __init__(self, evidence_dir: Path) -> None:
        self.evidence_dir = evidence_dir

    def ensure_run_dir(self, run_id: str) -> Path:
        path = self.evidence_dir / run_id
        path.mkdir(parents=True, exist_ok=True)
        return path


class EvidenceManager:
    def checksum(self, path: Path) -> EvidenceItem:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        return EvidenceItem("checksum", path=path, metadata={"sha256": digest})


class LogManager:
    def redact(self, value: str) -> str:
        redacted = value
        for token in ("token", "password", "secret", "proof", "authorization", "prompt"):
            redacted = redacted.replace(token, "[redacted-key]")
        return redacted


class ScreenshotManager:
    pass


class SerialManager:
    pass


class PerformanceCollector:
    pass
