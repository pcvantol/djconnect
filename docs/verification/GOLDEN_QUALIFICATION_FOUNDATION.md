# Golden Qualification Foundation

## Status

**Implemented deterministic server-side qualification foundation.** It is the
sole executable qualification path for all six original Session Intelligence
Golden Scenarios (`SI-GOLDEN-001` through `SI-GOLDEN-006`). It runs locally
through `djconnect.golden_qualification` and in advisory CI through the same
composition boundary.

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

## Execution profiles

Golden Smoke is an implemented **execution profile** of this same
qualification pipeline, not a separate implementation. It selects only
`SI-GOLDEN-001` through `djconnect.golden_smoke`.

Golden Regression is the implemented local **broader execution profile**. It
selects the immutable canonical Session Intelligence contract,
`SI-GOLDEN-001` through `SI-GOLDEN-006`, through
`djconnect.golden_regression`. Its bounded report identifies
`profile: golden_regression` and `profile_version: 1`. It only delegates to
this Foundation, so it reuses the same Bootstrap, Driver, Runtime, Capture,
Validator, cleanup and two-run deterministic comparison.

The advisory CI integration invokes Smoke for pull requests and Regression for
`main`, manual and scheduled qualification through these same profiles. It
publishes only an allowlist-validated Markdown Job Summary and creates no
required check, release gate or alternate execution path.

## Universal Receiver Browser E2E

The implemented optional Browser E2E observer attaches to the existing active
Foundation execution through the already-authorized, runtime-scoped Broadcast
viewer contract. It executes the existing `/djconnect/receiver` page in a
deterministic headless runtime and observes only snapshot-first delivery,
ordered renderer-safe events, reconnect, Runtime termination and subscription
cleanup. Pull-request CI observes Golden Smoke; `main`, manual and scheduled
CI observe Golden Regression. The workflow remains advisory and non-blocking.

The observer has no Session, Runtime, Planner, Knowledge, Capture or Validator
ownership. It does not alter the two-run comparison, Structural Validator
authority, qualification result or bounded Qualification Report. Its transient
token and renderer inputs remain process-local; no browser state, token, raw
Broadcast payload, screenshot, trace, HAR, video or DOM baseline is published
or retained.

## Advisory Intelligence Quality Metrics

Each existing bounded qualification report can optionally include an
**Intelligence Quality Metrics v1** section. It is a transient, read-only
projection created only after the Foundation has produced its immutable
`GoldenQualificationReport`; it is not a second qualification or evidence
model. The section is selected with `include_advisory_metrics: true` on a
Golden Foundation, Smoke or Regression developer service.

Metrics v1 is schema-versioned and limited to report-derived profile metadata,
scenario selection and execution counts, coverage, session-verification and
determinism rates, applicable Presentation-verification count and pass rate,
and aggregated invariant-failure identifier counts. Its `advisory_status` is
always advisory. It cannot influence Structural Validator authority, the
qualification PASS/FAIL result, Foundation execution or cleanup.

The projection retains no history and exposes no prompts, Moment text, Runtime
objects, Planner or Knowledge state, provider or renderer information, memory,
credentials, or raw evidence.

## Scope exclusions

No visual presentation, screenshot, DOM baseline, animation, generated audio,
TTS provider, Apple, Home Assistant, VibeCast or hardware behavior is tested.
The optional Universal Receiver observer validates only renderer-host Broadcast
transport integration; all other renderer behavior remains renderer-owned.

## References

- [Session Intelligence E2E Verification Architecture](SESSION_INTELLIGENCE_E2E_ARCHITECTURE.md)
- [Presentation Verification Architecture](PRESENTATION_VERIFICATION_ARCHITECTURE.md)
- [Session Intelligence Qualification Policy](SESSION_INTELLIGENCE_QUALIFICATION_POLICY.md)
