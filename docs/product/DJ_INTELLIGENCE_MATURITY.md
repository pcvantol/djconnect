# DJ Intelligence Maturity Model

## Purpose

This is the canonical capability-oriented implementation roadmap for the AI
DJ. It complements, but does not replace, the Product Backlog. Future work
enriches the established Session Runtime architecture in small, production-safe
vertical slices.

## Runtime Integration milestone

**Session Intelligence Runtime Complete** is the current architectural
milestone. For every supported Track Started decision, the server uses one
canonical Runtime lifecycle:

```text
Runtime -> Planner -> Knowledge Engine -> DJ Moment Engine -> Session Flow -> Broadcast
```

The Planner, Knowledge Engine and DJ Moment Engine have stable ownership within
that lifecycle. The legacy Track Started route is only bounded runtime
protection for lifecycle failure. Future maturity cells extend these existing
abstractions and never introduce a parallel Runtime, Flow or Broadcast path.

This milestone does not advance deferred intelligence. In particular,
Audience Intelligence remains intentionally deferred until a separately
authorized bounded Planner-influence cell has its required evidence. It is
low priority behind Automated Session Intelligence E2E Verification; it must
not become active merely because its future cell exists. The E2E foundation must
protect the canonical pipeline before material new Intelligence Engine
complexity is added.

## Maturity principles

Every stage must remain production ready, testable and faithful to established
ownership. Reuse proven infrastructure where possible; later stages enrich
behaviour rather than replace architecture or introduce speculative systems.

### Implementation-cell rule

A future implementation cell is actionable only when it names one bounded
behaviour, its existing trigger, owner, safe input, deterministic policy,
existing output path, fallback and deferred work. A broad stage is product
direction, not authorization to implement every idea named by that stage.
Cells below refine existing goals; they introduce no new Runtime state,
DJMoment type, provider, API, persistence or renderer responsibility.

## Session Planner

| Stage | Maturity |
| --- | --- |
| 1 — current | Track Started trigger, Track Context, Silence and Runtime heuristics. |
| 2 — partial | Deterministic Artist, Album, Genre and Recommendation intent selection from available knowledge hints. Discover has selected Stage 2 behaviour; Transition and broader Session Update refinement remain deferred. |
| 3 — current | The live Track Started Runtime path resolves one safe Track Insight projection and deterministically combines its bounded knowledge hints with Session Start Strategy, Session Mood, DJ Persona, Session Direction and Runtime-scoped Performance Memory when selecting its initial semantic intent. Direction and Mood guide trajectory, pacing and silence; Persona influences the performance profile; Discover favours exploration; Performance Memory prevents immediate repetition. Audience-driven adaptation, additional context-aware Transition policies, continuous replanning and multi-track planning remain deferred. |
| 4 | Persistent cross-session performance learning, multi-track planning, narrative sequencing, dynamic replanning and pacing. `ROLLING_SESSION_HORIZON_ARCHITECTURE.md` defines their prerequisite architecture and bounded implementation order; no Stage 4 behaviour is current. |
| 5 | Autonomous session strategy and long-term performance optimisation. |

## Knowledge Engine

| Stage | Maturity |
| --- | --- |
| 1 — current | Track metadata, artist, album, genre and existing metadata enrichment. |
| 2 — current | The Knowledge Engine selects a bounded, intent-relevant subset of existing Track Insight metadata: artist/production context for Artist Story, release context for Album Story, genre characteristics for Genre Story and related works for Recommendation. For each approved semantic intent, it now deterministically selects exactly one primary safe evidence value by fixed precedence; malformed and empty candidates are excluded. Missing intent-specific metadata produces an empty intent context so the existing safe Silence fallback applies. Lyrics and dedicated recording-history retrieval remain deferred; external music knowledge, historical context and related-artist retrieval remain future Stage 3 work. |
| 3 | Concert information, external music knowledge, historical context and related artists. |
| 4 | Cross-session learning and narrative knowledge chains. |

## DJ Moment Engine

