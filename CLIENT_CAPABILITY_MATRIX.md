# DJConnect Client Capability Matrix

This document defines how platform capabilities map to DJConnect client classes.

No client owns product features. Clients render or expose platform capabilities according to their strengths and constraints.

## Client classes

| Class | Examples | Role |
| --- | --- | --- |
| Personal Experience | iOS, iPadOS, macOS, Windows, Apple Watch | Native, Profile-bound DJ Session experience |
| Shared Experience | Browser, TV, Chromecast, Raspberry Pi, desktop, guest phones | Renderer Host for an active shared DJ Session; lifecycle and experience mode are classified separately |
| Room Experience | ESP32, Home Assistant Voice Satellite | Voice/control rendering for the active room DJ Session |

## Capability matrix

| Capability | Personal Experience | Shared Experience | Room Experience |
| --- | --- | --- | --- |
| Profile state | Native profile-bound access | Never stored; rendered only when permitted | Never stored; room/profile resolution only |
| Session Flow | Full control and rendering | Broadcast Feed rendering | Short voice/control contributions |
| Music control | Full | Basic/shared when the receiver permits it | Physical or voice controls |
| Ask DJ | Rich text and voice where available | Guest-safe/read-only where permitted | Voice and short TTS only |
| Music DNA | Personal UI | Never exposed without explicit policy | Never exposed without explicit policy |
| VibeCast | Control and handoff | Guest + Ambient Renderer experience by default | No visual rendering |
| Diagnostics and updates | Platform-specific | Platform-specific | Device-focused |

## Rules

### Personal Experience

Apple and Windows render the richest personal DJConnect experience while
remaining backend-owned for intelligence, recommendations and Profile state.
The Apple application is one shell with Owner, Guest and Demo runtimes, but its
UI is capability-driven rather than mode-driven.

### Shared Experience

Shared Experience uses one Universal Session Receiver for an active DJ Session.
Browser, TV, Chromecast, Raspberry Pi, desktop and guest-phone modes consume
the event-driven Broadcast Feed and render it locally. They never receive
private Profile state without explicit policy.

The canonical [Renderer Host Classification](docs/technical/RENDERER_HOST_CLASSIFICATION.md)
separates Device Lifecycle (Guest/Registered) from Experience Mode
(Interactive/Ambient). Chromecast need not be permanently registered; the
Raspberry Pi Wall Panel is Registered + Interactive by default, with a future
renderer-local Ambient state. VibeCast is Guest + Ambient by default.

By default, Pi should resolve to a shared profile unless explicitly linked to a personal profile.

### Room Experience

ESP32 and HA Voice are Room Experience renderers. They represent the active DJ
Session through voice and control rather than a rich personal or shared visual
surface. ESP32 remains simple, robust and community-first.

It should not gain rich intelligence UI, Music DNA, persistent chat history or Discover. It may play short TTS DJ responses through its built-in speaker.

### Voice Endpoints

Voice Endpoints are Voice / Control request sources for spoken DJConnect
interactions. A Home Assistant Voice Satellite is one implementation. Voice
Endpoints may be represented by Home Assistant device IDs, satellite/entity
IDs, Assist pipeline context and area/room associations.

A DJConnect ESP32 PTT device is a registered Voice / Control Client and resolves
through `device_id`. A generic Home Assistant Voice Satellite resolves
through HA satellite/device/area context. These flows may use similar voice and
Assist paths, but they are not necessarily the same domain object.

An HA Voice Satellite does not need to become a full DJConnect Device
solely for Profile resolution. It should resolve through the canonical
`ProfileResolver` using explicit Voice Endpoint mapping, area/room mapping or
fallback. Shared room Voice Endpoints should normally resolve to shared, room,
household, guest-safe or kids profiles unless explicitly configured otherwise.

Future Room Presentation Routing is distinct from Profile resolution. It uses
the active playback output's reliably resolved Home Assistant Area only to
choose eligible independent Visual and Audio Renderer Hosts for the same
immutable DJMoment. When the Area is unresolved, it must not route autonomous
speech to an arbitrary room; see
[`docs/technical/ROOM_PRESENTATION_ROUTING_ARCHITECTURE.md`](docs/technical/ROOM_PRESENTATION_ROUTING_ARCHITECTURE.md).

Future speaker recognition may become a resolver hint, but it is not a current
client capability and must not override explicit profile selection. HA Voice
Voice Endpoints have no persistent personal UI and no automatic access to personal
Ask DJ history.

## Capability evolution

Capabilities should move through maturity stages:

1. experimental;
2. preview;
3. beta;
4. stable;
5. deprecated;
6. removed.

A client should advertise capabilities explicitly. Backend and clients should not infer support from version strings when a capability contract exists.
