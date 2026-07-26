# Prompt History: CMB-09 Voice Interaction Host and Native ESP32 Appliance Capability Assessment

**Generation:** Generation 2

**Engineering program:** Platform Evolution assessment

**Decision:** `GO_CMB09_VOICE_HOST_PROFILE_QUALIFIED`

## Evidence and result

The assessment synchronized the canonical `djconnect` platform at
`93292c1b305d277644aaa75d8a3345fa7c0d9a9b` and the native appliance repository
`djconnect-esp32` at `42fe290b9abffad0d103685a78918d2959ed82ae`.

It distinguishes two non-interchangeable routes. The Home Assistant Voice
Interaction Host is a platform-owned Conversation/Audio Interaction Host:
Home Assistant and satellite platforms own hardware, firmware, provisioning,
OTA and local audio, while DJConnect supplies its Conversation Agent, Ask DJ,
authorized Session Start Request handling and existing Assist/STT/TTS route.

The LilyGO T-Embed CC1101 is the DJConnect-owned native appliance. It adds
firmware, pairing, BLE Wi-Fi provisioning, OTA, display, rotary/buttons, PTT,
optional local wake-word initiation and bounded playback/response feedback. It
is not an ESPHome Voice Satellite and owns no Conversation Agent, Profile,
Music DNA, Ask DJ history, Session Runtime, Planner, Knowledge or Music
Backend.

Both profiles are qualified. Their capability differences are intentional and
durable, not feature-parity defects. The assessment authorizes no firmware,
Home Assistant, ESPHome, Runtime, Renderer, API, roadmap or Execution Horizon
change.
