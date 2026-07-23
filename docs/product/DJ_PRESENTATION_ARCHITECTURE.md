# DJ Presentation Architecture

## Status

Canonical conceptual architecture. This document introduces no production
implementation, runtime behaviour, client implementation, Voice, VibeCast or
Ask DJ behaviour.

## Purpose

This architecture is the canonical bridge between the server-owned DJ Session
and every future client experience. It separates what the AI decides from how
a platform presents it.

```text
Profile → Session Runtime → Session Planner → Knowledge Intent → DJ Moment Engine → DJ Moment → Broadcast → Renderer Host → DJ Moment Renderer → Presentation Mode
```

## Canonical layers

### Intelligence Layer

The Intelligence Layer owns Session Planner timing, Knowledge Intent
generation and Runtime decision making. It decides **what** the AI DJ should
communicate or intentionally not communicate.

Knowledge Intents may describe Track Context, Artist Story, Album Story, Genre
Story, Music History, Concert Information, Audience Response, Transition,
Recommendation, Session Direction or Silence. They contain no UI layout,
colour, button, platform, voice-provider or renderer instruction. The
Intelligence Layer never knows anything about UI.

### Domain Layer

The Domain Layer owns the platform-independent semantic output: DJ Moment,
Presentation Intent, contextual Actions, Visibility and Delivery Channels.

The DJ Moment Engine turns a Knowledge Intent and current Runtime context into
exactly one immutable DJ Moment. The Planner owns timing; the Moment Engine
owns creative execution. The Domain Layer contains no platform-specific
presentation logic.

### Presentation Layer

The Presentation Layer turns DJ Moments into user experiences. It owns Renderer
Hosts, Presentation Modes and DJ Moment Renderers. It never generates a Moment
or changes the semantic meaning already decided by the server.

The server-owned [Presentation Composer](PRESENTATION_COMPOSER_ARCHITECTURE.md)
is the canonical boundary between one immutable DJMoment and one immutable,
renderer-safe Presentation before Broadcast. It composes presentation only;
Session Intelligence retains Moment existence, meaning, placement and Silence.
Renderer Hosts consume immutable Presentations and render locally without
composing dialogue or Sidekick behaviour.

## DJ Persona and Session Mood

A **DJ Persona** is a first-class behavioural identity: Home DJ, Radio DJ,
Club DJ, Festival DJ or Late Night Host are examples. It defines storytelling,
verbosity, humour, enthusiasm, pacing, interaction frequency, wording and
delivery style. It is neither a voice nor Session Mood. Future Premium Cloud
voices implement Personas; they are not Personas themselves.

**Session Mood** remains a dynamic Runtime property. A change affects only
future Presentation Intents and Moments. It never mutates an existing Moment.

## DJ Moment and Presentation Intent

A **DJ Moment** is the universal presentation object. Everything intentionally
performed by the AI DJ becomes a Moment: Track Story, Artist Story, Genre
Story, Recommendation, Session Update, Concert Suggestion, Trivia,
Transition or Silence.

A Moment contains type, title, summary, content, artwork, Knowledge Intent,
Presentation Intent, actions, visibility, delivery and importance. Canonical
types include Track, Transition, Lyric, Artist, Album, Genre, Music History,
Audience, Session, Recommendation, Discover, Concert, Producer, Trivia and
Silence. Additional types may be added without changing Planner architecture.
Silence is explicit: a DJ may intentionally decide not to speak.

A Transition Moment is created only from Planner-approved timing and existing
Session context. It neither represents nor controls a Music Backend playback
transition, and Renderer Hosts may not infer or create it.

A **Presentation Intent** is an immutable semantic snapshot of how a Moment
should feel. It may include Session Mood, DJ Persona, Tone of Voice, Delivery
Style, Importance, Energy, Voice Style, Visual Theme, maximum duration,
Visibility and Delivery Channels. It never contains platform-specific styling,
literal colours, fonts, CSS, Swift, layout or voice-provider configuration.

Follow-up Actions belong to the Moment. They are semantic capabilities with
safe payloads; renderers only present them and never invent additional actions.

Track Insight is an expanded presentation of a Track DJ Moment. Artist Story,
Genre Story, Recommendation, Discover and Concert are likewise expanded
presentations of specific Moment types, not independent feature concepts.

## Renderer Hosts

A **Renderer Host** renders DJ Moments on one technology stack. Apple Renderer
Host, Windows Renderer Host, Web Renderer Host, Visual Renderer Host and Audio
Renderer Host are presentation examples. An Audio Renderer Host is the internal
DJConnect abstraction; a Home Assistant Voice Satellite remains the external
platform term for one possible implementation.

An Ambient Light Renderer Host is a separately deferred presentation role. It
interprets the same immutable DJMoment and Presentation Intent as other
Renderer Hosts and does not synchronize to raw audio or own lighting behavior.
See [`../technical/AMBIENT_LIGHT_RENDERER_HOST_ARCHITECTURE.md`](../technical/AMBIENT_LIGHT_RENDERER_HOST_ARCHITECTURE.md).

