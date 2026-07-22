# Renderer Host Classification

## Status

Canonical Renderer Host architecture. This document defines classification and
positioning only. It authorizes no Guest access, registration, pairing,
authorization, VibeCast, Chromecast, Raspberry Pi, Platform Adapter, UI,
transport or Runtime implementation.

## Purpose

Every Renderer Host is classified on two independent axes:

```text
Renderer Host
├── Device Lifecycle
│   ├── Guest
│   └── Registered
└── Experience Mode
    ├── Interactive
    └── Ambient
```

Device Lifecycle describes how long a renderer device exists and whether it is
configured as an appliance. Experience Mode describes how that renderer presents
an active Session. Neither axis changes Session ownership, Runtime behavior or
the canonical Broadcast contract.

Presentation role is a separate internal architectural distinction: a Renderer
Host may be a Visual Renderer Host or an Audio Renderer Host. The latter is
broader than a Home Assistant Voice Satellite, which remains external platform
terminology. Ambient remains an Experience Mode rather than a third host role;
see [Audio Renderer Host Architecture](AUDIO_RENDERER_HOST_ARCHITECTURE.md).
An [Ambient Light Renderer Host](AMBIENT_LIGHT_RENDERER_HOST_ARCHITECTURE.md)
is a separately deferred presentation role that responds only to approved
Presentation Intent; it is not raw-audio synchronization or a new experience
axis.

## Shared ownership boundary

All combinations consume the same renderer-safe, server-owned Broadcast
projections. A Renderer Host may select which approved projection it presents,
but never infers missing business state or alters Runtime decisions.

```text
Home Assistant Runtime → Planner / Knowledge / DJ Moment Engine → Session Flow → Broadcast
                                                                         ↓
                                                       Guest or Registered Renderer Host
                                                       Interactive or Ambient experience
```

The Runtime must not branch on Guest, Registered, Interactive, Ambient,
VibeCast, Raspberry Pi or Chromecast. These classifications create no parallel
Runtime, Planner, Knowledge, Session Flow or Session pipeline.

## Device Lifecycle axis

### Guest Renderer

A Guest Renderer is temporary and participates only while an active Session is
available or explicitly cast. It has no pairing, persistent device identity,
device-local configuration beyond temporary UI state, Profile ownership, Music
DNA, Performance Memory, Runtime ownership or business logic.

Guest access is Session-scoped and limited to renderer-safe projections.
Detailed token, discovery and authorization contracts remain separate future
architecture work. Examples include a temporary browser, Chromecast receiver,
temporary TV display, VibeCast session and ad-hoc development observer.

### Registered Renderer

A Registered Renderer is a permanently installed appliance-style Renderer Host.
Registration exists only for device identity, approved device-local
configuration, declared platform capabilities and appliance lifecycle. It is
not user login, Profile ownership or Session lifecycle.

A Registered Renderer may retain bounded device configuration such as device
name, approved room or placement metadata, orientation, brightness policy,
ambient-audio preference, hardware capability declaration, update channel and
kiosk/watchdog settings. It must not retain Session Runtime, Planner or
Knowledge state, Music DNA, chat history, Performance Memory or canonical
Session state.

Pairing therefore belongs solely to Device Lifecycle. Ending, replacing or
joining a Session neither requires nor changes pairing.

## Experience Mode axis

### Interactive Renderer

An Interactive Renderer is a product application for direct operation. It may
render approved Now Playing, Session Flow, DJ Moments, Ask DJ, Discover,
player controls, navigation, status and product/legal screens. It emits only
approved renderer actions through existing server-owned boundaries and never
reconstructs Runtime state or business logic.

The Universal Receiver web application is the canonical platform-neutral
Interactive Renderer and product shell.

### Ambient Renderer

An Ambient Renderer is a passive, attention-light expression of an active
Session. Its goal is to experience the Session rather than operate it. It may
present a selected safe subset of playback, artwork, current DJMoment, selected
Session Flow moments, Session Mood Presentation Intent, renderer-safe progress,
or explicitly supplied lyric/artist-fact Moment content.

