"""Append-only local release journal; external retention must be verified separately."""
from __future__ import annotations

import json
import os
from pathlib import Path


class PublicationJournal:
    """Create one new journal; never reuse or overwrite an earlier attempt."""

    def __init__(self, path: Path, *, candidate_sha: str, manifest_digest: str, archive_sha256: str = "", archive_artifact_id: str = "", archive_artifact_digest: str = ""):
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
        self._fd = os.open(path, flags, 0o600)
        try:
            self.append("start", candidate_sha=candidate_sha, manifest_digest=manifest_digest, archive_sha256=archive_sha256, archive_artifact_id=archive_artifact_id, archive_artifact_digest=archive_artifact_digest)
        except BaseException:
            self.close()
            raise

    def append(self, event: str, **fields: str) -> None:
        if event not in {"start", "push_intent", "push_confirmed", "failure", "completed"}:
            raise ValueError("unexpected journal event")
        payload = (json.dumps({"event": event, **fields}, sort_keys=True) + "\n").encode()
        view = memoryview(payload)
        while view:
            count = os.write(self._fd, view)
            if count <= 0:
                raise OSError("journal write failed")
            view = view[count:]
        os.fsync(self._fd)

    def close(self) -> None:
        os.close(self._fd)
