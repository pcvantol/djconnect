# Presentation Composer Architecture

**Status:** Canonical architecture and first bounded server implementation
**Owner:** Presentation Platform
**Scope:** Immutable renderer-safe Presentation composition after an approved
DJMoment and before Broadcast.

## Purpose

Presentation Composer transforms exactly one approved immutable DJMoment into
exactly one immutable, renderer-safe Presentation. It determines how an
already-approved Moment is presented; it never changes whether the Moment
exists, what it means, where it belongs in Session Flow or whether Silence was
selected.

```text
Session Intelligence
  -> immutable DJMoment
  -> Presentation Composer
  -> immutable Presentation
  -> Broadcast
  -> Renderer Host
```

Presentation Composer is a first-class server component of the Presentation
Platform. It is neither a Planner, Knowledge Engine, DJ Moment Engine nor a
second Session Runtime.

## Ownership

| Owner | Responsibility | Does not own |
| --- | --- | --- |
| Session Intelligence | DJMoment existence, semantic intent, approved knowledge, placement, Session timing, Direction, Performance Memory and Silence. | Presentation composition or renderer behaviour. |
| Presentation Composer | Presentation composition, pacing, sequencing, roles, presentation-specific fallback and immutable Presentation creation. | Planning, knowledge retrieval, semantic intent, Session Flow, playback, TTS, voice selection or hardware capability. |
| Broadcast | Renderer-safe distribution of immutable Presentations. | Composition, rendering or semantic ownership. |
| Renderer Host | Local presentation and local Speaker Role-to-voice mapping where supported. | Dialogue composition, Sidekick behaviour or Presentation rewriting. |

The Composer consumes only an approved immutable DJMoment and Runtime-derived
Presentation Context. It never creates a DJMoment or independent knowledge.

## Presentation model

An internal Presentation has one source DJMoment identity, Session identity,
source type, shared Presentation Context and optional capability projections.
It never exists without a source DJMoment. At the Broadcast boundary it becomes
the additive canonical **Presentation Projection**: presentation identity,
source Moment identity and type, renderer-safe visibility, optional speech mode
and ordered renderer-safe segments. The Projection deliberately excludes
Session identity, Presentation Context, Planner state, Knowledge data, prompts,
provider data, renderer configuration and Profile-private data.

The first implemented capability is **Speech Presentation**. Future Visual,
Ambient, Audience and Ambient Light Presentation capabilities remain separate
and deferred; the Composer is Presentation-oriented, not Speech-oriented. The
complete hierarchy, ownership and capability-independence model is defined in
the [Presentation Capability Architecture](PRESENTATION_CAPABILITY_ARCHITECTURE.md).

### Presentation Context

Presentation Context is derived by the server from approved Runtime and
DJMoment presentation data. It carries one shared Session Mood, DJ Persona,
Session Direction, Session Energy, presentation style and bounded constraints.
Every Presentation Role inherits this one context; no role owns independent
Mood, Persona, Direction or Energy.

### Speech Presentation

Speech Presentation is a renderer-safe Presentation capability, not a new
Session Intelligence model. It contains ordered immutable Speech Segments.
Each segment has an ordinal, renderer-safe text and a semantic Speaker Role.

Speaker Role is platform-neutral. The first bounded roles are `DJ` and
`Sidekick`. A role is not a voice, TTS engine, renderer identity or provider
identifier. A Renderer Host may map a role to a configured local voice; the
Composer never receives voice identifiers, provider names, TTS engines or
hardware capabilities.

## First composition slice

The implementation supports exactly two Speech Presentation modes:

| Mode | Segments |
| --- | --- |
| Primary Only | One DJ segment. |
| Primary With Sidekick | One DJ segment followed by one bounded Sidekick segment. |

The Sidekick is a bounded secondary Presentation Role. It is not a second DJ,
Planner, Knowledge Engine, Runtime or autonomous AI agent. It cannot author a
DJMoment, select a topic, retrieve knowledge, alter Session Direction,
reinterpret Silence or expand semantic scope.

The first deterministic Sidekick eligibility rule requires an approved Artist
Story realized as an Artist DJMoment with a non-empty approved summary. Its
single secondary segment repeats that approved summary verbatim. This creates
no new facts or knowledge. Every other eligible speech-bearing Moment falls
back deterministically to Primary Only. Silence and Moments without approved
speech content have no Speech Presentation.

Composition failure never invalidates the source DJMoment, creates Silence,
changes Session Flow or changes Session Direction. The canonical fallback is
Primary Only whenever the source supports one primary segment.

## Runtime, projection and diagnostics

The active Session Runtime invokes the Composer only after a DJMoment is
approved and realized. It then keeps the existing DJMoment and Session Flow
publication order intact, and publishes the additive immutable Presentation
Projection through the same Broadcast snapshot and incremental event model.
Presentations never become Session Flow entries, do not alter Flow ordering and
cannot replace the DJMoment projection used by existing Renderer Hosts.

Runtime-only bounded diagnostics record `presentation_created`, `primary_only`,
`primary_with_sidekick`, `sidekick_disabled`, `sidekick_ineligible` or
`sidekick_fallback`. They are neither Broadcast payloads nor renderer state.
They contain no source payload, provider data or user-profile data.

## Server and Broadcast boundary

The Composer runs entirely inside the server-owned active Session Runtime. The
Runtime composes before Broadcast publication. Broadcast retains the existing
DJMoment projection for Session-history compatibility and additionally publishes
the immutable Presentation projection as the renderer execution output. The
new presentation publication is renderer-safe and respects the source
visibility constraint.

Renderer Hosts receive immutable Presentations and render them locally. They
must not compose dialogue, generate Sidekick behaviour or rewrite content.

An Audio Renderer Host may map the semantic `DJ` and `Sidekick` roles to local
voices and perform local TTS after it receives a Projection. That mapping is
renderer-local: the server never selects a voice, TTS engine, room or speech
provider, and Broadcast carries text only.

The complete Renderer-neutral consumption boundary is the
[Speech Rendering Contract](../technical/SPEECH_RENDERING_CONTRACT.md).

## Deferred capabilities

The following are explicitly deferred: DJ–Sidekick–DJ dialogue, Presentation
Cast, Presentation Memory, multiple Sidekick personas, generative dialogue,
Audience-aware presentation, renderer-specific composition, voice mapping UI,
Apple and Home Assistant renderer implementation, Apple local speech rendering,
VibeCast speech rendering, Audio Renderer Host implementation, room routing,
ambient presentation, synchronized segment highlighting, speech assets, cloud
speech, Audience Presentation and Ambient Light Presentation.

## Canonical references

- [DJ Presentation Architecture](DJ_PRESENTATION_ARCHITECTURE.md)
- [Presentation Capability Architecture](PRESENTATION_CAPABILITY_ARCHITECTURE.md)
- [DJ Session Runtime Contracts](../../DJ_SESSION_RUNTIME_CONTRACTS.md)
- [Platform Overview Architecture](../../PLATFORM_OVERVIEW_ARCHITECTURE.md)
- [Renderer Host Classification](../technical/RENDERER_HOST_CLASSIFICATION.md)
- [Speech Rendering Contract](../technical/SPEECH_RENDERING_CONTRACT.md)
