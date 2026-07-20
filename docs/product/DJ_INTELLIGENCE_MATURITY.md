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
| 2 — partial | Deterministic Artist, Album, Genre and Recommendation intent selection from available knowledge hints. Transition, Discover and Session Update remain deferred. |
| 3 — partial | Runtime-owned, timestamped Session Direction with deterministic Session Start initialization, Planner proposals and Session Update Moments. Audience-driven adaptation, context-aware transitions, autonomous replanning and multi-track planning remain deferred. |
| 4 | Multi-track planning, narrative sequencing, dynamic replanning and pacing. |
| 5 | Autonomous session strategy and long-term performance optimisation. |

## Knowledge Engine

| Stage | Maturity |
| --- | --- |
| 1 — current | Track metadata, artist, album, genre and existing metadata enrichment. |
| 2 — partial | Producer/composer, release and recording context, related works and richer musical characteristics when existing metadata supplies them. Lyrics and dedicated recording-history retrieval remain deferred. |
| 3 | Concert information, external music knowledge, historical context and related artists. |
| 4 | Cross-session learning and narrative knowledge chains. |

## DJ Moment Engine

| Stage | Maturity |
| --- | --- |
| 1 — current | Track Context and Silence. |
| 2 — partial | Artist Story, Album Story, Genre Story and Recommendation specialise existing Track Context when reliable Knowledge Context supports them. |
| 3 — partial | Session Update Moments expose Planner-approved Session Direction changes. Concert Suggestion, Music History and Discovery remain deferred. |
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
| 1 | Session Start Strategy and track recommendations. |
| 2 | Personalised Discovery and permitted Music DNA influence. |
| 3 | Narrative discovery sessions. |
| 4 | Autonomous discovery journeys. |

## DJ Persona and Session Mood

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

Session experience matures from one active Session (Stage 1), through Discover
and themed Sessions (Stages 2–3), autonomous evening experiences (Stage 4) to
a continuous AI DJ (Stage 5).

## Implementation policy

Every future implementation PR must state its current and target maturity
stage, capabilities introduced, reused, intentionally deferred and explicitly
excluded. No stage may be skipped without explicit architectural justification.

## Principles

- Architecture first; capability second; behaviour third.
- Complexity grows by enrichment rather than replacement.
- Every stage should feel like a complete product.
- Nothing is implemented solely because it may eventually be needed.
- Architecture supports future stages; implementation reaches them incrementally.
