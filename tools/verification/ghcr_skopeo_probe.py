"""Check existing GHCR tags around a separately invoked unique OCI-copy probe."""
from __future__ import annotations

import hashlib
import json
import os
import re
import urllib.request

from tools.verification.ghcr_readonly_probe import NoRedirect
from tools.verification.ghcr_release_guard import HISTORICAL_DIGEST, authenticated_registry_probe

REPOSITORY = "djconnect-music-dj/djconnect-verification-platform"
BASE_TAGS = ("1.1.0", "1.1", "latest", "sha-f05773616a1a", "1.1.0-f05773616a1a")
MARKER = re.compile(r"skopeo-check-[0-9]+-[0-9]+-[0-9a-f]{32}\Z")
DIGEST = re.compile(r"sha256:[0-9a-f]{64}\Z")


def check(probe, marker: str, expected: str | None = None) -> None:
    if not MARKER.fullmatch(marker):
        raise ValueError("invalid unique probe tag")
    if expected is not None and not DIGEST.fullmatch(expected):
        raise ValueError("invalid expected digest")
    for tag in BASE_TAGS:
        if probe(tag) != (200, HISTORICAL_DIGEST):
            raise ValueError("historical tag changed or unavailable")
    observed = probe(marker)
    if observed != ((404, None) if expected is None else (200, expected)):
        raise ValueError("probe tag state mismatch")


def readback_bytes(marker: str, expected: str) -> None:
    opener = urllib.request.build_opener(NoRedirect())
    with opener.open("https://ghcr.io/token?scope=repository:" + REPOSITORY + ":pull", timeout=15) as response:
        bearer = json.load(response)["token"]
    request = urllib.request.Request(
        "https://ghcr.io/v2/" + REPOSITORY + "/manifests/" + marker,
        headers={"Authorization": "Bearer " + bearer,
                 "Accept": "application/vnd.oci.image.manifest.v1+json, application/vnd.docker.distribution.manifest.v2+json"},
    )
    with opener.open(request, timeout=15) as response:
        body = response.read(8 * 1024 * 1024 + 1)
        if len(body) > 8 * 1024 * 1024 or response.headers.get("Docker-Content-Digest") != expected:
            raise ValueError("probe readback header or size mismatch")
    if "sha256:" + hashlib.sha256(body).hexdigest() != expected:
        raise ValueError("probe readback bytes mismatch")


def main() -> None:
    marker = os.environ["PROBE_TAG"]
    expected = os.environ.get("PROBE_DIGEST") or None
    probe = authenticated_registry_probe(os.environ.get("GITHUB_ACTOR", ""), os.environ.get("GITHUB_TOKEN", ""))
    check(probe, marker, expected)
    if expected is not None:
        readback_bytes(marker, expected)
    print("GHCR probe baseline and tag checks passed; no deletion performed")


if __name__ == "__main__":
    main()
