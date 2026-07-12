# DJConnect Software Assurance Architecture

Status: canonical architecture  
Scope owner: `pcvantol/djconnect`  
Builds on: `SOFTWARE_ASSURANCE_PLATFORM.md`

## Purpose

Software Assurance Architecture defines how DJConnect organizes engineering
quality governance without taking ownership away from the Platform Foundation,
Verification Platform, runtime repositories or release processes.

It is a platform governance layer. It defines quality ownership, execution
boundaries, evidence flow, reporting flow and integration with existing
verification systems. It does not implement analyzers, modify workflows or
enable gates.

## Layered Architecture

```text
Platform Foundation
  -> Platform Quality Standard
  -> Verification Platform
  -> Software Assurance Platform
  -> Quality Policies
  -> Planning Engine
  -> Execution Environment
  -> Execution Targets
  -> Evidence
  -> Reports
  -> Release Qualification
  -> Platform Baseline
```

The Platform Foundation defines what DJConnect is and which architecture
boundaries matter. The Platform Quality Standard defines the desired quality
baseline. Verification proves behaviour. Software Assurance governs the quality
system that surrounds building, scanning, verifying, releasing and evolving the
platform.

## Responsibility Boundaries

| Layer | Owns | Does not own |
| --- | --- | --- |
| Platform Foundation | Product, architecture, domain, ownership and governance truth. | Tool execution or quality evidence. |
| Verification Platform | Behavioural correctness, scenarios, adapters, evidence and readiness for behaviour. | Supply chain governance or repository health trends. |
| Software Assurance Platform | Quality governance, assurance themes, quality policies, evidence taxonomy, reporting and health trends. | Product behaviour, implementation logic or direct execution. |
| Planning Engine | Scenario, policy, mode, matrix, data, resource and cost-aware plan generation. | Execution, pass/fail evaluation or release decisions. |
| Execution Environment | Toolchains, dependencies, CI inspection, lab/runtime setup, snapshots and cleanup. | Expected behaviour, governance decisions or quality policy ownership. |
| Execution Targets | Running selected work on local, CI, self-hosted, hardware or lab environments. | Quality ownership or final release authority. |
| Release Qualification | Promotion, release gates, evidence review and final release decision. | Definition of product truth or duplicated evidence stores. |

## Assurance Flow

```text
Quality Theme
  -> Quality Policy
  -> Execution Profile
  -> Planned Work
  -> Execution Target
  -> Evidence
  -> Quality Report
  -> Platform Health Trend
  -> Roadmap or Release Decision Input
```

Quality themes define the area of concern. Quality policies define what level
of assurance is expected for a context. Execution profiles define the cost,
retention and environment posture. The Planning Engine turns this into planned
work. Execution targets produce evidence. Reports and health trends summarize
the evidence without replacing blocking policies.

## Execution Model

Software Assurance does not execute work itself.

Execution remains:

```text
Planning Engine
  -> Execution Environment
  -> Execution Targets
```

Execution targets include:

- local developer workstation;
- GitHub-hosted runner;
- self-hosted runner;
- local Home Assistant verification lab;
- physical client or hardware lab;
- future cloud runner.

GitHub Actions is an execution target and orchestration surface. It is not the
canonical owner of quality policy, evidence meaning or release authority.

## Cost-Aware Execution

Execution cost is a first-class architecture concern.

Software Assurance defines profile intent:

- Economy minimizes runtime, cloud minutes, hardware occupancy and retained
  artifacts.
- Balanced gives normal development confidence with representative coverage
  and structured evidence.
- Release maximizes release confidence with release-equivalent artifacts,
  stricter evidence, broader matrix coverage and longer retention.

The Planning Engine owns optimization:

- environment selection;
- parallelism;
- batching;
- retry planning;
- artifact retention planning;
- hardware scheduling;
- nightly strategy;
- estimated runtime;
- resource conflict avoidance.

Workflow files may later execute plans, but they must not become the place
where quality governance is invented.

## Evidence Architecture

Software Assurance evidence is classified by theme and source.

Evidence classes include:

- static analysis results;
- formatting and lint results;
- dependency and advisory snapshots;
- SBOM and license metadata;
- provenance and artifact integrity metadata;
- performance and runtime robustness observations;
- CI and workflow run metadata;
- verification evidence references;
- release qualification evidence;
- repository health observations;
- manual attestations where automation is not yet available.

Evidence should be referenced once and reused. Software Assurance may aggregate
or summarize evidence, but it must not duplicate the canonical raw evidence
owned by Verification or execution systems.

## Reporting Architecture

Reports are layered:

