# DJConnect Client Capability Matrix

## Historical recording and captured reply media — contract1

The [bounded Core producer](docs/product/HISTORICAL_PLAYBACK_AND_REPLY_ARTWORK_V1.md)
adds `historical_exact_track_playback` and `captured_reply_artwork`, both version1,
for paired Profile owners. History play actions require explicit negotiation and
a human tap; existing output selection is reused. Original reply subject/edition
and current temporary media authority remain separate. Shared/guest display gains
no permission. Exact protected delivery, installed readback and native/physical
adoption each require their own evidence.

## Current shared settings3 / target-aware speech3 producer

Protected source main `e8cc70ddffb4112b09babdda4d45140b98926ae5`, PR [#1193](https://github.com/pcvantol/djconnect/pull/1193). [Exact source readback](docs/verification/PROFILE_SESSION_SETTINGS_SOURCE_READBACK_20261016.md). Six-field producer/capabilities are delivered in Core; earlier local-candidate/design checkpoints below are historical. Consumer adoption, complete legacy removal, Finalization and actual installed/native/audible/joint outcomes remain separately qualified.

## Historical contract checkpoints

## Current settings owner addenda — local contract3 producer

[Canonical delta](docs/product/PROFILE_SESSION_SETTINGS_CONSOLIDATION_V1.md) adds `announcement_output` to the five shared DJ choices under owner6220590330/6220695648. Six-field settings contract3 and target-aware speech prepare3 are implemented and advertised in the unpublished Core candidate; final exact review/protected delivery remain required. `text_only` forbids announcement synthesis and all replay; speaker-only still permits explicit local owner replay. Physical speaker/Assist pipeline/ESP administration stay HA-only; local autoplay defaults OFF and OS permissions remain local. Existing contract2 checkpoints below are historical five-field proof. Integrated chat/DNA portability is parked, unchanged. Native/installed/joint remain OPEN; no new consumer writer or WIP expansion.

Before six-field activation, an existing Session with unknown Mood has `snapshot.session.settings: null`, `selection_required: true` and `selection_basis: legacy_mood_unknown`. Keep its identity/revision, show separate defaults only as proposals, and require all six explicit choices for activation. Ask DJ1/prepare1 preserve legacy behavior; prepare3 is typed unavailable until selection. Reads do not invent Mood or history coverage.


## Selected Profile/Session settings consolidation — contract2

[Canonical all-five contract](docs/product/PROFILE_SESSION_SETTINGS_CONSOLIDATION_V1.md), [settings inventory](docs/product/PROFILE_SESSION_SETTINGS_INVENTORY_V1.json), owner6214905647. Allfive Persona/voice/gender/Mood/Presence are Core-owned Profile defaults plus effective Session state; last explicit accepted field patch is automatically remembered and changes an active Session atomically. No device-local voice truth, global pipeline mutation, read effect, source-right expansion or consumer writer dispatch. New typed API/WS contract2 has its own revision/receipt/generation semantics; contract1 is not silently changed. Core implementation/fixtures remain in progress and unpublished; native/installed/hardware/joint and platform-wide legacy removal are not yet qualified.

## Owner-selected Profile-authorized Pi app — 20 October 2026

Both Pi sizes have the same target feature set as Apple in their explicitly
Profile-authorized native app. The [current Pi scope](docs/product/PI_PROFILE_AUTHORIZED_APP_V1.md)
supersedes the older restricted shared-appliance/no-Flow/no-free-prompt scope.
Screen size changes presentation, not entitlement. Current Pi hardware lacks
speech input and local audio playback; availability is detected and negotiated
with the server, not permanently prohibited by `client_type`. Unavailable local
routes are hidden; text and authorized remote Spotify/HA controls remain usable.
Implementation, common producer gaps, installation and physical acceptance stay
separate from this product decision. Shared/guest/VibeCast authority is unchanged.

## Existing delivered contracts and historical context

This document defines how platform capabilities map to DJConnect client classes.

No client owns product features. Clients render or expose platform capabilities according to their strengths and constraints.

## Client classes

| Class | Examples | Role |
| --- | --- | --- |
| Personal Experience | iOS, iPadOS, macOS, Apple Watch, explicitly Profile-authorized native Raspberry Pi app | Native, Profile-bound DJ Session experience |
| Shared Experience | Browser, TV, Chromecast, shared-display Raspberry Pi deployment, desktop, guest phones | Renderer Host for an active shared DJ Session; lifecycle and experience mode are classified separately |
| Room Experience | ESP32, Home Assistant Voice Satellite | Voice/control rendering for the active room DJ Session |

## Capability matrix

| Capability | Personal Experience | Shared Experience | Room Experience |
| --- | --- | --- | --- |
| Profile state | Native profile-bound access | Never stored; rendered only when permitted | Never stored; room/profile resolution only |
| Session Flow | Full control and rendering | Broadcast Feed rendering | Short voice/control contributions |
| Music control | Full | Basic/shared when the receiver permits it | Physical or voice controls |
| Ask DJ | Rich text and voice where available | Guest-safe/read-only where permitted | Voice and short TTS only |
| Music DNA | Personal UI | Never exposed without explicit policy | Never exposed without explicit policy |
| VibeCast | Paired owner display setup; existing-app temporary guest join from pairing screen or paired top menu, by discovery or QR; optional Cast sender | Web-first ambient TV/desktop/tablet plus responsive guest view; same server-authorized meaning | No visual rendering |
| Diagnostics and updates | Platform-specific | Platform-specific | Device-focused |

## Rules

### Personal Experience

Apple clients and the Profile-authorized native Pi app expose the same shared
product features while remaining backend-owned for intelligence, recommendations
and Profile state. Available speech/local audio routes depend on detected hardware,
permissions and the common client/server handshake, not platform-name exclusions.
The Apple application is one shell with Owner, Guest and Demo runtimes, but its
UI is capability-driven rather than mode-driven.

### Shared Experience

Shared Experience uses one Universal Session Receiver for an active DJ Session.
Browser, TV, Chromecast, shared-display Raspberry Pi, desktop and guest-phone modes consume
the event-driven Broadcast Feed and render it locally. They never receive
private Profile state without explicit policy.

The canonical [Renderer Host Classification](docs/technical/RENDERER_HOST_CLASSIFICATION.md)
separates Device Lifecycle (Guest/Registered) from Experience Mode
(Interactive/Ambient). Chromecast need not be permanently registered; the
Raspberry Pi Wall Panel is Registered + Interactive by default, with a future
renderer-local Ambient state. VibeCast is Guest + Ambient by default. Its
web-first entry is https://vibecast.tv/ at root, with two-step destination/display
admission. The only web-first exception is guest participation through the
existing DJConnect app, retaining home pairing and isolated guest authority.
Google Cast is an optional adapter to the same renderer; native TV applications
and Cast hardware are not browser-bootstrap prerequisites. Glass/Soft/Solid retain
identical authorized functions. Readonly display, guest proposal/chat/reaction
writes and owner playback authority are distinct; generic shared-host capability
rows above do not widen new VibeCast TV permissions. See the
[canonical VibeCast architecture](docs/product/VIBECAST_ARCHITECTURE.md),
[web-first experience](docs/product/VIBECAST_WEB_FIRST_EXPERIENCE_V1.md) and
[route/lifecycle contract](docs/product/VIBECAST_WEB_ENTRY_DISTRIBUTION_V1.md).

An explicitly Profile-linked native Pi app uses its authorized Profile and common
app capabilities. A separately admitted shared-display deployment uses only its
shared projection. Device identity, wall mounting and screen size do not infer a
personal identity or permission to share private Profile content.

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
[Audio Renderer Host](docs/technical/AUDIO_RENDERER_HOST_ARCHITECTURE.md) is the internal DJConnect presentation term; Home Assistant
Voice Satellite remains the external term for the Home Assistant product,
entity, configuration and UI. The distinction does not change Voice Endpoint
request-context or Profile-resolution behavior.

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
