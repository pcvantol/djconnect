# DJ Intelligence Architecture

## Status

Canonical conceptual architecture. This document introduces no production
implementation, runtime behaviour, API, autonomous loop or client behaviour.

## Purpose

DJConnect is an AI DJ, not a chatbot or a recommendation engine. Within an
active DJ Session, it intentionally guides a musical experience by repeatedly
considering three questions:

1. What should happen next?
2. Why?
3. Should this be communicated to the listener?

The Intelligence Architecture keeps future AI work session-centred instead of
allowing it to fragment into feature-specific capabilities.

## Ownership

| Owner | Responsibility | Does not own |
| --- | --- | --- |
| Session Runtime | Active state, current Session Mood and orchestration. | Persistent Profile intelligence or renderer presentation. |
| Session Planner | Future planning, pacing, transitions, timing, silence and direction. | User-facing content or UI. |
| Knowledge Engine | Retrieval and assembly of relevant musical and session knowledge. | Presentation generation or scheduling. |
| DJ Moment Engine | Transformation of semantic intent and context into an immutable DJ Moment. | Planner timing or playback execution. |
| Music Backend | Playback execution and provider-specific context. | Session planning or DJ meaning. |
| Broadcast | Scoped distribution of the resulting Session state and Moments. | Intelligence or rendering. |
| Renderer | Platform-appropriate presentation. | Intelligence, domain meaning or Moment generation. |

## Intelligence pipeline

```text
Profile
  ↓ optional, permitted Music DNA
Session Runtime
  ↓
Session Planner
  ↓ Knowledge Intent
Knowledge Engine
  ↓ Knowledge Context
DJ Moment Engine
  ↓ immutable DJ Moment
Session Flow
  ↓
Broadcast
  ↓
Presentation
```

The Runtime is the sole orchestrator. Nothing outside an active Runtime invokes
the Planner, Knowledge Engine or DJ Moment Engine directly.

## Session Planner

The Planner owns the future of a Session: its progression, pacing,
transitions, recommendations, timing, silence and future musical direction. It
plans performances rather than features.

The Planner never generates user-facing content. It produces a **Knowledge
Intent**: a semantic statement of what the DJ may want to communicate and why.
It may intentionally choose Silence. Silence is a successful performance
decision, never an error.

## Context-aware Transition contract

A Transition is one intentional DJ performance act that connects two existing,
consecutive Session Flow contributions. It is not a Music Backend playback
transition and does not control playback, a provider queue or a future track.

The Planner alone decides a Transition's necessity and timing from the current
trigger, Planner Intent, Session Direction, Session Mood, DJ Persona,
Performance Memory and already-recorded Session Flow. It may approve one
Transition Intent that identifies the existing contributions and their
relationship rationale, or choose no transition. It must not inspect a future
track or queue, schedule multiple tracks, or perform autonomous replanning.

The approved intent contains no wording, renderer instruction or provider
playback command. When needed, the Knowledge Engine may assemble only already
available, safe context for that approved intent. The DJ Moment Engine then
performs the approval as an immutable Transition Moment with Presentation
Intent frozen at creation. No Planner approval produces no Transition Moment.

## Knowledge Intent

A Knowledge Intent describes **what** the DJ wants to communicate, not how it
will look or sound. Track Context, Artist Story, Recommendation, Genre Context,
Transition Explanation, Concert Suggestion, Session Update and Silence are
examples.

An Intent contains semantic goals only. It contains no UI layout, colour,
button, renderer-specific instruction, voice-provider setting or platform
assumption.

## Knowledge Engine

The Knowledge Engine retrieves and assembles the context relevant to a
Knowledge Intent. It may draw from current track, artist, album, genre, music
metadata, Music Backend context, permitted Music DNA, conversation context,
previous DJ Moments, Session history, Audience Signals and external music
knowledge.

It returns **Knowledge Context**, not presentation. It does not schedule,
generate user-facing storytelling or decide a renderer. Privacy filtering and
source reliability apply before context reaches the DJ Moment Engine.

## DJ Moment Engine

The DJ Moment Engine transforms:

```text
Knowledge Intent
  + Knowledge Context
  + Session Mood
  + DJ Persona
  + Runtime Context
  ↓
DJ Moment
```

It owns storytelling, tone, timing constraints, Presentation Intent, Actions
and Visibility. Its output is validated and immutable. The Engine never
generates UI and never knows platforms; presentation belongs to Renderer Hosts
and DJ Moment Renderers as defined in
[`DJ_PRESENTATION_ARCHITECTURE.md`](DJ_PRESENTATION_ARCHITECTURE.md).
For a Transition, the Engine never infers timing or necessity; it only realizes
Planner approval.

## Music DNA and privacy

Music DNA belongs exclusively to the Profile. It is optional intelligence
input, never a required dependency for a valid DJ Moment and never direct
output. It may influence selection, recommendations, phrasing or priority only
when the active Profile and capability rules permit it.

Community intelligence understands music and the active Session through track,
artist, album, genre and session context. Personal intelligence may additionally
use permitted Music DNA, conversation memory, preferences and listening
history. Personal context never leaks outside owner visibility or into shared
Session output.

## Session Start Strategy, Mood and Persona

The Runtime receives three independent dimensions: **Session Start Strategy**,
**Session Mood** and **DJ Persona**. The Planner combines them with Session
Direction and Performance Memory; no dimension owns or derives another.

**Session Start Strategy** answers why the Session exists. The production
strategies are Continue, Manual and Discover. Discover is not a standalone
feature: it sets a discovery-oriented Session objective whose results appear
as DJ Moments.

Continue may eventually join one already-active item only through the validated
Current Playback Projection contract in
[`CONTINUE_CURRENT_PLAYBACK_CONTINUITY.md`](CONTINUE_CURRENT_PLAYBACK_CONTINUITY.md).
The Planner receives the adopted safe context only after Runtime startup; it
does not decide bootstrap eligibility, inspect a queue or control playback.
The Music Backend Observation Boundary owns the opaque Playback Instance
Identity that accompanies both projection and Track Started observation;
Runtime only compares it to suppress duplicates within the active Session. It
does not depend on the separate Playback Control Boundary.

**Session Mood** answers how the active Session should feel. The client may
supply its initial Mood, and the Runtime may evolve the current Mood later.
Mood influences future DJ Moments and never rewrites history.

**DJ Persona** answers how the DJ performs. It guides verbosity, humour,
storytelling, enthusiasm, interaction frequency and delivery style. Persona
does not own voices; voices are future presentation implementations.

## Reuse and convergence

Future implementation should reuse and refactor proven DJConnect intelligence
services rather than duplicate them. Expected reusable capabilities include Ask
DJ, Track Insight, Music DNA, Discover, music metadata, Music Backend/provider
abstractions, AI provider abstractions, conversation context, response
validation and privacy filtering.

Existing feature-specific ownership should converge behind reusable
intelligence services owned and orchestrated by the Session Runtime. This does
not itself authorize any implementation or deprecation.

## Principles

- The Planner decides.
- The Knowledge Engine knows.
- The DJ Moment Engine performs.
- Broadcast distributes.
- Renderers present.
- The AI never generates UI.
- The AI never knows platforms.
- The AI thinks in Sessions rather than features.
