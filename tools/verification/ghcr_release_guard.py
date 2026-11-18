"""Coordinated GHCR publication for verification runtime; no atomic tag reservation exists."""
from __future__ import annotations

import base64
import json
import os
import re
import subprocess
import urllib.error
import urllib.parse
import urllib.request

from tools.verification.ghcr_readonly_probe import NoRedirect

TARGET = "ghcr.io/djconnect-music-dj/djconnect-verification-platform"
REPOSITORY = "djconnect-music-dj/djconnect-verification-platform"
CORE_REPOSITORY = "djconnect-music-dj/djconnect"
CORE_ID = "1258575431"
HISTORICAL_DIGEST = "sha256:3f0b8d3ba5f07afa5c8f05cd305dd92c43806e0fed24395be96d832e7ef72619"
DIGEST = re.compile(r"sha256:[0-9a-f]{64}\Z")


def validate_release(*, repository: str, repository_id: str, image: str,
                     checkout_sha: str, release_sha: str, version: str, publishing: bool = True) -> None:
    if repository != CORE_REPOSITORY or repository_id != CORE_ID:
        raise ValueError("unexpected Core repository identity")
    if image != TARGET:
        raise ValueError("unexpected image destination")
    if not re.fullmatch(r"[0-9a-f]{40}", checkout_sha) or release_sha != checkout_sha:
        raise ValueError("release SHA must equal exact checked-out commit")
    if not re.fullmatch(r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)", version):
        raise ValueError("invalid stable runtime version")
    if publishing and tuple(map(int, version.split("."))) <= (1, 1, 0):
        raise ValueError("historical runtime tags must not be overwritten")


def authenticated_registry_probe(actor: str, token: str):
    if not actor or ":" in actor or not token:
        raise ValueError("missing registry identity")
    basic = base64.b64encode((actor + ":" + token).encode()).decode()
    scope = "repository:" + REPOSITORY + ":pull,push"
    req = urllib.request.Request("https://ghcr.io/token?" + urllib.parse.urlencode({"scope": scope}),
                                 headers={"Authorization": "Basic " + basic})
    opener = urllib.request.build_opener(NoRedirect())
    with opener.open(req, timeout=15) as response:
        bearer = json.load(response)["token"]
    if not isinstance(bearer, str) or not bearer or "\n" in bearer or "\r" in bearer:
        raise ValueError("invalid registry token")
    def probe(tag):
        req = urllib.request.Request("https://ghcr.io/v2/" + REPOSITORY + "/manifests/" + tag,
            headers={"Authorization": "Bearer " + bearer,
                     "Accept": "application/vnd.oci.image.manifest.v1+json, application/vnd.docker.distribution.manifest.v2+json"}, method="HEAD")
        try:
            with opener.open(req, timeout=15) as response:
                return response.status, response.headers.get("Docker-Content-Digest")
        except urllib.error.HTTPError as error:
            return error.code, None
    return probe


