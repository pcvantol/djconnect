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

Epic 8: Website and Product Story
  -> phases to be defined after product-language audit

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

Epic 7 should roll out the platform quality standard across repositories using Epic 2 discovery scores and registers.

## Epic 8

Epic 8 should align public product story, onboarding and website language with the Foundation.

## Rule

Do not use this roadmap as a substitute for architecture design. It defines order, not implementation details.
