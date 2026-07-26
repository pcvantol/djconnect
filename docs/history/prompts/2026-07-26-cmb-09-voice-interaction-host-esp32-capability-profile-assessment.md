# Prompt History: CMB-09 Voice Interaction Host and constrained ESP32 Capability Profile Assessment

**Generation:** Generation 2

**Engineering program:** Platform Evolution assessment

**Decision:** `GO_CMB09_VOICE_PROFILE_QUALIFIED`

## Evidence and result

The assessment synchronized the canonical `djconnect` platform at
`93292c1b305d277644aaa75d8a3345fa7c0d9a9b` and the concrete Voice Renderer
Host repository `djconnect-esp32` at `42fe290b9abffad0d103685a78918d2959ed82ae`.

Home Assistant owns Session Runtime, Session Start Request resolution, Assist
STT, TTS policy, Conversation/Ask DJ, Profile privacy, Music DNA, Planner,
Knowledge, Broadcast and Music Backend behavior. The constrained ESP32 owns
only the registered appliance boundary: explicit PTT and optional local
wake-word initiation, temporary WAV capture/upload, local physical interaction
and concise returned text/audio feedback, plus pairing, BLE provisioning and
OTA lifecycle.

The ESP32's lack of rich Session Flow, personal renderer/dashboard, Ask DJ chat
history, Music DNA and on-device intelligence is qualified as intentional,
durable profile scope, not a capability deficit. The assessment authorizes no
firmware, Home Assistant, API, Runtime, Renderer, roadmap or Execution Horizon
change.
