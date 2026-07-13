"""Simulation-only CLI for the Platform Release Orchestrator."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .simulation import ReleaseSimulation


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="release", description="Platform Release Orchestrator (simulation only)")
    parser.add_argument("--ownership", type=Path, default=Path("REPOSITORY_OWNERSHIP.md"))
    parser.add_argument("--platform-version", required=True)
    parser.add_argument("--mode", choices=("development", "nightly", "candidate", "dry_run", "qualification", "production", "hotfix", "maintenance"), default="dry_run")
    parser.add_argument("--profile", choices=("fast", "balanced", "full_qualification", "production"))
    parser.add_argument("--versions-file", type=Path)
    parser.add_argument("--shas-file", type=Path)
    parser.add_argument("--evidence-file", type=Path)
    parser.add_argument("--roles-file", type=Path)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("plan", "readiness", "simulate", "manifest", "graph", "explain"):
        subparsers.add_parser(command)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
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
    if args.command in {"simulate", "manifest"}:
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


if __name__ == "__main__":
    raise SystemExit(main())
