# DJConnect Client Capability Matrix

This document defines how platform capabilities map to DJConnect client classes.

No client owns product features. Clients render or expose platform capabilities according to their strengths and constraints.

## Client classes

| Class | Examples | Role |
| --- | --- | --- |
| Intelligence Client | iOS, iPadOS, macOS, Windows, future Android/web | Rich personal DJConnect experience |
| Ambient Client | Raspberry Pi display, wall display, household screen | Shared room display/control experience |
| Voice / Control Client | ESP32, Home Assistant Voice Satellite | Physical control, Assist/voice entrypoint, PTT, short TTS responses |
| Presentation Client | VibeCast / AirPlay / TV | Shared visual rendering of Insight Feed |
| Immersive Client | Future VR/MR | Spatial renderer and exploratory interface |

## Capability matrix

| Capability | Apple | Windows | Pi | ESP32 | VibeCast | VR/MR future |
| --- | --- | --- | --- | --- | --- | --- |
| Pairing | Full | Full | Full | Full | Controller-driven | Full / future |
| Music control | Full | Full | Basic/shared | Physical controls | No / minimal | Contextual |
| Ask DJ text | Full | Full | Readonly or light | No chat UI | No | Spatial/full |
| Ask DJ voice | Full/PTT | Full/PTT future | Not default | PTT upload | No | Spatial |
| Ask DJ history | Profile-bound | Profile-bound | Shared/readonly | None | None | Profile-bound |
| Music DNA | Personal UI | Personal UI | Household/light | None | None | Personal/spatial |
| Track Insights | Rich | Rich | Light | None | Rich visual | Spatial |
| Lyrics Explain | Rich | Rich | Light/future | None | Rich visual | Spatial |
| Live Lyrics | Rich/future | Rich/future | Light/future | None | Rich visual | Spatial |
| Discover | Full | Full | Feed/light | None | No | Discovery Galaxy |
| VibeCast control | Full | Full | Maybe launch only | No | N/A | Maybe |
| VibeCast rendering | Controller only | Controller only | No | No | Primary | Spatial variant |
| Guest Companion | QR/control | QR/control | Maybe display QR | No | QR source | Maybe |
| Give Love | Control/guest web | Control/guest web | Maybe display | No | Hearts layer | Spatial effects |
| Notifications | APNs | Windows notifications | Local UI | Local display/sound | No | Platform-dependent |
| Background audio | iOS/macOS research | Windows feasible | No | Built-in speaker only | No | Platform-dependent |
| OTA/update | App release | App release | App updater | Firmware OTA | N/A | Store/runtime |
| Diagnostics | Full | Full | Full | Device logs | Minimal | Future |
| Settings | Full | Full | Limited/shared | Device settings | No | Future |
| Feature flags | Profile/client | Profile/client | Shared/device | Device/capability | Session/capability | Profile/client |

## Rules

### Apple and Windows

Apple and Windows are Intelligence Clients. They should expose the richest personal DJConnect experience while staying backend-owned for intelligence, recommendations and profile state.

### Raspberry Pi

Pi is an Ambient Client. It should be optimized for a shared wall-mounted or household screen: playback, now playing, light insights, readonly Ask DJ stream and Discover feed.

By default, Pi should resolve to a shared profile unless explicitly linked to a personal profile.

### ESP32

ESP32 is a Voice / Control Client. It should remain simple, robust and community-first.

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

Future speaker recognition may become a resolver hint, but it is not a current
client capability and must not override explicit profile selection. HA Voice
Voice Endpoints have no persistent personal UI and no automatic access to personal
Ask DJ history.

### VibeCast

VibeCast is a Presentation Client. It renders the Insight Feed as a shared visual experience. It should not become a complex playback controller.

### VR/MR

VR/MR is a future Immersive Client class. It should not become a separate music player. It should reuse Profile, Music Backend and Insight Feed concepts.

## Capability evolution

Capabilities should move through maturity stages:

1. experimental;
2. preview;
3. beta;
4. stable;
5. deprecated;
6. removed.

A client should advertise capabilities explicitly. Backend and clients should not infer support from version strings when a capability contract exists.
