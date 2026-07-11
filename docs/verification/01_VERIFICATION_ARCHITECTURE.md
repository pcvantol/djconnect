# DJConnect Verification Architecture

Status: Canonical verification architecture  
Scope owner: `pcvantol/djconnect`  
Applies to: DJConnect platform-wide verification  
Builds on: `docs/verification/00_VERIFICATION_VISION.md`

## Purpose

Verification Architecture defines how DJConnect turns platform requirements
into reproducible evidence.

Verification is a platform capability. It is not only testing, not only CI and
not a temporary set of scripts around the current repository. It is the
permanent subsystem that connects foundation truth, accepted baselines,
repository state, build artifacts, real clients, real hardware, evidence and
readiness decisions.

The architecture exists to keep those responsibilities separated:

- platform requirements describe what must be true;
- scenarios describe what must be proven;
- orchestration coordinates when and where proof happens;
- adapters execute platform-specific actions;
- evidence records what happened;
- reports explain the result;
- readiness decisions decide whether the platform can move forward.

This document is architecture only. It does not define a runner, adapter API,
scenario schema, scenario catalog or execution plan.

## Layers

DJConnect verification is organized as a layered platform subsystem:

```text
Verification Vision
  -> Scenario Catalog
  -> Verification Orchestrator
  -> Adapters
  -> Evidence
  -> Reports
  -> Platform Readiness
```

**Verification Vision** defines why verification exists, what it guarantees
and which long-term principles guide it.

**Scenario Catalog** defines reusable platform scenarios. It names the
behavior that must be proven without binding the behavior to one client,
repository or execution tool.

**Verification Orchestrator** coordinates scenario selection, environment
preparation, hygiene checks, build qualification, execution, evidence
collection, result aggregation, reporting and readiness decisions.

**Adapters** translate platform scenarios into actions for specific runtimes,
repositories, clients, devices, services and release surfaces.

**Evidence** records what was observed: logs, screenshots, requests,
responses, serial output, metadata, manifests and other proof.

**Reports** turn evidence and results into human-readable and
machine-readable conclusions.

**Platform Readiness** is the final gate. It decides whether the platform can
release, advance to a candidate, continue an epic or must return work to the
backlog.

Each layer consumes the layer above and produces input for the layer below.
No layer should quietly redefine the responsibility of another layer.

## Verification Orchestrator

The Verification Orchestrator is the coordination layer of the verification
architecture.

It owns:

- scenario scheduling;
- environment preparation;
- repository hygiene;
- build qualification;
- scenario execution;
- evidence collection;
- result aggregation;
- reporting;
- platform readiness.

The generic Verification Platform runtime may be packaged as a Docker image,
but that image is an engine release only. Scenario catalogs, product
repositories, Home Assistant lab config, Apple app artifacts, hardware state,
secrets and evidence remain explicit inputs to a run. This keeps runtime
reproducibility separate from DJConnect product coverage.

Scenario scheduling means selecting which scenarios apply to the current
verification goal, baseline, release candidate, repository change or platform
scope.

Environment preparation means ensuring the run knows which local, CI, hardware
lab or future cloud environment it is using and which capabilities are
available.

Repository hygiene means verifying that source state, branches, dependency
state, toolchain state, logs and local artifacts are known before builds or
scenarios are trusted.

Build qualification means deciding which artifacts are eligible for
verification and whether they are release-equivalent, instrumented or
otherwise scoped.

Scenario execution means coordinating adapters to perform the actions needed
to prove the selected scenarios.

Evidence collection means gathering and sanitizing the proof required by each
scenario and run.

Result aggregation means combining adapter outcomes, scenario results,
warnings, failures, skipped work and limitations into a coherent platform
result.

Reporting means producing human and machine-readable outputs that can be
reviewed, stored, trended and used by CI or governance.

Platform readiness means making the final GO, Release Candidate or NO-GO
recommendation from evidence.

The Orchestrator does not own:

- scenario definitions;
- expected platform behavior;
- client implementations;
- backend logic;
- firmware logic;
- music backend business rules;
- product decisions.

Those responsibilities remain with the foundation, baselines, scenarios and
owning repositories. The Orchestrator coordinates proof; it does not become
the product specification.

## Scenario Catalog

The Scenario Catalog is the durable inventory of behavior DJConnect must be
able to prove.