Ambient mode generally avoids application menus, settings navigation, product
administration, dense lists, persistent controls, debugging surfaces and
Profile management. It is not an Interactive Renderer with buttons hidden: it
has its own layout, attention and input principles.

## Canonical combinations

| Renderer or deployment | Device Lifecycle | Experience Mode | Positioning |
| --- | --- | --- | --- |
| Temporary browser | Guest | Interactive | Temporary web product experience. |
| Chromecast receiver | Guest | Interactive or Ambient | Selected cast experience; no permanent registration is implied. |
| VibeCast | Guest by default | Ambient | Canonical passive layered visual Session experience. |
| Raspberry Pi Wall Panel | Registered | Interactive by default; Ambient later | Appliance-style wall panel with renderer-local future mode transition. |
| Dedicated ambient display | Registered | Ambient | Future appliance deployment. |

The same technical web foundation may share connection lifecycle, renderer
release lifecycle, snapshot/incremental Broadcast handling, safe projection
models, localization and suitable design tokens. Experience-specific code may
differ in layout, navigation, animation policy, projection selection, attention
model and input handling.

## VibeCast positioning

VibeCast is the canonical DJConnect Ambient Renderer experience. It is not the
Universal Receiver product shell, a remote control or a debug UI. It is a
passive, layered visual expression of the active Session, initially deployed as
Guest + Ambient for Chromecast, television and temporary browser displays.

VibeCast is a distinct experience built on the Universal Receiver Web Platform.
Its future V1 Google TV host is a Google Cast Custom Web Receiver that renders
locally from renderer-safe Broadcast projections; Cast does not stream sender
pixels and VibeCast is not a native Android TV or Google TV application. See
[VibeCast Architecture and V1 Product Definition](../product/VIBECAST_ARCHITECTURE.md).

Future Registered + Ambient deployment is separate work. VibeCast consumes the
same renderer-safe Broadcast projections and introduces no second transport or
Session pipeline.

## Raspberry Pi Wall Panel positioning

The Raspberry Pi Wall Panel is a Registered + Interactive Renderer by default.
It remains an additional native Renderer Host; the Universal Receiver does not
replace its QML or appliance implementation. A future Platform Adapter may let
the panel transition locally to Ambient after inactivity and to Sleep when no
Session is active. Such transitions are presentation behavior only: they create
no Session and do not alter Runtime state.

## Authorization and local-first boundary

Guest access is temporary, Session-scoped and renderer-safe without device
registration. Registered access is device-scoped and persistent only for
appliance lifecycle/configuration; it remains Session-safe and Renderer-only.
Neither classification authorizes a broad authentication redesign.

Both kinds remain local-first and may operate against the local DJConnect
installation without mandatory central cloud service. Host-platform requirements
such as Chromecast discovery remain separately designed implementation work.
Future room-scoped eligibility is independent of both classification axes and
is defined by [Room Presentation Routing](ROOM_PRESENTATION_ROUTING_ARCHITECTURE.md).
It does not make a Guest, Registered, Interactive or Ambient host authoritative
over another Renderer Host.

## Deferred follow-up capabilities

- Renderer discovery, registration, pairing and authorization architecture.
- VibeCast V1 implementation, including Guest Renderer access, bounded session
  handoff and Google Cast Custom Web Receiver feasibility.
- Registered Raspberry Pi onboarding and Platform Adapter implementation.
- Ambient mode, display power, ambient audio and local mode-transition policy.

## References

- [Universal Receiver V1 — Server Architecture](UNIVERSAL_RECEIVER_ARCHITECTURE.md)
- [Platform Ambient Experience](PLATFORM_AMBIENT_EXPERIENCE.md)
- [Ambient Light Renderer Host Architecture](AMBIENT_LIGHT_RENDERER_HOST_ARCHITECTURE.md)
- [Room Presentation Routing Architecture](ROOM_PRESENTATION_ROUTING_ARCHITECTURE.md)
- [DJ Presentation Architecture](../product/DJ_PRESENTATION_ARCHITECTURE.md)
- [ADR-0015: VibeCast is a Broadcast Capability](../adr/0015-vibecast-broadcast-capability.md)
