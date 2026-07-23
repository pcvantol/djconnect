# Presentation Capability Architecture

## Status

Canonical Presentation capability architecture. This document formalizes the
capability model only. It authorizes no Renderer Host, capability negotiation,
Visual, Ambient, Audience or Ambient Light implementation, Broadcast change,
Runtime behavior or Session Intelligence change.

## Purpose

One approved immutable DJMoment is experienced through one immutable
Presentation. At the Broadcast boundary its Presentation Projection is the
canonical renderer-safe execution model. Existing renderer-safe visual
Presentation remains authoritative through the established DJMoment, Session
Flow, Playback, Universal Receiver and renderer-safe metadata projections.
Presentation Composer augments that existing architecture with independent,
structured Presentation Capabilities.

```text
approved immutable DJMoment
  -> Presentation Composer
  -> Presentation
      -> existing renderer-safe visual Presentation
      + Speech Presentation
      -> Renderer Host local interpretation
```

A Presentation represents exactly one approved DJMoment. A Presentation
Capability never represents a second Moment, Session Flow item, planning
decision or renderer-owned message. Existing visual Presentation is not
remodelled as a new capability by this architecture.

## Capability model

```text
Presentation
├── existing renderer-safe visual Presentation     CURRENT, AUTHORITATIVE
├── Speech Presentation                            CURRENT, STRUCTURED
├── richer visual composition                      DEFERRED
├── Ambient Presentation                           DEFERRED
├── Audience Presentation                          DEFERRED
└── Ambient Light Presentation                     DEFERRED
```

Capabilities are orthogonal. No capability owns another capability, and a
Renderer Host is not required to support every capability. Speech is not the
Presentation; it is the first newly formalized structured Presentation
Capability introduced by Presentation Composer. It neither replaces nor
supersedes existing visual Presentation.

| Capability | Status | Renderer-safe purpose | Does not authorize |
| --- | --- | --- | --- |
| Existing visual Presentation | Current | Existing renderer-safe DJMoment, Flow, Playback and visual metadata projections. | A new Visual Presentation model or renderer change. |
| Speech Presentation | Current | Ordered text segments and semantic speaker roles. | TTS, voice mapping, audio asset or renderer implementation. |
| Richer visual composition | Deferred | Future additive composition over existing visual Presentation. | UI layout, theme system or Universal Receiver change. |
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

Presentation Composer is Presentation-oriented, not Speech-oriented. In the
current implementation slice it actively composes only Speech Presentation;
existing visual Presentation remains unchanged. Future work may add richer
visual, Ambient, Audience or Ambient Light composition through the same
Composer without a second Runtime or Presentation pipeline.

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
| Visual Renderer Host | Existing visual Presentation; Speech Presentation as text; future richer visual composition. |
| VibeCast | Existing visual Presentation; Speech Presentation; future richer visual and Ambient composition. |
| Future Ambient Light Renderer Host | Future Ambient Light Presentation. |

No Renderer Host changes the supplied capability, infers a missing capability
or makes its own supported-capability set authoritative for another host.

## Capability independence and fallback

Failure, absence or lack of renderer support for one capability never
invalidates the Presentation or another capability:

```text
Speech unavailable  -> existing visual Presentation remains valid
Future richer visual composition unavailable -> Speech and existing visual Presentation remain valid
Ambient unavailable -> Speech and existing visual Presentation remain valid
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
Speech -> richer visual composition -> Ambient -> Audience -> Ambient Light
```

This order records expansion of Presentation composition only. It does not
replace existing visual Presentation, authorize implementation or make
capabilities dependent on their predecessor.

## References

- [Presentation Composer Architecture](PRESENTATION_COMPOSER_ARCHITECTURE.md)
- [Speech Rendering Contract](../technical/SPEECH_RENDERING_CONTRACT.md)
- [DJ Presentation Architecture](DJ_PRESENTATION_ARCHITECTURE.md)
- [Room Presentation Routing Architecture](../technical/ROOM_PRESENTATION_ROUTING_ARCHITECTURE.md)
- [Renderer Host Classification](../technical/RENDERER_HOST_CLASSIFICATION.md)
