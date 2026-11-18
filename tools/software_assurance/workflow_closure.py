"""Recursively qualify GitHub Actions reusable-workflow closure.

The direct workflow scanner used during the initial Prompt 3 rollout verified
only the caller.  A caller pinned to a commit can still load a reusable
workflow which contains a mutable action reference.  This module resolves
reusable workflows at their requested immutable revisions and verifies every
terminal action in that graph.
"""

from __future__ import annotations

import argparse
import base64
import json
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable


SHA_RE = re.compile(r"^[0-9a-fA-F]{40}$")
USES_RE = re.compile(r"^\s*(?:-\s*)?uses:\s*['\"]?([^\s'\"]+)", re.MULTILINE)
WORKFLOW_MARKER = "/.github/workflows/"


@dataclass(frozen=True)
class Edge:
    """One resolved workflow ``uses`` edge."""

    source: str
    target: str
    kind: str
    immutable: bool
    registry_match: bool | None
    outcome: str


class WorkflowClosureError(RuntimeError):
    """Raised when a reusable workflow cannot be obtained at its requested ref."""


def _split_uses(value: str) -> tuple[str, str] | None:
    if "@" not in value:
        return None
    target, ref = value.rsplit("@", 1)
    return target, ref


def _is_reusable_workflow(target: str) -> bool:
    return WORKFLOW_MARKER in target and target.count("/") >= 3


def _repository_and_path(target: str) -> tuple[str, str]:
    repository, workflow_path = target.split(WORKFLOW_MARKER, 1)
    return repository, f".github/workflows/{workflow_path}"


def load_registry(registry_path: Path) -> set[tuple[str, str]]:
    """Return approved ``(repository, immutable_sha)`` terminal action pins."""
    payload = json.loads(registry_path.read_text(encoding="utf-8"))
    approved: set[tuple[str, str]] = set()
    for batch in payload.get("batches", []):
        for pin in batch.get("pins", []):
            repository = pin.get("repository") or pin.get("dependency_repository")
            value = pin.get("sha") or pin.get("immutable_sha")
            if not repository or not value:
                continue
            for sha in re.findall(r"\b[0-9a-fA-F]{40}\b", value):
                approved.add((repository.lower(), sha.lower()))
    return approved


def github_content_fetcher(repository: str, workflow_path: str, ref: str) -> str:
    """Fetch a workflow at one exact GitHub revision without checking it out."""
    command = [
        "gh",
        "api",
        "-X",
        "GET",
        f"repos/{repository}/contents/{workflow_path}?ref={ref}",
        "--jq",
        ".content",
    ]
    result = subprocess.run(command, check=False, capture_output=True, text=True)
    if result.returncode:
        detail = result.stderr.strip() or result.stdout.strip()
        raise WorkflowClosureError(f"cannot fetch {repository}/{workflow_path}@{ref}: {detail}")
    try:
        return base64.b64decode(result.stdout).decode("utf-8")
    except (ValueError, UnicodeDecodeError) as exc:
        raise WorkflowClosureError(
            f"invalid GitHub content response for {repository}/{workflow_path}@{ref}"
        ) from exc


