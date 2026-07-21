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
| Activation | The Runtime resolves effective session capabilities, consumes available bounded playback observations and begins its Session Flow. A future Continue bootstrap may consume exactly one validated Current Playback Projection under [`CONTINUE_CURRENT_PLAYBACK_CONTINUITY.md`](docs/product/CONTINUE_CURRENT_PLAYBACK_CONTINUITY.md); it does not observe or own a queue. |
| Replanning | The Session Planner continuously maintains its rolling horizon as permitted inputs change. |
| Broadcasting | The Broadcast Engine publishes the active session's scoped event-driven Broadcast Feed. |
| Completion | A session ends through an explicit end, an applicable lifecycle condition or a future policy defined by an implementation contract. |
| Persistence | Only permitted Profile-owned outcomes, such as session history or opted-in Music DNA learning, may persist. Runtime state itself never persists. |
| Disposal | The server stops broadcasting and destroys the Runtime, its Planner state, Session Memory and other ephemeral state. |

## Ownership

| Owner | Owns | Never owns |
| --- | --- | --- |
| Profile | Identity, exactly one Music Backend binding, settings, preferences, Music DNA, persistent Session ownership and Conversation History. | Active runtime state, planner state or renderer state. |
| Persistent DJ Session | Durable lifecycle, authorized historical projections and retention state. | Runtime object restoration, provider playback state or Broadcast recovery infrastructure. |
| DJ Session Runtime | Active listening experience, effective Session Capabilities and orchestration of Planner, Moment Engine and Broadcast. | Persistent Profile identity, backend credentials, durable playback state, Playback Instance Identity derivation or Playback Control. |
| Session Planner | The future: rolling planning horizon and Session Flow. | Direct provider playback execution or Profile persistence. |
| DJ Moment Engine | Creative execution from Knowledge Intent to immutable DJ Moment. | Planner timing, direct playback execution or renderer-specific business logic. |
| Broadcast Engine | Distribution of scoped active-session events through Broadcast Feed. | Video, pixels, renderer presentation or persistent profile data. |
| Renderer | Local presentation and user input. | Business logic, planner state, Profile state or backend logic. |
| Music Backend Playback Control Boundary | Provider-specific playback execution, queues, transport, commands and credentials. | DJ Session ownership, planning or audience interpretation. |
| Music Backend Observation Boundary | Normalized playback observation, Current Playback Projection, Track Started observation and opaque Playback Instance Identity. | Playback Control ownership, Session ownership or identity persistence. |

## Profile contract

A Profile is persistent and server-owned. It contains Profile Identity, exactly
one Music Backend binding, Settings, Preferences, Music DNA, persistent Session
ownership and Conversation History. A Profile may start or join a DJ Session,
but never owns its active Runtime state. The durable Session boundary is
defined by [`PERSISTENT_SESSION_ARCHITECTURE.md`](PERSISTENT_SESSION_ARCHITECTURE.md).

## DJ Session Runtime contract

A Runtime is server-owned and exists only while its DJ Session is active. It
owns:

- bounded, validated playback observations consumed for Session orchestration;
- Session Planner;
- DJ Moment Engine;
- Session Flow;
- Conversation Engine;
- Session Memory;
- Broadcast Engine;
- Audience Signals; and
- Runtime State.

All Runtime state is ephemeral. The authoritative Playback Context and Playback
Instance Identity remain owned by the Music Backend Observation Boundary; the
Runtime may only consume bounded, validated observations under their applicable
privacy and capability rules.

For a future Continue Session Start, the Runtime may become active only after
Session Start orchestration validates and adopts one Current Playback Projection
supplied by the Music Backend Observation Boundary. Its opaque Playback Instance
Identity must be unchanged when the corresponding normalized Track Started event
reaches Runtime.
A missing, unavailable or unsupported observation creates no Runtime; the
Runtime never falls back to another Strategy, changes playback or imports
pre-session history. The detailed projection, identity and failure contract is
[`CONTINUE_CURRENT_PLAYBACK_CONTINUITY.md`](docs/product/CONTINUE_CURRENT_PLAYBACK_CONTINUITY.md).
Runtime communicates only with that Observation Boundary for this flow; it does
not depend on the Playback Control Boundary.

The Stage 2 canonical ingress is one `TrackStartedObservation` produced by the
Observation Boundary. It carries the same opaque Playback Instance Identity as
the validated projection and only safe bounded context. The current
Session-Start-internal Track Insight trigger is not a live observation producer.
Runtime compares identity only; it never substitutes URI, title, metadata,
timestamp or progress.

Before Stage 2, a separate Stage 1 active-session observation capability may
compare only safe Media Identity and invoke the existing Track Started
processing for an eligible changed item. It is intentionally not
occurrence-correct, cannot bootstrap Continue and must not use timestamp,
progress or other replay heuristics. Its lifecycle, ownership and limits are
defined in [`docs/product/LIVE_PLAYBACK_OBSERVATION.md`](docs/product/LIVE_PLAYBACK_OBSERVATION.md).

Continue bootstrap is transactional: a Profile-scoped reservation and candidate
Runtime remain non-public until one validated occurrence is atomically adopted.
Failure before commitment silently discards them rather than calling the normal
end lifecycle, which would publish state. The detailed race, rollback and
outcome rules are in `docs/product/CONTINUE_CURRENT_PLAYBACK_CONTINUITY.md`.

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
Flow and Knowledge Intents. A Knowledge Intent states what should be
communicated, not how it should be presented. The Session Runtime exposes the
resulting Broadcast output; clients never consume planner internals. The v4-02
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

### Bounded context-aware Transition