def _publish(*, image: str, version: str, release_sha: str, checkout_sha: str,
            repository: str, repository_id: str, probe, push, expected_digest: str, journal, mutable_expected=None) -> str:
    """Check, push and read back tags. Checks are not atomic against outside writers."""
    validate_release(repository=repository, repository_id=repository_id, image=image,
                     checkout_sha=checkout_sha, release_sha=release_sha, version=version)
    if not DIGEST.fullmatch(expected_digest):
        raise ValueError("independent manifest digest required")
    if probe("1.1.0") != (200, HISTORICAL_DIGEST):
        raise ValueError("historical public baseline changed or unavailable")
    immutable = (version, f"{version}-{release_sha[:12]}", f"sha-{release_sha[:12]}")
    if any(probe(tag)[0] != 404 for tag in immutable):
        raise ValueError("immutable target tag not demonstrably absent")
    aliases = (".".join(version.split(".")[:2]), "latest")
    if mutable_expected is not None:
        if aliases[0] == "1.1":
            raise ValueError("historical 1.1 alias must not be overwritten")
        if set(mutable_expected) != set(aliases):
            raise ValueError("explicit expected digest required for both mutable tags")
        for tag in aliases:
            expected = mutable_expected[tag]
            if expected != "ABSENT" and not DIGEST.fullmatch(expected):
                raise ValueError("invalid expected mutable tag state")
            if probe(tag) != ((404, None) if expected == "ABSENT" else (200, expected)):
                raise ValueError("mutable tag state changed")
    new_digest = None
    for tag in immutable:
        if probe(tag)[0] != 404:
            raise ValueError("immutable target tag appeared before push")
        journal.append("push_intent", tag=tag, manifest_digest=expected_digest)
        try:
            push(f"{image}:{tag}")
            status, digest = probe(tag)
        except Exception:
            journal.append("failure", tag=tag, manifest_digest=expected_digest)
            raise
        if status != 200 or digest != expected_digest:
            journal.append("failure", tag=tag, manifest_digest=expected_digest)
            raise ValueError("immutable tag readback differs from independently verified manifest")
        journal.append("push_confirmed", tag=tag, manifest_digest=expected_digest)
        if new_digest is not None and digest != new_digest:
            raise ValueError("immutable tag digest mismatch")
        new_digest = digest
    if mutable_expected is not None:
        for tag in aliases:
            expected = mutable_expected[tag]
            if probe(tag) != ((404, None) if expected == "ABSENT" else (200, expected)):
                raise ValueError("mutable tag changed before push")
            journal.append("push_intent", tag=tag, manifest_digest=expected_digest)
            try:
                push(f"{image}:{tag}")
                actual = probe(tag)
            except Exception:
                journal.append("failure", tag=tag, manifest_digest=expected_digest)
                raise
            if actual != (200, expected_digest):
                journal.append("failure", tag=tag, manifest_digest=expected_digest)
                raise ValueError("mutable tag readback mismatch")
            journal.append("push_confirmed", tag=tag, manifest_digest=expected_digest)
    if probe("1.1.0") != (200, HISTORICAL_DIGEST):
        raise ValueError("historical baseline changed")
    journal.append("completed", manifest_digest=expected_digest)
    return new_digest



def publish(**kwargs) -> str:
    journal = kwargs["journal"]
    try:
        return _publish(**kwargs)
    except Exception:
        journal.append("failure", stage="publication")
        raise



def validate_run_metadata(run: dict, *, run_id: str, attempt: str, release_sha: str, version: str) -> None:
    """Validate API-returned provenance; no package-wide exclusivity is implied."""
    workflow_path = ".github/workflows/verification-platform-docker-release.yml"
    if (not run_id.isdigit() or not attempt.isdigit() or str(run.get("id")) != run_id
            or str(run.get("run_attempt")) != attempt or run.get("path") != workflow_path
            or run.get("status") != "in_progress" or run.get("head_sha") != release_sha
            or run.get("event") not in ("push", "workflow_dispatch")
            or run.get("repository", {}).get("id") != int(CORE_ID)
            or run.get("head_repository", {}).get("id") != int(CORE_ID)):
        raise ValueError("GitHub API run provenance mismatch")
    branch = run.get("head_branch")
    if run.get("event") == "workflow_dispatch" and branch != "main":
        raise ValueError("manual release must target main")
    if run.get("event") == "push" and branch != "verification-platform-v" + version:
        raise ValueError("release tag does not match runtime version")


def fetch_run_metadata(token: str, run_id: str) -> dict:
    if not token or not run_id.isdigit():
        raise ValueError("missing run provenance credentials")
    request = urllib.request.Request(
        "https://api.github.com/repos/" + CORE_REPOSITORY + "/actions/runs/" + run_id,
        headers={"Authorization": "Bearer " + token, "Accept": "application/vnd.github+json"},
    )
    with urllib.request.build_opener(NoRedirect()).open(request, timeout=15) as response:
        return json.load(response)


