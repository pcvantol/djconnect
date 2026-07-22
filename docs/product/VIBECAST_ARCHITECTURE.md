# VibeCast Architecture and V1 Product Definition

## Status

Canonical product positioning and deferred implementation architecture.
VibeCast V1 is not authorized for implementation by this document. It adds no
Google Cast integration, native television application, Runtime behaviour,
Broadcast contract, transport, Session command or renderer code.

## Purpose

**VibeCast** is DJConnect's ambient-first, minimally interactive web-renderer
experience for large displays and television devices. It makes an active DJ
Session present in the room without becoming a music player, a mirrored screen,
a video stream, a general-purpose DJConnect client or a second Universal
Receiver application.

VibeCast renders only canonical, renderer-safe Broadcast projections. Session
Runtime, Planner, Knowledge Engine, DJ Moment Engine, Session Flow and
Broadcast remain server-owned.

## Relationship to the Universal Receiver Web Platform

The **Universal Receiver Web Platform** is shared projection-based web
infrastructure. It supplies receiver connection lifecycle, renderer-safe
projection subscriptions, session handoff/authentication foundations, reusable
presentation primitives and design tokens. Its current Universal Receiver
experience remains the Interactive web product shell.

VibeCast is a distinct product experience built on that platform. It owns its
ambient composition, layered presentation, pacing, television-oriented
transitions, minimal interaction surface and ambient-experience lifecycle. It
may reuse the platform's projection and connection infrastructure, but it is
not a Universal Receiver page with controls hidden and must not be forced into
the general application shell.

## Canonical V1 host model

VibeCast V1 is an HTML5 web application. Its primary television host is a
**Google Cast Custom Web Receiver**, with **Google TV** as the primary target
environment. Google Cast launches or joins the receiver; the television device
is the Renderer Host and renders VibeCast locally.

```text
DJConnect iOS Sender
        ↓
Google Cast session
        ↓
VibeCast Custom Web Receiver
        ↓
Universal Receiver Web Platform
        ↓
DJConnect Broadcast projections
        ↓
local HTML / CSS / JavaScript rendering on the television
```

The sender does not continuously render or stream VibeCast pixels. VibeCast is
not a native Google TV or Android TV application. A native television host is
deferred unless empirical validation proves that the Custom Web Receiver cannot
meet the required experience, interaction, lifecycle or performance needs.

AirPlay mirroring and video streaming are outside VibeCast architecture. They
would make the sender's lifecycle authoritative, add media encoding, latency,
network and energy use, and contradict independent Renderer Host ownership.

## Ambient experience

VibeCast is ambient-first: its default experience needs no interaction and
creates Session atmosphere rather than exposing all DJConnect features. Its
future presentation can combine these conceptual layers:

1. **Background Atmosphere** — adaptive gradients, slow movement, Session Mood
   and contextual artwork colour.
2. **Music Presence** — artwork, track and artist identity, renderer-safe
   progress, and subtle waveform-style or particle motion.
3. **Session Intelligence** — approved Artist Story, Track or Album Context,
   Genre Story, Recommendation, Transition, Session Update or intentional
   Silence.
4. **Optional Context** — safely available lyrics, artist facts, album or
   track metadata and contextual overlays.

A later Audience Layer may coexist beneath these presentation concerns using a
privacy-filtered Audience Projection. It never replaces or obscures an active
DJMoment, turns VibeCast into a social feed or grants VibeCast Session
authority. Audience Experience is a separate future enrichment and is not
required by VibeCast V1; see [Audience Experience Architecture](AUDIENCE_EXPERIENCE_ARCHITECTURE.md).

These are product directions, not styling rules, animation algorithms or
requirements to derive data locally. The ambient palette gives Session Mood
dominant semantic influence; artwork colours and the current DJMoment's
Presentation Intent are contextual inputs. VibeCast preserves Session
continuity rather than mechanically changing its entire visual language for
every track.

## Minimal Interaction and ownership

Ambient does not mean entirely passive. A future temporary, remote-friendly
Minimal Interaction Surface may offer contextual requests such as a calmer or
more energetic direction, more like the current track, dismissing an overlay,
enabling DJ speech or selecting a VibeCast presentation mode. No V1 interaction
set is authorized until actual receiver input capability has been validated.

VibeCast never mutates Session state locally:

```text
Remote or Sender Input
        ↓
VibeCast Interaction Adapter
        ↓
DJConnect Session Command
        ↓
server-side validation and canonical Session Runtime update
        ↓
new Broadcast projection for eligible Renderer Hosts
```

Receiver remote or media-key input may be used only where practical. V1 must
not assume unrestricted native D-pad navigation. Where remote input is
insufficient, the iOS sender remains a controller; a native television
application is not justified solely for richer navigation.

## Optional speech and room coherence

