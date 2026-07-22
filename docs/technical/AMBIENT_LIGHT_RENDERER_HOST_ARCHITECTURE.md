# Ambient Light Renderer Host Architecture

## Status

**Deferred architecture.** This document preserves a future renderer direction
only. It authorizes no WLED, Philips Hue, ESPHome, Home Assistant lighting,
color algorithm, effect, service, Renderer code, Broadcast, Runtime or
transport implementation.

## Purpose

An **Ambient Light Renderer Host** is a Renderer Host whose local presentation
surface is ambient lighting. It consumes the same immutable DJMoment and
Presentation Intent as every other Renderer Host. It is not a lighting
integration, a playback owner or an independent music-analysis system.

```text
immutable DJMoment + Presentation Intent
        ↓
Ambient Light Renderer Host
        ↓
local, capability-appropriate ambient light presentation
```

The Renderer Host architecture therefore permits presentation roles including
Visual Renderer Host, Audio Renderer Host and Ambient Light Renderer Host.
These roles remain independent of Device Lifecycle (Guest/Registered) and
Experience Mode (Interactive/Ambient). An Ambient Light Renderer Host is a
presentation role; it does not make Ambient a new Runtime state or a new
Broadcast path.

## Presentation philosophy

Ambient Light Renderers respond to the approved **Presentation Intent**. They
do not synchronize to raw audio, perform beat detection, implement FFT
visualization or become music-reactive lighting. Their purpose is to reinforce
the Session experience the AI DJ has already created, not to reinterpret the
music independently.

The following are illustrative expressions only, not rendering rules or
implementation requirements:

| Approved presentation | Illustrative ambient expression |
| --- | --- |
| Artist Story | Warm ambient pulse |
| Recommendation | Short ambient highlight |
| Transition | Slow color transition |
| Silence | Subtle breathing light |
| Session Mood | Overall room color palette |

## Mood and artwork

Future Session Mood may influence an ambient color palette. Artwork colors may
contribute to that palette only through an already-approved Presentation Intent;
Mood remains the dominant influence. An Ambient Light Renderer Host interprets
the resulting Intent according to its local capabilities and never derives a
palette from raw provider metadata or audio.

## Room Presentation Routing

Ambient Light Renderer Hosts participate in the existing
[Room Presentation Routing](ROOM_PRESENTATION_ROUTING_ARCHITECTURE.md)
architecture. The same future Room Presentation Context may select eligible
Visual Renderer Hosts, Audio Renderer Hosts and Ambient Light Renderer Hosts
within a reliably resolved Home Assistant Area. They receive the same immutable
DJMoment and never communicate directly with another Renderer Host.

An unresolved Area must not cause lighting to be presented in an arbitrary
room. This preserves the existing safety principle for room-scoped
presentation; no fallback Area or renderer-to-renderer coordination is allowed.

## Future implementations

WLED, Philips Hue, ESPHome light devices and other Home Assistant lighting
platforms are possible future implementations of this Renderer Host concept.
They are not this architecture, do not define its ownership and must not become
independent feature requests. A future implementation requires its own
Pre-Flight, hardware evaluation and bounded integration contract.

## Deferred Audience coherence

A future, aggregate Audience Projection or Audience Presentation Intent may
produce a restrained semantic response such as a short warm lift, gentle
brightness pulse or brief palette accent. An Ambient Light Renderer never
consumes participant identity, communicates directly with VibeCast, becomes
beat-reactive or turns reaction bursts into a strobe system. This is deferred
Audience Experience presentation only, not a lighting implementation; see
[Audience Experience Architecture](../product/AUDIENCE_EXPERIENCE_ARCHITECTURE.md).

## Deferred gate

Ambient Light Renderer Host implementation remains deferred until all of the
following are true:

1. Universal Receiver product experience has matured;
2. Room Presentation Routing is operational; and
3. practical evaluation on real hardware is possible.

It does not outrank the current Universal Receiver roadmap or the active
Automated Session Intelligence E2E Verification roadmap.

## Non-goals

This architecture does not implement or authorize WLED, Hue, ESPHome, color
algorithms, beat detection, FFT, raw-audio synchronization, lighting effects,
Home Assistant services, renderer code, persistence, a new HTTP endpoint, a
new WebSocket channel, Broadcast changes or Runtime behavior changes.

## References

- [DJ Presentation Architecture](../product/DJ_PRESENTATION_ARCHITECTURE.md)
- [Renderer Host Classification](RENDERER_HOST_CLASSIFICATION.md)
- [Audio Renderer Host Architecture](AUDIO_RENDERER_HOST_ARCHITECTURE.md)
- [Room Presentation Routing Architecture](ROOM_PRESENTATION_ROUTING_ARCHITECTURE.md)
- [Platform Ambient Experience](PLATFORM_AMBIENT_EXPERIENCE.md)