def scan_workflow_closure(
    repository: str,
    workflow_sources: dict[str, str],
    registry: set[tuple[str, str]],
    fetcher: Callable[[str, str, str], str] = github_content_fetcher,
) -> tuple[list[Edge], list[str]]:
    """Resolve all reusable workflow edges, including cycles and duplicates.

    ``workflow_sources`` supplies locally available root workflows under their
    repository-relative paths. Remote reusable workflows are fetched only at
    the SHA specified by their caller.  A visited-node set makes cycles safe;
    an edge list deliberately preserves duplicates for auditability.
    """
    edges: list[Edge] = []
    findings: list[str] = []
    visited: set[tuple[str, str, str]] = set()

    def visit(source_id: str, content: str, node: tuple[str, str, str] | None) -> None:
        if node is not None:
            if node in visited:
                return
            visited.add(node)
        for value in USES_RE.findall(content):
            split = _split_uses(value)
            if split is None:
                if value.startswith("./.github/workflows/"):
                    local_path = value.removeprefix("./")
                    edge = Edge(source_id, value, "reusable_workflow", True, None, "accepted")
                    if local_path not in workflow_sources:
                        findings.append(f"missing local reusable workflow: {source_id} -> {value}")
                        edges.append(Edge(**{**asdict(edge), "outcome": "missing"}))
                    else:
                        edges.append(edge)
                        visit(f"{repository}/{local_path}", workflow_sources[local_path], None)
                    continue
                # Local actions and docker actions do not have a remote mutable ref.
                edges.append(Edge(source_id, value, "local_or_container", True, None, "accepted"))
                continue
            target, ref = split
            immutable = bool(SHA_RE.fullmatch(ref))
            if _is_reusable_workflow(target):
                edge = Edge(source_id, value, "reusable_workflow", immutable, None, "accepted")
                if not immutable:
                    findings.append(f"mutable reusable workflow reference: {source_id} -> {value}")
                    edges.append(Edge(**{**asdict(edge), "outcome": "failed"}))
                    continue
                edges.append(edge)
                remote_repository, remote_path = _repository_and_path(target)
                remote_node = (remote_repository.lower(), remote_path, ref.lower())
                if remote_node in visited:
                    continue
                try:
                    remote_content = fetcher(remote_repository, remote_path, ref)
                except WorkflowClosureError as exc:
                    findings.append(str(exc))
                    edges[-1] = Edge(**{**asdict(edge), "outcome": "missing"})
                    continue
                visit(f"{remote_repository}/{remote_path}@{ref}", remote_content, remote_node)
                continue

            if target.startswith("./") or target.startswith("docker://"):
                edges.append(Edge(source_id, value, "local_or_container", True, None, "accepted"))
                continue
            action_repository = target.lower()
            registry_match = immutable and any(
                ref.lower() == approved_sha
                and (action_repository == approved_repository or action_repository.startswith(f"{approved_repository}/"))
                for approved_repository, approved_sha in registry
            )
            outcome = "accepted" if immutable and registry_match else "failed"
            edges.append(Edge(source_id, value, "terminal_action", immutable, registry_match, outcome))
            if not immutable:
                findings.append(f"mutable terminal action reference: {source_id} -> {value}")
            elif not registry_match:
                findings.append(f"terminal action is not in approved registry: {source_id} -> {value}")

    for path, content in sorted(workflow_sources.items()):
        visit(f"{repository}/{path}", content, None)
    return edges, findings


def markdown_report(repository: str, edges: list[Edge], findings: list[str]) -> str:
    """Render a compact human-readable closure evidence report."""
    reusable = sum(edge.kind == "reusable_workflow" for edge in edges)
    terminal = sum(edge.kind == "terminal_action" for edge in edges)
    lines = [
        "# Workflow Closure Report",
        "",
        "## Scope",
        "",
        f"- Repository: `{repository}`",
        f"- Reusable-workflow edges inspected: {reusable}",
        f"- Terminal action edges inspected: {terminal}",
        f"- Duplicate edges retained in evidence: {len(edges)}",
        "- Cycle handling: visited immutable workflow nodes are resolved once; every caller edge remains recorded.",
        "",
        "## Result",
        "",
    ]
    if findings:
        lines.extend(["**BLOCKED** — recursive closure validation found:", ""])
        lines.extend(f"- {finding}" for finding in findings)
    else:
        lines.extend(["**PASS** — every reachable reusable workflow and terminal action is immutable and registry-approved."])
    lines.extend(["", "## Edge Evidence", "", "| Source | Target | Type | Immutable | Registry | Outcome |", "| --- | --- | --- | --- | --- | --- |"])
    for edge in edges:
        registry = "n/a" if edge.registry_match is None else str(edge.registry_match).lower()
        lines.append(
            f"| `{edge.source}` | `{edge.target}` | {edge.kind} | {str(edge.immutable).lower()} | {registry} | {edge.outcome} |"
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", default="pcvantol/djconnect")
    parser.add_argument("--workflow-dir", type=Path, default=Path(".github/workflows"))
    parser.add_argument(
        "--registry", type=Path, default=Path("software_assurance/action-pinning/batch-1-pins.json")
    )
    parser.add_argument("--format", choices=("json", "markdown"), default="markdown")
    args = parser.parse_args()
    sources = {
        f".github/workflows/{path.relative_to(args.workflow_dir).as_posix()}": path.read_text(encoding="utf-8")
        for path in args.workflow_dir.glob("*.y*ml")
    }
    edges, findings = scan_workflow_closure(args.repository, sources, load_registry(args.registry))
    if args.format == "json":
        print(json.dumps({"repository": args.repository, "edges": [asdict(edge) for edge in edges], "findings": findings}, indent=2))
    else:
        print(markdown_report(args.repository, edges, findings), end="")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
