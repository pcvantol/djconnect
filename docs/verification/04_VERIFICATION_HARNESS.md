# DJConnect Verification Harness

Status: implemented platform harness
Scope owner: `pcvantol/djconnect`
Related code: `tools/verification/`

## Purpose

The DJConnect Verification Harness is the permanent execution framework for
platform scenarios. It exists so future verification runs use one lifecycle,
one evidence model and one reporting path instead of direct scenario scripts.

The harness does not define product behavior. Scenarios, contracts, baselines,
ADRs and foundation documents define behavior. Adapters execute that behavior
through a platform surface.

## Architecture

```text
Scenario Loader
  -> Scenario Validator
  -> Scenario Scheduler
  -> Verification Planning Engine
  -> Repository Hygiene Gate
  -> Verification Execution Environment
  -> Build Qualification
  -> Verification Orchestrator
  -> Adapter Manager
  -> Evidence Manager
  -> Result Manager
  -> Reporters
  -> Platform Readiness
```

## Module Responsibilities

`config.py` loads local or CI configuration, scenario paths, evidence paths and
references to environment or secrets files.

`scenarios.py` loads scenario files, validates the required schema shape and
selects scenarios by ID, tag or component.

`verification/data/` owns canonical verification data catalogs, generator
metadata, security payloads, localization payloads and reusable data profiles.
Scenarios define behavior; data profiles define values.

`verification/modes/` owns canonical Verification Modes. Modes define which
quality attribute is evaluated without changing scenarios.

`verification/policies/` owns canonical Verification Policies. Policies select
which modes, matrix profiles, data profiles, platforms and build types should
run.

`verification/planning/` owns canonical planning metadata, strategies,
templates and examples. The implementation in `tools/verification/planning/`
expands scenarios, policies, matrix profiles, data profiles and modes into
machine-readable execution plans without executing anything.

`gates.py` owns compatibility access to reusable gates.

`environment/` owns the Verification Execution Environment: repository
hygiene, toolchain discovery, dependency inspection, GitHub CI inspection,
run identity, platform environment discovery, host preflight checks, cleanup
planning, environment snapshots and restore operations. It prepares the world
around execution but does not own scenario behavior or adapter assertions.

`orchestrator.py` owns the run lifecycle. It prepares the execution
environment, records run evidence, delegates scenario execution, aggregates
results and persists summaries.

`adapters.py` defines the common adapter interface. Adapters prepare, execute,
collect evidence and clean up, but never define expected results.

`home_assistant_adapter.py` implements the first thin runtime adapter. It
performs Home Assistant REST, websocket, service, storage snapshot, fixture and
metadata primitives for the first profile scenarios without embedding Profile,
Privacy, Music DNA or assertion logic.

`evidence.py` owns evidence and artifact helpers for logs, requests,
responses, screenshots, serial logs, environment metadata, artifacts,
checksums, timing, performance and future audio/video evidence.

`contracts.py` reserves localization, capability and contract validators.

`results.py` aggregates scenario results into a run result.

`reporters.py` renders Markdown, JSON, JUnit XML and summary output.

`cli.py` exposes the command surface for local and CI usage.

`execution/` owns scenario execution. It preserves scenario order in reported
results while allowing independent scenarios to run in sandboxed parallel
waves.

`runtime.py` owns the Verification Platform runtime identity. Every run,
environment snapshot, summary and machine-readable report records the
`djconnect-verification-platform` runtime name, runtime version and runtime
schema version.

Run summaries include a canonical `execution_summary` with total scenario
count, executed scenario count, aggregate status, per-status counts and total
execution time in seconds. Human summaries must report this in the form
`x of y tests executed, status z (...), total g.s`.

## Adapter Targets

The interface is designed for these adapters:

- Home Assistant;
- Apple;
- Windows Catalyst;
- Windows Native ARM64;
- Raspberry Pi;
- ESP32;
- Voice Endpoint;
- Website;
- Release;
- Spotify Direct;
- Music Assistant;
- Android future;
- Cloud future;
- Runtime future.

## CLI

Initial commands:

```bash
python -m tools.verification.cli list
python -m tools.verification.cli validate
python -m tools.verification.cli dry-run
python -m tools.verification.cli --ha-adapter execute --scenario-id PROFILE-001
python -m tools.verification.cli plan
python -m tools.verification.cli prepare
python -m tools.verification.cli restore
python -m tools.verification.cli report
python -m tools.verification.cli config
python -m tools.verification.cli apple ensure-ios-runtime
python -m tools.verification.cli apple qualify-runtime
```

Additional commands:

```bash
python -m tools.verification.cli doctor
python -m tools.verification.cli env
python -m tools.verification.cli clean
python -m tools.verification.cli schema
python -m tools.verification.cli runs list
```

