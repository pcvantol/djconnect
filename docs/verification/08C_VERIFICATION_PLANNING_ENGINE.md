# Verification Program V1
## Phase 8C - Verification Planning Engine

Status: Complete

The Verification Planning Engine is the final pre-adapter subsystem. It turns
abstract verification assets into executable verification plans without running
anything.

The engine owns planning decisions only:

Scenario

x

Verification Matrix

x

Verification Data

x

Verification Mode

x

Verification Policy

=

Execution Plan

## Responsibility Boundary

The Planning Engine owns:

- scenario selection and filtering;
- policy expansion;
- matrix profile expansion;
- data profile expansion;
- mode expansion;
- environment matching;
- adapter selection;
- execution ordering;
- parallelization planning;
- resource allocation;
- batching;
- retry planning;
- runtime estimation;
- coverage analysis;
- risk and priority ordering;
- execution plan generation.

For Software Assurance integration, the Planning Engine also consumes
Software Assurance execution profiles, evidence expectations, retention
posture, runner capability requirements and cost constraints once future
implementation phases add those inputs. The engine still owns planning only;
it does not execute assurance work or own quality policy.

The Planning Engine never:

- executes tests;
- builds software;
- calls platform adapters;
- evaluates assertions;
- produces pass or fail results;
- collects evidence;
- mutates platform runtime state.

Adapters must consume the plan they are given. They must not decide which
scenarios, data, modes, matrix dimensions or policies apply.

## Inputs

The engine accepts:

- Scenario Catalog;
- Verification Matrix;
- Verification Data Framework;
- Verification Modes;
- Verification Policies;
- repository capabilities;
- platform capabilities;
- Execution Environment capabilities;
- adapter capabilities;
- available hardware;
- available virtual machines;
- available simulators;
- available build artifacts;
- environment configuration;
- current branch and SHA;
- GitHub CI status;
- build qualification status.

The current implementation reads the scenario catalog through the existing
scenario loader and reads the canonical mode and policy catalogs from:

- `verification/modes/catalog/modes.json`;
- `verification/policies/catalog/policies.json`;
- `verification/data/profiles/`.

## Outputs

The engine produces machine-readable:

- execution plan;
- execution graph;
- execution batches;
- execution timeline approximation;
- resource plan;
- environment plan;
- coverage report;
- estimated runtime;
- required hardware;
- required builds;
- required evidence;
- expected reports.

The CLI command is:

```bash
python -m tools.verification.cli plan --strategy smoke --policy smoke --format json
```

This command plans only. It does not execute scenarios and does not call an
adapter.

## Planning Pipeline

Canonical pipeline:

1. Scenario Selection
2. Policy Expansion
3. Matrix Expansion
4. Data Expansion
5. Mode Expansion
6. Environment Matching
7. Adapter Selection
8. Execution Ordering
9. Parallelization
10. Resource Allocation
11. Execution Plan

The implementation keeps each generated case traceable to scenario id, mode,
policy, matrix profile, data profile, platform, adapter, execution environment
and expected evidence.

## Lab Requirement Planning

The Planning Engine also aggregates scenario `requires` declarations into a
Lab Execution Plan. This plan is metadata only. It does not start Docker,
configure Home Assistant or call adapters.

The Lab Execution Plan includes:

- selected scenario IDs;
- transitive required capabilities;
- optional capabilities;
- selected canonical lab profile;
- selected lab services;
- Compose fragments;
- bootstrap actions;
- required secrets;
- required hardware;
- external resources;
- persistence mode;
- readiness gates;
- evidence requirements;
- unresolved requirements.

The planner selects the smallest canonical lab profile that satisfies the local
lab capabilities. Future client runtimes, physical hardware and external
services remain explicit resource requirements and do not force `ha-full`.

Canonical lab profiles are defined in:

```text
verification/lab/profiles/
```

The capability taxonomy is defined in:

```text
verification/lab/capabilities.yaml
```

For `PROFILE-001` through `PROFILE-005`, the aggregated requirements select
`ha-profile`.

## Planning Strategies

The canonical strategies are:

- Minimal;
- Smoke;
- Regression;
- Release;
- Security;
- Localization;
- Accessibility;
- Performance;
- Hardware;
- Nightly;
- Research.

Each strategy optimizes a different tradeoff between runtime, coverage, risk
and confidence. Strategies select a default policy but may be overridden by the
CLI or future CI configuration.

## Scenario Expansion

Example:

PROFILE-001

x

Release Candidate

x

Apple Verification Profile

x

Unicode data

x

Boundary mode

=

one concrete planned execution case.

The same scenario can expand into many concrete cases without duplicating the
scenario definition.

