# Automated Session Intelligence E2E Verification Roadmap

## Status

**Primary active Epic:** Automated Session Intelligence E2E Verification.

The single recommended next capability is **Automated Session Intelligence E2E
Verification Architecture**. This document is a roadmap and governance record;
it authorizes no implementation of CI, Developer Mode, simulation, browser
testing or runtime behavior.

## Purpose

Developer Mode exists primarily to make the real Session Intelligence pipeline
fully automated, deterministic and headless in CI. Interactive Home Assistant
Developer Tools use is secondary convenience, never a CI prerequisite.

The target test path is:

```text
CI runner -> isolated Home Assistant development environment
-> Developer Session Bootstrap -> deterministic Scenario Driver
-> Playback Observation Boundary or approved test adapter
-> Session Runtime -> Planning Runtime Coordinator -> Planner
-> Knowledge Engine -> DJ Moment Engine -> Session Flow -> Broadcast
-> E2E Session Capture -> invariant and regression evaluation -> CI artifacts
```

The test system must reuse production-owned normalized contracts and the one
canonical Runtime pipeline. It must not create an alternative Intelligence
Engine or inject test-specific business logic into Runtime, Planner, Knowledge,
DJ Moment Engine, Session Flow or Broadcast.

## Automation requirements

The baseline suite must have zero manual interaction, deterministic inputs and
cleanup, bounded headless execution and isolated test state. It must be
reproducible locally and in CI, independent of a developer's Spotify account
and live external providers, and leave no persistent test Session, Broadcast
credential, Profile mutation or production-data change. Failures must retain
useful redacted artifacts.

CI must never require a human to copy a Session identifier or Broadcast
credential. The server-side automation boundary returns only the bounded,
ephemeral information required by its invoking test process.

## Enabling capability: Developer Session Bootstrap

Developer Session Bootstrap is the first enabling capability in this Epic; its
primary consumer is automated CI. A future bounded machine-readable Home
Assistant boundary may start an ordinary server-owned Session for a deterministic
development Profile or fixture, return internal bootstrap output to the test
process, establish ephemeral session-scoped Broadcast access where required,
and stop and clean up deterministically.

It must reuse the production Session Runtime lifecycle. A browser never creates
a Session, CI never performs a manual token exchange, and the boundary does not
own Planner, Knowledge, Moments, Flow or Broadcast behavior.

## Ordered delivery sequence

Only the first item is active. Each later item requires predecessor evidence
and a separately authorized capability.

| Order | Capability | Status | Boundary |
| --- | --- | --- | --- |
| 1 | Automated Session Intelligence E2E Verification Architecture | Active / next | Defines test-host ownership, production-boundary reuse, bootstrap, scenario, clock, capture, validation, CI shape, security, artifacts and staged rollout. |
| 2 | Developer Session Bootstrap | Planned | Enables machine-readable, server-owned Session startup, scoped test access and cleanup for CI. |
| 3 | Deterministic Scenario Driver | Planned | Supplies provider-independent scripted normalized inputs without fabricating provider-owned occurrence identity. |
| 4 | Immutable E2E Session Capture | Planned | Captures safe canonical outcomes and cleanup evidence. |
| 5 | Structural Invariant Validator | Planned | Blocks immediate architectural and lifecycle violations. |
| 6 | CI Smoke Suite | Planned | Runs bounded selected scenarios in an isolated headless environment. |
| 7 | Accelerated / event-driven Session execution | Planned | Uses approved infrastructure clock/observation controls, never business-logic conditionals. |
| 8 | Golden Session Regression Suite | Planned | Applies versioned semantic and structural expectations. |
| 9 | Intelligence Quality Metrics | Planned, initially non-blocking | Reports stable metrics before any governance-approved blocking threshold. |
| 10 | Full CI Qualification and readable reports | Planned | Expands scenario coverage, artifacts and explicit qualification shape. |
| 11 | Universal Receiver browser E2E | Optional / separate layer | Validates Receiver presentation through Broadcast and a headless browser, not core Intelligence behavior. |
| 12 | Read-only Developer Overlay | Optional / deferred | Development-only, non-authoritative and disabled in production by default. |
| 13 | Optional TTS Session Replay | Deferred | Reuses eligible presentation output without canonical audio persistence. |
| 14 | Optional side-by-side Session comparison | Deferred | Compares capture artifacts without creating a competing planner. |

