"""CLI entry point for the DJConnect Verification Harness."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .artifacts import ArtifactManager
from .config import load_config
from .configuration import SecretLoader
from .orchestrator import VerificationOrchestrator
from .reporters import JSONReporter, JUnitReporter, MarkdownReporter, SummaryReporter
from .scenarios import ScenarioLoader, ScenarioScheduler, ScenarioValidator


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="verification")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--config", type=Path)
    parser.add_argument("--env-file", type=Path)
    parser.add_argument("--secrets-file", type=Path)
    parser.add_argument("--ci", action="store_true")
    parser.add_argument("--dry-run", action="store_true")

    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("list", "validate", "dry-run", "execute", "report"):
        sub = subparsers.add_parser(command)
        _add_filters(sub)
    report = subparsers.choices["report"]
    report.add_argument("--format", choices=("markdown", "json", "junit"), default="markdown")
    clean = subparsers.add_parser("clean")
    clean.add_argument("--apply", action="store_true")
    prepare = subparsers.add_parser("prepare")
    _add_filters(prepare)
    restore = subparsers.add_parser("restore")
    restore.add_argument("--apply", action="store_true")
    restore.add_argument("--allow-destructive", action="store_true")
    subparsers.add_parser("doctor")
    subparsers.add_parser("env")
    subparsers.add_parser("schema")
    subparsers.add_parser("config")
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
        dry_run=args.dry_run,
    )
    loader = ScenarioLoader(config)
    scenarios = loader.load()
    orchestrator = VerificationOrchestrator(config)

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
        result = orchestrator.dry_run(_select(args, scenarios))
        print(SummaryReporter().render(result))
        return 0

    if args.command == "execute":
        result = orchestrator.execute(_select(args, scenarios))
        print(SummaryReporter().render(result))
        return 0

    if args.command == "report":
        result = orchestrator.dry_run(_select(args, scenarios))
        reporter = {
            "markdown": MarkdownReporter(),
            "json": JSONReporter(),
            "junit": JUnitReporter(),
        }[args.format]
        print(reporter.render(result))
        return 0

    if args.command == "doctor":
        for gate in orchestrator.doctor():
            print(f"{gate.state.value}\t{gate.name}\t{gate.message}")
        return 0

    if args.command == "env":
        print(json.dumps(orchestrator.snapshot().__dict__, indent=2, sort_keys=True))
        return 0

    if args.command == "clean":
        paths = ArtifactManager(config.evidence_dir).clean(dry_run=not args.apply)
        mode = "would remove" if not args.apply else "removed"
        print(f"{mode} {len(paths)} evidence entries")
        return 0

    if args.command == "prepare":
        print(json.dumps(orchestrator.prepare_environment(_select(args, scenarios)), indent=2, sort_keys=True, default=str))
        return 0

    if args.command == "restore":
        gate = orchestrator.restore_environment(
            dry_run=not args.apply,
            allow_destructive=args.allow_destructive,
        )
        print(json.dumps(gate.__dict__, indent=2, sort_keys=True, default=str))
        return 0

    if args.command == "schema":
        schema = config.root / "verification/schema/scenario.schema.json"
        print(schema.read_text(encoding="utf-8") if schema.exists() else "{}")
        return 0

    if args.command == "config":
        secrets = SecretLoader().load(config.secrets_file)
        print(
            json.dumps(
                {
                    "root": str(config.root),
                    "scenario_paths": [str(path) for path in config.scenario_paths],
                    "evidence_dir": str(config.evidence_dir),
                    "report_dir": str(config.report_dir),
                    "ci": config.ci,
                    "secrets": {"source": secrets.source, "names": list(secrets.names)},
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    parser.error(f"unsupported command: {args.command}")
    return 2


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
