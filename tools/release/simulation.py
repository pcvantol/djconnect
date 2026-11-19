"""Non-mutating composition of Platform Release simulation outputs."""

from __future__ import annotations

from dataclasses import asdict
import hashlib
import json
from pathlib import Path

from .discovery import RepositoryNode, discover_repositories
from .component_scope import validate_component_selection
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
        reconciliations: dict[str, object] | None = None,
        component_selection: dict[str, object] | None = None,
    ) -> dict[str, object]:
        platform = PlatformVersion.parse(platform_version)
        nodes = discover_repositories(self.ownership_path, role_overrides)
        component = validate_component_selection(component_selection, platform, versions or {}, shas or {}) if component_selection is not None else None
        selected = {str(name) for name in component["participants"]} if component else {node.name for node in nodes if node.mandatory}
        scoped_nodes = [node for node in nodes if node.name in selected]
        stages = execution_plan(scoped_nodes, mode, profile)
        readiness = evaluate_readiness(scoped_nodes, platform, versions or {}, shas or {}, evidence or {}, mode, profile, reconciliations, component["conditions"] if component else None)
        policy = mode_policy(mode, profile)
        repository_records = [
            {
                **asdict(node),
                "version": (versions or {}).get(node.name),
                "sha": (shas or {}).get(node.name),
                "post_merge_evidence": (reconciliations or {}).get(node.name),
                "dependencies": _dependencies(node, stages),
                "included": node.name in selected,
                "scope_reason": "selected component closure participant" if component and node.name in selected else "non-selected component" if component else "mandatory release role" if node.mandatory else "not in scope by default",
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
            "artifact_inventory": artifact_plan(scoped_nodes),
            "rollback_plan": rollback_plan(stages),
            "certification_state": "NOT_CERTIFIED" if readiness["state"] != "READY" else "PLANNED",
            "qualification_status": _qualification_status(readiness, mode),
        }
        if component:
            manifest["component_selection"] = _component_record(component_selection or {}, component)
            manifest["component_execution_authorized"] = False
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


def _component_record(selection: dict[str, object], result: dict[str, object]) -> dict[str, object]:
    """Persist a normalized selection record without accepting executable scope."""

    return {
        "state": result["state"],
        "readiness": result["readiness"],
        "component_id": selection.get("component_id"),
        "component_owner": selection.get("component_owner"),
        "source_repository": selection.get("source_repository"),
        "source_sha": selection.get("source_sha"),
        "version": selection.get("version"),
        "platform_train": selection.get("platform_train"),
        "artifact_identity": selection.get("artifact_identity"),
        "artifact_sha256": selection.get("artifact_sha256"),
        "manifest_id": selection.get("manifest_id"),
        "manifest_sha256": selection.get("manifest_sha256"),
        "release_channel": selection.get("release_channel"),
        "target_distribution": selection.get("target_distribution"),
        "artifact_kind": selection.get("artifact_kind"),
        "participants": result["participants"],
        "evidence": selection.get("evidence"),
        "conditions": result["conditions"],
    }
