"""Read and verify the manifest digest of a single-image OCI archive."""
from __future__ import annotations

import hashlib
import json
import re
import tarfile
from pathlib import Path

SHA256 = re.compile(r"sha256:[0-9a-f]{64}\Z")
MAX_METADATA = 8 * 1024 * 1024


def _read_unique(archive: tarfile.TarFile, name: str, limit: int) -> bytes:
    matches = [member for member in archive.getmembers() if member.name == name]
    if len(matches) != 1 or not matches[0].isfile() or matches[0].size > limit:
        raise ValueError("missing, duplicate, non-file or oversized OCI archive entry")
    with archive.extractfile(matches[0]) as stream:
        if stream is None:
            raise ValueError("missing OCI archive data")
        return stream.read()


def manifest_details(path: Path) -> tuple[str, str]:
    with tarfile.open(path, "r:*") as archive:
        index = json.loads(_read_unique(archive, "index.json", MAX_METADATA))
        manifests = index.get("manifests")
        if index.get("schemaVersion") != 2 or not isinstance(manifests, list) or len(manifests) != 1:
            raise ValueError("expected exactly one OCI manifest")
        descriptor = manifests[0]
        digest = descriptor.get("digest")
        if not isinstance(digest, str) or not SHA256.fullmatch(digest):
            raise ValueError("invalid OCI manifest digest")
        raw = _read_unique(archive, "blobs/sha256/" + digest[7:], MAX_METADATA)
        if len(raw) != descriptor.get("size") or "sha256:" + hashlib.sha256(raw).hexdigest() != digest:
            raise ValueError("OCI manifest digest or size mismatch")
        manifest = json.loads(raw)
        if manifest.get("schemaVersion") != 2 or not isinstance(manifest.get("config"), dict) or not isinstance(manifest.get("layers"), list):
            raise ValueError("unexpected OCI manifest")
        for blob in [manifest["config"], *manifest["layers"]]:
            blob_digest = blob.get("digest")
            if not isinstance(blob_digest, str) or not SHA256.fullmatch(blob_digest):
                raise ValueError("invalid OCI blob digest")
            name = "blobs/sha256/" + blob_digest[7:]
            matches = [member for member in archive.getmembers() if member.name == name]
            if len(matches) != 1 or not matches[0].isfile() or matches[0].size != blob.get("size"):
                raise ValueError("missing, duplicate or wrong-size OCI blob")
            hasher = hashlib.sha256()
            with archive.extractfile(matches[0]) as stream:
                if stream is None:
                    raise ValueError("missing OCI blob data")
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    hasher.update(chunk)
            if "sha256:" + hasher.hexdigest() != blob_digest:
                raise ValueError("OCI blob digest mismatch")
        return digest, manifest["config"]["digest"]


def manifest_digest(path: Path) -> str:
    return manifest_details(path)[0]
