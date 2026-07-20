# DJ Session Runtime Contracts

**Status:** Accepted architecture contract
**Owner:** DJConnect Product Development
**Scope:** Canonical target contracts; no production implementation

## Purpose

This document defines the stable ownership, lifecycle and capability contracts
for a server-owned DJ Session Runtime. Every future Home Assistant, Apple,
Windows, Raspberry Pi, Room Voice and Universal Session Receiver implementation
must conform to these contracts without recreating business logic locally.

It defines no API, storage schema, transport, AI behaviour, playback behaviour
or compatibility layer.

## Lifecycle

```text
Profile
  -> Start Session
  -> DJ Session Runtime created
  -> Runtime active
  -> Replan and broadcast while active
  -> Session ends
  -> Persist permitted results
  -> Destroy Runtime
```

| Phase | Contract |
| --- | --- |
| Creation | The server resolves the Profile and its one Music Backend binding, then creates one ephemeral Runtime for the requested DJ Session. |
| Activation | The Runtime resolves effective session capabilities, observes available Playback Context and begins its Session Flow. |
| Replanning | The Session Planner continuously maintains its rolling horizon as permitted inputs change. |
| Broadcasting | The Broadcast Engine publishes the active session's scoped event-driven Broadcast Feed. |
| Completion | A session ends through an explicit end, an applicable lifecycle condition or a future policy defined by an implementation contract. |
| Persistence | Only permitted Profile-owned outcomes, such as session history or opted-in Music DNA learning, may persist. Runtime state itself never persists. |
| Disposal | The server stops broadcasting and destroys the Runtime, its Planner state, Session Memory and other ephemeral state. |

## Ownership

| Owner | Owns | Never owns |
| --- | --- | --- |
| Profile | Identity, exactly one Music Backend binding, settings, preferences, Music DNA, Session History and Conversation History. | Active runtime state, planner state or renderer state. |
| DJ Session Runtime | Active listening experience and the effective Session Capabilities. | Persistent Profile identity, backend credentials or durable playback state. |
| Session Planner | The future: rolling planning horizon and Session Flow. | Direct provider playback execution or Profile persistence. |
| Broadcast Engine | Distribution of scoped active-session events through Broadcast Feed. | Video, pixels, renderer presentation or persistent profile data. |
| Renderer | Local presentation and user input. | Business logic, planner state, Profile state or backend logic. |
| Music Backend | Provider-specific playback execution, queues, credentials and availability. | DJ Session ownership, planning or audience interpretation. |

## Profile contract

A Profile is persistent and server-owned. It contains Profile Identity, exactly
one Music Backend binding, Settings, Preferences, Music DNA, Session History
and Conversation History. A Profile may start or join a DJ Session, but never
owns its active Runtime state.

## DJ Session Runtime contract

A Runtime is server-owned and exists only while its DJ Session is active. It
owns:

- Playback Context;
- Session Planner;
- Session Flow;
- Conversation Engine;
- Session Memory;
- Broadcast Engine;
- Audience Signals; and
- Runtime State.

All Runtime state is ephemeral. The Runtime may consume Profile and Music
Backend information only under their applicable privacy and capability rules.

## Session Planner contract

The Planner owns the future: a rolling planning horizon of approximately
fifteen minutes, planning state, current musical direction, pending Planner
Events and the future production of Session Flow and Broadcast generation. The
Runtime owns the present; the Profile owns the past.

The horizon is intentionally rolling rather than a static playlist:

| Horizon | Meaning |
| --- | --- |
| Near future | The next moments requiring immediate planning attention. |
| Medium future | The remainder of the active fifteen-minute planning horizon. |
| Longer future | Intent beyond the current horizon, refreshed only as the rolling window advances. |

The foundation creates one Planner together with its Runtime and destroys it
with that Runtime. It is never persistent and never shared between sessions.
Its initial state is `ready`, a 15-minute horizon, `maintain` direction and no
current goal or pending events. Initial direction placeholders are `maintain`,
`increase_energy`, `decrease_energy`, `explore` and `recover`.