def publish_from_environment(image: str, version: str, release_sha: str, checkout_sha: str) -> str:
    if os.environ.get("GITHUB_ACTIONS") != "true":
        raise ValueError("publication requires the coordinated GitHub Actions workflow")
    validate_release(repository=os.environ.get("GITHUB_REPOSITORY", ""),
                     repository_id=os.environ.get("GITHUB_REPOSITORY_ID", ""), image=image,
                     checkout_sha=checkout_sha, release_sha=release_sha, version=version)
    expected_workflow = CORE_REPOSITORY + "/.github/workflows/verification-platform-docker-release.yml@"
    if not os.environ.get("GITHUB_WORKFLOW_REF", "").startswith(expected_workflow):
        raise ValueError("publication requires the coordinated release workflow")
    actor, token = os.environ.get("GITHUB_ACTOR", ""), os.environ.get("GITHUB_TOKEN", "")
    run_id, attempt = os.environ.get("GITHUB_RUN_ID", ""), os.environ.get("GITHUB_RUN_ATTEMPT", "")
    validate_run_metadata(fetch_run_metadata(token, run_id), run_id=run_id, attempt=attempt, release_sha=release_sha, version=version)
    probe = authenticated_registry_probe(actor, token)
    mutable = None
    if os.environ.get("PROMOTE_MUTABLE") == "true":
        minor = ".".join(version.split(".")[:2])
        mutable = {minor: os.environ.get("EXPECTED_MINOR", ""), "latest": os.environ.get("EXPECTED_LATEST", "")}
    from pathlib import Path
    from tools.verification.ghcr_publication_journal import PublicationJournal
    from tools.verification.oci_manifest_digest import manifest_details

    runner_temp = Path(os.environ["RUNNER_TEMP"]).resolve(strict=True)
    archive = Path(os.environ["OCI_ARCHIVE"])
    if archive.is_symlink() or archive.resolve(strict=True).parent != runner_temp:
        raise ValueError("OCI archive must be a regular file directly inside runner temp")
    expected_digest, config_digest = manifest_details(archive)
    image_id = subprocess.check_output(
        ["docker", "image", "inspect", "--format", "{{.Id}}", image + ":" + version], text=True
    ).strip()
    if image_id != config_digest:
        raise ValueError("smoke-tested image does not match OCI archive config")
    archive_id = os.environ.get("ARCHIVE_ARTIFACT_ID", "")
    artifact_digest = os.environ.get("ARCHIVE_ARTIFACT_DIGEST", "")
    if not archive_id.isdigit() or not re.fullmatch(r"[0-9a-f]{64}", artifact_digest):
        raise ValueError("retained OCI artifact identity and digest are required")
    artifact_digest = "sha256:" + artifact_digest
    import hashlib
    archive_hash = hashlib.sha256()
    with archive.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            archive_hash.update(chunk)
    journal_path = runner_temp / ("ghcr-publication-" + run_id + "-" + attempt + ".jsonl")
    journal = PublicationJournal(journal_path, candidate_sha=release_sha, manifest_digest=expected_digest,
                                 archive_sha256="sha256:" + archive_hash.hexdigest(),
                                 archive_artifact_id=archive_id, archive_artifact_digest=artifact_digest)
    try:
        return publish(image=image, version=version, release_sha=release_sha, checkout_sha=checkout_sha,
                       repository=os.environ.get("GITHUB_REPOSITORY", ""), repository_id=os.environ.get("GITHUB_REPOSITORY_ID", ""),
                       probe=probe, push=lambda ref: subprocess.check_call(
                           ["skopeo", "copy", "--preserve-digests", "oci-archive:" + str(archive), "docker://" + ref]),
                       expected_digest=expected_digest, journal=journal, mutable_expected=mutable)
    finally:
        journal.close()
