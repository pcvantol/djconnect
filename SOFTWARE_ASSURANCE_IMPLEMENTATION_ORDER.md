# DJConnect Software Assurance Implementation Order

Status: canonical implementation order  
Scope owner: `pcvantol/djconnect`  
Phase: architecture and backlog only; no implementation

## Purpose

This document groups Software Assurance capabilities into implementation
milestones. It defines order and rationale, not calendar dates.

## Implementation Principles

- Implement contracts before tools.
- Implement evidence before gates.
- Implement reporting before dashboards.
- Implement repository-local extensions only after canonical platform models.
- Keep Verification as owner of behavioural correctness.
- Do not modify CI or enable gates unless a future milestone explicitly asks
  for that implementation and review.

## Milestone SA-M0: Foundation Contracts

Priority: P0

Goal: make Software Assurance implementable without duplicating evidence or
governance.

Capabilities:

- `SA-X01` Evidence Contract
- `SA-X02` Policy Catalog
- `SA-X03` Reporting Contract
- `SA-X04` Configuration Model
- `SA-X05` Ownership Registry
- `SA-EX01` Execution Profiles
- `SA-EX12` Artifact Retention
- `SA-RA05` Release Evidence
- `SA-PH01` Health Metrics

Rationale:

These capabilities are shared roots for all themes. Without them, future
implementation would likely hardcode policy in scripts or duplicate evidence.

Exit criteria:

- canonical schemas and examples exist;
- no tool execution is required;
- all future findings can identify owner, evidence, severity and release
  impact.

## Milestone SA-M1: Repository Quality Inventory

Priority: P1

Goal: produce first useful quality posture across repositories without gates.

Capabilities:

- `SA-SQ01` Formatting
- `SA-SQ02` Linting
- `SA-SQ03` Static Analysis
- `SA-SQ07` Documentation Validation
- `SA-SQ08` Architecture Drift Detection
- `SA-SQ09` Repository Drift Detection
- `SA-SC01` Dependency Governance
- `SA-SC07` Dependency Drift
- `SA-SC08` License Compliance
- `SA-PH05` Repository Health

Rationale:

This milestone turns the platform quality standard into visible repository
health while staying advisory.

Exit criteria:

- repository health reports exist;
- findings map to owner and backlog;
- existing CI/scanner signals are referenced, not reconfigured.

## Milestone SA-M2: Supply Chain and Artifact Evidence

Priority: P1

Goal: make dependencies and release artifacts traceable.

Capabilities:

- `SA-SC02` SBOM
- `SA-SC05` CVE Advisory Mapping
- `SA-SC09` Artifact Provenance
- `SA-SC10` Checksums
- `SA-SC12` Release Metadata
- `SA-SC13` Container Provenance
- `SA-RA08` Artifact Validation

Rationale:

Supply chain posture is required before release assurance can be trusted.

Exit criteria:

- artifact evidence can trace source, SHA, metadata and integrity;
- vulnerability findings have release impact classification;
- release repositories remain distribution surfaces only.

## Milestone SA-M3: Execution Governance

Priority: P1

Goal: let the Planning Engine reason about cost, targets, retention and
resources before execution.

Capabilities:

- `SA-EX05` Scheduling
- `SA-EX06` Parallelism
- `SA-EX07` Concurrency
- `SA-EX09` Runner Qualification
- `SA-EX13` Nightly Strategy
- `SA-EX14` Execution Budget
- `SA-X09` Compatibility Model

Rationale:

Execution governance must exist before expensive dynamic, hardware or release
assurance work is automated.

Exit criteria:

- execution profiles map to budgets and targets;
- runner capabilities can be qualified;
- nightly and release execution are planned, not enabled by accident.

## Milestone SA-M4: Release Assurance Readiness

Priority: P1

Goal: define and produce release-assurance inputs without enabling gates.

Capabilities:

- `SA-RA01` Release Gates
- `SA-RA03` Promotion
- `SA-RA04` Rollback
- `SA-RA06` Compatibility Validation
- `SA-RA07` Release Qualification
- `SA-PH07` Verification Health
- `SA-PH10` Supply Chain Health

Rationale:

Release qualification needs to consume Verification and Software Assurance
evidence through one model.

