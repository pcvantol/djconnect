# DJConnect Implementation Roadmap

This document establishes the implementation sequence for future epics. It is intentionally high-level. Detailed phase content belongs in each Epic context and phase plan.

## Sequence

```text
Epic 3: Profile Architecture
  -> Phase 1
  -> Phase 2
  -> Phase 3
  -> Phase 4

Epic 4: Intelligence Engine / Insight Feed
  -> phases to be defined after Epic 3

Epic 5: Feature Flags, Capability Maturity and Client Parity
  -> phases to be defined after Epic 4 design

Epic 6: Distribution and Release Strategy
  -> phases to be defined after release-channel review

Epic 7: Platform Quality Standard rollout
  -> phases to be defined after repository-specific quality gaps are prioritized

Software Assurance Platform
  -> architecture complete
  -> implementation ready through registered explicit prompts

Architecture Closure Review
  -> frozen on 2026-07-11
  -> do not create more foundational architecture without evidence-backed review

Platform Qualification
  -> complete

Platform Baseline v1.0 Certification
  -> certified on 2026-07-12

Generation 1 Platform Engineering
  -> complete and frozen

Platform Evolution
  -> current lifecycle

Software Assurance Implementation
  -> Software Assurance Generation 1 is the active program
  -> begins only through its explicit Prompt 1
  -> Prompt 1 through Prompt 4 in registered order

Epic 8: Website and Product Story
  -> phases to be defined after Platform Baseline v1.0 certification and product-language audit

Future Cloud and Personal
  -> only after Profile Architecture and central trust/relay ADRs are accepted
```

## Epic 3

Epic 3 should start immediately after this implementation framework is merged.

Expected phase count:

- Phase 1
- Phase 2
- Phase 3
- Phase 4

Detailed phase content is intentionally not defined here. Epic 3 must begin with a dedicated Context prompt and phase plan using `docs/implementation/epic-template/`.

## Epic 4

Epic 4 should not start until Profile Architecture provides stable Profile resolution and privacy boundaries.

## Epic 5

Epic 5 should build on Profile Architecture and the Insight Feed design so feature flags and capability maturity are attached to the correct owners.

## Epic 6

Epic 6 should formalize release channels, public release repositories, store readiness and artifact validation.

## Epic 7

Epic 7 should roll out the platform quality standard across repositories using Epic 2 discovery scores, registers and the canonical Software Assurance Platform architecture.

## Software Assurance Platform

The Software Assurance Platform defines engineering quality governance above
the Verification Platform. Its architecture phase must complete before any
new scanners, CI gates, release gates or repository health tooling are
introduced.

Canonical architecture:

- `SOFTWARE_ASSURANCE_PLATFORM.md`
- `SOFTWARE_ASSURANCE_ARCHITECTURE.md`
- `SOFTWARE_ASSURANCE_THEMES.md`
- `SOFTWARE_ASSURANCE_CAPABILITY_MODEL.md`
- `SOFTWARE_ASSURANCE_BACKLOG.md`
- `SOFTWARE_ASSURANCE_DEPENDENCIES.md`
- `SOFTWARE_ASSURANCE_IMPLEMENTATION_ORDER.md`
- `SOFTWARE_ASSURANCE_INTEGRATION.md`
- `SOFTWARE_ASSURANCE_EXECUTION_MODEL.md`
- `SOFTWARE_ASSURANCE_PLATFORM_HEALTH.md`
- `SOFTWARE_ASSURANCE_REPOSITORY_MODEL.md`
- `SOFTWARE_ASSURANCE_GOVERNANCE.md`
- `SOFTWARE_ASSURANCE_ROLLOUT.md`
- `SOFTWARE_ASSURANCE_IMPLEMENTATION_STRATEGY.md`
- `SOFTWARE_ASSURANCE_QUALITY_GATES.md`
- `SOFTWARE_ASSURANCE_VERSIONING.md`

Implementation is intentionally deferred until an explicit post-baseline
implementation prompt starts Software Assurance work.

Canonical implementation registration:

- `SOFTWARE_ASSURANCE_IMPLEMENTATION.md`

The lifecycle transition is:

```text
Platform Qualification
  -> Platform Baseline v1.0 Certification
  -> Software Assurance Implementation
  -> Business-first Engineering
```

## Platform Baseline v1.0 Certification

The current Platform Baseline v1.0 certification result is
`PLATFORM_BASELINE_V1_CERTIFIED`.

Platform Baseline is not the completion of architecture. Architecture is
already frozen by the Architecture Closure Review. Platform Baseline certifies
the implemented and qualified platform after Platform Qualification has
produced sufficient evidence.

Canonical assessment artifacts:

- `PLATFORM_BASELINE_1_0.md`
- `PLATFORM_BASELINE_CERTIFICATION.md`
- `PLATFORM_BASELINE_GAP_ANALYSIS.md`

Generation 1 is complete. Future work proceeds under Platform Baseline v1.0
through normal platform evolution and the separately registered Software
Assurance implementation sequence.

## Architecture Closure Review

The Architecture Closure Review returned `ARCHITECTURE_FROZEN` on 2026-07-11.

Canonical closure artifacts:

- `ARCHITECTURE_CLOSURE_REVIEW.md`
- `ARCHITECTURE_DECISION.md`

Future work should proceed through implementation, verification, quality and
product evolution inside the frozen architecture. Additional foundational
architecture should be created only after a future evidence-backed Architecture
Review demonstrates a genuine gap.

## Epic 8

Epic 8 should align public product story, onboarding and website language with the Foundation.

## Rule

Do not use this roadmap as a substitute for architecture design. It defines order, not implementation details.
