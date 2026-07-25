# Automated Session Intelligence E2E Verification Architecture

## Status

**Accepted architecture with Bootstrap, Driver, immutable Capture and
Structural Invariant Validator implemented for all six original Session
Intelligence Golden Scenarios.** These
boundaries remain narrow production-lifecycle, event-injection and read-only
observation infrastructure only; this document defines no CI workflow or
production Runtime behavior change.

The companion [Golden Scenario Catalogue](SESSION_INTELLIGENCE_GOLDEN_SCENARIOS.md)
is the primary product artifact. Verification infrastructure exists only to
execute those approved behaviors automatically.

The companion [Golden Scenario Governance](GOLDEN_SCENARIO_GOVERNANCE.md)
requires future Verification and Session Intelligence capabilities to declare
their relationship to those approved behaviors and prevents duplicate
execution paths.

This architecture remains the canonical E2E contract for **Session
Intelligence** behavior. The separate
[Presentation Verification Architecture](PRESENTATION_VERIFICATION_ARCHITECTURE.md)
defines the future read-only verification boundary for deterministic
Presentation composition and renderer-safe projection. It neither broadens
this capture into renderer verification nor changes the semantic Golden
Scenario family.

The [Golden Qualification Foundation](GOLDEN_QUALIFICATION_FOUNDATION.md)
now composes the existing execution path twice per executable scenario and
reports Session Verification, Presentation Verification and Overall
Qualification. It ends at renderer-safe Broadcast projection and creates no
renderer, CI or alternate verification path.

## Purpose

DJConnect must protect user-visible Session Intelligence behavior end to end.
The future system therefore observes the canonical production path rather than
participating in it:

```text
Isolated test host
  -> production-boundary bootstrap
  -> normalized observation or approved test adapter
  -> Session Runtime -> Planning Runtime Coordinator -> Planner
  -> Knowledge Engine -> DJ Moment Engine -> Presentation Composer
  -> Session Flow -> Broadcast
  -> immutable E2E capture -> validation -> redacted CI artifacts
```

This is not a second Runtime, Planner, Knowledge Engine, Broadcast
implementation, browser application or diagnostics product. It neither
replaces unit tests nor replaces integration tests. It verifies approved
cross-component behavior that those narrower layers cannot prove alone.

## Ownership and boundaries

| Owner | Responsibility | Does not own |
| --- | --- | --- |
| Production Runtime | Session lifecycle and orchestration of Planner, Knowledge, Moment, Presentation, Flow and Broadcast | Test control, assertions or artifact policy |
| Planner / Knowledge / DJ Moment Engine | Existing production planning, resolution and immutable realization | Scenario orchestration or validation outcomes |
| Session Flow / Broadcast | Canonical result history and renderer-safe distribution | Test-specific history or a second event protocol |
| E2E Verification host | Isolated environment, scenario invocation, capture collection and cleanup verification | Runtime business behavior or product decisions |
| Golden Scenario Catalogue | Approved product behaviors, expected outcomes and prohibited outcomes | Execution technology, adapter commands or CI workflow syntax |
| Capture and Validation | Read-only collection and evaluation of canonical outcomes | Mutation, recovery or correction of a live Session |
| CI orchestration | Runs selected scenarios, retains redacted artifacts and reports results | Scenario semantics or Runtime ownership |

The verification side can request the bounded start/stop boundary provided by
the [Developer Session Bootstrap](../technical/DEVELOPER_SESSION_BOOTSTRAP.md).
It may never create
Sessions from a browser, obtain user credentials, mutate a user Profile or
recreate Planner/Knowledge/Moment decisions.

## Future lifecycle

1. CI or a local developer starts an isolated Home Assistant test environment.
2. Developer Session Bootstrap starts one ordinary server-owned Session for a
   deterministic fixture and returns bounded, ephemeral bootstrap data only to
   the invoking test process.
3. The Deterministic Scenario Driver supplies the approved scripted normalized
   input at the existing Runtime boundary. `SI-GOLDEN-004` uses the
   Runtime-owned observed-playback replanning boundary only: it deliberately
   produces no DJMoment, Presentation or renderer-facing planning data. It
   never fabricates provider-owned Playback Instance Identity or Knowledge
   results.
4. The existing Runtime processes the events using its production contracts.
5. A read-only capture observes safe Runtime outcomes, immutable DJMoments,
   their immutable Presentation Projections, Flow and renderer-safe Broadcast
   publications.
6. The Validation Engine evaluates the selected Golden Scenario's assertions.
7. CI emits redacted, human-readable and machine-readable artifacts.
8. Bootstrap stops the Session; the host proves Runtime and scoped access are
   released even when an assertion fails.

No step permits verification to modify a decision, retry a provider silently,
heal Flow, rewrite a Moment or substitute business logic.

## Scenario model

A Golden Scenario represents a real user-facing Session Intelligence behavior,
not a branch-coverage target. Every scenario has a stable identifier, product
intent, user story, runtime preconditions, deterministic fixture, event
timeline, expected owner behavior, result projections, blocking assertions,
non-blocking observations and forbidden outcomes.

Fixtures contain only provider-neutral normalized observations and safe,
bounded knowledge results or typed failures. They must not require a personal
Spotify account, live provider availability, provider queues, credentials or
profile-private data. Every fixture is versioned and seeded where a seed is
needed.

Scenarios are added only when they protect an approved product behavior. A
technical path with no user-visible Session Intelligence consequence belongs in
unit or integration tests, not this catalogue.