VibeCast may eventually have both Visual Renderer Host and optional Audio
Renderer Host capability. A renderer-safe Speech Presentation associated with
the same immutable DJMoment may contain a presentation identity, optional text,
temporary audio asset reference, locale, voice identity, expected duration and
presentation policy. The preferred V1 model is centrally generated speech
audio played locally by standard web media capability.

VibeCast never becomes the music playback target. Music continues through the
selected backend output; approved DJ speech may independently use the
television or connected soundbar. Automatic music-volume ducking is not V1
scope.

[Room Presentation Routing](../technical/ROOM_PRESENTATION_ROUTING_ARCHITECTURE.md)
and a future Area Presentation Policy determine eligible Audio Renderer Hosts.
The same speech must not automatically play through multiple hosts unless a
future policy authorizes fan-out. VibeCast and future Ambient Light Renderer
Hosts consume the same DJMoment, Presentation Intent and Room Presentation
Context without direct communication, pixel mirroring or a timing master.
Shared presentation identity and timing hints permit soft, not sample-accurate,
synchronization.

## V1 scope

VibeCast V1 is the smallest coherent future product slice:

- Google Cast Custom Web Receiver lifecycle, bootstrap, DJConnect connection,
  session join/handoff, reconnect and idle handling;
- renderer-safe projection consumption for active Session, Now Playing,
  server-owned progress, eligible DJMoments, Session Mood and Presentation
  Intent;
- an ambient visual experience with artwork, adaptive background, basic
  motion, track identity, progress, DJMoment and graceful Silence presentation;
- official Google Cast launch, target selection, Session handoff and reconnect
  from a supported iOS/iPadOS sender;
- feasibility validation for remote/media-key input and bounded Session
  Commands; and
- optional feasibility validation for secure temporary speech-asset playback.

V1 explicitly excludes native Android TV/Google TV applications, Cast Connect,
AirPlay mirroring or streaming, continuous video encoding, music playback or
streaming through the receiver, generic Universal Receiver navigation, full
Ask DJ, search, profiles, backend configuration, queue management,
unrestricted D-pad navigation, ducking, local Session Intelligence, Planner,
Knowledge Engine, DJMoment generation, renderer-to-renderer communication,
WLED/Hue implementation, beat detection, FFT and required local TTS.

## Security and receiver classification

A future Cast receiver must not receive permanent DJConnect credentials. Its
future session handoff requires bounded receiver-safe authorization: short
lifetime, Session scope, receiver identity, revocation, reconnect/expiry and
guest-versus-registered lifecycle treatment. It must not expose Profile-private
data beyond approved renderer-safe projections.

Under the orthogonal Renderer Host model, a VibeCast Google TV receiver is
Guest or Registered where future support requires it, Ambient as its primary
experience, None or Minimal in interaction capability, Visual in presentation
capability and optionally Audio Speech. It has no music playback ownership.

VibeCast differs from the Raspberry Pi Wall Panel: the Wall Panel is a
registered, interactive-first, touch-oriented, persistent room installation;
VibeCast is ambient-first, television-oriented, remotely launched or joined,
minimally interactive and optimized for passive viewing at distance.

## Implementation-entry validation

Before an implementation epic can be authorized, repository evidence must
answer rather than assume:

- whether target Google TV environments run a Custom Web Receiver at the needed
  frame rate;
- which remote or media-key events are reliable;
- whether an independent receiver can securely maintain Broadcast access;
- how bounded Session handoff works without permanent credentials;
- whether temporary speech assets can play while music remains elsewhere;
- receiver idle/timeout and reconnect behaviour, including sender departure;
- which functions remain without a sender; and
- the supported Google TV, Chromecast built-in and receiver compatibility
  baseline.

## Roadmap position

VibeCast is a bounded future product capability. It does not interrupt the
Automated Session Intelligence E2E Verification roadmap or expand Universal
Receiver implementation by implication. The intended order is: complete the
original Golden Scenarios, establish Golden Smoke CI, mature the Universal
Receiver Web Platform, validate Custom Web Receiver feasibility, then authorize
a separately bounded VibeCast V1 implementation epic.

## References

- [Universal Receiver V1 — Server Architecture](../technical/UNIVERSAL_RECEIVER_ARCHITECTURE.md)
- [Renderer Host Classification](../technical/RENDERER_HOST_CLASSIFICATION.md)
- [Room Presentation Routing Architecture](../technical/ROOM_PRESENTATION_ROUTING_ARCHITECTURE.md)
- [Audio Renderer Host Architecture](../technical/AUDIO_RENDERER_HOST_ARCHITECTURE.md)
- [Ambient Light Renderer Host Architecture](../technical/AMBIENT_LIGHT_RENDERER_HOST_ARCHITECTURE.md)