## Combination Reduction

The matrix is intentionally not expanded naively. The planner supports these
reduction concepts:

- risk-based reduction;
- pairwise testing;
- representative combinations;
- mandatory combinations;
- critical path selection;
- dependency-aware reduction;
- resource-limited hardware selection.

This prevents combinatorial explosion while keeping release, privacy,
localization, security and hardware risks visible.

## Dependency Graph

The planner orders scenarios by platform category so invalid sequences are
avoided. Setup precedes Profiles, Profiles precede Resolver, Resolver precedes
Ask DJ, Music DNA, Playback and related feature areas.

The generated graph contains case nodes and dependency edges. It is an ordering
model only; the execution layer is responsible for enforcing it later.

## Environment Matching

The planner selects the required environment type, not the adapter:

- local macOS plus Xcode for Apple plans;
- Parallels and Windows ARM VM for Windows plans;
- SSH and Pi resources for Raspberry Pi plans;
- serial, WiFi and board resources for ESP32 plans;
- Home Assistant and Assist pipeline resources for Voice Endpoint plans.

This keeps platform adapters thin.

## Build Planning

The planner determines which build type is required:

- Debug;
- Instrumented;
- Release-equivalent;
- Production Package;
- Store Build;
- Hardware.

It never creates a build. Build production remains owned by the Execution
Environment and platform toolchains.

## Resource Planning

Plans identify required resources:

- devices;
- simulators;
- VMs;
- SSH sessions;
- serial ports;
- GitHub;
- Home Assistant development environment;
- build artifacts.

Exclusive resources such as serial ports, a Pi, an ESP32 board, shared
persistent storage or a physical watch are marked so the execution scheduler
can avoid unsafe parallelism.

## Parallel Execution

The planner supports:

- sequential batches;
- parallel batches;
- hybrid batches.

Batching respects dependencies and resource exclusivity. Hardware policies use
limited or sequential batching; CI-friendly policies may use safe parallel
batches.

The execution engine runs independent scenarios in parallel by default. It
forms waves from scenarios whose `depends_on` or `dependencies` are satisfied,
then excludes scenarios that share `requires.exclusive_resources` from the same
wave. Operators can force sequential execution with `--no-parallel` or
`DJCONNECT_VERIFICATION_PARALLEL=0`.

## Retry Planning

Retry behavior is policy driven:

- no retry for deterministic local and smoke plans;
- controlled retry for nightly plans;
- manual retry for release-gated plans that require human confirmation.

The planner records retry intent only. It never retries anything itself.

## Coverage

Generated plans include measurable coverage:

- scenario coverage;
- platform coverage;
- localization coverage;
- accessibility coverage;
- verification mode coverage;
- policy coverage;
- data profile coverage;
- matrix profile coverage.

The coverage report describes what would be exercised if the plan were executed.

## Cost Estimation

The planner estimates:

- runtime;
- hardware usage;
- storage and artifact expectations;
- evidence scope;
- log volume class;
- CI and lab resource class.

These estimates are approximate and intended for scheduling decisions, not for
pass/fail evaluation.

## Scheduling

The planning model supports:

- developer run;
- pull request;
- nightly;
- release;
- full qualification;
- research;
- hardware lab.

Scheduling remains metadata until an execution system consumes a plan.

## Templates

Canonical templates live under `verification/planning/templates/`:

- Smoke;
- Release;
- Nightly;
- Security;
- Localization;
- Apple;
- Pi;
- ESP;
- Voice;
- Cross-platform.

Example generated-plan shapes live under `verification/planning/examples/`.

## Traceability

Every planned case references:

- scenario id;
- source scenario file;
- Verification Matrix profile;
- Verification Data profile;
- Verification Mode;
- Verification Policy;
- platform;
- adapter;
- Execution Environment requirements;
- expected evidence;
- expected reports.

This is the bridge between platform documentation and future adapter execution.

## Implementation

Code:

- `tools/verification/planning/`;
- `tools/verification/models/core.py`;
- `tools/verification/cli.py`.

Artifacts:

- `verification/planning/planners/canonical_planner.json`;
- `verification/planning/strategies/strategies.json`;
- `verification/planning/templates/`;
- `verification/planning/examples/`.

## Completion Decision

Phase 8C is complete.

The platform now has:

- Scenario Catalog;
- Verification Matrix;
- Verification Data;
- Verification Modes;
- Verification Policies;
- Verification Planning Engine;
- Verification Execution Environment;
- Verification Core.

No further architectural subsystem should be introduced before adapter
implementation. The next phase is Phase 9: Home Assistant Verification Adapter.
