# DJConnect Software Assurance Platform

Status: canonical architecture foundation  
Scope owner: `pcvantol/djconnect`  
Phase: architecture only; no tooling enabled

## Purpose

The Software Assurance Platform is the canonical owner of platform-wide
software quality governance.

Verification answers:

```text
Does the platform behave correctly?
```

Software Assurance answers:

```text
Can this platform be trusted to build, verify, release and evolve safely?
```

Verification remains responsible for behavioural correctness. Software
Assurance governs the engineering quality system around that behaviour: source
quality, supply chain posture, runtime robustness, execution strategy, release
assurance, evidence, reporting and long-term platform health.

This document defines scope, ownership, boundaries, governance and roadmap
positioning. It does not introduce scanners, CI gates, workflow changes or
release gates.

## Platform Position

Software Assurance extends the Verification Platform. It does not replace it.

```text
Platform Foundation
  -> Verification Platform
  -> Software Assurance Platform
  -> Release Qualification
  -> Platform Baseline
```

The Platform Foundation defines product and architecture truth. The
Verification Platform proves platform behaviour against that truth. The
Software Assurance Platform governs whether the engineering system itself is
trustworthy enough to build, verify, release and evolve the platform safely.
Release Qualification consumes Verification and Software Assurance evidence.
Accepted results may then update the Platform Baseline.

## Ownership

Software Assurance owns:

- engineering quality governance;
- supply chain assurance;
- dependency governance;
- static quality;
- dynamic quality;
- release quality;
- execution strategy;
- quality policies;
- quality evidence;
- quality reporting;
- platform health;
- repository health.

Software Assurance does not own:

- business logic;
- product behaviour;
- client implementation;
- runtime execution;
- feature implementation;
- platform architecture;
- verification scenarios or behavioural expected results.

Verification remains the owner of behavioural correctness, scenario execution,
adapter outcomes and readiness conclusions about platform behaviour.

## Boundary Model

Software Assurance governs quality domains. It does not directly execute them.

```text
Software Assurance
  -> Quality Themes
  -> Quality Policies
  -> Verification Planning Engine
  -> Verification Execution Environment
  -> Execution Targets
  -> Evidence
  -> Reports
  -> Platform Health
```

Execution remains owned by the existing planning and execution stack:

```text
Planning Engine
  -> Execution Environment
  -> Execution Targets
```

Execution targets include:

- developer workstation;
- GitHub-hosted runners;
- self-hosted runners;
- local verification lab;
- physical hardware lab;
- future cloud runners.

GitHub Actions is one execution environment. It is not the owner of Software
Assurance, quality governance or release decisions.

## Canonical Quality Themes

Software Assurance is organized into six canonical themes:

1. Static Quality
2. Supply Chain Assurance
3. Dynamic Runtime Assurance
4. Execution Strategy and Cost Governance
5. Release Assurance
6. Platform Health

The detailed theme architecture lives in `SOFTWARE_ASSURANCE_THEMES.md`.

## Execution Profiles

Software Assurance defines cost-aware execution profiles. The Planning Engine
optimizes execution from these profiles; GitHub Actions or any runner only
executes the selected work.

Canonical profiles:

| Profile | Purpose | Default posture |
| --- | --- | --- |
| Economy | Fast, low-cost feedback for local work and early PR checks. | Narrow scope, low artifact retention, minimal parallelism. |
| Balanced | Normal development confidence. | Representative coverage, structured evidence, moderate retention. |
| Release | Release or promotion confidence. | Highest required evidence, release-equivalent artifacts, broader matrix, stricter retention. |

Profiles determine:

- preferred execution environment;
- parallelism;
- artifact retention;
- evidence level;
- retry policy;
- hardware usage;
- nightly strategy;
- cost and runtime budgets.

## Governance Principles

Software Assurance follows these platform principles:

- Repository over Prompt.
- Evidence over Opinion.
- Verification before Trust.
- Policies over Scripts.
- Cloud where possible.
- Local where necessary.
- One canonical owner.
- No duplicated evidence.
- No duplicated governance.
- Advisory trends never override blocking policies.

## Integration Points

Software Assurance integrates with:

- Verification Planning Engine for execution profile, policy and cost-aware
  planning;
- Verification Execution Environment for toolchain, dependency, CI, lab and
  runtime metadata;
- Verification Policies and Modes for behavioural scope and blocking severity;
- Verification Investigator for classifying failures by owning subsystem;
- Evidence stores and reports for durable quality proof;
- Phase Completion Protocol for repository knowledge updates and qualification;
- Platform Backlog for roadmap and follow-up ownership;
- Meta Engineering for repository-first process and AI-agent discipline;
- CI/CD and Release Governance for release hygiene and distribution posture.

Software Assurance must not duplicate Verification evidence, redefine
Verification policies or introduce a second quality-gate system beside the
canonical Planning Engine.

## Platform Health

Platform Health is an evidence-derived trend model. It supports decision
making by showing quality posture over time.

Health dimensions:

- Functional Health;
- Security Health;
- Supply Chain Health;
- Engineering Health;
- Operational Health;
- Repository Health.

Platform Health never replaces release policies. A positive health trend does
not unblock a failed release gate, and a release-blocking policy failure remains
blocking until resolved or explicitly waived through the release governance
process.

## Current Architecture Inventory

The repository already contains quality-related execution surfaces:

- Home Assistant custom integration CI in `.github/workflows/validate.yaml`;
- shared Python and Home Assistant CI workflows;
- CodeQL workflows;
- Semgrep workflows;
- verification framework tests;
- Verification Platform Docker release workflow;
- CI/CD governance documentation;
- Verification Planning Engine and Execution Environment;
- evidence and reporting infrastructure.

These are inputs and execution surfaces for Software Assurance architecture.
This phase does not modify them, enable new gates or introduce new scanners.

## Roadmap Position

Software Assurance begins after the Platform Foundation, Verification Platform
and Meta Engineering Foundation are architecturally complete.

Initial roadmap:

1. Foundation and Architecture: define ownership, boundaries, themes,
   integration and roadmap.
2. Capability Model and Backlog: define reusable capabilities, epics,
   features, stories, dependencies, priorities and implementation milestones.
3. Policy Model: define quality policies, evidence classes and reporting
   contracts without enabling gates.
4. Execution Planning: map assurance themes to cost-aware execution profiles
   and existing Verification Planning assets.
5. Platform Integration and Execution Architecture: define interfaces with the
   Verification Runtime, Execution Environment, execution targets,
   cross-repository evidence, Platform Health and Release Qualification.
6. Reporting and Health: define Platform Health trend reports and repository
   health scorecards.
7. Implementation Phases: introduce tooling only through explicit later
   prompts, with no hidden CI or release-gate activation.

## Completion Criteria

The Software Assurance Platform is architecturally complete when it has:

- explicit ownership;
- explicit boundaries;
- canonical themes;
- execution model;
- integration model;
- cost-aware execution strategy;
- Platform Health definition;
- roadmap positioning;
- navigation from the platform foundation.

This architecture sprint completed with decision:

```text
SOFTWARE_ASSURANCE_PLATFORM_ARCHITECTURE_COMPLETE
```

The architecture is frozen. Implementation starts only after all prerequisites
in `SOFTWARE_ASSURANCE_GOVERNANCE.md` are satisfied and a later approved
implementation phase begins.
