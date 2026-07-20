# DJConnect v4 Architecture

**Status:** Accepted architecture direction
**Owner:** DJConnect Product Development
**Scope:** Canonical v4 product architecture; documentation only

## Purpose

DJConnect v4 converges the existing product around one model: an AI DJ hosts
one or more active **DJ Sessions**. Playback is context supplied by a Music
Backend; the DJ Session is the product.

This is an architectural convergence, not a new application. Future delivery
must reuse proven components where they fit, move responsibility to its
canonical owner, and remove obsolete architecture when it no longer fits. As
DJConnect v3 was never publicly released, v4 introduces no compatibility
layer, migration path, or transitional architecture solely for v3 support.

## Ownership model

```text
Profile (persistent)
  -> exactly one Music Backend binding
  -> Music DNA, settings, preferences and conversation/session history
  -> starts or joins DJ Sessions

DJ Session Runtime (ephemeral, server-owned)
  -> Playback Context
  -> Session Planner
  -> DJ Moment Engine
  -> Conversation Engine
  -> Session Memory and Session Flow
  -> Broadcast Engine and Audience Signals
  -> active Runtime State
```

A Profile owns persistent identity and long-term state. A Session Runtime owns
only the active listening experience. The Runtime ends with the session; only
permitted durable outcomes are written back to the owning Profile. A Music
Backend belongs to a Profile, never to a DJ Session.

The v4 ownership chain is strict: Profile owns identity and history; Runtime
owns the present; Planner owns the future; the DJ Moment Engine owns creative
execution; Broadcast owns distribution; Renderers own local presentation; and
the Music Backend owns playback execution. The Runtime is the only
orchestrator: inputs enter the Runtime, which coordinates its Planner, DJ
Moment Engine and then its Broadcast Engine. Renderers never read Planner state
or other Runtime internals directly.

## Session Planner and Session Flow

The **Session Planner** is the central AI orchestration engine. It continuously
plans roughly the next fifteen minutes and replans as playback, listener
interaction, audience signals, conversation, mood, backend availability or
permitted Music DNA changes.

The Planner does not generate a static playlist and does not take ownership of
provider playback. It supplies a **Session Flow**: what the DJ is planning
next, including the current track, announcements, Track Insights, Discover
moments, musical direction and planned transitions. A provider queue can
remain available as an advanced view under More, but is no longer the primary
DJConnect experience.

The Planner's presentation output is a **Knowledge Intent**: what the DJ should
communicate, never its wording, voice, visual treatment or delivery. A DJ
Moment Engine combines the Knowledge Intent with Runtime context, current
Session Mood and DJ Persona, then creates one immutable **DJ Moment** with its
resolved Presentation Intent. The Planner remains responsible for timing; the
Moment Engine is responsible for creative execution.

## Broadcast and rendering

The **Broadcast Engine** publishes an event-driven **Broadcast Feed** for an
active DJ Session. It is not video streaming and is not server-rendered video.
Receivers render the feed locally according to their capabilities and privacy
scope.

VibeCast is a renderer of an active DJ Session's Broadcast Feed. It is
delivered by one Universal Session Receiver with render modes such as TV,
Guest, Desktop, Browser, Raspberry Pi and Chromecast.

Renderers belong to three experience categories:

| Category | Responsibility | Examples |
| --- | --- | --- |
| Personal Experience | Native, profile-bound DJ Session experience and control. | iPhone, iPad, macOS, Windows, Apple Watch |
| Shared Experience | Universal Session Receiver for an active shared session. | Browser, TV, Chromecast, Raspberry Pi, desktop, guest phones |
| Room Experience | Voice/control rendering for the active room DJ Session. | HA Voice, ESP32 Voice Satellite |

The native Apple application is one shell containing Owner, Guest and Demo
runtimes. Its interface is capability-driven, not mode-driven.

Every active Runtime owns exactly one ephemeral Broadcast Engine. It publishes
the canonical Broadcast State and, in future, Broadcast Events; it does not
plan, execute playback or render pixels. The initial state is intentionally
empty except for safe session, planner and lifecycle placeholders. It is the
only outward-facing representation of an active DJ Session.

```text
Inputs -> Session Runtime -> Session Planner -> Knowledge Intent -> DJ Moment Engine -> DJ Moment -> Broadcast Engine -> Renderers
```

All renderers consume Broadcast State and Broadcast Events only: Native Owner,
Native Guest, Demo, Universal Session Receiver, TV, Browser, Pi, Chromecast
and Room Voice. No renderer accesses Runtime internals. Session Flow remains
Planner-owned, Broadcast-distributed and renderer-presented. The V4-04
foundation creates only deterministic current-horizon placeholders; it does
not add AI planning, recommendations or content generation. VibeCast is a renderer that consumes the
Broadcast Feed, never a Broadcast implementation, Planner or Runtime. Room
Voice likewise consumes the Runtime through the Broadcast model rather than
querying the Planner directly.

## Boundaries

- Clients never store Profile state or become sources of persistent session
  truth.
- Music Backend adapters retain provider credentials, playback control, queues
  and provider-specific behaviour.
- Session Runtimes consume Playback Context; they do not own a backend,
  provider account or playback state. A future Continue bootstrap may consume
  one safe Current Playback Projection only as defined in
  [`docs/product/CONTINUE_CURRENT_PLAYBACK_CONTINUITY.md`](docs/product/CONTINUE_CURRENT_PLAYBACK_CONTINUITY.md).
- Broadcast receivers render locally and do not infer private Profile data.
- This document defines target architecture only. It creates no storage,
  protocol, API, synchronization, client UI, migration or implementation
 commitment.

The detailed conceptual model, including Personas, Presentation Intents,
immutable Moments and explicit Silence, is
[`docs/product/DJ_PRESENTATION_ARCHITECTURE.md`](docs/product/DJ_PRESENTATION_ARCHITECTURE.md).

## Delivery consequences

Future implementation must first establish the runtime, event and privacy
contracts needed by this model, then adopt the Session Planner, Session Flow,
Broadcast Feed and renderers in bounded increments. No client may recreate the
planner, persistent profile state or broadcast semantics locally.

`DJ_SESSION_RUNTIME_CONTRACTS.md` is the canonical lifecycle, ownership and
capability contract for this architecture.
