# Golden Qualification Foundation

## Status

**Implemented deterministic server-side qualification foundation.** It is the
sole executable qualification path for `SI-GOLDEN-001`, `SI-GOLDEN-002` and
`SI-GOLDEN-003`. It runs locally through `djconnect.golden_qualification`; a
future CI invocation must reuse the same composition boundary.

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

`SI-GOLDEN-003` reports Presentation Verification as `not_applicable`: its
approved Silence has no narrative Presentation and verification must not
invent one. It remains qualified through its Session and Broadcast contract.

Reports contain only bounded statuses and invariant identifiers. They expose no
mutable Runtime state, Planner or Knowledge internals, renderer configuration,
audio or provider data. Runtime-only Presentation Context is not captured.

## Golden Smoke positioning

Golden Smoke is a future **execution profile** of this same qualification
pipeline, not a separate implementation. A future authorized Smoke profile may
select only `SI-GOLDEN-001`; a Golden Regression profile may select a broader
approved set. Both reuse the same Bootstrap, Driver, Capture, Validator and
reporting boundary.

This foundation introduces no CI workflow, scheduled run or release gate.

## Scope exclusions

No Renderer Host, browser UI, DOM, visual snapshot, animation, generated audio,
TTS provider, Apple, Home Assistant, Universal Receiver, VibeCast or hardware
behavior is tested. Those remain renderer responsibilities.

## References

- [Session Intelligence E2E Verification Architecture](SESSION_INTELLIGENCE_E2E_ARCHITECTURE.md)
- [Presentation Verification Architecture](PRESENTATION_VERIFICATION_ARCHITECTURE.md)
- [Session Intelligence Qualification Policy](SESSION_INTELLIGENCE_QUALIFICATION_POLICY.md)
