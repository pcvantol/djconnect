# DJ Session Domain Model

**Status:** Canonical product domain vocabulary
**Owner:** DJConnect Product Development
**Scope:** Product concepts and relationships

## Purpose

This document defines the canonical product vocabulary for the DJ Session
model. It gives Product Engineering, clients, backend components and
Innovation Engineering one shared meaning for the concepts below.

`PRODUCT_DEFINITION.md` remains authoritative for product direction. This
document describes the product domain only. It does not prescribe storage,
databases, persistence, synchronization, APIs, protocol contracts, event
schemas, serialization or implementation.

## Core concepts

| Concept | Product meaning | Responsibility |
| --- | --- | --- |
| DJ Session | One coherent listening experience orchestrated by the AI DJ. | A Profile-owned durable lifecycle aggregate that brings relevant DJConnect capabilities together without owning playback. |
| Playback Context | The current playback situation available to the DJ. | Is owned by the configured Music Backend; DJConnect consumes it to enrich the session. |
| Media Identity | One safe, adapter-normalized reference for a playable media entity. | Is owned and normalized by the Music Backend Observation Boundary, compared ephemerally by Runtime for Stage 1 observation and never identifies a playback occurrence. |
| Current Playback Projection | One immutable, safe observation of an active current item for Continue startup. | Is resolved by the Music Backend Observation Boundary and consumed ephemerally by Session Start orchestration; it is not a queue, control contract or playback authority. |
| Playback Instance Identity | One opaque identifier for one concrete playback occurrence. | Is generated and owned by the Music Backend Observation Boundary, passed unchanged through Current Playback Projection and Track Started, and consumed only for Runtime-scoped deduplication. |
| Track Started Observation | One normalized Stage 2 live observation that a playback occurrence has started. | Is produced by the Music Backend Observation Boundary with the matching opaque Playback Instance Identity and consumed by Runtime; it is not a provider callback or renderer event. |
| Session Memory | The objective chronological memory of one live DJ Session Runtime. | Records what happened as events only; it performs no interpretation and remains ephemeral unless an authorized historical projection is persisted. |
| Session Timeline | The user-facing chronological presentation of one completed DJ Session. | Tells the story through authorized immutable historical projections; it is not a chat history. |
| Music DNA | The evolving, opt-in understanding of a person's musical identity across many DJ Sessions. | Interprets patterns in Session Memory; it never replaces Session Memory. |
| Session Start Strategy | The listener's objective for starting a Session. | Continue, Manual and Discover define why the Session exists; it is independent from Mood and Persona. |
| DJ Persona | A behavioural DJ identity for a session. | Shapes how future contributions are presented; it is not a voice or mood. |
| Session Mood | The dynamic emotional atmosphere of the active Session Runtime. | Is initialized independently from Strategy and Persona, informs future presentation and never rewrites completed Moments. |
| Knowledge Intent | A planned statement of what the DJ should communicate. | Contains no delivery, wording, voice or visual choice. |
| Presentation Intent | The immutable snapshot of how a Knowledge Intent will be delivered. | Carries Persona, Mood, tone, delivery and channel choices into one Moment. |
| DJ Moment | The immutable, renderer-safe presentation contribution. | Is the universal unit published to Broadcast and presented by renderers. |

## DJ Session

A **DJ Session** is the primary DJConnect product experience. The user
perceives one AI DJ experience rather than separately selecting capabilities.
Ask DJ, Discover, Track Insight, announcements, Music DNA and VibeCast remain
individual capabilities that may contribute to a session.

A DJ Session is independent from any specific playback provider. It enriches a
listening experience but never owns playback.

Session Start Strategy, Session Mood and DJ Persona are orthogonal dimensions
of a Runtime: Strategy answers why the Session exists, Mood answers how it
should feel, and Persona answers how the DJ performs. Their combinations do
not create competing Session types.

## DJ presentation model

The presentation path is conceptually:

```text
Session Planner → Knowledge Intent → DJ Moment Engine → DJ Moment → Broadcast → Renderers
```

A Knowledge Intent states what matters to the session, for example an Artist
Story, Transition, Audience response or Silence. The DJ Moment Engine owns the
creative execution and combines that intent with the current Session Mood,
Persona and Runtime context. The resulting DJ Moment is immutable and may
carry content, artwork, delivery, visibility and follow-up actions. Renderers
present a Moment; they do not derive a competing presentation from the
underlying session state.

This document defines product vocabulary only. The canonical architecture and
future implementation boundary are in
[`DJ_PRESENTATION_ARCHITECTURE.md`](DJ_PRESENTATION_ARCHITECTURE.md). The
durable lifecycle, historical projection and storage boundary are in
[`../../PERSISTENT_SESSION_ARCHITECTURE.md`](../../PERSISTENT_SESSION_ARCHITECTURE.md).

## Playback Context

**Playback Context** represents the playback situation available to the DJ. It
may include the current track, recent tracks, queue, playback state, playback
device and room context.

Playback Context is owned by the configured **Music Backend**, such as Spotify
Direct or Music Assistant. DJConnect consumes the available context; it does
not take ownership of playback in order to operate.

### Current Playback Projection