A Renderer Host owns its renderer registry, renderer discovery, renderer
lifecycle and navigation integration. It selects an appropriate Presentation
Mode for its current context. It does not own server meaning, Moment creation,
Session Flow or cross-platform semantics.

The Universal Receiver is the Web Renderer Host. Its server-owned projection,
subscription lifecycle and security boundary are defined in
[`../technical/UNIVERSAL_RECEIVER_ARCHITECTURE.md`](../technical/UNIVERSAL_RECEIVER_ARCHITECTURE.md).
Device Lifecycle (Guest/Registered) and Experience Mode
(Interactive/Ambient) are independent Renderer Host axes defined in
[`../technical/RENDERER_HOST_CLASSIFICATION.md`](../technical/RENDERER_HOST_CLASSIFICATION.md).
Future room-scoped delivery is separately bounded by the
[`../technical/ROOM_PRESENTATION_ROUTING_ARCHITECTURE.md`](../technical/ROOM_PRESENTATION_ROUTING_ARCHITECTURE.md):
the active playback Area selects eligible independent visual and audio Renderer
Hosts, without changing DJMoment ownership or introducing host-to-host
communication.
The platform-neutral Audio Renderer Host boundary is defined in
[`../technical/AUDIO_RENDERER_HOST_ARCHITECTURE.md`](../technical/AUDIO_RENDERER_HOST_ARCHITECTURE.md).
The renderer-neutral Speech Presentation consumption boundary is defined in
[`../technical/SPEECH_RENDERING_CONTRACT.md`](../technical/SPEECH_RENDERING_CONTRACT.md).
VibeCast is the distinct ambient-first web-renderer product experience built on
the Universal Receiver Web Platform. Its deferred Google Cast Custom Web
Receiver V1 model is defined in
[`VIBECAST_ARCHITECTURE.md`](VIBECAST_ARCHITECTURE.md); it adds no second
presentation pipeline or Renderer Host authority.
Audience Experience is a separate, deferred participant-originated presentation
concern. Its Audience Events are not DJMoments and its renderer-safe Audience
Projection may add an independent Audience Layer without changing DJMoment
ownership or Session Intelligence; see
[`AUDIENCE_EXPERIENCE_ARCHITECTURE.md`](AUDIENCE_EXPERIENCE_ARCHITECTURE.md).

## Presentation Modes

Presentation Modes describe user experiences, not platforms. The initial
canonical modes are:

| Mode | Purpose | Typical contexts |
| --- | --- | --- |
| Compact | The primary current-session contribution. | iPhone Session, small desktop surfaces. |
| Expanded | Richer detail for a selected Moment. | iPhone detail, macOS, Windows. |
| Timeline | A chronological Session Flow entry. | Session Flow on any visual client. |
| Micro | A glanceable contribution. | Apple Watch. |
| TV | Shared, room-scale presentation. | Television. |
| Voice | Spoken or conversational presentation. | Voice surfaces. |
| Notification | Brief out-of-app awareness. | Live Activity or equivalent. |
| Ambient | Passive room presentation. | Raspberry Pi or ambient displays. |

A platform chooses the mode appropriate to its capability and current context:
Apple Watch commonly selects Micro; an iPhone Session selects Compact; an
iPhone detail, macOS or Windows may select Expanded; TV selects TV; Voice
selects Voice; Raspberry Pi may select Ambient or TV; a Live Activity may
select Notification. The modes themselves remain platform independent.

## DJ Moment Renderers

A **DJ Moment Renderer** understands one Moment type and may support multiple
Presentation Modes. Track Renderer, Artist Renderer, Genre Renderer,
Recommendation Renderer, Concert Renderer and Session Renderer are examples.

For example, a Track Renderer can support Compact, Expanded, Timeline, TV,
Voice and Notification. Its wording and visuals may adapt to the selected
mode, but the Moment's semantic meaning, Presentation Intent, actions,
visibility and delivery remain identical.

## Current Session State and Session Flow

The DJ Session screen presents exactly one primary **Current Session State**
card. It represents the currently active Session item, most commonly the latest
DJ Moment. Users may continue from that card into the complete Session Flow.

**Session Flow** is the canonical chronological narrative of the Session. Its
items may include Session Started, Track Started, DJ Moment, Transition,
Recommendation, Mood Change, Silence and Session Finished. Audience Events are
separate participant-originated Session context, not Flow items or DJMoments.
It tells the story of the session; it is not a provider queue or a collection
of unrelated feature pages.

## Canonical principles

- Everything the AI intentionally performs becomes a DJ Moment.
- Every device presents the same DJ Moment.
- Presentation adapts to context; meaning remains identical.
- Renderer Hosts own platforms.
- Presentation Modes own experiences.
- Renderers own visualization.
- The server owns meaning.
- Clients own presentation.
