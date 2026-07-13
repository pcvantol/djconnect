"""Dependency, execution, artifact and rollback planning for release simulation."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from .discovery import RepositoryNode


MODE_POLICIES = {
    "development": {"publication": False, "profile": "fast"},
    "nightly": {"publication": False, "profile": "balanced"},
    "candidate": {"publication": False, "profile": "balanced"},
    "dry_run": {"publication": False, "profile": "full_qualification"},
    "qualification": {"publication": False, "profile": "full_qualification"},
    "production": {"publication": True, "profile": "production"},
    "hotfix": {"publication": True, "profile": "production"},
    "maintenance": {"publication": False, "profile": "balanced"},
}

PROFILE_REQUIREMENTS = {
    "fast": ("verification",),
    "balanced": ("verification", "software_assurance", "trusted_delivery"),
    "full_qualification": (
        "verification",
        "software_assurance",
        "trusted_delivery",
        "coverage",
        "platform_qualification",
    ),
    "production": (
        "verification",
        "software_assurance",
        "trusted_delivery",
        "coverage",
        "platform_qualification",
    ),
}


@dataclass(frozen=True)
class ExecutionStage:
    index: int
    name: str
    repositories: list[str]
    depends_on: list[str]
    blocking_conditions: list[str]
    expected_evidence: list[str]


def mode_policy(mode: str, profile: str | None = None) -> dict[str, object]:
    if mode not in MODE_POLICIES:
        raise ValueError(f"unsupported release mode: {mode}")
    selected_profile = profile or str(MODE_POLICIES[mode]["profile"])
    if selected_profile not in PROFILE_REQUIREMENTS:
        raise ValueError(f"unsupported execution profile: {selected_profile}")
    return {
        "mode": mode,
        "profile": selected_profile,
        "publication_permitted": bool(MODE_POLICIES[mode]["publication"]),
        "simulation_only": True,
        "required_evidence": list(PROFILE_REQUIREMENTS[selected_profile]),
    }


def execution_plan(nodes: list[RepositoryNode], mode: str, profile: str | None = None) -> list[ExecutionStage]:
    """Build a generic role-driven graph with explicit parallel stages."""

    policy = mode_policy(mode, profile)
    grouped = {
        role: sorted(node.name for node in nodes if node.role == role)
        for role in ("active_source", "release_source", "distribution", "optional", "future")
    }
    stages: list[ExecutionStage] = [
        ExecutionStage(
            index=0,
            name="release_control",
            repositories=[],
            depends_on=[],
            blocking_conditions=["ownership discovery must be complete", "platform version must be valid"],
            expected_evidence=["release_manifest", "repository_version_matrix"],
        )
    ]
    prerequisites = ["release_control"]
    for name, roles in (
        ("source_candidates", ("active_source", "release_source")),
        ("distribution_candidates", ("distribution",)),
    ):
        repositories = [repository for role in roles for repository in grouped[role]]
        if not repositories:
            continue
        stages.append(
            ExecutionStage(
                index=len(stages),
                name=name,
                repositories=repositories,
                depends_on=prerequisites.copy(),
                blocking_conditions=["all prerequisite stages must qualify"],
                expected_evidence=list(policy["required_evidence"]),
            )
        )
        prerequisites = [name]
    return stages


def artifact_plan(nodes: list[RepositoryNode]) -> list[dict[str, object]]:
    """Plan identities and evidence only; no artifact is created or published."""

    artifacts: list[dict[str, object]] = []
    for node in nodes:
        artifacts.append(
            {
                "repository": node.name,
                "kind": "distribution_artifact" if node.role == "distribution" else "candidate_artifact",
                "required": node.mandatory,
                "state": "PLANNED" if node.mandatory else "EXCLUDED_NOT_IN_SCOPE",
                "evidence": ["source_sha", "version", "provenance", "integrity"],
            }
        )
    return artifacts


def rollback_plan(stages: list[ExecutionStage]) -> dict[str, object]:
    checkpoints = []
    for stage in reversed(stages):
        checkpoints.append(
            {
                "stage": stage.name,
                "repositories": stage.repositories,
                "checkpoint": f"{stage.name}_checkpoint",
                "tag_checkpoint": "NOT_APPLICABLE_SIMULATION",
                "artifact_checkpoint": f"{stage.name}_artifact_inventory",
                "qualification_checkpoint": f"{stage.name}_qualification",
                "actions": ["reconcile_state", "halt_dependents", "preserve_evidence", "requalify"],
            }
        )
    return {"execution": "NOT_PERMITTED", "checkpoints": checkpoints}


def plan_as_dict(stages: list[ExecutionStage]) -> list[dict[str, object]]:
    return [asdict(stage) for stage in stages]
