# Automated Session Intelligence E2E Verification Roadmap

## Status

**Primary active Epic:** Automated Session Intelligence E2E Verification.

Golden Smoke, Golden Session Regression and Advisory Intelligence Quality
Metrics are complete. Accelerated / event-driven Session execution concluded
`NO-GO`: the existing restricted Verification Clock already satisfies every
approved behavior, and generic acceleration has no current product value. The
next Product Development candidate requiring a Pre-Flight is **Full CI
Qualification and readable reports**.
The Architecture,
Developer Session Bootstrap, Deterministic Scenario Driver, Immutable E2E
Session Capture and Structural Invariant Validator now execute all six original
Golden Scenarios. This document is a roadmap and governance record; it authorizes no implementation of CI,
Developer Mode, simulation, browser testing or runtime behavior.

The [Session Intelligence Qualification Policy](../verification/SESSION_INTELLIGENCE_QUALIFICATION_POLICY.md),
established in PR #378, defines the intended qualification layers and makes
Golden Scenarios the product-behavior contracts that Verification infrastructure
serves.

The [Golden Scenario Governance](../verification/GOLDEN_SCENARIO_GOVERNANCE.md)
records the mandatory scenario relationship and no-duplicate-execution-path
checks for future Verification and Session Intelligence increments.

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

## Completed enabling capability: Developer Session Bootstrap

Developer Session Bootstrap is the first completed enabling capability in this
Epic. PR #370 provides the bounded machine-readable Home Assistant boundary for
`SI-GOLDEN-001`: it starts and stops an isolated deterministic fixture through
the existing Runtime Manager and returns only bounded lifecycle information to
the invoking test process. It does not execute the Scenario, grant Broadcast
access, or own Runtime state.

It must reuse the production Session Runtime lifecycle. A browser never creates
a Session, CI never performs a manual token exchange, and the boundary does not
own Planner, Knowledge, Moments, Flow or Broadcast behavior.

## Ordered delivery sequence

Only the first item is active. Each later item requires predecessor evidence
and a separately authorized capability.

| Order | Capability | Status | Boundary |
| --- | --- | --- | --- |
| 1 | [Automated Session Intelligence E2E Verification Architecture](../verification/SESSION_INTELLIGENCE_E2E_ARCHITECTURE.md) | Complete | Defines test-host ownership, production-boundary reuse, bootstrap, scenario, clock, capture, validation, CI shape, security, artifacts and staged rollout. Its [Golden Scenario Catalogue](../verification/SESSION_INTELLIGENCE_GOLDEN_SCENARIOS.md) is the primary product artifact; [Golden Scenario Governance](../verification/GOLDEN_SCENARIO_GOVERNANCE.md) keeps future work product-driven and prevents duplicate execution paths. |
| 2 | [Developer Session Bootstrap](../technical/DEVELOPER_SESSION_BOOTSTRAP.md) | Complete — extended by PR #416 | Enables machine-readable, server-owned startup and cleanup for all six original approved scenarios; returns bounded lifecycle information and executes no scenario. |
| 3 | [Deterministic Scenario Driver](../technical/DETERMINISTIC_SCENARIO_DRIVER.md) | Complete — extended by PR #416 | Supplies only approved deterministic fixtures through the existing Runtime boundary, including planner-only bounded replanning. |
| 4 | Immutable E2E Session Capture | Complete — extended by PR #416 | Captures safe canonical outcomes and cleanup evidence for all six scenarios without Runtime mutation. |
| 5 | Structural Invariant Validator | Complete — extended by PR #416 | Deterministically assesses immutable capture evidence for all six original contracts; fails closed without Runtime participation. |
| 6 | Verification Clock Architecture | Complete | Accepts one restricted infrastructure-owned elapsed-time source for isolated verification Runtimes; implementation remains separate. |
| 7 | Verification Clock implementation for `SI-GOLDEN-002` | Complete — PR #382 | Binds the accepted Clock only at the Runtime composition boundary; executes, captures and structurally validates deterministic first-eligible Performance Memory repetition avoidance without changing production clock composition. |
| 8 | Original `SI-GOLDEN-001` through `SI-GOLDEN-006` behavioral roadmap | Complete — PR #416 | Completes the original six product contracts: normal flow, repetition avoidance, safe knowledge degradation, planner-only replanning, Session Update after repeated Silence and Intentional Silence. |
| 9 | [Golden Qualification Foundation](../verification/GOLDEN_QUALIFICATION_FOUNDATION.md) | Complete | Executes each of the six original approved scenarios twice through the existing server-side path and validates Session Intelligence, applicable Presentation and safe Broadcast evidence. |
| 10 | Golden Smoke execution profile | Complete | Selects only `SI-GOLDEN-001` from the same Qualification Foundation; no separate verification implementation or CI gate. |
| 11 | Accelerated / event-driven Session execution | Deferred — `NO-GO` | Existing Verification Clock satisfies all approved scenarios; no implementation remains unless a new approved time-dependent behavior justifies a fresh Pre-Flight. |
| 12 | [Presentation Verification Architecture](../verification/PRESENTATION_VERIFICATION_ARCHITECTURE.md) | Complete — PR #412 | Defines the server-side Presentation contract now exercised by the Qualification Foundation; no renderer, audio or CI implementation. |
| 13 | Presentation Golden Scenarios | Deferred | Future product contracts for Primary Only, Sidekick, fallback, projection and determinism; they reuse canonical Runtime execution and end at the renderer-safe projection. |
| 14 | Golden Session Regression profile | Complete — PR #422 | Fixed local `golden_regression` profile selects `SI-GOLDEN-001` through `SI-GOLDEN-006` through the same Qualification Foundation, with bounded profile version metadata and no CI gate. |
| 15 | Intelligence Quality Metrics | Complete — PR #425 | Optional transient, report-derived advisory projection; no scoring, threshold, gate or history. |
| 16 | Full CI Qualification and readable reports | Planned | Expands scenario coverage, artifacts and explicit qualification shape. |
| 17 | Universal Receiver browser E2E | Optional / separate layer | Validates Receiver presentation through Broadcast and a headless browser, not core Intelligence or server-side Presentation verification behavior. |
| 18 | Read-only Developer Overlay | Optional / deferred | Development-only, non-authoritative and disabled in production by default. |
| 19 | Optional TTS Session Replay | Deferred | Reuses eligible presentation output without canonical audio persistence. |
| 20 | Optional side-by-side Session comparison | Deferred | Compares capture artifacts without creating a competing planner. |

