"""CLI entry point for the DJConnect Verification Harness."""

from __future__ import annotations

import argparse
from pathlib import Path

from .config import load_config
from .orchestrator import VerificationOrchestrator
from .reporters import JSONReporter, MarkdownReporter, SummaryReporter
from .scenarios import ScenarioLoader, ScenarioScheduler, ScenarioValidator


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="verification")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--config", type=Path)
    parser.add_argument("--env-file", type=Path)
    parser.add_argument("--secrets-file", type=Path)
    parser.add_argument("--ci", action="store_true")

    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("list", "validate", "dry-run", "execute", "report"):
        sub = subparsers.add_parser(command)
        _add_filters(sub)
    subparsers.add_parser("evidence")
    subparsers.add_parser("clean")
    subparsers.add_parser("doctor")
    subparsers.add_parser("env")
    subparsers.add_parser("build")
    subparsers.add_parser("ci")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    config = load_config(
        args.root,
        args.config,
        environment_file=args.env_file,
        secrets_file=args.secrets_file,
        ci=args.ci,
    )
    loader = ScenarioLoader(config)
    scenarios = loader.load()

    if args.command == "list":
        selected = _select(args, scenarios)
        for scenario in selected:
            print(f"{scenario.id}\t{scenario.category}\t{scenario.title}")
        return 0

    if args.command == "validate":
        validator = ScenarioValidator()
        issues = [issue for scenario in _select(args, scenarios) for issue in validator.validate(scenario)]
        for issue in issues:
            source = f"{issue.source}: " if issue.source else ""
            print(f"{issue.severity}: {source}{issue.message}")
        print(f"validated {len(_select(args, scenarios))} scenarios")
        return 1 if any(issue.severity == "error" for issue in issues) else 0

    if args.command == "dry-run":
        result = VerificationOrchestrator(config).dry_run(_select(args, scenarios))
        print(SummaryReporter().render(result))
        return 0

    if args.command == "execute":
        result = VerificationOrchestrator(config).execute(_select(args, scenarios))
        print(SummaryReporter().render(result))
        return 0

    if args.command == "report":
        result = VerificationOrchestrator(config).dry_run(_select(args, scenarios))
        print(MarkdownReporter().render(result))
        print(JSONReporter().render(result))
        return 0

    print(f"{args.command}: scaffold command registered; implementation pending")
    return 0


def _add_filters(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--scenario-id", action="append", default=[])
    parser.add_argument("--tag", action="append", default=[])
    parser.add_argument("--component", action="append", default=[])
    parser.add_argument("--platform", action="append", default=[])
    parser.add_argument("--locale", action="append", default=[])
    parser.add_argument("--automation-level", action="append", default=[])
    parser.add_argument("--build-type", action="append", default=[])


def _select(args: argparse.Namespace, scenarios):
    return ScenarioScheduler().select(
        scenarios,
        ids=set(args.scenario_id or ()),
        tags=set(args.tag or ()),
        components=set(args.component or ()),
    )


if __name__ == "__main__":
    raise SystemExit(main())