| Stage | Maturity |
| --- | --- |
| 1 — current | Track Context and Silence. |
| 2 — current | Artist Story, Album Story, Genre Story and Recommendation deterministically translate their selected Knowledge Context into immutable Moments with frozen Presentation Intent and intent-specific semantic actions. Invalid, incomplete or empty selected context creates canonical Silence. |
| 3 — partial | Session Update Moments expose Planner-approved Session Direction changes and deterministically realize the existing safe Session Direction Knowledge Context, including Direction, Start Strategy, Mood and runtime-scoped Performance Memory. In addition to Mood/Persona direction changes, two immediately preceding Silence Moments in the bounded Performance Memory window approve one `RESETTING` Session Update; when that Resetting update is the immediately preceding Flow contribution, the Planner deterministically approves one `RETURNING` Session Update. The existing Flow and Broadcast path publish each immutable result. The live Transition slice supports one Planner-approved `NEXT` Transition after a current Exploring Recommendation follows an existing Track, Artist, Album or Genre Flow contribution. The Planner owns approval and placement; the Moment Engine freezes the immutable Transition. No-transition is silent and recent Transition memory prevents immediate repetition. The next defined Stage 3 cell is realization of the Planner's bounded audience-direction approval as an existing Session Update. Broader Session Update policy, multiple Session Updates per Track Started event, broader Transition timing, multiple Transitions, future-track or queue context, autonomous replanning, Concert Suggestion, Music History and Discovery remain deferred. |
| 4 | Narrative storytelling, linked Moments and multi-step experiences. |

## DJ Moment types

Every canonical Moment type follows the same model: one platform-independent
semantic object with a current maturity and future enrichments. Track and
Silence are Stage 1. Artist, Album, Genre and Recommendation are Stage 2.
Discovery, Transition, Concert, History, Audience and Session follow through
later Planner and Knowledge stages. Future types must fit this model rather
than create a feature-specific execution path.

## Discover

| Stage | Maturity |
| --- | --- |
| 1 — complete | Immutable Discover Session Start Strategy initializes the Exploring Direction and a high exploration preference; it does not prescribe Mood or Persona. |
| 2 — current | Repository-alignment of already implemented and tested behaviour: deterministic Discover Planner preference for Recommendation, Artist, Genre and Album context; Performance Memory diversity; optional, safe opt-in Music DNA familiarity avoidance. No dedicated Discover provider, search or playback behaviour. |
| 3 | Discover-specific narrative sequencing and richer DJ-guided transitions beyond the already-current narrow Exploring Recommendation Transition. These require a separately defined policy cell; Discover remains a Session Start Strategy, never a provider, feature page or playback owner. |
| 4 | Autonomous discovery journeys. |

## Implementation-sized future cells

The following cells decompose existing maturity goals into one reviewable
production increment each. A cell may be selected only when every prerequisite
in its row is already true; otherwise it remains planned or gated. All retain
the canonical Runtime → Planner → Knowledge Engine → DJ Moment Engine →
Session Flow → Broadcast path.

### Session Planner

| Cell | Status | Bounded contract |
| --- | --- | --- |
| PL-3.2 — audience-direction consensus | Planned | **Objective:** let the Planner use already aggregated audience energy signals as one bounded direction input. **Trigger:** the next existing Track Started evaluation after pending `AUDIENCE_SIGNAL`. **Input:** aggregate `more_energy`/`dance` or `less_energy`/`chill` totals, current Direction, Mood, Persona and Performance Memory; no identity, Music DNA, provider or queue data. **Policy:** two compatible signals, with no equally strong opposite request, approve `BUILDING_ENERGY` or `COOLING_DOWN`; otherwise no audience direction change. A same direction or the existing recent-Session-Update guard uses the current Silence/no-update fallback. **Output:** existing Planner-approved Session Direction decision only. **Deferred:** single-signal action, genre/artist requests, playback control, persistence, conflict ranking beyond no-op, autonomous planning and Audience Moments. |
| PL-4.1 — recommendation spacing | Current | **Objective:** avoid consecutive Recommendation intents when another already valid contextual intent is available. **Trigger:** existing Track Started evaluation. **Input:** the immediately preceding Flow Moment type through Runtime-scoped Performance Memory, current bounded hints and existing priority order. **Policy:** when the previous Moment is Recommendation, deterministically demote Recommendation for this one decision only if Artist, Album or Genre has a safe, non-repeating and Discover-eligible hint; otherwise preserve the existing ordering. **Output:** one existing Knowledge Intent; no new Moment type. **Fallback:** existing Recommendation or Track Context selection; spacing never creates Silence. **Evidence:** focused Planner and live Track Started tests prove deterministic selection, preserved Discover preference where no alternative exists, immutable Moment delivery and unchanged Flow/Broadcast publication. **Deferred:** frequency learning, timers, future-track or queue context, persistent history and autonomous pacing. |
| PL-4.2 — session-arc policy | Gated | Existing Stage 4 direction (`narrative sequencing`, `dynamic replanning` and `pacing`) needs one later, explicit policy that defines its Flow evidence, direction transition, fallback and test contract. It is not authorized by the broad label alone. |

