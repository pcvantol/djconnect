"""One unique GHCR write probe. Never delete or retag existing versions."""
from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
import uuid

from tools.verification.ghcr_readonly_probe import NoRedirect

REPOSITORY = "djconnect-music-dj/djconnect-verification-platform"
BASE_DIGEST = "sha256:3f0b8d3ba5f07afa5c8f05cd305dd92c43806e0fed24395be96d832e7ef72619"
BASE_TAGS = ("1.1.0", "1.1", "latest", "sha-f05773616a1a", "1.1.0-f05773616a1a")
OCI = "application/vnd.oci.image.manifest.v1+json"
ACCEPT = OCI + ", application/vnd.docker.distribution.manifest.v2+json"


def build_manifest(source: dict, marker: str) -> bytes:
    if not re.fullmatch(r"rights-check-[0-9]+-[0-9]+-[0-9a-f]{32}", marker):
        raise ValueError("invalid probe marker")
    if source.get("schemaVersion") != 2 or not isinstance(source.get("config"), dict) or not isinstance(source.get("layers"), list):
        raise ValueError("unexpected source manifest")
    source = json.loads(json.dumps(source))
    source["mediaType"] = OCI
    source["config"]["mediaType"] = "application/vnd.oci.image.config.v1+json"
    for layer in source["layers"]:
        if layer.get("mediaType") != "application/vnd.docker.image.rootfs.diff.tar.gzip":
            raise ValueError("unexpected layer media type")
        layer["mediaType"] = "application/vnd.oci.image.layer.v1.tar+gzip"
    source["annotations"] = {"org.djconnect.verification.probe": marker,
                             "org.djconnect.verification.purpose": "temporary-write-rights-check"}
    return json.dumps(source, sort_keys=True, separators=(",", ":")).encode()


def run_probe(opener, *, actor: str, secret: str, run_id: str, attempt: str, nonce: str) -> tuple[str, str]:
    if not actor or ":" in actor or not secret or not run_id.isdigit() or not attempt.isdigit():
        raise SystemExit("missing probe identity")
    marker = f"rights-check-{run_id}-{attempt}-{nonce}"
    base = "https://ghcr.io/v2/" + REPOSITORY + "/manifests/"
    auth = base64.b64encode((actor + ":" + secret).encode()).decode()
    url = "https://ghcr.io/token?" + urllib.parse.urlencode({"scope": "repository:" + REPOSITORY + ":pull,push"})
    try:
        with opener.open(urllib.request.Request(url, headers={"Authorization": "Basic " + auth}), timeout=15) as response:
            bearer = json.load(response)["token"]
        def get(tag):
            request = urllib.request.Request(base + tag, headers={"Authorization": "Bearer " + bearer, "Accept": ACCEPT})
            with opener.open(request, timeout=15) as response:
                return response.headers.get("Docker-Content-Digest"), response.read(1048577)
        for tag in BASE_TAGS:
            if get(tag)[0] != BASE_DIGEST:
                raise ValueError("historic tag changed")
        digest, raw = get("1.1.0")
        if hashlib.sha256(raw).hexdigest() != BASE_DIGEST.removeprefix("sha256:"):
            raise ValueError("historic manifest bytes mismatch")
        manifest = build_manifest(json.loads(raw), marker)
        candidate = "sha256:" + hashlib.sha256(manifest).hexdigest()
        if candidate == digest:
            raise ValueError("probe must be a separate manifest")
        try:
            get(marker)
        except urllib.error.HTTPError as error:
            if error.code != 404:
                raise
        else:
            raise ValueError("probe tag already exists")
        print("GHCR_PROBE_TAG=" + marker)
        print("GHCR_PROBE_DIGEST=" + candidate)
        request = urllib.request.Request(base + marker, data=manifest, method="PUT",
            headers={"Authorization": "Bearer " + bearer, "Content-Type": OCI})
        with opener.open(request, timeout=30) as response:
            if response.status != 201 or response.headers.get("Docker-Content-Digest") != candidate:
                raise ValueError("unexpected write result")
        actual, actual_bytes = get(marker)
        if (actual != candidate or actual_bytes != manifest
                or "sha256:" + hashlib.sha256(actual_bytes).hexdigest() != candidate
                or any(get(tag)[0] != BASE_DIGEST for tag in BASE_TAGS)):
            raise ValueError("post-write verification failed")
    except Exception:
        print("GHCR probe failed; tag may have been created: " + marker)
        raise SystemExit(1) from None
    return marker, candidate


def main() -> None:
    marker, candidate = run_probe(urllib.request.build_opener(NoRedirect()),
        actor=os.environ.get("GITHUB_ACTOR", ""), secret=os.environ.get("GITHUB_TOKEN", ""),
        run_id=os.environ.get("GITHUB_RUN_ID", ""), attempt=os.environ.get("GITHUB_RUN_ATTEMPT", ""),
        nonce=uuid.uuid4().hex)
    print("GHCR_PROBE_TAG=" + marker)
    print("GHCR_PROBE_DIGEST=" + candidate)
    print("Existing baseline tags unchanged; probe retained for later cleanup.")


if __name__ == "__main__":
    main()
