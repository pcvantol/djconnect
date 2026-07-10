# Technical Overview

## Current Shape

`CONFIRMED_CODE` The Home Assistant integration is the local backend runtime.
It registers HTTP views under `/api/djconnect/v1`, Home Assistant websocket
commands under `djconnect/...`, Home Assistant services, entities and a
conversation agent named `DJConnect DJ`.

`CONFIRMED_CODE` ESP32 and Raspberry Pi expose local device APIs under
`/api/device/*`. Home Assistant uses those local APIs for device pairing,
device commands, OTA, reboot/forget and DJ response delivery.

`CONFIRMED_CODE` Apple, Windows and Pi clients call the HA API directly after
pairing. Apple, Windows and Pi also contain websocket fast-path support for
selected routes, gated by `djconnect/capabilities` and with HTTP fallbacks.

`CONFIRMED_CODE` The central `djconnect-api` repository is a Cloudflare Worker
used for Apple push relay/install-token/bootstrap-proof flows. It is not the
music intelligence runtime.

## Repository Roles

| Repository | Current implementation role | Classification |
| --- | --- | --- |
| `djconnect` | HA integration, profile/runtime state, HTTP, websocket, services, Spotify Direct/Music Assistant orchestration, voice/STT/TTS, push relay client, OTA orchestration. | `CONFIRMED_CODE` |
| `djconnect-app` | Apple iOS/macOS/watchOS Intelligence Client, HTTP and websocket client, APNs registration surface. | `CONFIRMED_CODE` |
| `djconnect-windows` | .NET MAUI Windows client with HTTP/websocket transport, Credential Manager/Keychain credential storage, local pairing UI. | `CONFIRMED_CODE` |
| `djconnect-pi` | Python Raspberry Pi Ambient Client with local `/api/device` API, HA HTTP client, optional websocket fast path, updater. | `CONFIRMED_CODE` |
| `djconnect-esp32` | PlatformIO/Arduino ESP32 firmware with local `/api/device` API, mDNS, NVS provisioning, PTT WAV upload, OTA. | `CONFIRMED_CODE` |
| `djconnect-api` | Cloudflare Worker for install tokens, bootstrap proofs and APNs relay. | `CONFIRMED_CODE` |
| `djconnect-website` | Product website/docs implementation. No runtime protocol ownership observed. | `DOCUMENTED_ONLY` |
| `djconnect-firmware` | Public firmware release artifacts/manifest. | `DOCUMENTED_ONLY` |
| `djconnect-app-releases` | Public app release artifacts. | `DOCUMENTED_ONLY` |
| `djconnect-pi-releases` | Public Pi release artifacts. | `DOCUMENTED_ONLY` |

## Verification Mapping

| Technical area | Scenario families |
| --- | --- |
| Pairing | `SETUP-013`, `SETUP-014`, `SETUP-015`, `SETUP-019`, `SETUP-021`, `SETUP-022`, `NETWORK-*`, `ESP-*`, `PI-*`, `APPLE-*`, `WINDOWS-*` |
| HTTP API | `ASKDJ-*`, `MUSICDNA-*`, `DISCOVER-*`, `TRACK-*`, `PLAYBACK-*`, `BACKEND-*`, `PRIVACY-*` |
| WebSocket API | `CAPABILITY-*`, `ASKDJ-*`, `MUSICDNA-*`, `DISCOVER-*`, `TRACK-*` |
| Voice | `VOICE-*`, `ESP-*`, `APPLE-*` |
| Push | `APPLE-*`, `PRIVACY-*`, `NETWORK-*` |
| Updates/releases | `RELEASE-*`, `ESP-*`, `PI-*`, `WINDOWS-*` |
