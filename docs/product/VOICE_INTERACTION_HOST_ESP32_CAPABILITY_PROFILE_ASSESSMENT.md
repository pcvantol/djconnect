# CMB-09 — Voice Interaction Host and Native ESP32 Appliance Capability Assessment

**Status:** Assessment complete

**Decision:** `GO_CMB09_VOICE_HOST_PROFILE_QUALIFIED`

**Scope:** Repository-first qualification of two deliberately separate routes:
the Home Assistant Voice Interaction Host in `djconnect` at
`93292c1b305d277644aaa75d8a3345fa7c0d9a9b`, and the native DJConnect LilyGO
T-Embed CC1101 appliance in `djconnect-esp32` at
`42fe290b9abffad0d103685a78918d2959ed82ae`. No Home Assistant, ESP32,
ESPHome, Runtime, Renderer, API, roadmap or Execution Horizon behavior changes.

## Route A — Home Assistant Voice Interaction Host

### Role and ownership

The Home Assistant Voice Interaction Host is a **Conversation/Audio Interaction
Host**, not DJConnect-owned hardware. Home Assistant Voice Preview, ESPHome
Voice Satellites and future supported Assist satellites supply their own
firmware, hardware, provisioning, OTA, microphones, speakers and any local
display or buttons. They must not be treated as DJConnect firmware or as a
native ESP32 appliance variant.

DJConnect contributes the Conversation Agent, Ask DJ routing, authorized
Session Start Request handling, DJ-intelligence response path and use of the
existing Home Assistant Assist/STT/TTS routes. Home Assistant owns Assist
Pipeline selection and execution, satellite lifecycle, audio hardware and
transport, user/area context, and the Session Runtime. The Voice Host owns no
Session, Planner, Knowledge, DJMoment, Music Backend, Broadcast or personal
state.

### Capability profile

| Dimension | Canonical Home Assistant Voice Host profile | Evidence | Qualification |
| --- | --- | --- | --- |
| Primary role | Natural spoken interaction through Home Assistant Assist and DJConnect Conversation/Ask DJ behavior. | `conversation.py`, `assist_stt.py`, `pipeline.py`, the Capability Model and Voice Transport retain the server-side route. | Qualified. |
| Secondary role | Submit an already authorized spoken request, including a possible Session Start Request, then render/speak the returned answer through the host platform. | `CAP-SI-07` places Start Strategy and authorization in HA; the Capability Model defines voice contexts inside/outside an active Session. | Qualified. |
| Renderer role | A bounded Audio Renderer: short spoken or otherwise host-native response realization only. | Audio Renderer Host architecture and Renderer Experience Roadmap classify voice/notification presentation as bounded and never intelligence. | Qualified. |
| Privacy | Shared room input is resolver context, not personal-device identity; personal data is server-side and resolved only through existing Profile/privacy policy. | Domain Model Voice Endpoint boundary and Capability Model exclude local Music DNA, history and Session ownership. | Qualified. |
| Non-goals | No DJConnect hardware, ESPHome firmware, pairing/provisioning/OTA, rich Session Flow, visual dashboard, persistent local Ask DJ history or local intelligence. | Repository ownership boundaries above. | Qualified intentional absence. |

The canonical shared Voice Interaction capability is therefore **conversation
ingress and concise response delivery under Home Assistant ownership**. It is
not a generic visual Renderer Host and does not prescribe a hardware form.

## Route B — Native LilyGO T-Embed CC1101 DJConnect appliance

### Appliance role

The LilyGO T-Embed CC1101 is a **DJConnect-owned registered native appliance**.
It exists to combine room-local voice and bounded playback interaction with
device lifecycle responsibility: firmware, pairing, Wi-Fi/BLE provisioning,
OTA, display, encoder/buttons, battery-aware operation and local appliance
recovery. It is not an ESPHome Voice Satellite, a generic Assist satellite, a
personal rich renderer or a Session controller.

### Capability profile

