# CMB-09 — Voice Interaction Host and constrained ESP32 Capability Profile Assessment

**Status:** Assessment complete

**Decision:** `GO_CMB09_VOICE_PROFILE_QUALIFIED`

**Scope:** Repository-first qualification of the canonical DJConnect Voice
Interaction Host role against `djconnect-esp32` current `main` at
`42fe290b9abffad0d103685a78918d2959ed82ae`. This assessment changes no Home
Assistant Runtime, ESP32 firmware, Voice implementation, Renderer, API,
roadmap or Execution Horizon behavior.

## Canonical host role

A Voice Interaction Host is a **registered, appliance-style Audio Renderer and
bounded Interaction Host**. Its primary role is natural local interaction:
capture an explicit voice request, provide concise device-local feedback, and
return the user to the surrounding room experience. Its secondary role is
bounded, authorized playback control through existing Home Assistant command
and voice boundaries.

It is not a visual personal renderer, Session coordinator, Conversation Agent,
or intelligence runtime. Home Assistant owns Profile resolution, Session
Runtime, Session Start Request resolution, Planner, Knowledge, immutable
DJMoments, Ask DJ interpretation/history, STT, TTS policy, Music DNA, Broadcast
and Music Backend behavior. A Voice Interaction Host sends a request and
renders only the returned, locally appropriate response.

## Voice and interaction profile

| Dimension | Canonical constrained Voice Host profile | ESP32 repository evidence | Qualification |
| --- | --- | --- | --- |
| Voice intake | Explicit PTT is the canonical request boundary; local wake-word detection may initiate the same bounded capture path. | `VoiceRecorder`, `VoiceHttpClient`, `WakeWordEngine` and the vendored Okay Nabu micro-wake-word model exist; wake word remains a device setting. | Qualified. |
| STT and response intelligence | Host records and uploads audio; Home Assistant Assist/STT and the existing command/Ask DJ path interpret it. | Physical PTT stores bounded mono PCM WAV temporarily, uploads it to `/api/djconnect/v1/voice` with the paired token, and accepts returned text plus optional temporary audio. | Qualified. |
| TTS and output | The host provides local short spoken/text feedback when HA supplies it; it does not choose voice policy or a remote speaker. | `DjResponseAudioPlayer` handles compatible returned WAV/MP3; text-only responses remain valid and are displayed. | Qualified. |
| Session entry | Outside an active Session, voice may submit an already authorized Session Start Request; inside one, it uses the active Session context. | `CAP-SI-07` and the Capability Model place the authorization and Start Strategy in HA; the ESP sends no Session-creation logic. | Qualified. |
| Ask DJ | Voice is a bounded spoken request surface, not a rich chat client. | The firmware deliberately has no Ask DJ text chat, history, client-message idempotency or follow-up UI; it uses the existing voice/command path only. | Qualified intentional absence. |
| Physical interaction | Voice, encoder/buttons, LED and concise display/speaker feedback are local appliance interaction. | The LilyGO target has a PDM microphone, speaker, rotary encoder, buttons, WS2812 LED ring and ST7789 display; the firmware owns input, display and local feedback. | Qualified. |

## Renderer and privacy profile

The constrained ESP32 has a **limited display**, not no display: pairing,
status, current playback, concise response text and device feedback are local
appliance surfaces. It is not eligible for rich Session Flow, a Session
timeline, personal dashboard, rich Ask DJ history, Discover, queue browsing as
a canonical rich-client surface, or renderer-owned Current DJMoment reasoning.
Those absences are intentional and do not indicate a Voice Host deficit.

Only request-scoped audio, returned short text, optional temporary response
media, bounded playback state and necessary device lifecycle data belong on
the appliance. The host must never retain or project Music DNA, Profile details,
Ask DJ history, recommendation or Performance Memory, Planner/Knowledge/Runtime
context, provider payloads, credentials, tokens or a canonical Session state.
Pairing and configuration are device lifecycle data only; they do not grant
Profile or Session ownership.

## Boundaries with adjacent hosts

| Adjacent capability | Canonical distinction |
| --- | --- |
| Home Assistant Conversation Agent | HA is the server-side conversation, Assist/STT and authorization boundary. The Voice Host is the local capture/output appliance and owns neither the agent nor conversation state. |
| Ask DJ | Ask DJ interprets authorized requests with Profile and backend context. The ESP32 neither stores Ask DJ history nor executes intelligence; its PTT is only a bounded ingress. |
| Apple and Windows personal renderers | Personal renderers may expose authorized rich text/history, Discover, Track Insight and navigation. A shared constrained Voice Host intentionally does not. |
| Pi 4-inch and Pi 10-inch | Pi appliances are native visual Renderer Hosts with their independently assessed visual profiles. The ESP32 is voice/control first and has no full Session Flow or Presentation timeline. |
| Apple Watch conversational companion | A companion is a personal, moment-first renderer candidate with a user-owned companion context. A Voice Host is room/appliance-first, request-scoped and has no personal conversational persistence. |

## Hardware and appliance boundary

The ESP32-S3 LilyGO T-Embed target has finite embedded resources and a fixed
appliance lifecycle: Wi-Fi LAN traffic, NVS pairing/settings, LittleFS
request-scoped WAV storage, BLE Wi-Fi provisioning, mDNS discovery, battery
guards and manifest-verified OTA. The firmware deliberately preserves heap for
display, network, voice and OTA work and uses a 16 MB flash target with PSRAM
support. These facts support short, serialized local capture/output and
appliance recovery; they do not create a requirement for on-device STT, local
DJ intelligence, streaming transcription, persistent conversation storage or a
rich visual Session product.

BLE is provisioning-only, OTA is firmware lifecycle-only, and the local device
API is paired-device control only. Home Assistant retains backend credentials
and server authority. These boundaries are enduring architecture, not temporary
feature omissions.

## Capability conclusion

The canonical Voice Interaction Host and the current ESP32 appliance align:
voice-first, bounded control, local response delivery and no Session or
personal-intelligence ownership. Its differences from personal and visual
Renderer Hosts are deliberate, durable profile boundaries. No remaining
qualification item is required for this CMB-09 role-profile assessment, and no
implementation is authorized by this decision.

## Sources

- [DJConnect Capability Model](../../DJCONNECT_CAPABILITY_MODEL.md)
- [Domain Model](../../DOMAIN_MODEL.md)
- [Renderer Host Classification](../technical/RENDERER_HOST_CLASSIFICATION.md)
- [Voice Transport](../technical/VOICE_TRANSPORT.md)
- [Renderer Experience Roadmap](RENDERER_EXPERIENCE_ROADMAP.md)
- `djconnect-esp32` `README.md`, `platformio.ini`, `src/VoiceRecorder.cpp`,
  `src/VoiceHttpClient.cpp`, `src/WakeWordEngine.cpp`, `src/DJConnectPairing.cpp`,
  `src/BleWifiProvisioning.cpp`, `src/DJConnectOTA.cpp`, `src/InputController.cpp`,
  `src/DisplayManager.cpp` and `DESIGN_DECISIONS.md` at
  `42fe290b9abffad0d103685a78918d2959ed82ae`.
