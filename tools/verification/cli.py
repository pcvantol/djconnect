"""CLI entry point for the DJConnect Verification Harness."""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict
from pathlib import Path

from .config import load_config


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="verification")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--config", type=Path)
    parser.add_argument("--env-file", type=Path)
    parser.add_argument("--secrets-file", type=Path)
    parser.add_argument("--ci", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--test-mode", choices=("stable", "future_beta"), default=None)
    parallel_group = parser.add_mutually_exclusive_group()
    parallel_group.add_argument("--parallel", action="store_true")
    parallel_group.add_argument("--no-parallel", action="store_true")
    parser.add_argument("--workers", type=int, default=None)
    parser.add_argument("--ha-adapter", action="store_true")
    parser.add_argument("--apple-adapter", action="store_true")
    parser.add_argument("--raspberry-pi-adapter", action="store_true")
    parser.add_argument("--windows-adapter", action="store_true")

    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("list", "validate", "dry-run", "execute", "report"):
        sub = subparsers.add_parser(command)
        _add_filters(sub)
    report = subparsers.choices["report"]
    report.add_argument("--format", choices=("markdown", "json", "junit"), default="markdown")
    plan = subparsers.add_parser("plan")
    _add_filters(plan)
    plan.add_argument("--policy", default=None)
    plan.add_argument("--strategy", default="smoke")
    plan.add_argument("--format", choices=("summary", "json"), default="summary")
    clean = subparsers.add_parser("clean")
    clean.add_argument("--apply", action="store_true")
    prepare = subparsers.add_parser("prepare")
    _add_filters(prepare)
    restore = subparsers.add_parser("restore")
    restore.add_argument("--apply", action="store_true")
    restore.add_argument("--allow-destructive", action="store_true")
    doctor = subparsers.add_parser("doctor")
    doctor.add_argument("--environment", choices=("ha-docker",), default=None)
    doctor.add_argument("--ha-container", default=None)
    doctor.add_argument("--ha-port", type=int, default=None)
    doctor.add_argument("--fix-auth", action="store_true")
    doctor.add_argument("--interactive-auth", action="store_true")
    investigate = subparsers.add_parser("investigate")
    investigate.add_argument("run_id")
    investigate.add_argument("--scenario")
    investigate.add_argument("--failure")
    runs = subparsers.add_parser("runs")
    run_subparsers = runs.add_subparsers(dest="runs_command", required=True)
    run_subparsers.add_parser("list")
    for command in ("show", "verify", "evidence"):
        sub = run_subparsers.add_parser(command)
        sub.add_argument("run_id")
    lab = subparsers.add_parser("lab")
    lab_subparsers = lab.add_subparsers(dest="lab_target", required=True)
    ha_lab = lab_subparsers.add_parser("ha")
    ha_lab.add_argument("lab_command", choices=("build", "start", "stop", "restart", "recreate", "fresh", "clean", "destroy", "bootstrap-auth", "doctor", "metadata"))
    ha_lab.add_argument("--allow-destructive", action="store_true")
    apple = subparsers.add_parser("apple")
    apple_subparsers = apple.add_subparsers(dest="apple_command", required=True)
    apple_subparsers.add_parser("qualify-runtime")
    apple_subparsers.add_parser("ensure-ios-runtime")
    apple_prepare = apple_subparsers.add_parser("prepare-qualification-config")
    apple_prepare.add_argument("--apple-repo", type=Path, default=None)
    docker = subparsers.add_parser("docker")
    docker_subparsers = docker.add_subparsers(dest="docker_command", required=True)
    docker_release = docker_subparsers.add_parser("release")
    docker_release.add_argument("--image", default=None)
    docker_release.add_argument("--base-image", default=None)
    docker_release.add_argument("--release-sha", default=None)
    docker_release.add_argument("--push", action="store_true")
    docker_release.add_argument("--dry-run", action="store_true")
    coverage = subparsers.add_parser("coverage")
    coverage_subparsers = coverage.add_subparsers(dest="coverage_command", required=True)
    coverage_ingest = coverage_subparsers.add_parser("ingest")
    coverage_ingest.add_argument("report", type=Path)
    coverage_ingest.add_argument("--format", required=True, choices=("cobertura", "lcov", "apple-xccov"))
    coverage_ingest.add_argument("--repository", default="pcvantol/djconnect")
    coverage_ingest.add_argument("--commit-sha", default=None)
    coverage_ingest.add_argument("--expected-commit-sha", default=None)
    coverage_ingest.add_argument("--scope", default="repository")
    coverage_ingest.add_argument("--run-id", default="coverage")
    coverage_ingest.add_argument("--write-evidence", action="store_true")
    coverage_ingest.add_argument("--output", choices=("json", "markdown"), default="json")
    subparsers.add_parser("env")
    subparsers.add_parser("schema")
    subparsers.add_parser("config")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    _load_env_file(args.env_file)

    if args.command == "apple":
        root = args.root
        if args.apple_command == "qualify-runtime":
            from .apple_runtime_qualification import AppleRuntimeQualification, result_to_json

            result = AppleRuntimeQualification(root).run()
            print(result_to_json(result))
            return 0 if result.state == "PASS" else 1
        if args.apple_command == "ensure-ios-runtime":
            from .apple_toolchain import AppleToolchainMaintenance, result_to_json

            result = AppleToolchainMaintenance(root).ensure_ios_runtime()
            print(result_to_json(result))
            return 0 if result.state == "PASS" else 1
        if args.apple_command == "prepare-qualification-config":
            from .apple_operator_config import AppleQualificationConfigPreparer, result_to_json

            result = AppleQualificationConfigPreparer(root, apple_repo=args.apple_repo).prepare()
            print(result_to_json(result))
            return 0 if result.state == "READY" else 1

    config = load_config(
        args.root,
        args.config,
        environment_file=args.env_file,
        secrets_file=args.secrets_file,
        ci=args.ci,
        dry_run=args.dry_run,
        overrides=_cli_overrides(args),
    )
    from .scenarios import ScenarioLoader

    loader = ScenarioLoader(config)
    scenarios = loader.load()
    adapters = None
    if args.ha_adapter or args.apple_adapter or args.raspberry_pi_adapter or args.windows_adapter:
        from .adapters import AdapterRegistry

        adapters = AdapterRegistry()
        if args.ha_adapter:
            from .home_assistant_adapter import HomeAssistantVerificationAdapter

            adapters.register(HomeAssistantVerificationAdapter(_home_assistant_adapter_config(config.root)))
        if args.apple_adapter:
            from .apple_adapter import AppleAdapterConfig, AppleVerificationAdapter

            adapters.register(AppleVerificationAdapter(AppleAdapterConfig.from_environment(config.root)))
        if args.raspberry_pi_adapter:
            from .raspberry_pi_adapter import RaspberryPiAdapterConfig, RaspberryPiVerificationAdapter

            adapters.register(RaspberryPiVerificationAdapter(RaspberryPiAdapterConfig.from_environment(config.root)))
        if args.windows_adapter:
            from .windows_adapter import WindowsAdapterConfig, WindowsVerificationAdapter

            adapters.register(WindowsVerificationAdapter(WindowsAdapterConfig.from_environment(config.root)))
    from .orchestrator import VerificationOrchestrator

    orchestrator = VerificationOrchestrator(config, adapters=adapters)

    if args.command == "list":
        selected = _select(args, scenarios)
        for scenario in selected:
            print(f"{scenario.id}\t{scenario.category}\t{scenario.title}")
        return 0

    if args.command == "validate":
        from .scenarios import ScenarioValidator

        validator = ScenarioValidator(config.root)
        issues = [issue for scenario in _select(args, scenarios) for issue in validator.validate(scenario)]
        for issue in issues:
            source = f"{issue.source}: " if issue.source else ""
            print(f"{issue.severity}: {source}{issue.message}")
        print(f"validated {len(_select(args, scenarios))} scenarios")
        return 1 if any(issue.severity == "error" for issue in issues) else 0

    if args.command == "dry-run":
        from .reporters import SummaryReporter

        result = orchestrator.dry_run(_select(args, scenarios))
        print(SummaryReporter().render(result))
        return 0

    if args.command == "execute":
        from .reporters import SummaryReporter

        result = orchestrator.execute(_select(args, scenarios))
        print(SummaryReporter().render(result))
        return 0

    if args.command == "report":
        from .reporters import JSONReporter, JUnitReporter, MarkdownReporter

        result = orchestrator.dry_run(_select(args, scenarios))
        reporter = {
            "markdown": MarkdownReporter(),
            "json": JSONReporter(),
            "junit": JUnitReporter(),
        }[args.format]
        print(reporter.render(result))
        return 0

    if args.command == "plan":
        from .planning import VerificationPlanningEngine

        planning_engine = VerificationPlanningEngine(config)
        plan = planning_engine.plan(
            _select(args, scenarios),
            policy_id=args.policy,
            strategy_id=args.strategy,
        )
        if args.format == "json":
            print(json.dumps(asdict(plan), indent=2, sort_keys=True, default=str))
        else:
            print(
                "\n".join(
                    [
                        f"plan_id: {plan.plan_id}",
                        f"strategy: {plan.strategy}",
                        f"policy: {plan.policy}",
                        f"cases: {plan.coverage.case_count}",
                        f"batches: {len(plan.batches)}",
                        f"estimated_seconds: {plan.estimated_seconds}",
                    ]
                )
            )
        return 0

    if args.command == "doctor":
        if args.environment == "ha-docker":
            from .environment.docker_ha import HADockerDiscovery

            expected_name = args.ha_container or os.getenv("DJCONNECT_VERIFICATION_HA_CONTAINER")
            expected_port = args.ha_port or int(os.getenv("DJCONNECT_VERIFICATION_HA_PORT", "8123"))
            gate = HADockerDiscovery(config.root).qualify(expected_port=expected_port, expected_name=expected_name)
            print(json.dumps(gate.__dict__, indent=2, sort_keys=True, default=str))
            return 0 if gate.passed else 1
        if args.fix_auth or args.interactive_auth:
            gate = orchestrator.execution_environment.github.auth_status(
                fix_auth=args.fix_auth or args.interactive_auth,
                interactive=args.interactive_auth or None,
            )
            print(f"{gate.state.value}\t{gate.name}\t{gate.message}")
            return 0 if gate.passed else 1
        for gate in orchestrator.doctor():
            print(f"{gate.state.value}\t{gate.name}\t{gate.message}")
        return 0

    if args.command == "investigate":
        from .core.investigator import VerificationInvestigator, investigation_to_dicts
        from .evidence import RunStore

        run_dir = config.evidence_dir / args.run_id
        bundle_path = run_dir / "summary.json"
        if not bundle_path.exists():
            print(json.dumps({"error": "run_not_found", "run_id": args.run_id}, indent=2, sort_keys=True))
            return 1
        results = VerificationInvestigator().investigate_file(
            bundle_path,
            scenario_id=args.scenario,
            failure_id=args.failure,
        )
        RunStore(config.evidence_dir).write_json(args.run_id, "investigation.json", investigation_to_dicts(results))
        print(json.dumps(investigation_to_dicts(results), indent=2, sort_keys=True))
        return 0

    if args.command == "runs":
        from .evidence import RunStore

        store = RunStore(config.evidence_dir)
        if args.runs_command == "list":
            print(json.dumps({"runs": store.list_runs()}, indent=2, sort_keys=True))
            return 0
        if args.runs_command == "show":
            print(json.dumps(store.show(args.run_id), indent=2, sort_keys=True))
            return 0
        if args.runs_command == "verify":
            result = store.verify(args.run_id)
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0 if result.get("ok") else 1
        if args.runs_command == "evidence":
            path = config.evidence_dir / args.run_id / "evidence-index.json"
            print(path.read_text(encoding="utf-8") if path.exists() else "{}")
            return 0 if path.exists() else 1

    if args.command == "lab":
        from .environment.docker_ha import HALocalVerificationLab

        lab = HALocalVerificationLab(config.root)
        if args.lab_target == "ha":
            if args.lab_command == "doctor":
                gate = lab.qualify()
            elif args.lab_command == "metadata":
                print(json.dumps(lab.metadata(), indent=2, sort_keys=True, default=str))
                return 0
            else:
                gate = lab.lifecycle(args.lab_command, allow_destructive=args.allow_destructive)
            print(json.dumps(gate.__dict__, indent=2, sort_keys=True, default=str))
            return 0 if gate.passed else 1

    if args.command == "docker":
        if args.docker_command == "release":
            from .docker_release import main as docker_release_main

            release_args = ["--root", str(config.root)]
            if args.image:
                release_args.extend(["--image", args.image])
            if args.base_image:
                release_args.extend(["--base-image", args.base_image])
            if args.release_sha:
                release_args.extend(["--release-sha", args.release_sha])
            if args.push:
                release_args.append("--push")
            if args.dry_run:
                release_args.append("--dry-run")
            return docker_release_main(release_args)

    if args.command == "coverage":
        if args.coverage_command == "ingest":
            from .coverage import CoveragePipeline
            from .coverage.reporting import CoverageJSONReporter, CoverageMarkdownReporter

            commit_sha = args.commit_sha or _git_sha(config.root)
            qualification = CoveragePipeline().ingest(
                args.report,
                coverage_format=args.format,
                repository=args.repository,
                commit_sha=commit_sha,
                scope=args.scope,
                expected_commit_sha=args.expected_commit_sha,
            )
            investigation = CoveragePipeline().investigator.investigate(qualification)
            if args.write_evidence:
                CoveragePipeline().write_evidence(config.evidence_dir, args.run_id, qualification)
            reporter = CoverageJSONReporter() if args.output == "json" else CoverageMarkdownReporter()
            print(reporter.render(qualification, investigation))
            return 0 if qualification.validation.ok else 1

    if args.command == "env":
        print(json.dumps(orchestrator.snapshot().__dict__, indent=2, sort_keys=True))
        return 0

    if args.command == "clean":
        from .artifacts import ArtifactManager

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
        from .configuration import SecretLoader
        from .runtime import runtime_metadata

        secrets = SecretLoader().load(config.secrets_file)
        print(
            json.dumps(
                {
                    "root": str(config.root),
                    "scenario_paths": [str(path) for path in config.scenario_paths],
                    "evidence_dir": str(config.evidence_dir),
                    "report_dir": str(config.report_dir),
                    "ci": config.ci,
                    "test_mode": config.test_mode,
                    "parallel_execution": config.parallel_execution,
                    "parallel_workers": config.parallel_workers,
                    "verification_runtime": runtime_metadata(),
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


def _cli_overrides(args: argparse.Namespace) -> dict[str, str] | None:
    overrides: dict[str, str] = {}
    if args.test_mode:
        overrides["test_mode"] = args.test_mode
    if args.parallel:
        overrides["parallel_execution"] = "true"
    if args.no_parallel:
        overrides["parallel_execution"] = "false"
    if args.workers is not None:
        overrides["parallel_workers"] = str(args.workers)
    return overrides or None


def _select(args: argparse.Namespace, scenarios):
    from .scenarios import ScenarioScheduler

    return ScenarioScheduler().select(
        scenarios,
        ids=set(args.scenario_id or ()),
        tags=set(args.tag or ()),
        components=set(args.component or ()),
    )


def _home_assistant_adapter_config(root: Path) -> "HomeAssistantAdapterConfig":
    from .environment.docker_ha import HALocalVerificationLab
    from .home_assistant_adapter import HomeAssistantAdapterConfig

    explicit = HomeAssistantAdapterConfig.from_environment(root)
    if os.getenv("DJCONNECT_VERIFICATION_HA_TOKEN"):
        return explicit
    lab_config = HALocalVerificationLab(root).adapter_config()
    return HomeAssistantAdapterConfig(
        base_url=os.getenv("DJCONNECT_VERIFICATION_HA_URL", str(lab_config["base_url"])).rstrip("/"),
        token=str(lab_config.get("token") or ""),
        storage_dir=explicit.storage_dir or lab_config.get("storage_dir"),
        log_path=explicit.log_path or lab_config.get("log_path"),
        timeout_seconds=explicit.timeout_seconds,
        allow_destructive=explicit.allow_destructive,
        fixture_namespace=explicit.fixture_namespace,
    )


def _load_env_file(path: Path | None) -> None:
    if path is None or not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        if not key or key in os.environ:
            continue
        os.environ[key] = _unquote_env_value(value.strip())


def _unquote_env_value(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def _git_sha(root: Path) -> str:
    import subprocess

    try:
        return subprocess.check_output(("git", "rev-parse", "HEAD"), cwd=root, text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


if __name__ == "__main__":
    raise SystemExit(main())