### Knowledge Engine

| Cell | Status | Bounded contract |
| --- | --- | --- |
| KE-2.2 — primary existing-metadata evidence | Current | **Objective:** for an already Planner-approved Artist, Album, Genre or Recommendation intent, select one canonical primary evidence value from the existing sanitized Track Insight projection. **Trigger:** existing Track Started Knowledge Context assembly. **Input:** the selected intent and existing safe Track Insight fields only. **Policy:** fixed intent-specific precedence selects exactly one bounded scalar or first safe sequence value; malformed or empty values are excluded. **Output:** existing Knowledge Context, with shared track identity and one selected evidence value; no retrieval or presentation. **Fallback:** empty intent context so the existing Silence path applies. **Evidence:** focused Knowledge Engine and live Track Started tests prove precedence, safe fallback, a single insight resolution and immutable Flow/Broadcast delivery. **Deferred:** new metadata sources, lyrics, recording history, external knowledge and provider calls. |
| KE-3.1 — concert source qualification | Gated | Existing Stage 3 Concert knowledge may become one cell only after an approved source contract supplies bounded, attributable concert evidence. The Knowledge Engine selects it; the Planner decides whether to request it. |
| KE-3.2 — historical source qualification | Gated | Existing Stage 3 historical context may become one cell only after an approved bounded source and provenance contract. It must not infer history from provider payloads. |
| KE-3.3 — related-artist source qualification | Gated | Existing Stage 3 related-artist retrieval may become one cell only after an approved safe source contract. Selecting already available Track Insight related-artist metadata remains Stage 2. |

### DJ Moment Engine

| Cell | Status | Bounded contract |
| --- | --- | --- |
| ME-3.3 — audience-direction Session Update | Planned, depends on PL-3.2 | **Objective:** realize the Planner's bounded audience-direction approval as one existing immutable Session Update. **Trigger:** existing Track Started path after `CREATE_SESSION_UPDATE`. **Input:** existing safe Session Direction Knowledge Context. **Policy:** the Engine realizes only Planner approval; it never interprets audience totals. **Output:** existing Session DJMoment, then existing Flow and Broadcast publication. **Fallback:** existing Silence for invalid context and no Moment for no Planner approval. **Deferred:** Audience Moment types, direct audience responses, playback action, multiple updates and renderer behaviour. |
| ME-3.4 — additional Transition policy | Gated | Existing Stage 3 broad Transition wording requires a later cell that selects one exact allowed predecessor/successor relationship, Direction/Strategy constraint, repetition guard and no-transition fallback. The already-current Exploring Recommendation policy remains unchanged. |
| ME-4.1 — narrative continuation | Gated | Existing Stage 4 linked Moments and multi-step experiences require a separately approved semantic sequence contract. It must not be inferred from a renderer, queue or future-track state. |

### Discover

| Cell | Status | Bounded contract |
| --- | --- | --- |
| DI-3.1 — Discover recommendation spacing | Planned, depends on PL-4.1 | **Objective:** apply the existing Planner recommendation-spacing policy within a Discover Session while preserving Discover's exploration preference. **Trigger/input/output/fallback:** PL-4.1, with `DISCOVER` Strategy as the only additional input. **Policy:** use an alternative existing contextual intent only when its safe hint is valid; otherwise retain the Discover Recommendation. **Deferred:** search, provider ownership, playback action, new Discover Moment type and narrative multi-track journeys. |
| DI-3.2 — narrative Discover sequence | Gated | Existing Stage 3 narrative discovery requires a later policy that defines one allowed sequence of existing Moment intents and its Session Flow evidence. It cannot be implemented from the current broad label alone. |