Planner Events are internal inputs, not client commands: `track_finished`,
`playback_changed`, `mood_changed`, `audience_signal`, `conversation` and
`planner_tick`. The foundation recognises their vocabulary but does not yet
handle or schedule them.

The Planner produces a Planner Output that will eventually contain Session
Flow. The Session Runtime exposes that output; clients consume it. The v4-02
foundation exposes `session_flow: null` and generates no flow.

Mood belongs exclusively to the active Session Runtime. The Planner consumes
runtime mood as an input and never owns it; a Profile never owns mood.

Future Planner implementations will add replanning, announcements, Track
Insight scheduling, Discover scheduling, mood progression and transition
planning.

The Planner consumes available playback, aggregated Audience Signals, owner
interaction, conversation, permitted Music DNA and backend availability. It
does not issue direct playback commands, generate a static playlist or mutate
Profile state.

## Session Flow contract

Session Flow is independent of the provider playback queue. It is an ordered,
typed runtime representation of what the DJ is planning next. Its initial item
catalogue is:

- `Track`
- `Announcement`
- `TrackInsight`
- `Discover`
- `MoodTransition`
- `MusicalDirection`
- `ConversationOpportunity`

The selected Music Backend owns its Playback Queue. Queue behaviour is a
backend implementation detail and may appear only as an advanced playback view.

## Broadcast contract

Broadcast Feed is an event-driven, scoped representation of an active Runtime.
It is never video and never pixels. It exists only while its Runtime exists.

The Feed may publish playback state, current track, progress, artwork, lyrics,
AI Lyric Moments, Track Insight, Session Flow, mood, audience state, planner
events and reactions. Each publication remains capability- and privacy-scoped;
the Feed never exposes private Profile information by default.

## Audience Signal contract

Audience Signals are planner inputs, never direct playback commands. The
initial catalogue is:

- `Like`
- `MoreEnergy`
- `LessEnergy`
- `MoodSuggestion`
- `GenreSuggestion`
- `ArtistSuggestion`
- `ArtistExclusion`
- `TrackSuggestion`
- `MoreLikeThis`
- `SurpriseUs`

The Runtime aggregates signals within the active session before the Planner
interprets them. Aggregation may combine compatible inputs, retain meaningful
direction or suppress insufficient/conflicting signals; it never translates a
single signal directly into provider playback. The Planner decides whether and
how aggregated signals influence a future Session Flow.

## Room Voice contract

Room Voice communicates with the active Session Runtime. It supports General
Music Knowledge, Session Questions, Session Flow Questions and Audience
Signals. Room Voice never exposes private Profile information, Music DNA,
Conversation History or Session History unless a future explicit privacy
contract permits a safe shared presentation.

## Renderer contract

Each Runtime resolves and supplies effective capabilities to its renderers.
Renderers consume those capabilities, render scoped session state locally and
submit permitted user input. They never own business logic or Planner state.

| Renderer | Contract |
| --- | --- |
| Personal Renderer | Native, Profile-bound DJ Session experience and control. |
| Shared Renderer | Universal Session Receiver for the scoped Broadcast Feed of an active shared session. |
| Room Renderer | Voice/control representation of the active room session. |

## Session capability contract

Session Capabilities are effective, runtime-owned availability statements. The
Profile owns enduring preferences and eligibility, the Music Backend owns its
execution availability, and the Runtime resolves the resulting capabilities
for its active session. Renderers may consume but never enable capabilities.

The initial capability catalogue is:

- `canAskDJ`
- `canSubmitAudienceSignals`
- `canChangeMood`
- `canStartBroadcast`
- `canUseMusicDNA`
- `canExportProfile`

Additional capabilities require a documented owner, privacy boundary and
renderer-consumption rule before implementation.

## First production slice

1. Create a server-owned DJ Session Runtime.
2. Expose a native active Session UI capable of starting, displaying and
   ending one active session.

This slice must remain bounded: it does not add AI logic, playback logic,
Broadcast Feed transport, Audience Signal execution, persistence beyond the
accepted contract, or v3 compatibility work.