Filters are designed for scenario IDs, tags, platform, locale, automation
level, build type and component.

## Installation

The local harness is source-based and runs from a checked-out repository:

```bash
cd /path/to/djconnect
python3 -m venv .venv-verification
source .venv-verification/bin/activate
python -m pip install --upgrade pip
python -m pip install PyYAML==6.0.2 pytest
python -m tools.verification.cli config
```

`PyYAML` keeps local runs aligned with the generic Docker runtime dependency.
`pytest` is required for framework dogfooding:

```bash
python -m pytest tests/verification
```

Additional host tools are capability-specific. Docker is required for Home
Assistant lab work and runtime image releases. Xcode plus command-line tools
are required for Apple simulator qualification. GitHub Actions hosted runners
should use the Docker runtime for non-mutating verification jobs; labs,
simulators, hardware, signing and destructive cleanup require self-hosted
runners or approved local labs with explicit capabilities.

Parallel scenario execution is enabled by default. The harness detects local
CPU capacity dynamically, using Apple Silicon performance/efficiency core
metadata when available and falling back to logical CPU count otherwise. The
worker count can be overridden or disabled:

```bash
python -m tools.verification.cli --workers 12 execute
python -m tools.verification.cli --no-parallel execute
```

Equivalent environment controls:

```text
DJCONNECT_VERIFICATION_PARALLEL=0
DJCONNECT_VERIFICATION_PARALLEL_WORKERS=12
```

Parallel waves remain dependency-aware and resource-aware. Scenarios with
`depends_on` or `dependencies` wait for their prerequisites. Scenarios sharing
`requires.exclusive_resources` are never placed in the same wave.

Before local lab runners start, host preflight blocks unsafe runs when the
target lab port is already occupied, conflicting Home Assistant/DJConnect
processes are detected, or the lab filesystem does not have enough free disk
space.

Stable verification is the default test mode. Future/beta runtime evidence is
explicitly separated:

```text
DJCONNECT_VERIFICATION_TEST_MODE=future_beta
```

In stable mode, Apple runtime qualification uses the latest eligible stable iOS
simulator runtime. Beta iOS runtimes, Xcode beta and Home Assistant beta are
advisory early-warning routes and do not replace stable release qualification.

The runtime version is part of verification evidence. Operators can inspect it
before execution with:

```bash
python -m tools.verification.cli config
```

Reports and summaries expose it under `verification_runtime`.

## Docker Runtime Release

The Verification Platform runtime can be released as a generic Docker image.
The image contains only the engine components under `tools/verification`; it
does not include DJConnect repository scenarios, scenario data profiles, lab
profiles, prompts, product code or integration source. Scenario catalogs and
project-specific assets must be mounted or supplied by the repository under
test.

Build command:

```bash
python -m tools.verification.cli docker release \
  --image ghcr.io/pcvantol/djconnect-verification-platform \
  --base-image python:3.12-slim \
  --release-sha "$(git rev-parse HEAD)"
```

The release command tags the image with:

```text
<image>:<runtime-version>
<image>:<runtime-version>-<release-sha-12>
<image>:sha-<release-sha-12>
```

The Dockerfile records OCI labels for runtime version, release SHA, build date,
base image and MIT license. The image entrypoint is:

```bash
python -m tools.verification.cli
```

Typical use with a checked-out project mounted as `/workspace`:

```bash
docker run --rm \
  -v "$PWD:/workspace" \
  ghcr.io/pcvantol/djconnect-verification-platform:0.2.0 \
  --root /workspace config
```

The same image is intended to run inside GitHub Actions. In hosted GitHub
runners it should execute engine validation, scenario catalog validation,
planning, report schema checks, Docker dry-runs and other non-mutating
verification steps against the checked-out repository. Live Home Assistant labs,
Apple simulator runs, hardware rigs and destructive cleanup remain gated and
belong on explicitly prepared self-hosted runners or local labs with the
required host capabilities.

Runtime release notes are maintained separately from the DJConnect product
changelog in `tools/verification/RELEASE_NOTES.md`. They record engine-level
changes, validation commands, known limitations and runner/release notes for
each Verification Platform runtime version.

## Developer Workflow

1. Add or update scenarios in the canonical scenario catalog.
2. Run `validate` to confirm scenario shape.
3. Run `dry-run` to verify scenario selection and report plumbing.
4. Run `prepare` to capture the execution environment and cleanup plan.
5. Add or extend the smallest required adapter.
6. Qualify repository hygiene, environment and build artifacts.
7. Execute through the harness, never directly through ad hoc scripts.
8. Store sanitized evidence and publish Markdown, JSON, JUnit and summary
   reports.

## Future Readiness

The harness is intentionally shaped for nightly runs, hardware farms, cloud
execution, remote runners, distributed execution, dashboard ingestion,
historical trends and production readiness gates.
