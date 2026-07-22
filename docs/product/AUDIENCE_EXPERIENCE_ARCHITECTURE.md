# Audience Experience Architecture

## Status

Canonical product and architecture definition. **Deferred implementation only.**
This document authorizes no reaction intake, Audience Event storage, Broadcast
change, renderer code, Session Intelligence behaviour, Planner influence,
persistent learning, music-backend Like or television interaction.

## Purpose and principle

**Audience Experience** is the parallel, server-owned Session concern through
which Guests and Registered participants may eventually express lightweight,
time-bound reactions and eligible Renderer Hosts may present them safely.

> Audience reactions are visible and observable, but not authoritative. The DJ
> feels the audience, but is not controlled by every reaction.

Audience Experience does not create DJMoments. A DJMoment remains immutable,
authored Session Intelligence output; an Audience Event remains immutable,
participant-originated Session context.
Audience Events are not DJMoments.

```text
Session Intelligence                         Audience Experience
Session Planner                              Audience Reaction Intake
Knowledge Engine                             Audience Event Stream
DJ Moment Engine                             Audience Projection
Session Direction                            Audience Energy Aggregation (deferred)
Performance Memory
immutable DJMoments
```

The concerns may share Session time and renderer-safe delivery, but neither
rewrites the other. The current task does not authorize the Planner to consume
Audience Events, reactions, counts or Audience Energy.

## Audience Events

An **Audience Event** is an immutable, ephemeral, participant-originated event
associated with one active Session and its Session time. It is independent of
DJMoment identity. It may be contextually associated with the active playback
occurrence, a current DJMoment, a Transition or the Session atmosphere, but
those associations never turn it into a command or guaranteed preference for a
particular track.

A future implementation may model only bounded conceptual information:

- audience event identity and active Session identity;
- a small reaction type;
- occurrence time;
- an optional safe playback-occurrence reference;
- an optional privacy-filtered presentation identity; and
- privacy mode.

This is not a production schema. Raw participant, Profile, account, device,
history and preference data are never renderer-safe by default.

## Reaction vocabulary and intake

The initial conceptual vocabulary is deliberately small and ambient-appropriate:

- Heart;
- Love;
- Applause; and
- Cheer.

Audience Experience is not a social platform. It excludes free-form chat,
comments, images, GIFs, user-generated visual content and unrestricted emoji.

The future conceptual flow is:

```text
Guest or Registered Participant
        ↓
Audience Reaction Command
        ↓
server-side validation
        ↓
Audience Event
        ↓
Audience Event Stream
        ↓
Audience Projection
        ↓
eligible Renderer Hosts
```

Audience state is server-owned. A client may show immediate local acknowledgement
after an interaction, but it must not represent that reaction as accepted until
server validation supplies the canonical Audience Projection. A future
implementation must address duplicate submissions, flooding, automated clients,
replay attacks, unsafe attribution, visual overload and unauthorized Session
participation.

## Broadcast and privacy boundary

Audience Experience extends the **conceptual** renderer-safe Broadcast model
only; it changes no current Broadcast implementation:

```text
Broadcast
├── Playback Projection
├── Session Projection
├── DJMoment Projection
└── Audience Projection
```

An Audience Projection is privacy-filtered and renderer-safe. It does not
expose Profile identity, account identifiers, device identifiers, personal
history or private preference data unless an explicit future privacy policy
authorizes a narrower presentation. Ambient presentation defaults to anonymous
reaction-only output; a generic participant or display name requires separately
approved attribution policy.

Guest reactions remain Session-scoped and do not create persistent preferences.
A Registered participant may be associated internally with a Profile only under
future policy; that does not make the reaction a Spotify Like, library Favorite,
Profile recommendation signal, Music DNA preference or repeat request. A future
persistent Favorite action must be explicit and separate.

## Audience Layer and presentation pressure

Audience is an independent renderer presentation layer:

```text
Background Atmosphere Layer
        ↓
Music Presence Layer
        ↓
DJMoment Layer
        ↓
Audience Layer
```

The Audience Layer coexists with, and never replaces, dismisses or obscures the
DJMoment Layer. Each Renderer Host chooses whether and how to present an
eligible Audience Projection according to its experience and capabilities.

