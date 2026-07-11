# DJConnect Verification Harness

Status: core plus execution environment, planning engine and runtime release
Scope owner: `pcvantol/djconnect`  
Builds on: `docs/verification/00_VERIFICATION_VISION.md`,
`docs/verification/01_VERIFICATION_ARCHITECTURE.md` and
`docs/verification/02_SCENARIO_SCHEMA.md`
Runtime version: `1.0.0`

Clean verification sessions should start with
`BOOTSTRAP_CODEX_VERIFICATION.md` and `PROMPT_INDEX.md`.

Verification Platform release notes live in
`tools/verification/RELEASE_NOTES.md`.

The Verification Harness is the reusable execution framework for DJConnect
platform scenarios. Scenarios describe platform behavior. The harness loads,
validates, schedules, qualifies, executes through adapters, collects evidence
and reports readiness. Future phases extend this scaffold instead of running
verification scenarios directly.

The generic runtime can also be released as a Docker image. That image contains
only the reusable verification engine, not DJConnect product scenarios,
artifacts, secrets or lab state.

## Software Assurance Integration

The Verification Runtime is a versioned product consumed by the Software
Assurance Platform.

Software Assurance may validate runtime quality signals, runtime provenance,
runtime metadata, evidence references and report compatibility. It does not
become the runtime and does not redefine scenario behaviour, adapter ownership
or behavioural qualification.

Canonical integration documents:

- `SOFTWARE_ASSURANCE_INTEGRATION.md`
- `SOFTWARE_ASSURANCE_EXECUTION_MODEL.md`
- `SOFTWARE_ASSURANCE_PLATFORM_HEALTH.md`
- `SOFTWARE_ASSURANCE_REPOSITORY_MODEL.md`

The Docker image is the portability layer for GitHub Actions runners. Hosted
GitHub runners should use it for engine smoke tests, scenario validation,
planning, schema/report checks and non-mutating dry-runs. Live labs, Apple
simulators, hardware, SSH, serial devices, signing and destructive cleanup need
self-hosted runners or approved local labs with explicit capabilities.

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

## Functional Help

Use the Verification Harness when you need reproducible proof of DJConnect
platform behavior. The framework answers four practical questions:

- Which scenarios are in scope for this run?
- Is the repository, host, CI state and runtime safe enough to execute them?
- Which adapter actions were executed, with which evidence?
- Is the resulting platform status ready, blocked or warning-only?

Common workflows:

| Goal | Start with | Then use |
| --- | --- | --- |
| See available scenarios | `list` | Add `--tag`, `--component` or scenario IDs to narrow scope. |
| Check scenario shape | `validate` | Fix catalog/schema issues before planning or execution. |
| Preview a run | `dry-run` | Confirm selected scenarios without mutating lab state. |
| Build an execution plan | `plan --strategy smoke --format json` | Inspect matrix, policy, data profile and batch expansion. |
| Capture environment state | `prepare` | Review run identity, toolchain, dependencies, cleanup and host readiness. |
| Execute HA scenarios | `--ha-adapter execute --scenario-id <id>` | Use only after qualification gates pass. |
| Inspect a run | `runs list`, `runs verify <run-id>` | Confirm evidence files and result metadata. |
| Investigate failures | `investigate <run-id>` | Classify owner, confidence, blocking status and rerun scope. |
| Check local lab readiness | `doctor --environment ha-docker` | Use before starting or mutating a Home Assistant lab. |
| Build/publish runtime | `docker release` | Build the generic engine image, then smoke-test before publish. |

Result summaries always report the total scenario count, executed count,
aggregate status, per-status buckets and total execution time. Machine-readable
metadata records `verification_runtime`, parallel worker settings and
`execution_summary`.

Failure handling:

- A failed gate means the run must stop before mutation.
- Product bugs, scenario defects, environment issues and framework defects must
  be classified separately.
- Scenarios define expected behavior; adapters only execute and collect
  evidence.
- Secrets are loaded by name and must never appear in logs, reports or
  diagnostics.

## Installation

### Local Checkout

Run the framework from a checked-out DJConnect repository. The current local
runtime is source-based; no wheel or package install is required.

```bash
cd /path/to/djconnect
python3 -m venv .venv-verification
source .venv-verification/bin/activate
python -m pip install --upgrade pip
python -m pip install PyYAML==6.0.2 pytest
python -m tools.verification.cli config
```

`PyYAML` matches the generic Docker runtime dependency. `pytest` is needed only
for dogfooding the framework tests:

```bash
python -m pytest tests/verification
```

For local Home Assistant lab or Docker release work, Docker Desktop must be
installed and available to the shell:

```bash
docker version
```

For Apple runtime qualification, install Xcode and command-line tools first and
make sure `xcodebuild` and `xcrun simctl` are available. Stable verification
uses the latest eligible stable iOS simulator runtime; beta runtimes belong in
`DJCONNECT_VERIFICATION_TEST_MODE=future_beta`.

