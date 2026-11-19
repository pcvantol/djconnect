# Native Ask DJ Voice Ingest Reconciliation

**Decision:** `NO_GO_ASSIST_PIPELINE_CONTRACT_INSUFFICIENT`

## Current-state matrix

| Route | Capture/transport | STT and pipeline ownership | Classification |
| --- | --- | --- | --- |
| Apple app Ask DJ | complete `audio/wav` HTTP upload to `/voice` | HA Assist/STT, then canonical Ask DJ | partially fitting |
| Windows/Linux | native voice route not evidenced in this repository | no safe inference | missing |
| Pi | text-only Ask DJ contract | not applicable | fitting |
| ESP32 | complete WAV HTTP PTT upload | HA Assist/STT, command path | fitting for device PTT |
| Home Assistant integration | bounded WAV ingest; `async_process_audio_stream` | selected/stored Assist Pipeline, then fallback pipeline resolution | fitting server authority |

The integration is the canonical STT authority: pipeline selection, provider
credentials, language and transcript semantics stay server-side. Audio is
request-scoped and raw audio is not retained by default; the existing debug
WAV is runtime-only and conditional. Voice uses the same Ask DJ input/history
path after final transcription; it is not a second conversation runtime.

No repository evidence establishes an HA-supported DJConnect native WebSocket
binary audio ingest, chunk ordering, backpressure, VAD/end-of-stream contract,
or native client implementation that can safely use one. Current app input is
a bounded complete WAV clip. Remote native connectivity remains HTTPS-only;
remote WebSocket is not authorized.

Therefore no streaming optimization is safe in this repository. A future
proposal needs primary Home Assistant contract evidence plus owning native-client
repository evidence for pipeline start stage, binary framing, cancellation,
backpressure, audio format and final-only transcript submission. It must retain
HTTPS clip upload as the remote boundary unless a separately approved HTTP
streaming contract exists.