### Ownership and readiness

- The Planner decides any pacing, spacing, direction or Transition approval.
- The Knowledge Engine selects only safe knowledge already authorized for the
  approved intent; source-qualified Stage 3 cells remain gated until their
  source contract exists.
- The DJ Moment Engine realizes the selected context or Planner approval as an
  immutable existing DJMoment; it never schedules or interprets audience input.
- Session Flow remains the canonical history and Broadcast distributes only
  resulting immutable state and Moments.
- Performance Memory stays a bounded, ephemeral Planner projection. It may be
  evidence for a cell but never owns pacing, audience interpretation,
  storytelling, persistence or cross-session learning.

## Session Start Strategy, Session Mood and DJ Persona

Session Start Strategy answers why the Session exists, Session Mood answers how
it should feel, and DJ Persona answers how the DJ should perform. These are
orthogonal Runtime dimensions: a Strategy sets the Session objective, not its
emotional atmosphere or DJ behaviour.

Persona evolves from Stage 1 speaking-frequency heuristics to Stage 2
storytelling and interaction differences, Stage 3 consistency and Stage 4
Premium Persona packages. Premium expressive voices are Stage 5: voices are a
presentation implementation, never the architectural starting point.

Session Mood evolves from Stage 1 Planner heuristics to Stage 2 Presentation
Intent, Stage 3 Planner adaptation and Stage 4 a longer-term emotional arc.

## Music DNA and Audience

Music DNA remains Profile-owned throughout every stage: optional recommendation
input (Stage 1), Planner influence (Stage 2), Session adaptation (Stage 3),
long-term evolution (Stage 4) and continuous listener understanding (Stage 5).

Audience matures from no active planning input (Stage 1), to Signals (Stage 2),
audience-aware planning (Stage 3) and multi-user optimisation (Stage 4).

## Presentation and Session experience

Presentation begins with Current Session State, Session Flow and Expanded
Renderer (Stage 1); adds Timeline, Micro and TV (Stage 2); Voice, Ambient and
Notification (Stage 3); platform refinements (Stage 4); and future modes
(Stage 5).

Session experience begins with an explicit immutable Runtime Start Strategy
(Continue, Discover or Manual) that defines the Session objective. The client
selects initial Mood independently and Persona defines DJ behaviour; the
Runtime initializes Direction and Planner configuration from these independent
inputs (Stage 1). Selected Discover behaviour is Stage 2;
narrative and themed Session execution remain Stage 3. Autonomous evening
experiences are Stage 4 and a continuous AI DJ is Stage 5.

### Live Playback Observation

| Stage | Maturity |
| --- | --- |
| 0 — complete | No generic production path observes external playback changes while a DJ Session is active. |
| 1 — current for Spotify Direct | Spotify Direct performs bounded adapter-owned active-session polling of its safe normalized playable track URI. Manual, Discover and Continue Stage 1 Sessions compare only runtime-scoped Media Identity and route an eligible changed URI through the existing Track Insight → Planner → Knowledge Engine → DJ Moment Engine → Session Flow → Broadcast path. Repeated URI observations are suppressed; pause/resume with the same URI, same-track replay, tracks between polls, reconnect/transfer edge cases and occurrence-correct deduplication remain explicitly unsupported. Music Assistant remains conditionally eligible but unimplemented. No Playback Instance Identity or Continue bootstrap correlation is introduced. |
| 2 — authorized, deferred | Observation Boundary-owned Playback Instance Identity and correlated live `TrackStartedObservation` provide occurrence-correct replay/deduplication behaviour and Continue Stage 2 bootstrap correlation. |

The detailed Stage 1 contract, capability model, backend readiness and future
implementation slice are in
[`LIVE_PLAYBACK_OBSERVATION.md`](LIVE_PLAYBACK_OBSERVATION.md). Stage 1 never
weakens the separate Continue contract.

### Continue Current Playback Continuity