| Dimension | Native appliance profile | ESP32 repository evidence | Qualification |
| --- | --- | --- | --- |
| Voice | Explicit physical PTT is the canonical device ingress; optional local wake-word initiation remains device-local. HA performs Assist/STT and the existing command/Ask DJ handling. | `VoiceRecorder`, `VoiceHttpClient`, `WakeWordEngine`, Okay Nabu micro-wake-word model and `/api/djconnect/v1/voice` PTT flow. | Qualified. |
| Interaction | Rotary encoder, buttons, LED ring, speaker and compact display feedback are appliance-owned interaction. | LilyGO target configuration, `InputController`, `LedRing`, `SoundManager` and `DisplayManager`. | Qualified. |
| Display | Pairing/status, bounded current playback and concise returned text/device feedback only. No rich Session Flow, timeline, dashboard or renderer-owned DJMoment reasoning. | `DisplayManager` and firmware README screen/voice behavior. | Qualified intentional boundary. |
| Playback | Existing authorized generic commands and current-state feedback; no provider credentials, backend policy or Session ownership. | Firmware README and HA-owned generic command contract. | Qualified. |
| Appliance lifecycle | Local pairing, token storage, LAN/mDNS runtime, BLE Wi-Fi provisioning, battery guards and manifest-verified OTA. | `DJConnectPairing`, `BleWifiProvisioning`, `DJConnectOTA`, `ProvisioningController`, NVS/LittleFS and PlatformIO target configuration. | Qualified. |
| Privacy | Request-scoped WAV/audio and concise returned response only. Never Music DNA, Profile details, Ask DJ history, recommendations, Planner/Knowledge/Runtime context, provider payloads, credentials, tokens or canonical Session state. | ESP PTT transport, device lifecycle contract and canonical Device/Voice Endpoint boundaries. | Qualified. |

The device is constrained by embedded appliance resources and lifecycle. Its
16 MB flash/PSRAM-capable ESP32-S3 target, bounded temporary LittleFS audio,
networking, display and OTA coexistence support serialized local interaction;
they do not imply on-device STT, streaming transcription, local DJ intelligence
or persistent conversation storage.

## Comparison and enduring boundaries

| Capability | Home Assistant Voice Interaction Host | Native LilyGO appliance |
| --- | --- | --- |
| Shared Voice Interaction | Assist-facing spoken request and concise response under HA/DJConnect server ownership. | Same server-owned request/response semantics through the paired device route. |
| Hardware lifecycle | Home Assistant or satellite platform owns it. | DJConnect firmware owns it: pairing, BLE provisioning, OTA and appliance recovery. |
| Local controls and display | Platform-defined; not a DJConnect firmware contract. | Canonical bounded encoder, buttons, LED, speaker and display feedback. |
| Conversation and intelligence | DJConnect/HA owns Conversation Agent, Ask DJ, Profile/privacy, Session Start Request and intelligence. | Uses those existing server-owned paths; owns none of them. |
| Rich personal/visual surfaces | Not implied by voice participation. | Intentionally absent: no rich history, personal dashboard or Session Flow. |

These differences are intentional, durable and not feature-parity gaps. Route
A is a host-platform voice capability. Route B adds an owned hardware appliance
capability around the same server-owned voice boundary. Neither route gains
local Session authority, personal-memory ownership or a new renderer contract.

## Qualification conclusion

Both profiles are objectively qualified and strictly separated. The Home
Assistant Voice Interaction Host is a shared, platform-owned conversational
audio interaction route. The LilyGO appliance is the native DJConnect-specific
voice/control hardware realization with its own lifecycle and bounded local
surfaces. No remaining qualification item or implementation follow-up is
created by CMB-09.

## Sources

- [DJConnect Capability Model](../../DJCONNECT_CAPABILITY_MODEL.md)
- [Domain Model](../../DOMAIN_MODEL.md)
- [Audio Renderer Host Architecture](../technical/AUDIO_RENDERER_HOST_ARCHITECTURE.md)
- [Renderer Host Classification](../technical/RENDERER_HOST_CLASSIFICATION.md)
- [Voice Transport](../technical/VOICE_TRANSPORT.md)
- [Renderer Experience Roadmap](RENDERER_EXPERIENCE_ROADMAP.md)
- `custom_components/djconnect/conversation.py`, `assist_stt.py`, `pipeline.py`
  and `ask_dj/` in `djconnect`.
- `djconnect-esp32` `README.md`, `platformio.ini`, `src/VoiceRecorder.cpp`,
  `src/VoiceHttpClient.cpp`, `src/WakeWordEngine.cpp`, `src/DJConnectPairing.cpp`,
  `src/BleWifiProvisioning.cpp`, `src/DJConnectOTA.cpp`, `src/InputController.cpp`,
  `src/DisplayManager.cpp` and `DESIGN_DECISIONS.md` at
  `42fe290b9abffad0d103685a78918d2959ed82ae`.