## Capture model

The future **E2E Session Capture** is one immutable, versioned and redacted
artifact. It may record, when safely available:

- scenario identifier, catalogue version and fixture revision;
- Session configuration and normalized playback timeline;
- planning generations, selected and approved intents, readiness and prefetch
  outcomes;
- immutable DJMoments, their source-linked Presentation Projections, Silence
  reasons, Session Updates and Transitions;
- canonical Session Flow ordering and renderer-safe Broadcast projections;
- fallback use, validation warnings, Session completion and cleanup result.

It must exclude credentials, tokens, raw provider payloads, raw prompts,
unnecessary Profile-private data and provider-owned identifiers not approved
for projection. Capture is evidence, not an alternate Session history or a
new Broadcast contract.

## Validation model

### Structural invariant assessment

These are immediate CI blockers: correct Session start/stop, exactly one
canonical approval path, immutable/non-duplicate Moments, Flow ordering,
expected renderer-safe Broadcast projection, source-linked immutable
Presentation Projection, unchanged Flow semantics, stale-generation rejection
and complete Runtime cleanup.

### Deterministic behavioral assessment

These validate explicitly approved fixed-fixture behavior, such as repetition
avoidance, safe knowledge fallback, supersession, earliest-eligible approval,
Session Update and intentional Silence. They become blocking only when the
relevant Golden Scenario marks them approved.

### Quality observations

Repetition and Silence ratios, Moment distribution, recommendation diversity,
fallback use, replanning churn and transition frequency are reporting-only
initially. A metric may block CI only after its definition is stable, its
baseline is reviewed, false-positive behavior is understood and repository
governance explicitly authorizes a threshold.

## Enabling infrastructure sequence

The following capabilities execute the catalogue; none is the goal of the
Epic.

1. Developer Session Bootstrap — machine-readable production-lifecycle start,
   scoped test access and deterministic cleanup.
2. Deterministic Scenario Driver — scripted normalized observations and typed
   safe knowledge results/failures.
3. Immutable E2E Session Capture — redacted canonical evidence.
4. Structural Invariant Validator — Layer 1 and approved Layer 2 evaluation.
5. Golden Qualification Foundation — complete; one local deterministic
   execution path that composes Bootstrap, Driver, Capture and Validator for
   all six original Session Intelligence Golden Scenarios.
6. Golden Smoke and later Golden Session profiles — future bounded selections
   over that same qualification path, with no duplicate implementation.
7. Verification Clock implementation for `SI-GOLDEN-002` — complete in PR
   #382 as the restricted infrastructure time source accepted by the
   [Verification Clock Architecture](VERIFICATION_CLOCK_ARCHITECTURE.md); it
   remains infrastructure, never business logic.
8. Accelerated/event-driven execution — a future separately authorized
   capability that may use the approved Clock boundary, never `test_mode`
   conditionals in business logic.

Core E2E validation remains headless and frontend-independent. A later
Universal Receiver layer may use `Broadcast -> headless browser -> DOM
assertions`; it validates the Receiver, not the core Intelligence Engine.
Likewise, any Developer Overlay remains read-only, development-only,
non-authoritative and optional. Its completed Pre-Flight is
[`READ_ONLY_DEVELOPER_OVERLAY_PREFLIGHT.md`](READ_ONLY_DEVELOPER_OVERLAY_PREFLIGHT.md):
it may only project existing renderer-safe Broadcast data and local transport
state, and cannot become a second observability model.

## CI model

Future CI must provision an isolated environment, use deterministic fixtures,
enforce bounded execution, preserve redacted failure artifacts, always clean up
and report a clear pass/fail result. It must run without manual Home Assistant
Developer Tools interaction, copied Session IDs or copied Broadcast tokens.

The [Session Intelligence Qualification Policy](SESSION_INTELLIGENCE_QUALIFICATION_POLICY.md)
defines intended PR, main, release and scheduled qualification placement. It
does not authorize or prescribe a GitHub Actions implementation.

## Scope exclusions

This architecture does not authorize a browser UI, Developer Overlay,
diagnostics framework, live-provider baseline suite, personal Spotify account,
new Runtime pipeline, alternate Planner/Knowledge/Moment logic, persistent
test Sessions or quality-score release gates. It does not reopen completed
Universal Receiver connection, Timeline, Playback Projection or Now Playing
capabilities.

## Canonical references

- [Developer Experience Roadmap](../product/DEVELOPER_EXPERIENCE_ROADMAP.md)
- [Golden Scenario Catalogue](SESSION_INTELLIGENCE_GOLDEN_SCENARIOS.md)
- [Golden Scenario Governance](GOLDEN_SCENARIO_GOVERNANCE.md)
- [Session Intelligence Qualification Policy](SESSION_INTELLIGENCE_QUALIFICATION_POLICY.md)
- [Presentation Verification Architecture](PRESENTATION_VERIFICATION_ARCHITECTURE.md)
- [Golden Qualification Foundation](GOLDEN_QUALIFICATION_FOUNDATION.md)
- [Verification Clock Architecture](VERIFICATION_CLOCK_ARCHITECTURE.md)
- [DJ Session Runtime Contracts](../../DJ_SESSION_RUNTIME_CONTRACTS.md)
- [DJ Moment Engine](../technical/DJ_MOMENT_ENGINE.md)
- [Verification Architecture](01_VERIFICATION_ARCHITECTURE.md)
