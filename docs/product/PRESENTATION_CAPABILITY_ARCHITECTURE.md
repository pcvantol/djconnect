# Presentation Capability Architecture

## Status

Canonical Presentation capability architecture. This document formalizes the
capability model only. It authorizes no Renderer Host, capability negotiation,
Visual, Ambient, Audience or Ambient Light implementation, Broadcast change,
Runtime behavior or Session Intelligence change.

## Purpose

One approved immutable DJMoment is experienced through one immutable
Presentation. At the Broadcast boundary its Presentation Projection is the
canonical renderer-safe execution model. A Presentation consists of independent
Presentation Capabilities: modalities through which the same approved meaning
may be experienced.

```text
DJMoment
  -> Presentation
      -> Presentation Capabilities
          -> Renderer Host local interpretation
```

A Presentation represents exactly one approved DJMoment. A Presentation
Capability never represents a second Moment, Session Flow item, planning
decision or renderer-owned message.

## Capability model

```text
Presentation
├── Speech Presentation                 CURRENT
├── Visual Presentation                 DEFERRED
├── Ambient Presentation                DEFERRED
├── Audience Presentation               DEFERRED
└── Ambient Light Presentation          DEFERRED
```

Capabilities are orthogonal. No capability owns another capability, and a
Renderer Host is not required to support every capability. Speech is not the
Presentation; it is the first implemented Presentation Capability.

| Capability | Status | Renderer-safe purpose | Does not authorize |
| --- | --- | --- | --- |
| Speech Presentation | Current | Ordered text segments and semantic speaker roles. | TTS, voice mapping, audio asset or renderer implementation. |
| Visual Presentation | Deferred | Future visual composition of approved Presentation meaning. | UI layout, theme system or Universal Receiver change. |
| Ambient Presentation | Deferred | Future attention-light expression of approved meaning. | VibeCast, timing master or audio synchronization implementation. |
| Audience Presentation | Deferred | Future renderer-safe expression of separately owned Audience context. | Audience Signals, Planner influence or reaction implementation. |
| Ambient Light Presentation | Deferred | Future local lighting expression of approved meaning. | Lighting integration, raw-audio analysis or renderer communication. |

## Ownership

| Owner | Responsibility | Does not own |
| --- | --- | --- |
| Presentation Composer | Composes the complete immutable Presentation from one approved DJMoment. | Renderer selection, capability negotiation, TTS, voice, visual layout or device control. |
| Presentation Capability | Contains only renderer-safe data for one independent modality. | DJMoment creation, planning, knowledge, Session Flow or another capability. |
| Broadcast | Distributes renderer-safe Presentation Projections. | Capability composition, renderer behavior or capability selection. |
| Renderer Host | Independently consumes the capabilities it supports and renders locally. | Presentation modification, composition or server authority. |
| Room Presentation Routing | Future selection of eligible Renderer Hosts for a Presentation. | DJMoment creation, Presentation composition or capability-to-device selection. |

Presentation Composer is Presentation-oriented, not Speech-oriented. Speech is
currently its only implemented capability; a future capability may be composed
through the same Composer without a second Runtime or Presentation pipeline.

## Renderer capability consumption

Capability support is local to a Renderer Host and is not a server-side
negotiation protocol. The server distributes the same immutable Presentation;
each host consumes only the capabilities it supports.

```text
Presentation
  -> Renderer Host
      -> supported Presentation Capabilities
```

Examples are architectural relationships, not capability declarations or
implementation requirements:

| Renderer role | Possible supported capabilities |
| --- | --- |
| Audio Renderer Host | Speech Presentation. |
| Visual Renderer Host | Speech Presentation as text; future Visual Presentation. |
| VibeCast | Speech Presentation; future Visual and Ambient Presentation. |
| Future Ambient Light Renderer Host | Future Ambient Light Presentation. |

No Renderer Host changes the supplied capability, infers a missing capability
or makes its own supported-capability set authoritative for another host.

## Capability independence and fallback

Failure, absence or lack of renderer support for one capability never
invalidates the Presentation or another capability:

```text
Speech unavailable  -> Visual Presentation remains valid
Visual unavailable  -> Speech Presentation remains valid
Ambient unavailable -> Speech and Visual Presentation remain valid
```

The Presentation itself remains valid. A Renderer Host continues only with its
supported, authorized local behavior. It does not request server regeneration,
change Broadcast state or create a Session Flow entry.

## Room Presentation Routing

Room Presentation Routing routes Presentations to eligible Renderer Hosts; it
does not route or select individual capabilities. Each selected Renderer Host
then consumes only the capabilities it supports. Presentation Composer never
selects a Renderer Host, device or Home Assistant Area.

## Capability evolution

The formal evolution order is:

```text
Speech -> Visual -> Ambient -> Audience -> Ambient Light
```

This order records architectural positioning only. It does not authorize any
future implementation or make capabilities dependent on their predecessor.

## References

- [Presentation Composer Architecture](PRESENTATION_COMPOSER_ARCHITECTURE.md)
- [Speech Rendering Contract](../technical/SPEECH_RENDERING_CONTRACT.md)
- [DJ Presentation Architecture](DJ_PRESENTATION_ARCHITECTURE.md)
- [Room Presentation Routing Architecture](../technical/ROOM_PRESENTATION_ROUTING_ARCHITECTURE.md)
- [Renderer Host Classification](../technical/RENDERER_HOST_CLASSIFICATION.md)