## Scenario and execution policy

The future Scenario Driver may script Session start strategy, Mood, Persona,
Direction, observable current track, bounded upcoming projection, Track Started
transitions, metadata availability or absence, typed knowledge failure,
invalidation, replanning, Session Update, Silence and Session end. Baseline
scenarios remain provider-independent and must not invent provider-owned
playback occurrence identity.

Accelerated execution follows bootstrap, scenario and capture contracts. It
uses an injectable or controlled test clock only at approved infrastructure
boundaries and accelerated or event-driven observation timing. Production
owners consume the same normalized contracts in real and automated scenarios;
scattered `developer_mode`, `test_mode` or `accelerated` business-logic paths
are prohibited.

## E2E Session Capture and validation layers

The future immutable capture artifact is redacted and versioned. Where safe and
available it records scenario identity/version, fixture revision, Session
configuration, normalized playback timeline, planning generations, selected and
approved intents, readiness and prefetch outcomes, immutable DJMoments, Silence
and Session Update decisions, Transitions, Flow ordering, renderer-safe
Broadcast projections, fallbacks, warnings, completion and cleanup result.

Validation is deliberately layered:

1. **Structural invariants** — Session lifecycle, one canonical approval path,
   immutable/non-duplicate Moments, Flow ordering, expected Broadcast projection,
   generation safety and complete cleanup. These may block CI immediately.
2. **Deterministic behavioral expectations** — approved fixed-fixture policies
   such as Performance Memory repetition avoidance, safe knowledge fallback,
   obsolete-plan supersession and earliest-eligible approval. These block only
   after their contract is explicitly approved.
3. **Intelligence quality metrics** — repetition and Silence ratios, Moment
   distribution, recommendation diversity, fallback use, replanning churn and
   transition frequency. These start as non-blocking artifacts; a blocking
   threshold requires a stable definition, approved baseline, understood false
   positives and explicit governance authorization.

Golden Sessions are versioned scenario definitions with structural invariants,
approved deterministic expectations, optional quality baselines and schema
compatibility. Prefer semantic and structural assertions; narrative text is not
byte-compared unless a narrative contract is explicitly deterministic.

## CI and renderer separation

The later CI shape must provision an isolated environment, execute selected
baseline scenarios with timeouts, publish readable redacted captures and
failure diagnostics, clean up even after failure, and report clear pass/fail.
The choice between per-PR smoke and broader main/release/scheduled suites stays
for the architecture capability after inspecting runner capacity and CI
governance.

Core Intelligence Engine validation is headless and frontend-independent. A
separate optional Renderer E2E layer may later verify:

```text
Session Bootstrap -> Broadcast -> headless browser -> Receiver DOM assertions
```

That validates the Universal Receiver only; it is not a dependency of core
Intelligence regression coverage. Universal Receiver remains local-first and
installation-owned, with no mandatory DJConnect cloud dependency.

## Completed and deferred work

Completed work is not proposed again: Session Intelligence Runtime Integration,
Universal Receiver Architecture, Receiver Broadcast connection/lifecycle,
Session Flow Timeline, renderer-safe Playback Projection and Now Playing.
Every future capability requires a current-main Pre-Flight against these
records.

Preferences and feedback semantics, Music DNA expansion, Narrative Sequencing,
Lyrics, Discover evolution and Audience Intelligence remain deferred. Audience
is low priority. Playback Observation Stage 2 and Continue Stage 2 remain
separately blocked by backend-owned Playback Instance Identity. The E2E
foundation must exist before material new Intelligence Engine complexity.