Scenarios are platform assets. They are not throwaway scripts, client-local
checklists or one-off release notes. A scenario should remain meaningful as
execution technology evolves.

Every scenario has:

- stable ID;
- category;
- automation level;
- required components;
- evidence requirements;
- cleanup;
- expected result.

The stable ID allows reports, history, failures and backlog items to refer to
the same scenario over time.

The category connects the scenario to a verification domain such as
architecture, contracts, identity, profiles, privacy, localization,
performance, security, accessibility, hardware, release or production
readiness.

The automation level describes whether the scenario is currently manual,
partially automated, fully automated, hardware-dependent, live-service
dependent or future automation.

Required components identify which repositories, clients, devices, backends,
services, release artifacts or environments are needed.

Evidence requirements define the proof that must exist for the result to be
complete.

Cleanup describes the state that must be reset, removed, expired or recorded
after execution.

Expected result defines platform behavior. It must come from the foundation,
baseline, accepted contracts, ADRs or scenario intent. It must not be invented
by an adapter.

Scenarios are reusable. A profile-resolution scenario should not be duplicated
separately for every client if the behavior is the same platform behavior.
Instead, adapters execute the shared scenario through their own platform
surface.

## Adapters

Adapters translate platform scenarios into platform-specific actions.

An adapter knows how to interact with a runtime, client, device, repository,
service, release artifact or backend. It may know how to install a build,
start a local service, call an API, click through a UI, query a device, collect
logs, capture screenshots or read artifact metadata.

Expected adapters include:

- Home Assistant;
- Apple;
- Windows Catalyst;
- Windows Native ARM64;
- Raspberry Pi;
- ESP32;
- Voice Endpoint;
- Website;
- Release;
- future Android;
- future Runtime;
- Music Backend.

The Home Assistant adapter executes integration and local platform actions.
It may prepare a test instance, inspect integration state, exercise services,
call API endpoints and collect sanitized logs.

The Apple adapter executes iOS, iPadOS, macOS and watchOS client actions
through the appropriate native development, simulator, device or distribution
surfaces.

The Windows Catalyst adapter supports Catalyst-based development and debug
verification where that remains useful for cross-platform client behavior.

The Windows Native ARM64 adapter is authoritative for Windows-specific
rendering, packaging and native runtime behavior on Windows ARM64.

The Raspberry Pi adapter executes ambient client behavior, shared-profile
display checks, local runtime checks and remote UI evidence collection.

The ESP32 adapter executes firmware, device API, serial, OTA, BLE, display,
control and audio-related verification where real hardware is valuable.

The Voice Endpoint adapter executes Home Assistant Assist satellite and voice
request-source behavior, including mapping, privacy and fallback expectations.

The Website adapter executes product website, documentation, localization,
link, metadata and public distribution checks.

The Release adapter verifies release repositories, artifacts, checksums,
manifests, version metadata, release notes and distribution readiness.

The future Android adapter will execute Android client behavior without
changing shared platform scenarios.

The future Runtime adapter will execute scenarios against any later DJConnect
runtime model while preserving the same foundation contracts.

The Music Backend adapter executes backend/provider-specific compatibility
without allowing provider behavior to redefine platform expectations.

Each adapter owns execution only. It never owns expected behavior. If an
adapter appears to need a different expected result, the scenario, contract,
baseline or foundation must be reviewed instead of hiding the change inside
adapter code.

## Environment

The verification environment is part of the architecture and part of every
result.

DJConnect verification must support:

- local development;
- CI;
- hardware lab;
- future cloud runners;
- future nightly verification.

Local development verification helps contributors reproduce failures, qualify
small changes and collect evidence before review.

CI verification protects repository and platform gates through repeatable
automated checks, artifact validation and report generation.

Hardware lab verification proves physical device, audio, display, BLE, OTA,
power and network behavior that cannot be fully trusted from simulation.

Future cloud runners may provide scalable execution for multi-repository,
cross-platform or long-running verification.

Future nightly verification may continuously exercise live, integration,
compatibility, localization and release-readiness checks outside the normal PR
cycle.

Every environment must remain reproducible. A run should record enough detail
to explain where it ran, which repositories and artifacts it used, which
versions were active, which accounts or backends were configured, which
devices were present and which limitations applied.

## Repository Hygiene Gate

Repository Hygiene is the first gate before build qualification.

