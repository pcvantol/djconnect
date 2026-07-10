# DJConnect Verification Harness

Status: core plus execution environment and planning engine
Scope owner: `pcvantol/djconnect`  
Builds on: `docs/verification/00_VERIFICATION_VISION.md`,
`docs/verification/01_VERIFICATION_ARCHITECTURE.md` and
`docs/verification/02_SCENARIO_SCHEMA.md`

Clean verification sessions should start with
`BOOTSTRAP_CODEX_VERIFICATION.md` and `PROMPT_INDEX.md`.

The Verification Harness is the reusable execution framework for DJConnect
platform scenarios. Scenarios describe platform behavior. The harness loads,
validates, schedules, qualifies, executes through adapters, collects evidence
and reports readiness. Future phases extend this scaffold instead of running
verification scenarios directly.

## Pipeline

```text
Scenario Loader
  -> Repository Hygiene Gate
  -> Verification Execution Environment
  -> Build Qualification
  -> Verification Planning Engine
  -> Verification Orchestrator
  -> Platform Adapters
  -> Evidence Collector
  -> Report Generator
  -> Platform Readiness
```

## Current Scope

This package implements the framework shape and the platform-neutral execution
environment:

- scenario loading from the canonical catalog/examples;
- schema-oriented validation checks;
- scheduler filters for IDs, tags and components;
- repository hygiene, toolchain discovery, dependency inspection and GitHub
  workflow/status inspection;
- run identity and environment snapshots;
- cleanup planning and restore operations;
- adapter interface and adapter registry;
- Home Assistant adapter primitives for the first profile scenario set;
- planning engine for policies, modes, matrix profiles, data profiles,
  resource plans, environment plans and execution batches;
- evidence, result and reporter models;
- CLI command surface for future execution.

It implements the first Home Assistant runtime adapter and does not own product
assertions.

## CLI

Run with Python while the command is a local scaffold:

```bash
python -m tools.verification.cli list
python -m tools.verification.cli validate
python -m tools.verification.cli dry-run --scenario-id PROFILE-001
python -m tools.verification.cli --ha-adapter execute --scenario-id PROFILE-001
python -m tools.verification.cli report --tag localization
python -m tools.verification.cli plan --strategy smoke --format json
python -m tools.verification.cli doctor
python -m tools.verification.cli doctor --environment ha-docker
python -m tools.verification.cli doctor --environment ha-docker --ha-container homeassistant --ha-port 8123
python -m tools.verification.cli doctor --fix-auth
python -m tools.verification.cli prepare --scenario-id PROFILE-001
python -m tools.verification.cli restore
python -m tools.verification.cli runs list
python -m tools.verification.cli runs verify <run-id>
python -m tools.verification.cli investigate <run-id>
```

Reserved commands:

- `list`
- `validate`
- `dry-run`
- `execute`
- `report`
- `plan`
- `prepare`
- `restore`
- `clean`
- `doctor`
- `env`
- `evidence`
- `build`
- `ci`

Supported filters include scenario IDs, tags, components, platforms, locales,
automation level and build type. Only ID, tag and component filtering is active
in this scaffold.

## Configuration

Configuration is loaded from optional JSON plus CLI overrides. The config model
supports:

- scenario paths;
- evidence directory;
- report directory;
- environment file;
- secrets file;
- local developer mode;
- CI mode.
- execution environment overrides.

Secrets files are referenced only. They must not be committed.

## Extension Rules

- Adapters execute; they never define expected behavior.
- Expected behavior remains in the foundation, accepted baselines, contracts,
  ADRs and scenario catalog.
- Every executed scenario must follow the lifecycle: validation, setup,
  execution, assertions, evidence, cleanup, result and report.
- Evidence must be structured, redacted and reproducible.
- Build qualification must pass before real execution.
- Docker-based Home Assistant qualification must prove that the selected
  runtime is an intended verification/development instance before any mutation.
- GitHub CI qualification is exact-SHA based; missing auth, missing data and
  SHA mismatches are blocking qualification states.
- Run evidence is persisted under the configured evidence directory and can be
  listed, shown, verified and investigated through the CLI.
