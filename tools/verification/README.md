# DJConnect Verification Harness

Status: core plus execution environment, planning engine and runtime release
Scope owner: `pcvantol/djconnect`  
Builds on: `docs/verification/00_VERIFICATION_VISION.md`,
`docs/verification/01_VERIFICATION_ARCHITECTURE.md` and
`docs/verification/02_SCENARIO_SCHEMA.md`
Runtime version: `0.2.0`

Clean verification sessions should start with
`BOOTSTRAP_CODEX_VERIFICATION.md` and `PROMPT_INDEX.md`.

The Verification Harness is the reusable execution framework for DJConnect
platform scenarios. Scenarios describe platform behavior. The harness loads,
validates, schedules, qualifies, executes through adapters, collects evidence
and reports readiness. Future phases extend this scaffold instead of running
verification scenarios directly.

The generic runtime can also be released as a Docker image. That image contains
only the reusable verification engine, not DJConnect product scenarios,
artifacts, secrets or lab state.

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

Runtime metadata is recorded in environment snapshots, run metadata and summary
reports under `verification_runtime`. Execution summaries also include
`execution_summary.total_execution_seconds` plus total, executed and status
bucket counts.

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
python -m tools.verification.cli lab ha metadata
python -m tools.verification.cli lab ha start
python -m tools.verification.cli lab ha doctor
python -m tools.verification.cli docker release
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
- `docker`

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

## Runtime Docker Release

Build the generic Verification Platform runtime image from the repository root:

```bash
python -m tools.verification.cli docker release \
  --image ghcr.io/pcvantol/djconnect-verification-platform \
  --release-sha "$(git rev-parse HEAD)"
```

The release helper builds `docker/verification-platform/Dockerfile` and tags
the image with:

- `<runtime-version>`
- `<runtime-version>-<short-release-sha>`
- `sha-<short-release-sha>`

For the current runtime this means tags such as `0.2.0`,
`0.2.0-<short-sha>` and `sha-<short-sha>`.

Smoke test an image with:

```bash
docker run --rm ghcr.io/pcvantol/djconnect-verification-platform:0.2.0 config
```

Run repository scenarios by mounting a checkout and invoking the runtime from
that checkout. Keep scenarios, product source, secrets and artifacts outside the
released image:

```bash
docker run --rm \
  -v "$PWD:/workspace:ro" \
  -v "$PWD/artifacts/verification:/artifacts/verification" \
  ghcr.io/pcvantol/djconnect-verification-platform:0.2.0 \
  --config /workspace/verification-config.json validate
```

Use `--dry-run` when preparing release metadata without building locally.

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
- Runtime Docker images must stay generic: no DJConnect scenario catalog,
  product repository checkout, Home Assistant config, Apple artifacts, secrets
  or test results are baked into the image.
