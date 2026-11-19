# Error Model

## Authentication / Pairing

`CONFIRMED_CODE` HA and local device APIs return structured JSON errors for
missing pair data, invalid JSON, invalid pair code, invalid client type,
client-type mismatch, unauthorized, not configured and stale pairing.

`CONFIRMED_TEST` Windows maps pairing and profile-platform errors to localized
repair/setup guidance and treats selected stale auth errors as local cleanup
signals.

## Version Mismatch

`CONFIRMED_CODE` HA checks firmware/runtime protocol compatibility on status,
event and voice paths and returns HTTP 426 with version metadata.

## Backend Capability

`CONFIRMED_CODE` Pi and ESP32 parse `unsupported_backend_capability` responses.
Pi logs backend/capability/message. ESP32 tests include unsupported backend
capability parsing.

## Voice/STT

`CONFIRMED_CODE` HA voice returns `stt_failed` with HTTP 422 for Ask DJ app voice
clients and 503/500 for other STT failure paths depending on provider/mode.
Oversized audio returns 413, missing audio 400 and unsupported media type 415.

## Transport

`CONFIRMED_CODE` Websocket clients fall back to HTTP when capability detection
or websocket connection fails.

## Unknowns

`UNKNOWN` Timeout and retry policies are implemented differently per client and
were not fully enumerated across every operation in this pass.

## Verification Mapping

`NETWORK-*`, `SETUP-021`, `SETUP-022`, `BACKEND-*`, `VOICE-*`, `PRIVACY-*`.
