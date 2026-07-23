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
| 3 | Golden Qualification Foundation | Execute the canonical deterministic server-side path for current Session Intelligence and Presentation evidence. | Local development and future CI reuse | Implemented; no CI gate yet |
| 4 | Golden Smoke profile | Select the smallest approved end-to-end behavior, initially `SI-GOLDEN-001`, from the Foundation. | Every production-code implementation PR | Future separately authorized gate |
| 5 | Golden Regression profile | Select the broader approved catalogue from the Foundation. | `main`, release qualification and scheduled verification | Determined by repository policy for each execution context |
| 6 | Quality Reports | Observe long-term Intelligence quality. | Qualification reporting | Non-blocking |

Golden Smoke must remain deterministic, fast, stable and small enough for
routine CI. Golden Regression is the broader qualification suite. Both are
future execution profiles of the implemented
[Golden Qualification Foundation](GOLDEN_QUALIFICATION_FOUNDATION.md), not
separate verification implementations. This policy does not define their CI
workflow. The future
[Presentation Verification Architecture](PRESENTATION_VERIFICATION_ARCHITECTURE.md)
adds a distinct Presentation Golden Scenario family before either qualification
layer is extended. It verifies immutable Presentation composition and
renderer-safe Broadcast projection, never renderer output.

## Quality metrics policy

Quality Reports may include repetition ratio, Silence ratio, recommendation
diversity, transition frequency, planning churn and fallback frequency. They
are observational and non-blocking by default.

A quality metric may become a release gate only when its definition is stable,
its baseline is approved, false-positive behavior is understood, and repository
governance explicitly authorizes promotion. No metric becomes blocking merely
because it can be measured.

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

The intended policy is that every production-code implementation PR eventually
executes Unit Tests, Integration Tests and Golden Smoke. Golden Regression runs
in broader `main`, release-qualification and scheduled-verification contexts.
Once separately authorized and implemented, these layers may include both
Session Intelligence and Presentation Golden Scenario families. That future
extension does not alter the current suite or authorize CI work.

This document defines qualification policy only. It does not implement GitHub
Actions, scenario execution, reporting, metrics, Runtime changes or
Verification infrastructure.

## References

- [Golden Scenario Catalogue](SESSION_INTELLIGENCE_GOLDEN_SCENARIOS.md)
- [Golden Scenario Governance](GOLDEN_SCENARIO_GOVERNANCE.md)
- [E2E Verification Architecture](SESSION_INTELLIGENCE_E2E_ARCHITECTURE.md)
- [Presentation Verification Architecture](PRESENTATION_VERIFICATION_ARCHITECTURE.md)
- [Golden Qualification Foundation](GOLDEN_QUALIFICATION_FOUNDATION.md)
- [Developer Experience Roadmap](../product/DEVELOPER_EXPERIENCE_ROADMAP.md)
