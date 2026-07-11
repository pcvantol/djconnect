# DJConnect Software Assurance Integration

Status: canonical integration architecture  
Scope owner: `pcvantol/djconnect`  
Phase: architecture only; no implementation

## Purpose

This document defines how the Software Assurance Platform integrates with the
existing DJConnect platform architecture.

Software Assurance is an extension of the Verification Platform. It governs
engineering quality while Verification remains the owner of behavioural
correctness.

No functionality is implemented by this document. No scanners, CI workflows or
quality gates are added.

## Canonical Stack

```text
Platform Foundation
  -> Verification Platform
  -> Software Assurance Platform
  -> Verification Runtime
  -> Execution Environment
  -> Execution Targets
  -> Evidence
  -> Platform Health
  -> Release Qualification
```

Each layer has one owner. No layer may silently redefine another layer.

## Interface Map

| Interface | Producer | Consumer | Contract |
| --- | --- | --- | --- |
| Platform truth | Platform Foundation | Verification, Software Assurance, Release Qualification | Constitution, principles, domain model, ownership and baseline docs. |
| Behavioural proof | Verification Platform | Software Assurance, Release Qualification, Platform Health | Scenarios, execution results, evidence references and readiness decisions. |
| Quality policy | Software Assurance Platform | Verification Planning Engine, Execution Environment, repositories | Capability, policy, evidence, execution profile and reporting architecture. |
| Execution plan | Verification Planning Engine | Execution Environment | Planned work, environment requirements, evidence expectations and resource constraints. |
| Runtime metadata | Verification Runtime | Software Assurance, Platform Health, Release Qualification | Runtime version, schema version, image provenance, execution metadata and report metadata. |
| Environment metadata | Execution Environment | Verification, Software Assurance, Platform Health | Toolchain, dependency, CI, runner, lab, artifact and cleanup metadata. |
| Execution evidence | Execution Targets | Verification Runtime and Software Assurance reports | Logs, reports, snapshots, artifacts, checksums and run metadata. |
| Health trends | Platform Health | Maintainers, backlog, release review | Quality indicators and trend reports. |
| Release input | Verification and Software Assurance | Release Qualification | Behavioural readiness plus engineering-quality evidence. |

## Verification Integration

Verification owns:

- scenario definitions;
- planning;
- execution;
- evidence collection;
- investigator workflow;
- qualification decisions for behaviour.

Software Assurance consumes:

- evidence references;
- planning metadata;
- runtime metadata;
- repository metadata;
- CI metadata;
- dependency metadata;
- build metadata;
- investigator classifications.

Software Assurance must not:

- move scenario ownership;
- redefine expected behaviour;
- execute adapters directly;
- produce behavioural pass/fail results;
- replace Verification qualification.

When an assurance finding raises behavioural uncertainty, the finding becomes a
Verification follow-up rather than a Software Assurance-only conclusion.

## Verification Runtime Integration

The Verification Runtime is a versioned product.

Software Assurance validates runtime quality signals. It does not become the
runtime.

Runtime integration covers:

- runtime versioning;
- schema compatibility;
- Docker image provenance;
- release lifecycle evidence;
- runtime dependency posture;
- runtime health and execution metadata;
- compatibility between runtime reports and Software Assurance report
  contracts.

The runtime remains responsible for:

- scenario loading;
- planning integration;
- execution orchestration;
- adapter contracts;
- evidence production;
- report generation;
- run metadata.

Software Assurance remains responsible for:

- quality policy;
- engineering-quality evidence classification;
- release-assurance consumption of runtime evidence;
- Platform Health interpretation.

## Execution Environment Integration

Execution Environment remains responsible for:

- Docker;
- GitHub Actions inspection;
- self-hosted runner metadata;
- developer workstation metadata;
- cleanup planning;
- artifacts;
- build orchestration metadata;
- lab orchestration;
- toolchain and dependency inspection;
- environment snapshots.

Software Assurance specifies what should execute through:

- quality policies;
- execution profiles;
- evidence expectations;
- retention posture;
- runner qualification requirements;
- cost and resource constraints.

Execution Environment determines how it executes by resolving:

- available toolchains;
- available runners;
- lab capabilities;
- resource conflicts;
- cleanup and restore requirements;
- artifact locations;
- evidence paths.

## GitHub Actions Integration

GitHub Actions is an execution target.

It is not the owner of:

- Verification;
- Software Assurance;
- quality policy;
- planning;
- release qualification.

Software Assurance determines policy. The Planning Engine turns policy into an
execution plan. GitHub Actions may execute parts of that plan when a future
implementation phase wires it in.

Current workflow files are existing execution surfaces only. This architecture
does not modify them or mark any workflow as newly required.

## Release Integration

Release flow:

```text
Verification
  -> Software Assurance
  -> Release Qualification
  -> Promotion
  -> Distribution
  -> Platform Baseline
```

Release Qualification consumes:

- Verification evidence;
- Software Assurance evidence;
- policy status;
- release evidence bundles;
- artifact provenance;
- compatibility evidence;
- known limitations and waivers.

Software Assurance does not publish releases. Release repositories remain
distribution surfaces, and product/release decisions remain policy-driven.

## Backlog Integration

Backlog flow:

```text
Finding
  -> Evidence
  -> Investigator
  -> Classification
  -> Risk Assessment
  -> Backlog Recommendation
  -> Platform Backlog
  -> Implementation
```

Scanners, analyzers and tools must not create backlog items directly. They may
produce findings. Findings become backlog recommendations only after evidence,
owner, severity, risk and release impact are classified.

## Repository Bootstrap Integration

Clean-session architecture:

```text
BOOTSTRAP_CODEX_SESSION.md
  -> AGENTS.md
  -> Platform Foundation
  -> Verification Foundation when verification or evidence is relevant
  -> Software Assurance Foundation when engineering quality is relevant
  -> Repository Status
  -> Repository Phase or Prompt
```

Repository prompts must reference canonical Software Assurance docs instead of
copying capability, policy, execution or health definitions.

## Integration Principles

- One source of truth.
- Evidence before metrics.
- Metrics never replace policy.
- Cloud where possible.
- Local where necessary.
- Quality without duplicated ownership.
- Repository-native engineering.
- Versioned runtime.
- GitHub executes policy; it does not own policy.
- Platform Health visualizes evolution; it does not release software.