A future production slice may consider a Transition only after the current
contribution has been placed in Session Flow for an existing `track_started`
Planner Event. The Planner may inspect only the triggering Planner Intent,
Session Direction, Session Mood, DJ Persona, Performance Memory and the
immediately preceding recorded Flow contribution. It may return one approved
Transition Intent or no-transition; it must not inspect a future track, queue
or planning horizon.

For an approved Transition, the Runtime may pass the approved intent and only
already-available safe context to the Knowledge Engine when needed, then to
the DJ Moment Engine. The Engine creates one immutable Transition DJMoment
with Presentation Intent frozen at creation, or canonical Silence when the
approved input is invalid or incomplete. The Runtime publishes a non-Silence
Transition only through the existing `publish_moment()` route: the Planner
places its linked `DJ_MOMENT` Flow entry and Broadcast distributes that same
immutable Moment. This introduces no second Flow or Broadcast pipeline.

No-transition produces no Moment, Flow entry or Broadcast event. Performance
Memory records an emitted Transition so the Planner can prevent direct
repetition. A Transition is a DJ performance contribution, not a Music Backend
playback transition.

## DJ Moment Engine contract

The DJ Moment Engine receives one Knowledge Intent with Runtime context, the
current Session Mood and the active DJ Persona. It owns creative execution and
creates one universal immutable DJ Moment. It does not decide Planner timing,
control provider playback or ask renderers to invent presentation behaviour.

Each Moment carries a snapshot Presentation Intent: Persona, Mood, tone,
delivery and voice style, visual theme, energy, importance, maximum duration
and permitted delivery channels such as Broadcast, Voice, Owner and Shared.
A Mood or Persona change affects only future Moments; it never mutates an
already-created Moment. Silence is a first-class Knowledge Intent and Moment
type, allowing the DJ to intentionally make no contribution.

An approved Transition uses this same immutable Moment contract and frozen
Presentation Intent; the Engine may not create one without Planner approval.

Track Insight, Lyrics Insight, Artist Story, Discover and similar experiences
are Moment specializations. Follow-up actions belong to the Moment that
supplies them; a renderer may present those actions but never derive them.
The detailed conceptual vocabulary is in
[`docs/product/DJ_PRESENTATION_ARCHITECTURE.md`](docs/product/DJ_PRESENTATION_ARCHITECTURE.md).

### First production Moment slice

The first implementation is bounded to one active-track `track_context`
request per track identity in a Runtime, with Silence as the safe failure and
non-interruption outcome. It reuses the existing Track Insight pipeline for
current-track resolution, safe music context, Home Assistant Conversation
execution and structured response handling. It adds no autonomous planning,
Voice, VibeCast, Ask DJ chat, action execution or renderer behaviour.

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
A future Continue bootstrap may record only its Session Start and one adopted
current item after commitment. This is an internal post-start contribution with
no identity, provider payload or pre-session history; it is not a new public
DJMoment type or renderer payload. It must use one canonical normalized
`TrackStartedObservation` for later real events and may not synthesize earlier
history.

### Canonical Session Flow Foundation

The Planner creates exactly one non-persistent Session Flow with each active
Runtime and republishes its Flow through the Runtime whenever Planner state
changes. The Flow belongs to the Planner, is distributed only by the Broadcast
Engine and is presented by renderers; no renderer may create or infer its own
Flow. It is destroyed with the Runtime and is never a playlist, queue or
backend playback instruction.

V4-04 defines a deterministic 15-minute current horizon using only `now`,
`next` and `later` positions. Its typed placeholder items are `current_track`,
`planning_horizon`, `maintain_direction`, `future_direction` and
`future_placeholder`. It contains no AI content, recommendations, Track
Insight, Discover or announcements. Queue remains Music Backend playback
context; Session Flow expresses DJ intent for the coming horizon.

The separate [`SESSION_FLOW_RECOVERY_ARCHITECTURE.md`](SESSION_FLOW_RECOVERY_ARCHITECTURE.md)
defines the future Flow revision contract and distinguishes it from
Broadcast-owned delivery cursors and watermarks. It adds no current Runtime or
Flow implementation behaviour.

## Broadcast contract

Broadcast Feed is an event-driven, scoped representation of an active Runtime.
It is never video and never pixels. It exists only while its Runtime exists.

The Feed may publish playback state, current track, progress, artwork, lyrics,
AI Lyric Moments, Track Insight, Session Flow, mood, audience state, planner
events and reactions. Each publication remains capability- and privacy-scoped;
the Feed never exposes private Profile information by default.

### Broadcast Engine Foundation

Each active Runtime creates exactly one non-persistent Broadcast Engine and
destroys it with the Runtime. The Engine owns distribution only: it publishes
the canonical Broadcast State, but never owns planning, playback execution or
renderer presentation. No broadcast state or event survives a session.

Its initial Broadcast State has empty playback and audience sections, plus
safe placeholders for session (`session_id`, `runtime_state`,
`selected_mood`), Planner (`planning_state`, 15-minute planning horizon,
`current_direction`), the Planner-produced Session Flow and Broadcast
(`started_at`). Its stable event vocabulary
is `runtime_created`, `runtime_ended`, `playback_changed`, `playback_progress`,
`planner_updated`, `mood_changed`, `track_changed`, `session_flow_updated`,
`audience_updated`, `broadcast_started` and `broadcast_stopped`. The foundation
does not yet distribute events or generate state content.

The Runtime is the sole orchestrator: inputs flow through Runtime to Planner,
then Knowledge Intent, DJ Moment Engine, DJ Moment, Broadcast Engine and
renderers. Renderers consume only Broadcast State and Broadcast Events; they
never access Planner or Runtime internals. Future Voice follows the same
boundary. VibeCast and the Universal Session Receiver are future renderers that
consume the Broadcast Feed; neither is a Broadcast Engine, Planner or Runtime.

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
