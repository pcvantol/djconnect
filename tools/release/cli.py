"""CLI for simulation and explicitly authorized internal-release execution."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .execution import EvidenceOnlyExecutionClient, ExecutionRequest, ReleaseExecutor, write_execution_evidence
from .github import GitHubCliExecutionClient
from .simulation import ReleaseSimulation


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="release", description="Platform Release Orchestrator")
    parser.add_argument("--ownership", type=Path, default=Path("REPOSITORY_OWNERSHIP.md"))
    parser.add_argument("--platform-version", required=True)
    parser.add_argument("--mode", choices=("development", "nightly", "candidate", "dry_run", "qualification", "production", "hotfix", "maintenance"), default="dry_run")
    parser.add_argument("--profile", choices=("fast", "balanced", "full_qualification", "production"))
    parser.add_argument("--versions-file", type=Path)
    parser.add_argument("--shas-file", type=Path)
    parser.add_argument("--evidence-file", type=Path)
    parser.add_argument("--roles-file", type=Path)
    parser.add_argument("--execution-file", type=Path, help="approved INTERNAL_RELEASE execution request JSON")
    parser.add_argument("--output-dir", type=Path, help="directory for execution evidence JSON")
    parser.add_argument("--execute", action="store_true", help="explicitly permit external internal-release actions")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("plan", "readiness", "simulate", "manifest", "graph", "explain", "rehearse", "execute"):
        subparsers.add_parser(command)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    manifest = ReleaseSimulation(args.ownership).run(
        platform_version=args.platform_version,
        mode=args.mode,
        profile=args.profile,
        versions=_load_mapping(args.versions_file),
        shas=_load_mapping(args.shas_file),
        evidence=_load_mapping(args.evidence_file),
        role_overrides=_load_mapping(args.roles_file),
    )
    result: object
    if args.command in {"rehearse", "execute"}:
        if args.execution_file is None or args.output_dir is None:
            parser.error(f"{args.command} requires --execution-file and --output-dir")
        raw_request = _load_json_object(args.execution_file)
        request = ExecutionRequest.from_dict(raw_request)
        if args.command == "rehearse":
            if not request.non_production:
                parser.error("rehearse requires execution request non_production=true")
            result = ReleaseExecutor(EvidenceOnlyExecutionClient()).execute(manifest, request)
        else:
            if not args.execute:
                parser.error("execute requires --execute; no external action is implicit")
            result = ReleaseExecutor(GitHubCliExecutionClient()).execute(manifest, request)
        result = {**result, "evidence_files": [str(path) for path in write_execution_evidence(result, args.output_dir)]}
    elif args.command in {"simulate", "manifest"}:
        result = manifest
    elif args.command in {"plan", "graph"}:
        result = manifest["execution_plan"]
    elif args.command == "readiness":
        result = manifest["readiness"]
    else:
        result = {
            "simulation_only": True,
            "publication_permitted_by_mode": args.mode in {"production", "hotfix"},
            "publication_executed": False,
            "readiness": manifest["readiness"],
            "blocking_conditions": manifest["readiness"]["conditions"],
        }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def _load_mapping(path: Path | None) -> dict[str, str]:
    if path is None:
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not all(isinstance(key, str) and isinstance(value, str) for key, value in data.items()):
        raise ValueError(f"{path} must be a JSON object with string keys and values")
    return data


def _load_json_object(path: Path) -> dict[str, object]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


if __name__ == "__main__":
    raise SystemExit(main())
