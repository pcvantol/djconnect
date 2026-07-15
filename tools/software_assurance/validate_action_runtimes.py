"""Fail closed when a pinned GitHub Action targets a retired Node runtime."""

from __future__ import annotations

import argparse
import base64
import json
import os
from pathlib import Path
import re
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


USES_PATTERN = re.compile(r"^\s*(?:-\s+)?uses:\s+([^\s@]+)@([^\s#]+)", re.MULTILINE)
SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")
NODE_PATTERN = re.compile(r"^\s*using:\s*['\"]?node(\d+)", re.MULTILINE)


def _action_parts(target: str) -> tuple[str, str, str] | None:
    if target.startswith("./"):
        return None
    parts = target.split("/")
    if len(parts) < 2:
        raise ValueError(f"invalid action target: {target}")
    owner, repository, *action_path = parts
    path = "/".join(action_path)
    if path.startswith(".github/workflows/"):
        return None
    return owner, repository, path


def _get_manifest(token: str, owner: str, repository: str, action_path: str, sha: str) -> str:
    for filename in ("action.yml", "action.yaml"):
        path = "/".join(part for part in (action_path, filename) if part)
        request = Request(
            f"https://api.github.com/repos/{owner}/{repository}/contents/{path}?ref={sha}",
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {token}",
                "X-GitHub-Api-Version": "2026-03-10",
            },
        )
        try:
            with urlopen(request, timeout=20) as response:
                payload = json.load(response)
        except HTTPError as error:
            if error.code == 404:
                continue
            raise RuntimeError(f"cannot inspect {owner}/{repository}@{sha}: HTTP {error.code}") from error
        except URLError as error:
            raise RuntimeError(f"cannot inspect {owner}/{repository}@{sha}: {error.reason}") from error
        return base64.b64decode(payload["content"]).decode("utf-8")
    raise RuntimeError(f"cannot find action manifest for {owner}/{repository}@{sha}")


def validate(workspace: Path, token: str) -> list[str]:
    findings: list[str] = []
    manifests: dict[tuple[str, str], str] = {}
    for workflow in sorted(workspace.glob(".github/workflows/*.*y*ml")):
        content = workflow.read_text(encoding="utf-8")
        for target, ref in USES_PATTERN.findall(content):
            try:
                action = _action_parts(target)
            except ValueError as error:
                findings.append(f"{workflow}: {error}")
                continue
            if action is None:
                continue
            if not SHA_PATTERN.fullmatch(ref):
                findings.append(f"{workflow}: action must use a full commit SHA: {target}@{ref}")
                continue
            key = (target, ref)
            if key not in manifests:
                try:
                    manifests[key] = _get_manifest(token, *action, ref)
                except RuntimeError as error:
                    findings.append(f"{workflow}: {error}")
                    continue
            runtime = NODE_PATTERN.search(manifests[key])
            if runtime and int(runtime.group(1)) < 24:
                findings.append(f"{workflow}: {target}@{ref} targets Node {runtime.group(1)}; Node 24 or newer is required")
    return findings


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("workspace", type=Path)
    args = parser.parse_args()
    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        raise SystemExit("GITHUB_TOKEN is required for GitHub Action runtime validation")
    findings = validate(args.workspace, token)
    if findings:
        raise SystemExit("\n".join(findings))


if __name__ == "__main__":
    main()
