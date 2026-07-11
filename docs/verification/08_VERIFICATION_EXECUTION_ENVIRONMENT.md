# Verification Program V1 Phase 8 - Verification Execution Environment

Status: Implemented
Date: 2026-07-10
Scope: execution environment only; no platform adapters

## Purpose

The Verification Execution Environment is the DJConnect Digital Test
Laboratory. It prepares, inspects and restores the world around verification
execution.

It does not define scenario behavior, assertions, profile logic, privacy
rules, Music DNA behavior, localization behavior or product rules. Those remain
owned by the platform foundation, scenario catalog and Verification Core.

## Architecture

```text
Scenario
  -> Verification Matrix
  -> Scenario Engine
  -> Verification Core
  -> Verification Execution Environment
  -> Platform Adapter
  -> Platform Runtime
  -> Observed Result
  -> Evidence
  -> Verification Core
```

The execution environment sits between the Verification Core and platform
adapters. It owns repository state, toolchains, build qualification, cleanup,
evidence directories, run identity, secrets names, CI inspection and
environment snapshots.

Software Assurance may specify quality policy, execution profiles, evidence
expectations, retention posture and runner qualification requirements. The
Execution Environment remains responsible for resolving how that work can run:
toolchains, runners, Docker/lab setup, artifacts, cleanup, snapshots and
environment metadata.

## Responsibility Boundary

The execution environment owns repository hygiene, build qualification,
development environment discovery, virtual machine and simulator discovery,
physical device environment discovery, SSH and serial environment primitives,
build pipeline metadata, artifact directories, environment snapshots, evidence
storage locations, GitHub Actions inspection, toolchain and dependency
inspection, cleanup, run identity, secrets loading by name only and
configuration plumbing.

The execution environment never owns scenario behavior, verification logic,
assertions, product rules, profile resolution, privacy policy, Music DNA
behavior, localization policy or platform adapter behavior.

## Implementation

The implementation lives under `tools/verification/environment/`.

| Module | Responsibility |
| --- | --- |
| `execution.py` | Coordinates environment preparation and restore lifecycle. |
| `identity.py` | Generates run IDs, environment IDs, correlation IDs and artifact prefixes. |
| `toolchain.py` | Discovers Python, Git, Node, Xcode, Swift, .NET, PlatformIO, ESP-IDF, Docker, Parallels, OS and architecture. |
| `dependencies.py` | Inspects Python, Swift, NuGet, npm, PlatformIO and ESP-IDF manifests/lockfiles without upgrading anything. |
| `github.py` | Discovers workflows and inspects GitHub Actions status through `gh` when available. |
| `host_preflight.py` | Blocks lab runner startup when host ports, processes or disk space are unsafe. |
| `cleanup.py` | Plans and executes soft/destructive cleanup with explicit destructive opt-in. |
| `platforms.py` | Provides environment-control scaffolding for HA, Apple, Windows, Pi and ESP32 without adapter assertions. |
| `snapshot.py` | Captures reusable environment metadata and capability states. |

The Verification Core exposes `prepare_environment(scenarios)` and
`restore_environment(dry_run=True, allow_destructive=False)`.

The existing CLI namespace now includes:

```bash
python -m tools.verification.cli prepare
python -m tools.verification.cli restore
python -m tools.verification.cli config
python -m tools.verification.cli apple ensure-ios-runtime
python -m tools.verification.cli apple qualify-runtime
```

This is not a HA-specific or adapter-specific CLI.

## Modular Local HA Lab

The Execution Environment owns modular lab composition. Platform adapters do
not decide which containers, sidecars, integrations or bootstrap actions are
required.

The model is:

```text
Selected scenarios
  -> required capabilities
  -> Lab Execution Plan
  -> canonical lab profile
  -> Compose fragments
  -> idempotent bootstrap
  -> capability readiness
```

Canonical lab definitions live under:

- `verification/lab/capabilities.yaml`;
- `verification/lab/services/`;
- `verification/lab/profiles/`;
- `verification/lab/bootstrap/`;
- `docker/verification/`.

The Execution Environment resolves a selected profile into a deterministic
Compose file list and records the effective profile, fragments and readiness
gates as evidence. It rejects unknown capabilities, unknown services and
unsupported profile promises through validation.

Readiness is capability-based. A healthy container is not sufficient proof that
an integration, Assist pipeline, music backend or storage fixture is ready.

## Execution Model

Preparation produces a structured metadata bundle:

- run identity;
- environment snapshot;
- toolchain discovery;
- dependency inspection;
- GitHub workflow discovery;
- platform environment discovery;
- gates for workflow discovery, dependency inspection, cleanup planning and
  secret-name loading.

