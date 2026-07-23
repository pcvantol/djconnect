# Golden Qualification Foundation

## Status

**Implemented deterministic server-side qualification foundation.** It is the
sole executable qualification path for all six original Session Intelligence
Golden Scenarios (`SI-GOLDEN-001` through `SI-GOLDEN-006`). It runs locally
through `djconnect.golden_qualification`; a future CI invocation must reuse
the same composition boundary.

## Canonical execution

```text
Playback Observation fixture
  -> Developer Session Bootstrap
  -> Deterministic Scenario Driver
  -> Session Runtime -> Planner -> Knowledge Engine -> DJ Moment Engine
  -> Presentation Composer -> immutable Presentation
  -> Session Flow and renderer-safe Broadcast Projection
  -> immutable Capture -> Structural Validation -> Qualification report
```

The Foundation only composes the existing Bootstrap, Driver, Capture and
Validator. It stops every isolated Session and executes each scenario twice to
compare normalized immutable server-owned outputs. It is not a second Runtime,
Scenario Driver, Capture, validator or replay path.

## Qualification contract

Each scenario reports Session Verification, Presentation Verification and
Overall Qualification. Session Verification covers the existing Planner,
Knowledge, immutable DJMoment and Session Flow assertions. Where Presentation
exists, Presentation Verification covers source identity, mode, ordered Speech
segments, semantic Speaker Roles, safe fallback and renderer-safe projection.
Overall Qualification requires both executions to pass and to be equivalent.

`SI-GOLDEN-004` reports Presentation Verification as `not_applicable`: it is
deliberately planning-only and must not force a DJMoment, Presentation, Flow
rewrite or Broadcast planning projection. `SI-GOLDEN-003` and
`SI-GOLDEN-006` also report it as `not_applicable`: their Silence contracts
do not require narrative Speech Presentation. `SI-GOLDEN-006` may retain the
existing non-speech renderer-safe Presentation projection when the canonical
domain model produces one; qualification never fabricates one for uniformity.
All three remain qualified through their respective Session and Broadcast
contracts.

Reports contain only bounded statuses and invariant identifiers. They expose no
mutable Runtime state, Planner or Knowledge internals, renderer configuration,
audio or provider data. Runtime-only Presentation Context is not captured.

## Golden Smoke positioning

Golden Smoke is an implemented **execution profile** of this same
qualification pipeline, not a separate implementation. It selects only
`SI-GOLDEN-001` through `djconnect.golden_smoke`. A Golden Regression profile
may later select a broader approved set. Both reuse the same Bootstrap, Driver,
Capture, Validator and reporting boundary.

Golden Smoke introduces no CI workflow, scheduled run or release gate.

## Scope exclusions

No Renderer Host, browser UI, DOM, visual snapshot, animation, generated audio,
TTS provider, Apple, Home Assistant, Universal Receiver, VibeCast or hardware
behavior is tested. Those remain renderer responsibilities.

## References

- [Session Intelligence E2E Verification Architecture](SESSION_INTELLIGENCE_E2E_ARCHITECTURE.md)
- [Presentation Verification Architecture](PRESENTATION_VERIFICATION_ARCHITECTURE.md)
- [Session Intelligence Qualification Policy](SESSION_INTELLIGENCE_QUALIFICATION_POLICY.md)
