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
| `cleanup.py` | Plans and executes soft/destructive cleanup with explicit destructive opt-in. |
| `platforms.py` | Provides environment-control scaffolding for HA, Apple, Windows, Pi and ESP32 without adapter assertions. |
| `snapshot.py` | Captures reusable environment metadata and capability states. |

The Verification Core exposes `prepare_environment(scenarios)` and
`restore_environment(dry_run=True, allow_destructive=False)`.

The existing CLI namespace now includes:

```bash
python -m tools.verification.cli prepare
python -m tools.verification.cli restore
```

This is not a HA-specific or adapter-specific CLI.

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

## Platform Environment Control

The platform controllers in `platforms.py` are environment controls only:

- Home Assistant: discover local `ha`/`hass`, report health metadata, scaffold
  start/stop/restart operations.
- Apple: discover Xcode and `xcrun`, list simulators through a command runner.
- Windows: discover Parallels prerequisites.
- Raspberry Pi: record SSH availability and configured host metadata.
- ESP32: discover PlatformIO and externalized serial configuration.

They do not verify product behavior and do not contain profile, privacy,
localization or Music DNA assertions.

## Environment Snapshot

Snapshots capture date/time/timezone, host, OS, architecture, toolchain paths,
toolchain capability state, DJConnect integration manifest version,
requirements/dependencies, Git SHA, branch and configuration fingerprint.

The snapshot model is reusable by every adapter.

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
boundaries, execution environment preparation, fetch/prune dry-runs and CLI
`prepare`/`restore`.

## Future Extensions

Future phases may add richer HA process control, Xcode simulator lifecycle
helpers, Apple install/uninstall/launch control, Parallels VM snapshots and
command execution, Pi SSH file copy and service restart helpers, ESP serial
monitor and flash/OTA helpers, artifact downloads from GitHub Actions,
security advisory scanner integration and Docker/Linux/cloud runner backends.

These remain execution-environment features, not platform adapter assertions.

## Readiness

The project is ready for Phase 9: Home Assistant Verification Adapter.

The HA adapter can now rely on the execution environment for repository state,
toolchains, dependency metadata, GitHub CI inspection, run identity, evidence
locations, environment snapshots, cleanup and local environment discovery.