Restore uses cleanup planning. It defaults to dry-run mode and blocks
destructive cleanup unless `allow_destructive` is explicitly true.

Scenario execution is parallel by default. The execution engine groups ready
scenarios into sandboxed waves, preserves result order, records wave/sandbox
diagnostics and blocks unsafe concurrency when dependencies or exclusive
resources require sequencing.

Before local lab runners start, the host preflight checks for conditions that
can invalidate or destabilize a run:

- the intended lab port must not already have a listener;
- likely conflicting `home-assistant`, `hass` or `djconnect` processes are
  reported and block startup unless they are known harness/Codex commands;
- the lab root filesystem must have at least the configured minimum free disk
  space, currently 15 GiB by default;
- existing Docker Home Assistant lab containers are still qualified separately
  by the Docker HA discovery gate.

The HA lab lifecycle runs this preflight before `start`, `recreate` and
`fresh`. If it fails, Docker image updates and `docker compose up` are not
attempted.

Default worker count is derived dynamically from host CPU capacity. On Apple
Silicon, the loader reads performance and efficiency core counts through
`sysctl` and bounds the worker count by logical CPU capacity. When that metadata
is unavailable, it falls back to logical CPU count with local headroom. Operators
can override or disable this behavior:

```bash
python -m tools.verification.cli --workers 12 execute
python -m tools.verification.cli --no-parallel execute
```

```text
DJCONNECT_VERIFICATION_PARALLEL_WORKERS=12
DJCONNECT_VERIFICATION_PARALLEL=0
```

## Supported Environment Surfaces

The current execution environment can inspect or scaffold control for:

- local macOS workstation;
- Home Assistant development environment discovery;
- Python virtual environment/tooling;
- Xcode and simulator tooling;
- macOS app execution environment discovery;
- physical Apple device environment prerequisites;
- Parallels and Windows VM prerequisites;
- SSH availability for Raspberry Pi;
- PlatformIO and ESP32 prerequisites;
- GitHub workflow and Actions status;
- future Docker/Linux/cloud runner extension points.

Platform-specific behavior remains for future adapters.

Apple runtime qualification distinguishes stable and future/beta evidence.
Stable mode is the default and uses the latest eligible stable iOS simulator
runtime. Future/beta validation requires `DJCONNECT_VERIFICATION_TEST_MODE` set
to `future_beta`; Xcode beta and Home Assistant beta routes are isolated from
stable release qualification evidence.

## Repository Hygiene

Reusable operations include working tree validation, branch validation, SHA
validation, fetch dry-run/apply, prune dry-run/apply, dependency validation,
toolchain validation, GitHub CI validation, cleanup planning and environment
fingerprinting.

Network-affecting GitHub operations are read-only inspection. They do not
replace GitHub CI.

## Toolchain Inspection

Toolchains are discovered by executable lookup and version commands where
available. Missing optional tools are recorded as missing, not fatal.

Tracked tools include Python, Git, Node, npm, Xcode, Swift, .NET, MSBuild,
PlatformIO, ESP-IDF, Docker, Parallels, operating system and architecture.
No versions are hardcoded.

## Dependency Inspection

Dependency inspection covers Python `pyproject.toml`, Swift `Package.swift`,
NuGet project files, npm `package.json`, PlatformIO manifests and ESP-IDF
manifests. It records manifests, lockfiles, package counts and drift-check
potential. It never upgrades dependencies.

Security advisory detection is represented as metadata and remains a future
integration point for repository-specific scanners.

## Build Qualification

Build qualification can record artifact metadata, checksums, signing metadata,
entitlements, provisioning/configuration metadata, manifest version, build
type, release-equivalent marker, instrumented marker and CI metadata.

The environment records this as evidence-ready metadata. It does not perform
platform builds itself unless a future build pipeline service is explicitly
added.

## GitHub

GitHub support includes workflow discovery from `.github/workflows`, workflow
metadata extraction, read-only GitHub Actions status inspection through
`gh run list` when available and authenticated, and commit SHA association.

The execution environment never replaces GitHub CI and never writes GitHub
state.

GitHub Actions is an execution target for future Software Assurance work. It is
not the owner of quality policy, Verification, planning or release
qualification. Software Assurance determines policy; the Planning Engine and
Execution Environment determine how the work maps to available execution
targets.

## Platform Environment Control

The platform controllers in `platforms.py` are environment controls only:

- Home Assistant: discover local `ha`/`hass`, report health metadata, scaffold
  start/stop/restart operations.
- Apple: discover Xcode and `xcrun`, record Xcode version, list simulators as
  structured metadata through a command runner, and keep physical-device
  discovery skipped unless explicitly configured.