Exit criteria:

- release qualification reports can be generated as advisory inputs;
- compatibility references Verification evidence;
- no release gate is enabled until a later explicit phase.

## Milestone SA-M5: Dynamic Runtime Assurance

Priority: P2

Goal: add runtime quality signals beyond behavioural pass/fail.

Capabilities:

- `SA-DR01` Performance
- `SA-DR02` Stress
- `SA-DR06` Fuzz
- `SA-DR07` Memory
- `SA-DR08` Resource Usage
- `SA-DR09` Runtime Diagnostics
- `SA-DR10` Recovery
- `SA-DR11` Resilience
- `SA-PH08` Operational Health

Rationale:

Dynamic runtime work is higher-cost and needs execution governance first.

Exit criteria:

- dynamic findings are classified without redefining Verification scenarios;
- runtime diagnostics remain redacted;
- operational health can be reported.

## Milestone SA-M6: Health Trends and Budgets

Priority: P1/P2

Goal: make Software Assurance useful for long-term platform decisions.

Capabilities:

- `SA-X06` Metrics Contract
- `SA-PH02` Trend Analysis
- `SA-PH03` Historical Baselines
- `SA-PH04` Quality Budgets
- `SA-PH06` Engineering Health
- `SA-PH09` Security Health
- `SA-PH12` Reporting
- `SA-X08` Backlog Integration

Rationale:

Trend reporting helps prioritize work but must not override release policies.

Exit criteria:

- health reports show stale, missing, improving and degrading evidence;
- quality budgets create backlog pressure, not hidden gates;
- reports remain durable and redacted.

## Milestone SA-M7: Advanced Assurance Expansion

Priority: P2/P3

Goal: deepen advanced analysis after the foundation is useful.

Capabilities:

- `SA-SQ04` Language-specific Analyzers
- `SA-SQ05` Code Quality
- `SA-SQ06` Complexity Analysis
- `SA-SQ10` Prompt Drift Detection
- `SA-SC03` SPDX
- `SA-SC04` CycloneDX
- `SA-SC06` EPSS/KEV Risk Enrichment
- `SA-SC11` Signing
- `SA-DR03` Load
- `SA-DR04` Chaos
- `SA-DR05` Mutation
- `SA-EX02` Cloud Execution
- `SA-EX03` Self-hosted Execution
- `SA-EX04` Hybrid Execution
- `SA-EX08` Hardware Allocation
- `SA-EX10` Runner Health

Rationale:

These capabilities improve depth but should not block early assurance value.

Exit criteria:

- advanced evidence flows through the same contracts;
- expensive work is scheduled through cost governance;
- repository-specific implementation remains opt-in by milestone.

## Milestone SA-M8: Dashboards and Notifications

Priority: P3

Goal: make assurance posture easier to consume after reports are stable.

Capabilities:

- `SA-PH11` Dashboard
- `SA-X10` Notification Model
- `SA-EX11` Runner Cost Optimisation

Rationale:

Dashboards and notifications should render already-stable evidence rather than
becoming the source of quality truth.

Exit criteria:

- dashboard consumes report data only;
- notifications route by owner and severity;
- cost optimization is advisory and preserves required evidence.

## Future Implementation Wave Summary

| Milestone | Primary outcome | Blocking posture |
| --- | --- | --- |
| SA-M0 | Contracts and shared governance. | Required before implementation. |
| SA-M1 | Advisory repository health inventory. | Advisory. |
| SA-M2 | Supply chain and artifact evidence. | Advisory until policies promote. |
| SA-M3 | Execution governance. | Enables safe planning. |
| SA-M4 | Release assurance readiness. | Advisory until release gates are explicitly enabled. |
| SA-M5 | Dynamic runtime quality evidence. | Policy-scoped. |
| SA-M6 | Platform Health trends and budgets. | Trend/advisory. |
| SA-M7 | Advanced assurance depth. | Policy-scoped. |
| SA-M8 | Consumption surfaces. | Non-authoritative UI/notification layer. |

## Stop Rule

This document does not authorize implementation. Each milestone requires a
future explicit implementation prompt and must complete according to
`docs/meta/PHASE_COMPLETION_PROTOCOL.md`.