Ambient renderers may apply **Audience Presentation Pressure** locally to
preserve calm and stability: rate limiting, clustering, prioritization, density
limits, bounded animation concurrency and graceful dropping of redundant visual
reactions. These renderer-local choices never rewrite the underlying immutable
Audience Events or coordinate with other Renderer Hosts.

VibeCast is an illustrative future Ambient presentation: a Heart may be a
subtle upward bubble, gentle fade or small ambient particle response; Applause
may be a soft shimmer, restrained particle cluster or brief ambient highlight.
Several similar reactions may become one coherent cluster or restrained count
indicator. This should feel like the room responding, never like a social-feed
wall, notification storm, slot-machine effect or competitive counter.

A future television sequence is therefore: VibeCast presents the active track
and Session composition; a participant submits Heart; the server validates one
Audience Event; VibeCast receives the updated Audience Projection; a transient
Audience Layer bubble appears without interrupting the active DJMoment; a burst
may group visually; the presentation fades without user action. This example is
non-normative and defines no animation, window or threshold.

## Audience Energy and artistic autonomy

**Audience Energy Aggregation** is deferred. It may someday transform a bounded
window of raw Audience Events into a coarse, privacy-preserving observation
such as Calm, Engaged, Rising, Excited or Peak. It must never treat no reaction
as negative feedback: passive listening, unavailable interaction, small
audiences and deliberate immersion are all ambiguous.

A separate future **Audience Observation** decision may consider exposing only
coarse engagement level, momentum, confidence and observation window to Session
Intelligence. The Planner must never receive individual reactions, participant
identity or raw event history, and must never react directly to a Heart or
Applause. No Planner integration is authorized here.

Even if a later decision admits sustained, confidence-qualified Audience Energy
as weak context, it cannot become a track command, mandatory repeat request,
reason to abandon the active plan or proof that Silence is rejection. Session
Strategy, Mood, Persona, Direction and Performance Memory remain the canonical
decision context. Raw Audience Events must not automatically enter Performance
Memory or any persistent learning store.

## Renderer roles and room coherence

The same Audience Projection may be rendered differently without peer
coordination:

| Renderer Host | Illustrative future presentation |
| --- | --- |
| VibeCast | Ambient bubbles, particles or restrained clusters. |
| Raspberry Pi Wall Panel | Compact indicator or count. |
| Mobile client | Reaction input and lightweight acknowledgement. |
| Audio Renderer Host | Normally ignores individual reactions. |
| Ambient Light Renderer Host | Optional restrained aggregate accent only. |

A future Ambient Light Renderer may consume a renderer-safe Audience Projection
or Audience Presentation Intent for a short warm lift, gentle brightness pulse
or palette accent. It never receives raw identity, communicates directly with
VibeCast, becomes beat-reactive or turns reactions into strobing. No lighting
work is authorized.

## Deferred policy and sequencing

A future **Audience Participation Policy** is Session or installation policy,
not renderer-local policy. It may define whether reactions are enabled, Guest
access, allowed types, attribution mode, rate limits, persistence prohibition
or renderer exposure.

Audience Experience is not required for the initial VibeCast visual foundation.
The intended sequence is:

1. Universal Receiver Web Platform foundation;
2. VibeCast Custom Web Receiver;
3. canonical visual Session projections;
4. basic Ambient VibeCast experience;
5. Audience Experience architecture validation;
6. bounded Audience Projection implementation;
7. VibeCast Audience Layer implementation; and
8. only then consider Audience Energy or separately governed Audience
   Observation.

## Non-goals

This definition does not authorize reaction submission, Audience Event
persistence, social feeds, chat, comments, public profiles, leaderboards,
competitive metrics, raw Planner consumption, Session direction change,
automatic Spotify Likes, automatic Music DNA changes, identity-bearing
television overlays, VibeCast animation, Ambient Light implementation, speech
announcements for individual reactions or native television applications.

## References

- [DJ Presentation Architecture](DJ_PRESENTATION_ARCHITECTURE.md)
- [VibeCast Architecture and V1 Product Definition](VIBECAST_ARCHITECTURE.md)
- [Universal Receiver V1 — Server Architecture](../technical/UNIVERSAL_RECEIVER_ARCHITECTURE.md)
- [Room Presentation Routing Architecture](../technical/ROOM_PRESENTATION_ROUTING_ARCHITECTURE.md)
- [Ambient Light Renderer Host Architecture](../technical/AMBIENT_LIGHT_RENDERER_HOST_ARCHITECTURE.md)