The Apple runtime qualification includes an explicit `xcode_account` gate. It
uses `xcodebuild -allowProvisioningUpdates` to verify that Xcode is signed in to
an Apple developer account before release-equivalent build or live runtime
primitives can run. VPB-037 inventory on July 11, 2026 resolved the Xcode 27 beta
development signing path to team `ZEML4LPXH4`, bundle `dev.djconnect.ios`,
identity `Apple Development: Peter van Tol (4R93ZR43D5)` and profile
`iOS Team Provisioning Profile: dev.djconnect.ios`
(`00d91f4f-5a9e-4f13-8790-2393253068e7`). App Store/TestFlight distribution
signing is intentionally deferred until release v1.0 readiness and is
non-blocking for current platform verification.

### Docker Runtime

The generic runtime image can be built locally or pulled from a registry once a
tagged image has been published:

```bash
python -m tools.verification.cli docker release \
  --image pcvantol/djconnect-verification-platform \
  --release-sha "$(git rev-parse HEAD)"

docker run --rm pcvantol/djconnect-verification-platform:1.0.0 config
```

Published Verification Platform releases are authoritative. When verification
framework code changes, cut a new stable runtime release through the GitHub CI
Docker release workflow, let that workflow build, verify and push the image to
Docker Hub, and then consume the newly published Docker Hub tag. Do not treat a
local build as a release substitute.

Every live verification run starts by pulling the configured Verification
Platform runtime image from Docker Hub. The default reference is
`pcvantol/djconnect-verification-platform:1.0.0`; override only with
`DJCONNECT_VERIFICATION_PLATFORM_IMAGE` and `DJCONNECT_VERIFICATION_PLATFORM_TAG`
when intentionally qualifying another published image. If the pull fails, the
run stops before scenario execution.

When using Docker, mount the repository and artifacts from outside the image.
The image is engine-only and must not contain product scenarios, secrets or run
evidence.

### GitHub Runner

For hosted GitHub runners, use the Docker runtime for non-mutating jobs such as
engine smoke tests, scenario validation, planning and report/schema checks. The
workflow should provide the checkout and upload `artifacts/verification/` as a
workflow artifact.

Use a self-hosted runner or approved local lab for jobs that need Home
Assistant Docker labs, Apple simulators, hardware, SSH/serial, signing material
or destructive cleanup. Those jobs must advertise and gate on their required
capabilities before execution.

The repository workflow `.github/workflows/verification-platform-docker-release.yml`
publishes the generic runtime image to Docker Hub. It requires these repository
secrets:

- `DOCKERHUB_USERNAME`
- `DOCKERHUB_TOKEN`

The workflow can be started manually with `workflow_dispatch` or by pushing a
tag named `verification-platform-v<version>`. It runs `tests/verification`,
checks the Docker release command with `--dry-run`, builds the image, verifies
OCI labels, smoke-tests `docker run ... config`, then publishes the verified
runtime tags to the configured image repository.

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
  --image pcvantol/djconnect-verification-platform \
  --release-sha "$(git rev-parse HEAD)"
```

The release helper builds `docker/verification-platform/Dockerfile` and tags
the image with:

- `<runtime-version>`
- `<runtime-version>-<short-release-sha>`
- `sha-<short-release-sha>`

For the current runtime this means tags such as `1.0.0`,
`1.0.0-<short-sha>` and `sha-<short-sha>`.

Smoke test an image with:

```bash
docker run --rm pcvantol/djconnect-verification-platform:1.0.0 config
```

Run repository scenarios by mounting a checkout and invoking the runtime from
that checkout. Keep scenarios, product source, secrets and artifacts outside the
released image:

```bash
docker run --rm \
  -v "$PWD:/workspace:ro" \
  -v "$PWD/artifacts/verification:/artifacts/verification" \
  pcvantol/djconnect-verification-platform:1.0.0 \
  --config /workspace/verification-config.json validate
```

Use `--dry-run` when preparing release metadata without building locally.

In GitHub Actions, the workflow should provide the checkout, mount or pass the
workspace to the container, upload `artifacts/verification/`, and record GitHub
run/job metadata beside `verification_runtime` and `execution_summary`.

Consumers must pull the latest published stable Verification Platform image
from Docker Hub before running Docker-based verification:

```bash
docker pull pcvantol/djconnect-verification-platform:1.0.0
docker run --rm pcvantol/djconnect-verification-platform:1.0.0 config
```

Do not silently fall back to a stale local image or ad hoc local build. If the
Docker Hub pull fails, block the Docker-based verification run and fix
publishing, authentication or network access first.

Update `tools/verification/RELEASE_NOTES.md` for every runtime release. Keep
those notes scoped to the generic engine and leave DJConnect product changes in
their owning changelogs.

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
