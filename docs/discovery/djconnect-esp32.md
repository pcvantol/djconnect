# Repository Discovery Report: `pcvantol/djconnect-esp32`

## Overview

The ESP32 repo owns Voice/Control Client firmware for LilyGO T-Embed S3 hardware. It is local-first, physical, robust and Community-oriented.

## Purpose

Owns firmware runtime, device UI, buttons/encoder, display, audio cues, PTT upload, local device API, BLE WiFi provisioning, OTA endpoint, NVS pairing state, web portal and hardware safety.

Does not own Spotify credentials, backend playback orchestration, Music DNA, Ask DJ chat history or foundation docs.

## Strengths

- Strong product boundary: README states ESP is not a Spotify Connect speaker/player and sends generic backend-agnostic commands.
- Good firmware safety posture: SHA256 OTA, token auth, NVS secrets, battery guards, watchdogs.
- Host-side tests cover protocol parsing, backend summaries, OTA version logic and contract names.
- CI includes native tests, PlatformIO build, release dry-run, CodeQL and secret scanning.
- `include/Secrets.h` contains only an optional insecure TLS flag, not credentials.

## Weaknesses

- Firmware repo is described as both source and release repository, while foundation ownership separates `djconnect-esp32` source from `djconnect-firmware` public release artifacts. This is historically true but architecturally muddy.
- AGENTS is long and strong, but should be refreshed to include all Epic 1 foundation docs.
- Web portal includes rich controls/games; keep it from becoming a parallel app-client product.

## Architecture observations

ESP32 follows the Voice/Control Client class well. It should not gain Ask DJ chat UI, Music DNA or Discover. The local web portal is useful for device management but should remain device/control oriented.

## Product observations

Good Community hardware story. Product wording still leads with "Muziekbediening met karakter"; future docs should align with "Your AI DJ" while keeping device simplicity.

## Technical debt

- Source/release boundary needs clarification in docs and release process.
- Board support appears single-device; future hardware would need a board abstraction review.
- Protocol versioning is strict and should remain explicit.

## Product debt

- Physical device role is clear, but local games and web portal breadth could distract from Voice/Control identity.

## Feature drift

Appropriately behind clients on intelligence; ahead on physical controls, PTT and device settings.

## CI observations

Strong for firmware. Secret scan is especially important and present.

## Security observations

Good: no compiled credentials, token protected endpoints, SHA256 OTA. Insecure TLS flag must stay off by default.

## Privacy observations

Good: no durable personal intelligence. Raw audio flows through HA voice endpoint and should not be stored.

## Recommendations

1. Clarify source vs public release ownership in README after repository audit.
2. Refresh AGENTS to full foundation set.
3. Keep web portal scoped to device/control diagnostics; do not add personal intelligence UI.
4. Add future ADR/backlog item for multi-board firmware architecture before adding a second board.

## Priority

P1 for ownership clarification; P2 for AGENTS refresh and web portal scope guard.

## Estimated effort

Small for docs; medium if multi-board architecture is pursued.

## Scores

| Dimension | Score |
| --- | ---: |
| Product | 8 |
| Architecture | 8 |
| Documentation | 8 |
| Testing | 7 |
| CI/CD | 8 |
| Security | 9 |
| Privacy | 9 |
| Release | 8 |
| Developer Experience | 7 |
| Overall | 8.0 |