- Windows: discover Parallels prerequisites.
- Raspberry Pi: record SSH availability and configured host metadata.
- ESP32: discover PlatformIO and externalized serial configuration.

They do not verify product behavior and do not contain profile, privacy,
localization or Music DNA assertions.

## Environment Snapshot

Snapshots capture date/time/timezone, host, OS, architecture, toolchain paths,
toolchain capability state, DJConnect integration manifest version,
requirements/dependencies, Git SHA, branch, parallel execution settings and
configuration fingerprint.

The snapshot model is reusable by every adapter.

Snapshots include Verification Platform runtime metadata:

```text
verification_runtime.name
verification_runtime.version
verification_runtime.schema_version
```

The same metadata is persisted in run summaries and report metadata so test
results can be traced back to the runtime implementation that produced them.

Run result metadata also includes `execution_summary.total_execution_seconds`.
Reporters surface the same summary in JSON, Markdown, JUnit suite time and the
short CLI summary output, alongside executed/total scenario counts and
per-status counts.

The generic Verification Platform Docker runtime is built from
`docker/verification-platform/Dockerfile`. It copies only `tools/verification`
into the image and uses Dockerfile-specific ignore rules to exclude repository
scenarios, lab definitions, prompts, docs, tests, product source and evidence
artifacts. The image is therefore a reusable engine runtime; repositories mount
their own scenarios and assets at execution time.

The Docker runtime is also the portability layer for GitHub Actions runners.
Hosted GitHub runners can use the image for repository-safe verification work:
runtime smoke tests, scenario validation, planning, report/schema validation,
exact-SHA metadata capture and non-mutating dry-runs. Jobs that require Docker
Home Assistant labs, Xcode simulator state, local ports, hardware, SSH, serial
devices, signing material or destructive cleanup must run only on self-hosted
GitHub runners or approved local labs that advertise those capabilities.

GitHub runner execution must preserve the same evidence contract as local
execution: record `verification_runtime`, GitHub run/job metadata, checked
commit SHA, parallel worker count, execution summary totals and artifact paths.
The Docker image supplies the engine; the workflow supplies repository checkout,
scenario inputs, credentials by name, artifact upload and policy gates.

## Run Identity

Every prepared run receives `run_id`, `environment_id`, `correlation_id`,
scenario IDs and an artifact prefix. These IDs make evidence traceable without
embedding secrets or user data.

## Evidence And Artifacts

Evidence and artifacts stay under:

```text
artifacts/verification/
```

The execution environment provides run identity and cleanup boundaries so
future adapters can store logs, screenshots, serial output, requests,
responses, environment snapshots, checksums, build metadata and CI metadata
without overwriting previous runs.

## Cleanup

Cleanup supports soft cleanup and destructive cleanup with explicit opt-in.
Soft cleanup is the default. Destructive targets are blocked unless explicitly
approved.

Current cleanup targets include `.pytest_cache`, verification temporary
directories, verification logs, build/dist, derived-data markers under
artifacts and `obj`/`bin` folders. Future extensions can add simulator, SSH
temp and serial session cleanup.

## Configuration And Secrets

Configuration is externalized through environment variables, optional ignored
local configuration files, CLI overrides and secrets file references.

Secrets support includes HA tokens, GitHub tokens, SSH key names, certificates
and signing configuration names. The loader records secret names only. It never
returns secret values, logs secret values or commits secrets.

## Security

Security rules:

- never commit secrets;
- never log secret values;
- load least-privilege token names where practical;
- default cleanup to dry-run;
- require explicit opt-in for destructive cleanup;
- keep platform mutation in environment controls or future adapters, never in
  scenarios;
- preserve evidence boundaries before cleanup.

## Tests

Unit and mock tests cover run identity, toolchain discovery, dependency
inspection, GitHub workflow discovery, cleanup safeguards, platform controller
boundaries, execution environment preparation, host preflight checks,
fetch/prune dry-runs, CLI `prepare`/`restore`/`config`, dynamic parallel worker
detection, parallel disable overrides and Apple stable/future-beta runtime
channel separation.

## Future Extensions

Future phases may add richer HA process control, more simulator lifecycle
helpers, Parallels VM snapshots and command execution, Pi SSH file copy and
service restart helpers, ESP serial monitor and flash/OTA helpers, artifact
downloads from GitHub Actions, security advisory scanner integration and
Docker/Linux/cloud runner backends.

These remain execution-environment features, not platform adapter assertions.

## Readiness

The project is ready for Phase 9: Home Assistant Verification Adapter.

The HA adapter can now rely on the execution environment for repository state,
toolchains, dependency metadata, GitHub CI inspection, run identity, evidence
locations, environment snapshots, cleanup and local environment discovery.