A **Current Playback Projection** is the deliberately narrow, immutable subset
of Playback Context that a future Continue start may consume. It describes one
currently active item with safe identity, state and bounded optional metadata;
it never includes a queue, future playback, raw provider payload or pre-session
history. Its canonical contract is
[`CONTINUE_CURRENT_PLAYBACK_CONTINUITY.md`](CONTINUE_CURRENT_PLAYBACK_CONTINUITY.md).

**Playback Instance Identity** is distinct from a track URI or display metadata.
It is owned by the Music Backend Observation Boundary, opaque and valid only
for one concrete occurrence. Runtime never derives or persists it; it receives
the same identity in a future Continue projection and normalized Track Started
event. Playback Control remains separate and owns playback, queue and
transport.

A **Track Started Observation** is the canonical Stage 2 live Runtime entry point for
one normalized occurrence. It carries the matching opaque identity and only
safe bounded playback context. The Session Start-internal Track Insight trigger
is not a Track Started Observation. The detailed lifetime, scope, capability
and privacy contract is in
[`CONTINUE_CURRENT_PLAYBACK_CONTINUITY.md`](CONTINUE_CURRENT_PLAYBACK_CONTINUITY.md).

Stage 1 active-session observation instead compares a safe **Media Identity**
and invokes the established Track Started processing only for an eligible media
change. It does not claim occurrence correctness or become a
`TrackStartedObservation`. Its separate semantics are in
[`LIVE_PLAYBACK_OBSERVATION.md`](LIVE_PLAYBACK_OBSERVATION.md).

## Session Memory

**Session Memory** is the objective, chronological record of one DJ Session.
It records what happened during that session as events only. It does not
interpret preference, identity or meaning.

Session Memory is contextual source material for future DJ decisions and Ask
DJ conversations within the session. It is distinct from both a Timeline and
Music DNA.

## Session Events

The following event categories are canonical product vocabulary. They identify
meaningful session events without prescribing event schemas, fields, transport
or serialization.

| Category | Examples |
| --- | --- |
| Session lifecycle | `SessionStarted`, `SessionEnded` |
| Playback | `TrackStarted`, `TrackFinished`, `PlaybackPaused`, `PlaybackResumed`, `QueueChanged` |
| DJ contribution | `Announcement`, `TrackInsight`, `Recommendation` |
| Conversation | `AskDJQuestion`, `AskDJAnswer` |
| Listener action | `UserLike`, `UserDislike`, `UserSkip` |
| Context change | `ProfileChanged`, `RoomChanged` |

These categories do not imply that every event is visible to every person,
profile or client. Product privacy boundaries still apply.

## Session Timeline

The **Session Timeline** is the user-facing chronological presentation of
Session Memory for one completed DJ Session. It is the historical story of a
listening experience, not a chat history.

A Timeline may include played tracks, announcements, Track Insights, Ask DJ
conversations, Discover moments, recommendations and significant user
interactions. It does not change what occurred; it presents the relevant story
of the session under the active profile and privacy boundaries.

## Music DNA

**Music DNA** is the evolving, opt-in understanding of a person's musical
identity derived from patterns across many DJ Sessions. It interprets Session
Memory across sessions to help the same AI DJ understand the listener over
time.

Music DNA never replaces Session Memory. Session Memory records objective
events in one session; Music DNA interprets patterns across many sessions.
Music DNA remains profile-centric and must not be exposed to shared, guest or
room contexts unless the active profile and request context explicitly allow
it.

## Playback ownership

Playback ownership always remains with the configured Music Backend. Spotify
Direct and Music Assistant are examples of Music Backends. A DJ Session
observes Playback Context and enriches the listening experience; it never owns
playback, a provider account or provider-specific playback state.

## Conceptual relationship model

```text
DJ Session
  -> Playback Context
  -> Session Memory
  -> Session Timeline
  -> Music DNA
  -> Future DJ decisions
```

The relationship is conceptual:

1. A DJ Session uses available Playback Context to understand the listening
   moment.
2. Objective events from that session form its Session Memory.
3. The Session Timeline presents the chronological story of the completed
   Session Memory.
4. Across many sessions, opt-in Music DNA interprets relevant patterns in
   Session Memory.
5. That understanding can inform future DJ decisions without replacing the
   underlying Session Memory or Music Backend ownership.

## Terminology rules

- Use **DJ Session** for the coherent product experience, not a provider
  playback session or a client-specific screen.
- Use **Session Memory** for objective session events, never for personal
  preference interpretation.
- Use **Session Timeline** for the user-facing story of a completed DJ Session,
  never as a synonym for Ask DJ chat history.
- Use **Music DNA** for opt-in cross-session interpretation of personal musical
  identity, never as the primary session-event record.
- Use **Playback Context** for Music Backend-owned playback information that
  DJConnect consumes, not owns.
- Use **Current Playback Projection** only for the one safe observed item that
  may bootstrap a future Continue Session; never as a synonym for queue or
  playback control.

## Boundaries

This domain model introduces no implementation, architecture, roadmap,
pricing, API, synchronization or storage decision. Any future work that needs
those decisions must use this vocabulary and obtain its own appropriate scope.