The hygiene gate documents and validates:

- open PR validation;
- working tree validation;
- branch validation;
- SHA validation;
- dependency validation;
- toolchain validation;
- build cleanup;
- environment cleanup;
- log cleanup.

Open PR validation determines whether blocking, related or conflicting PRs
exist for the verified scope.

Working tree validation determines whether the source tree is clean or whether
local changes are intentionally part of the run.

Branch validation records the branch being verified and whether it is the
expected branch for the goal.

SHA validation records the exact commit or commits that produced the result.

Dependency validation records dependency versions, lockfile state and whether
dependencies were restored from known inputs.

Toolchain validation records the compiler, SDK, runtime, package manager,
Home Assistant version, platform tools and other required tool versions.

Build cleanup removes or records stale outputs that could affect the run.

Environment cleanup resets state that could cause hidden coupling between
runs.

Log cleanup ensures logs start from a known state or are clearly segmented for
the verification run.

Only after Repository Hygiene may the platform proceed to Build
Qualification.

## Build Qualification Gate

Build Qualification decides which artifacts are valid verification targets.

DJConnect recognizes two important build classes:

**Release-equivalent builds** are materially equivalent to what users receive.
They remain authoritative for readiness because they prove packaging,
optimization, signing, entitlements, metadata, migrations and production
runtime behavior.

**Instrumented Verification builds** include additional diagnostics, hooks,
debug symbols, logging or fixtures that make behavior easier to inspect.
They are useful for diagnosis, development and evidence collection, but they
cannot replace release-equivalent proof for release decisions.

Build Qualification covers:

- artifact qualification;
- signing;
- entitlements;
- checksums;
- environment capture.

Artifact qualification confirms that the build corresponds to the expected
source, version, channel and target platform.

Signing confirms that artifacts requiring signatures or trusted identities are
signed appropriately for their verification purpose.

Entitlements confirm that app, firmware, Home Assistant, release and future
runtime capabilities match the expected distribution context.

Checksums confirm that artifacts can be identified, compared and protected
against accidental substitution.

Environment capture records how the artifact was produced and what toolchain,
configuration and source state were involved.

Release-equivalent builds remain authoritative because users experience
release artifacts, not debug intent.

## CI Qualification

CI Qualification verifies that automated repository and platform checks are
trustworthy inputs to verification.

It includes:

- GitHub Actions verification;
- workflow validation;
- artifact validation;
- required checks;
- local build comparison.

GitHub Actions verification confirms that the intended workflows run for the
appropriate branches, pull requests, tags, release events or scheduled jobs.

Workflow validation confirms that CI stages match the platform quality model:
formatting, linting, unit tests, contract tests, security/dependency checks,
secret scans, build artifacts, release-note validation and artifact integrity
where applicable.

Artifact validation confirms that CI-produced outputs are complete, named,
versioned, traceable and suitable for downstream verification.

Required checks identify which CI results must pass before a PR, release
candidate or platform readiness decision can move forward.

Local build comparison records when local verification uses artifacts that
differ from CI artifacts and whether that difference affects trust.

This document does not define workflows or implement CI behavior. It defines
the architectural role CI plays in verification.

## Evidence

Evidence is the proof produced by verification.

Every verification run produces evidence appropriate to its scope. Evidence
may include:

- logs;
- screenshots;
- serial logs;
- requests;
- responses;
- environment snapshot;
- reproducibility manifest;
- CI metadata;
- artifact metadata;
- checksums.

Logs show backend, client, firmware, website, release or orchestration
behavior. They must be sanitized before storage or publication.

Screenshots show rendered UI, onboarding, localization, errors, accessibility
states, store readiness and public surfaces where visual proof matters.

Serial logs show hardware and firmware behavior where device runtime evidence
is needed.

Requests and responses prove API, contract, command, status, voice, capability
and backend behavior. They must exclude secrets and private contents.

Environment snapshots record platform versions, toolchains, devices, accounts,
backends, locales, branches, SHAs and other inputs.

Reproducibility manifests explain how the run can be repeated.

CI metadata links verification results to workflow runs, job status,
artifacts and checks.

Artifact metadata records filenames, versions, channels, build IDs,
signatures, entitlements, manifests and release notes.

Checksums identify artifacts and protect the evidence chain.

Evidence is not optional. A scenario without evidence is incomplete unless the
report explicitly records why evidence could not be retained safely.

