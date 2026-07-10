# DJConnect Verification Harness

Status: scaffold architecture  
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
run identity, platform environment discovery, cleanup planning, environment
snapshots and restore operations. It prepares the world around execution but
does not own scenario behavior or adapter assertions.

`orchestrator.py` owns the run lifecycle. In the scaffold it supports dry runs
and execution placeholders only.

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
```

Reserved future commands:

```bash
python -m tools.verification.cli execute
python -m tools.verification.cli evidence
python -m tools.verification.cli doctor
python -m tools.verification.cli env
python -m tools.verification.cli clean
python -m tools.verification.cli build
python -m tools.verification.cli ci
```

Filters are designed for scenario IDs, tags, platform, locale, automation
level, build type and component.

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

The scaffold is intentionally shaped for nightly runs, hardware farms, cloud
execution, remote runners, parallel execution, distributed execution,
dashboard ingestion, historical trends and production readiness gates.
