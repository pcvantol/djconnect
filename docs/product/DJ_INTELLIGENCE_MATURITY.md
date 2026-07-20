# DJ Intelligence Maturity Model

## Purpose

This is the canonical capability-oriented implementation roadmap for the AI
DJ. It complements, but does not replace, the Product Backlog. Future work
enriches the established Session Runtime architecture in small, production-safe
vertical slices.

## Maturity principles

Every stage must remain production ready, testable and faithful to established
ownership. Reuse proven infrastructure where possible; later stages enrich
behaviour rather than replace architecture or introduce speculative systems.

## Session Planner

| Stage | Maturity |
| --- | --- |
| 1 — current | Track Started trigger, Track Context, Silence and Runtime heuristics. |
| 2 — partial | Deterministic Artist, Album, Genre and Recommendation intent selection from available knowledge hints. Discover has selected Stage 2 behaviour; Transition and broader Session Update refinement remain deferred. |
| 3 — current | The live Track Started Runtime path resolves one safe Track Insight projection and deterministically combines its bounded knowledge hints with Session Start Strategy, Session Mood, DJ Persona, Session Direction and Runtime-scoped Performance Memory when selecting its initial semantic intent. Direction and Mood guide trajectory, pacing and silence; Persona influences the performance profile; Discover favours exploration; Performance Memory prevents immediate repetition. Audience-driven adaptation, context-aware transitions, continuous replanning and multi-track planning remain deferred. |
| 4 | Persistent cross-session performance learning, multi-track planning, narrative sequencing, dynamic replanning and pacing. |
| 5 | Autonomous session strategy and long-term performance optimisation. |

## Knowledge Engine

| Stage | Maturity |
| --- | --- |
| 1 — current | Track metadata, artist, album, genre and existing metadata enrichment. |
| 2 — current | The Knowledge Engine selects a bounded, intent-relevant subset of existing Track Insight metadata: artist/production context for Artist Story, release context for Album Story, genre characteristics for Genre Story and related works for Recommendation. Missing intent-specific metadata remains empty so the existing safe Silence fallback applies. Lyrics and dedicated recording-history retrieval remain deferred; external music knowledge, historical context and related-artist retrieval remain future Stage 3 work. |
| 3 | Concert information, external music knowledge, historical context and related artists. |
| 4 | Cross-session learning and narrative knowledge chains. |

## DJ Moment Engine

| Stage | Maturity |
| --- | --- |
| 1 — current | Track Context and Silence. |
| 2 — current | Artist Story, Album Story, Genre Story and Recommendation deterministically translate their selected Knowledge Context into immutable Moments with frozen Presentation Intent and intent-specific semantic actions. Invalid, incomplete or empty selected context creates canonical Silence. |
| 3 — partial | Session Update Moments expose Planner-approved Session Direction changes and deterministically realize the existing safe Session Direction Knowledge Context, including Direction, Start Strategy, Mood and runtime-scoped Performance Memory. In addition to Mood/Persona direction changes, two immediately preceding Silence Moments in the bounded Performance Memory window approve one `RESETTING` Session Update; when that Resetting update is the immediately preceding Flow contribution, the Planner deterministically approves one `RETURNING` Session Update. The existing Flow and Broadcast path publish each immutable result. The live Transition slice supports one Planner-approved `NEXT` Transition after a current Exploring Recommendation follows an existing Track, Artist, Album or Genre Flow contribution. The Planner owns approval and placement; the Moment Engine freezes the immutable Transition. No-transition is silent and recent Transition memory prevents immediate repetition. Broader Session Update policy, multiple Session Updates per Track Started event, broader Transition timing, multiple Transitions, future-track or queue context, autonomous replanning, audience adaptation, Concert Suggestion, Music History and Discovery remain deferred. |
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
| 3 | Narrative discovery sessions and richer DJ-guided transitions. |
| 4 | Autonomous discovery journeys. |

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