## Reporting

Reports turn evidence into decisions.

DJConnect verification should support:

- Markdown;
- JSON;
- JUnit;
- history;
- trend;
- platform score;
- pass rate;
- blocking issues;
- readiness.

Markdown reports are for maintainers, reviewers and release decisions. They
explain what ran, what passed, what failed, what was skipped, what evidence
exists and what must happen next.

JSON reports are for automation, dashboards, history, trend analysis and
future orchestration.

JUnit reports are for CI systems that understand test-like pass, fail, skip
and error output.

History records previous outcomes for the same scenarios, branches, releases
or platform baselines.

Trend shows whether quality is improving, degrading or becoming flaky.

Platform score summarizes maturity and risk without replacing detailed
results.

Pass rate shows scenario-level success while preserving severity distinctions.

Blocking issues identify failures that prevent readiness.

Readiness reports the final GO, Release Candidate or NO-GO decision.

Reports must distinguish between verification failure, missing evidence,
known limitation, skipped scenario, unsupported environment and out-of-scope
work.

## Readiness

Readiness is the final verification decision.

The decision flow is:

```text
GO
  -> Release Candidate
NO-GO
  -> Backlog
  -> Fix
  -> Verification
```

GO means the platform has sufficient evidence for the intended scope and can
move forward.

Release Candidate means the platform is close enough for final release-grade
qualification, store review preparation, field testing or controlled
distribution, but not yet declared fully ready.

NO-GO means verification found a blocking failure, unacceptable risk, missing
evidence or unresolved limitation.

A NO-GO result must not disappear into conversation history. It becomes
backlog with an owner, severity, evidence, recommendation and path back to
verification.

Fixes return to verification. The gate is not skipped because a fix seems
obvious or because only one repository changed. The relevant scenarios run
again and produce new evidence.

Readiness is mandatory. Every release, major baseline, epic gate and
production-facing capability must pass through the appropriate readiness gate.

## Extensibility

The architecture must support future adapters and execution environments
without changing the meaning of existing scenarios.

Future adapters may include:

- Android;
- Cloud;
- VR;
- DJConnect Runtime;
- Hardware Farm;
- Cloud runners;
- Nightly verification.

Android should plug into the same client-class and contract model used by
Apple and Windows.

Cloud should verify entitlement, relay, privacy, portability, degraded paths
and non-lock-in behavior without turning cloud into the only truth.

VR or immersive renderers should consume platform scenarios through renderer
and presentation-client expectations.

DJConnect Runtime should verify any future runtime model against the same
foundation, baseline and contract obligations rather than creating a parallel
platform.

Hardware Farm should scale physical-device verification while preserving
evidence, environment capture and reproducibility.

Cloud runners should scale execution without hiding environment or credential
assumptions.

Nightly verification should provide continuous confidence across live,
integration, compatibility, localization, release and production-readiness
domains.

Extensibility means the architecture can grow new adapters, environments,
report formats and evidence types while preserving responsibility boundaries.

## Relationship

Verification Architecture sits between long-term verification philosophy and
future execution.

The relationship is:

```text
Verification Vision
  -> Verification Architecture
  -> Scenario Schema
  -> Scenario Catalog
  -> Harness
  -> Execution
  -> Reports
  -> Platform Baseline
```

The Verification Vision explains why verification exists.

Verification Architecture defines the permanent subsystem boundaries and
responsibilities.

The future Scenario Schema will define the structured shape of scenarios.

The future Scenario Catalog will list reusable platform scenarios.

The future Harness will implement orchestration, adapter invocation, evidence
collection and reporting.

Execution will run scenarios in local, CI, hardware lab, cloud or nightly
environments.

Reports will feed governance, backlog, release decisions and historical
quality trends.

Platform Baseline will be informed by verification evidence. A baseline is
accepted only when the platform has enough proof that its claims are true.

Verification does not replace the foundation, implementation framework,
quality standard, localization standard or ADR process. It makes their claims
observable.

## Deliverables

This phase creates:

- `docs/verification/01_VERIFICATION_ARCHITECTURE.md`;
- a `FOUNDATION_INDEX.md` reference to the Verification Architecture.

This phase intentionally does not create:

- harness;
- scenario schema;
- scenario catalog;
- adapters;
- execution plans.

Those belong to later Verification Program phases.