| Stage | Maturity |
| --- | --- |
| 1 — current | Continue is an explicit immutable Start Strategy with a continuity-oriented Planner profile, `MAINTAINING_ENERGY` Direction and an empty Runtime-only fallback. It adopts no current playback. |
| 2 — authorized, deferred | Prerequisites are accepted Observation Boundary ownership; canonical opaque Playback Instance Identity; immutable CurrentPlaybackProjection; canonical live Track Started observation carrying the same identity; capability reporting; `ACTIVE`/`NO_ACTIVE_PLAYBACK`/`UNAVAILABLE`/`UNSUPPORTED` outcomes; bootstrap/live-event correlation; bounded runtime-scoped identity-only deduplication; the resolved Track Insight reuse rule; and at least one tested backend observation implementation capable of the complete contract. Only then may one implementation adopt one eligible active item exactly once, reuse the existing Track Started path and keep Playback unchanged. It must not read a queue or future track. |
| 3 | Optional safe current-playback context refinement and richer playlist or album continuity. |
| 4 | Multi-device continuity and cross-session restoration only under an explicitly authorized persistent contract. |
| 5 | Autonomous continuity and long-running performance adaptation. |

## External Capability Dependencies

The following roadmap items are intentionally blocked by capabilities that
must be supplied by a Music Backend Observation Boundary. They are not
abandoned, incomplete engineering work, technical debt or active
implementation targets. They remain deferred until new repository evidence or
upstream platform capabilities satisfy the stated unblock condition.

| Blocked capability | Current status | Explicit unblock condition |
| --- | --- | --- |
| Continue Stage 2 | Authorized, deferred | A backend supplies a backend-owned Playback Instance Identity in both a correlated immutable `CurrentPlaybackProjection` and correlated `TrackStartedObservation`, with an authoritative occurrence lifecycle and replay-correct behaviour. |
| Playback Instance Identity | Deferred | A backend observation capability can model concrete playback occurrences without URI, metadata, timestamp, progress or other heuristic identity. |
| Occurrence-correct Playback Observation | Deferred | An authoritative occurrence lifecycle provides stable observation identity and distinguishes a legitimate replay from duplicate delivery. |
| Music Assistant Live Playback Observation Stage 1 qualification | Conditionally eligible, deferred | Repository evidence proves that Music Assistant `media_content_id` is a safe playable Media Identity, or establishes another canonical Stage 1 Media Identity contract. |

### Planning policy

Future implementation planning must not select a blocked capability from this
table unless new repository evidence or upstream platform capabilities satisfy
its explicit unblock condition. The Planner must prefer active maturity work
over blocked roadmap items. A repeated architectural analysis is not evidence
that a blocker has changed.

### Active product priority

Active development returns to the AI DJ within the maturity stages supported by
this roadmap: Performance Memory, Session Planner, Knowledge Engine, DJ Moment
Engine, Session Updates, Transitions, Audience Adaptation and Rolling
Replanning. Live Playback Observation Stage 2 is not an active priority while
its external dependency conditions remain unmet.

## Implementation policy

Every future implementation PR must state its current and target maturity
stage, capabilities introduced, reused, intentionally deferred and explicitly
excluded. No stage may be skipped without explicit architectural justification.

## Current Stage 3 boundary

Performance Memory is ephemeral Runtime state only. It is derived from the
active Session Flow and current Runtime Moments, contains no Profile, Music DNA
or conversation data, and is destroyed with the Runtime. Persistent memory,
Audience Signals, autonomous planning and any cross-session learning remain
future work.

Session Start Strategies do not execute playback, create queues or generate
Moments. Continue currently uses its empty Runtime-only fallback. Its authorized
but deferred Stage 2 continuity contract is
[`CONTINUE_CURRENT_PLAYBACK_CONTINUITY.md`](CONTINUE_CURRENT_PLAYBACK_CONTINUITY.md):
one safe observed current item, never a queue, history or persistent Session.

## Principles

- Architecture first; capability second; behaviour third.
- Complexity grows by enrichment rather than replacement.
- Every stage should feel like a complete product.
- Nothing is implemented solely because it may eventually be needed.
- Architecture supports future stages; implementation reaches them incrementally.
