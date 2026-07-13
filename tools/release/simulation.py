"""Non-mutating composition of Platform Release simulation outputs."""

from __future__ import annotations

from dataclasses import asdict
import hashlib
import json
from pathlib import Path

from .discovery import RepositoryNode, discover_repositories
from .planner import artifact_plan, execution_plan, mode_policy, plan_as_dict, rollback_plan
from .readiness import evaluate_readiness
from .versioning import PlatformVersion


class ReleaseSimulation:
    """Build an immutable-in-memory release manifest; never execute a release."""

    def __init__(self, ownership_path: Path) -> None:
        self.ownership_path = ownership_path

    def run(
        self,
        platform_version: str,
        mode: str = "dry_run",
        profile: str | None = None,
        versions: dict[str, str] | None = None,
        shas: dict[str, str] | None = None,
        evidence: dict[str, str] | None = None,
        role_overrides: dict[str, str] | None = None,
    ) -> dict[str, object]:
        platform = PlatformVersion.parse(platform_version)
        nodes = discover_repositories(self.ownership_path, role_overrides)
        stages = execution_plan(nodes, mode, profile)
        readiness = evaluate_readiness(nodes, platform, versions or {}, shas or {}, evidence or {}, mode, profile)
        policy = mode_policy(mode, profile)
        repository_records = [
            {
                **asdict(node),
                "version": (versions or {}).get(node.name),
                "sha": (shas or {}).get(node.name),
                "dependencies": _dependencies(node, stages),
                "included": node.mandatory,
                "scope_reason": "mandatory release role" if node.mandatory else "not in scope by default",
            }
            for node in nodes
        ]
        manifest = {
            "schema_version": 1,
            "manifest_kind": "platform_release_simulation",
            "platform_version": str(platform),
            "release_mode": mode,
            "execution_profile": policy["profile"],
            "simulation_only": True,
            "repositories": repository_records,
            "dependency_graph": plan_as_dict(stages),
            "execution_plan": plan_as_dict(stages),
            "qualification_plan": {
                "required_evidence": policy["required_evidence"],
                "status": "PLANNED",
            },
            "readiness": readiness,
            "artifact_inventory": artifact_plan(nodes),
            "rollback_plan": rollback_plan(stages),
            "certification_state": "NOT_CERTIFIED" if readiness["state"] != "READY" else "PLANNED",
            "qualification_status": _qualification_status(readiness, mode),
        }
        manifest["manifest_id"] = _manifest_id(manifest)
        return manifest


def _dependencies(node: RepositoryNode, stages: list[object]) -> list[str]:
    for stage in stages:
        if node.name in stage.repositories:
            return list(stage.depends_on)
    return []


def _manifest_id(manifest: dict[str, object]) -> str:
    stable = json.dumps(manifest, sort_keys=True, separators=(",", ":"), default=str)
    return f"release-sim-{hashlib.sha256(stable.encode()).hexdigest()[:16]}"


def _qualification_status(readiness: dict[str, object], mode: str) -> str:
    """Mark only an evidence-complete production candidate as executable."""

    if readiness["state"] != "READY":
        return "NOT_QUALIFIED"
    if mode in {"production", "hotfix"}:
        return "QUALIFIED"
    return "PLANNED"