## Scenario and execution policy

The future Scenario Driver may script Session start strategy, Mood, Persona,
Direction, observable current track, bounded upcoming projection, Track Started
transitions, metadata availability or absence, typed knowledge failure,
invalidation, replanning, Session Update, Silence and Session end. Baseline
scenarios remain provider-independent and must not invent provider-owned
playback occurrence identity.

The [Verification Clock Architecture](../verification/VERIFICATION_CLOCK_ARCHITECTURE.md)
accepts a restricted verification-only elapsed-time source at the Runtime
composition boundary. Accelerated execution remains separately authorized.
Production owners consume the same normalized contracts in real and automated
scenarios; scattered `developer_mode`, `test_mode` or `accelerated`
business-logic paths are prohibited.

## E2E Session Capture and validation layers

The future immutable capture artifact is redacted and versioned. Where safe and
available it records scenario identity/version, fixture revision, Session
configuration, normalized playback timeline, planning generations, selected and
approved intents, readiness and prefetch outcomes, immutable DJMoments, Silence
and Session Update decisions, Transitions, Flow ordering, renderer-safe
Broadcast projections, fallbacks, warnings, completion and cleanup result.

Validation is deliberately layered:

1. **Structural invariant assessment** — Session lifecycle, one canonical approval path,
   immutable/non-duplicate Moments, Flow ordering, expected Broadcast projection,
   generation safety and complete cleanup. These may block CI immediately.
2. **Deterministic behavioral assessment** — approved fixed-fixture policies
   such as Performance Memory repetition avoidance, safe knowledge fallback,
   obsolete-plan supersession and earliest-eligible approval. These block only
   after their contract is explicitly approved.
3. **Quality observations** — repetition and Silence ratios, Moment
   distribution, recommendation diversity, fallback use, replanning churn and
   transition frequency. These start as non-blocking artifacts; a blocking
   threshold requires a stable definition, approved baseline, understood false
   positives and explicit governance authorization.

Golden Sessions are versioned scenario definitions with structural invariants,
approved deterministic expectations, optional quality baselines and schema
compatibility. Prefer semantic and structural assertions; narrative text is not
byte-compared unless a narrative contract is explicitly deterministic.

Presentation Verification is a separate future server-side layer. It proves
immutable Presentation composition, bounded Context handling and renderer-safe
Broadcast projection; it ends before any Renderer Host. Its future Presentation
Golden Scenarios may precede an extension of Golden Smoke and Golden Regression,
but do not authorize renderer, visual, audio, TTS, hardware or CI work.

## CI and renderer separation

The later CI shape must provision an isolated environment, execute selected
baseline scenarios with timeouts, publish readable redacted captures and
failure diagnostics, clean up even after failure, and report clear pass/fail.
Golden Smoke and broader Golden Regression placement are governed by the
[Session Intelligence Qualification Policy](../verification/SESSION_INTELLIGENCE_QUALIFICATION_POLICY.md).
This roadmap still authorizes no CI workflow implementation.

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
