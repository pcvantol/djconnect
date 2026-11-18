# Session Intelligence Qualification Policy

## Status

Canonical engineering policy for Session Intelligence qualification.

## Purpose

Golden Scenarios are versioned product-behavior contracts. Each protects one
approved, user-visible Session Intelligence behavior; it is not an
implementation test or a branch-coverage target. Verification infrastructure
exists only to execute, observe or validate these approved contracts.

## Qualification pyramid

| Layer | Qualification layer | Purpose | Intended execution | Initial gate |
| --- | --- | --- | --- | --- |
| 1 | Unit Tests | Protect local implementation correctness. | Every implementation PR | Blocking |
| 2 | Integration Tests | Protect subsystem boundaries. | Every implementation PR | Blocking |
| 3 | Golden Qualification Foundation | Execute the canonical deterministic server-side path for current Session Intelligence and Presentation evidence. | Local development and advisory CI reuse | Implemented; no required CI gate |
| 4 | Golden Smoke profile | Select the smallest approved end-to-end behavior, `SI-GOLDEN-001`, from the Foundation. | Local development and advisory pull-request CI | Implemented; advisory only |
| 5 | Golden Regression profile | Select the complete approved Session Intelligence catalogue, `SI-GOLDEN-001` through `SI-GOLDEN-006`, from the Foundation. | Local development and advisory `main`, manual and scheduled CI | Implemented; advisory only |
| 6 | Advisory Intelligence Quality Metrics | Provide bounded, report-derived qualification insight. | Optional local report section | Implemented; advisory only |

Golden Smoke remains deterministic, fast, stable and small enough for routine
CI. Golden Regression is the broader qualification suite. Both are execution
profiles of the implemented
[Golden Qualification Foundation](GOLDEN_QUALIFICATION_FOUNDATION.md), not
separate verification implementations. Advisory CI uses the existing Smoke
profile for pull requests and the existing Regression profile for `main`,
manual and scheduled qualification. The CI workflow remains non-blocking and
non-required. The future
[Presentation Verification Architecture](PRESENTATION_VERIFICATION_ARCHITECTURE.md)
adds a distinct Presentation Golden Scenario family before either qualification
layer is extended. It verifies immutable Presentation composition and
renderer-safe Broadcast projection, never renderer output.

## Quality metrics policy

Intelligence Quality Metrics v1 is a bounded, schema-versioned and transient
projection of an immutable `GoldenQualificationReport`. It is strictly
advisory: the Structural Validator remains the sole success authority, and the
projection cannot alter qualification PASS/FAIL, execution, Capture or
validation.

It includes only objective report-derived metadata, scenario coverage and
counts, session-verification and determinism rates, applicable Presentation
verification and pass rate, and aggregated invariant-failure identifiers. It
does not retain history, set thresholds or scores, create a gate, or expose
prompts, Moment text, Runtime state, Planner or Knowledge state, provider or
renderer data, memory, credentials or raw evidence.

## Scenario relationship for new capabilities

Every future Session Intelligence capability must identify one of the
following:

- the Golden Scenario it introduces;
- the existing Golden Scenario it extends; or
- the existing Golden Scenario it must continue to satisfy.

A capability without that relationship requires explicit architectural
justification. A Verification capability must in turn enable execution,
observation or validation of one or more approved Golden Scenarios; technical
interest alone is not sufficient scope justification.

The [Golden Scenario Governance](GOLDEN_SCENARIO_GOVERNANCE.md) defines the
mandatory relationship declaration, behavioral-preservation and
duplicate-execution-path checks for capability Pre-Flight. This qualification
policy continues to own qualification layers and metric-promotion rules.

## CI policy boundary

The current policy executes Unit Tests, Integration Tests and advisory Golden
Smoke for production-code implementation pull requests. Advisory Golden
Regression runs in broader `main`, manual and scheduled-verification contexts.
Neither profile is a required check, merge protection or release gate. A future
promotion or extension to further Golden Scenario families requires separate
governance and does not alter the current suite.

This document defines qualification policy. The advisory CI workflow reuses the
existing scenario execution and bounded report projection; it does not alter
metrics, Runtime behavior or Verification infrastructure.

## References

- [Golden Scenario Catalogue](SESSION_INTELLIGENCE_GOLDEN_SCENARIOS.md)
- [Golden Scenario Governance](GOLDEN_SCENARIO_GOVERNANCE.md)
- [E2E Verification Architecture](SESSION_INTELLIGENCE_E2E_ARCHITECTURE.md)
- [Presentation Verification Architecture](PRESENTATION_VERIFICATION_ARCHITECTURE.md)
- [Golden Qualification Foundation](GOLDEN_QUALIFICATION_FOUNDATION.md)
- [Developer Experience Roadmap](../product/DEVELOPER_EXPERIENCE_ROADMAP.md)