```text
Raw Evidence
  -> Theme Report
  -> Repository Health Report
  -> Platform Health Report
  -> Release Qualification Input
```

Theme reports explain one assurance area. Repository health reports summarize a
repository against platform quality expectations. Platform Health reports show
trend posture across repositories and assurance dimensions. Release
Qualification consumes the relevant reports and evidence according to release
policy.

## Platform Health Model

Platform Health is trend reporting. It is evidence-derived, reviewable and
non-authoritative for release gates.

Dimensions:

| Dimension | Meaning |
| --- | --- |
| Functional | Behavioural verification posture and known functional risks. |
| Security | Static security, secret safety, auth boundaries and vulnerability posture. |
| Supply Chain | Dependency, license, SBOM, provenance and artifact integrity posture. |
| Engineering | Code quality, test posture, CI reliability, documentation and maintainability. |
| Operational | Runtime robustness, diagnostics, incident readiness and release operations. |
| Repository | Per-repository hygiene, ownership alignment, bootstrap quality and drift. |

Health can recommend backlog work, highlight trends and inform release review.
It cannot convert a failed release-blocking policy into a pass.

## Integration With Verification

Software Assurance consumes Verification outputs through references:

- scenario plans;
- execution environment snapshots;
- evidence paths;
- reports;
- readiness decisions;
- investigator classifications;
- backlog items.

It does not redefine scenario expected results, adapter behaviour, readiness
states or the Verification Platform lifecycle.

The Verification Investigator remains the failure-classification workflow. If
an assurance finding points to behavioural uncertainty, it should produce a
Verification follow-up instead of being solved in Software Assurance alone.

## Integration With Meta Engineering

Meta Engineering defines how work is performed and how durable knowledge is
placed in the repository. Software Assurance follows that model:

- repository over prompt;
- completion reports over chat memory;
- decision placement in canonical docs;
- phase completion before next prompt generation;
- explicit ownership for follow-up work.

## Current Implementation Awareness

The current repository already has CI and analysis workflows for tests,
CodeQL, Semgrep, dependency-audit reporting and Verification Platform Docker
runtime release. Software Assurance architecture treats these as existing
signals and execution surfaces.

This architecture does not:

- add workflow triggers;
- change `continue-on-error` settings;
- add scanners;
- change release workflows;
- create required status checks;
- create release gates.

## Architecture Decision Rules

When adding future Software Assurance implementation:

1. Define the quality policy before adding scripts.
2. Prefer Planning Engine integration over workflow-specific logic.
3. Prefer reusable evidence contracts over one-off artifacts.
4. Keep behavioural checks in Verification.
5. Keep product architecture decisions in Foundation or ADRs.
6. Keep execution details in the Execution Environment or target repository.
7. Keep reports durable and redacted.
8. Avoid duplicate gates with different owners.

## Future Extension Points

Future phases may add:

- capability catalog implementation;
- backlog and milestone tracking;
- assurance policy catalog;
- SBOM and license evidence contracts;
- vulnerability and advisory ingestion;
- repository health report schema;
- Platform Health report generator;
- release assurance evidence bundle;
- cost-aware execution profile integration;
- cross-repository quality inventory.

Each extension requires its own explicit implementation prompt.

## Integration References

The canonical platform integration architecture is defined in:

- `SOFTWARE_ASSURANCE_INTEGRATION.md`
- `SOFTWARE_ASSURANCE_EXECUTION_MODEL.md`
- `SOFTWARE_ASSURANCE_PLATFORM_HEALTH.md`
- `SOFTWARE_ASSURANCE_REPOSITORY_MODEL.md`

These documents define interaction with the Verification Runtime, Execution
Environment, execution targets, Platform Health, Release Qualification and
cross-repository ownership. They do not implement tooling or change execution
ownership.

## Governance References

The architecture freeze, rollout and future implementation governance are
defined in:

- `SOFTWARE_ASSURANCE_GOVERNANCE.md`
- `SOFTWARE_ASSURANCE_ROLLOUT.md`
- `SOFTWARE_ASSURANCE_IMPLEMENTATION_STRATEGY.md`
- `SOFTWARE_ASSURANCE_QUALITY_GATES.md`
- `SOFTWARE_ASSURANCE_VERSIONING.md`

The final architecture decision is:

```text
SOFTWARE_ASSURANCE_PLATFORM_ARCHITECTURE_COMPLETE
```

The historical prerequisites in `SOFTWARE_ASSURANCE_GOVERNANCE.md` are
satisfied. Prompt 1 is complete and Prompt 2 is active pending explicit
execution; this implementation does not change the frozen architecture.
