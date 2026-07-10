# Verification Gap Backlog

Status: Phase 8 updated backlog
Date: 2026-07-10

Do not automatically create GitHub issues from this file.

| ID | Priority | Gap Type | Gap | Owner | Repository | Blocking | Estimated Effort | Recommended Phase |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| VG-001 | P0 | Verification Gap | Implement first Home Assistant adapter for HA-owned scenarios. | Verification | `djconnect` | Blocks automated scenario execution | M | Phase 8 |
| VG-002 | P0 | Verification Gap | Define Phase 8 HA scenario subset and mark client/hardware scenarios out of scope. | Verification | `djconnect` | Blocks clear Phase 8 scope | S | Phase 8 |
| VG-003 | P0 | Verification Gap | Add evidence metadata/redaction baseline to HA adapter outputs. | Verification | `djconnect` | Blocks trustworthy evidence | M | Phase 8 |
| VG-004 | P1 | Scenario Gap | Add explicit push/APNs scenario mapping or a push scenario group. | Platform Verification | `djconnect` | Non-blocking for HA adapter | S | Phase 9 |
| VG-005 | P1 | Verification Gap | Add Apple adapter plan for pairing, profile selection, Ask DJ, PTT, APNs and localization evidence. | Apple | `djconnect-app` | Blocks Apple verification | L | Phase 9 |
| VG-006 | P1 | Unknown | Complete Apple storage/logging/entitlement archaeology. | Apple | `djconnect-app` | Blocks Apple readiness scoring | M | Phase 9 |
| VG-007 | P1 | Verification Gap | Add Windows adapter for native ARM64 execution, pairing, websocket fallback, localization screenshots and secure storage checks. | Windows | `djconnect-windows` | Blocks Windows verification | L | Phase 10 |
| VG-008 | P1 | Verification Gap | Add Pi adapter for local-only pairing, shared-profile display, update UI and logs. | Pi | `djconnect-pi` | Blocks Pi verification | L | Phase 10 |
| VG-009 | P1 | Verification Gap | Add ESP32 adapter/hardware plan for serial, PTT, display, BLE, OTA and power evidence. | Firmware | `djconnect-esp32` | Blocks hardware verification | L | Phase 10 |
| VG-010 | P1 | Verification Gap | Add Voice Endpoint adapter for real HA Voice Satellite/VPE context, STT/TTS and mapping behavior. | HA/Voice | `djconnect` | Blocks live voice confidence | M | Phase 9 |
| VG-011 | P1 | Verification Gap | Add Release adapter for release repos, artifacts, manifests, checksums and release notes. | Release | all release repos | Blocks V6 readiness | M | Phase 11 |
| VG-012 | P1 | Verification Gap | Add Website adapter/static validation for localization, links, metadata and product copy. | Website | `djconnect-website` | Blocks website/release verification | M | Phase 11 |
| VG-013 | P2 | Legacy Behaviour | Verify Music DNA and Ask DJ legacy user/device key fallback cannot leak personal state after profile adoption. | HA | `djconnect` | Non-blocking, privacy-relevant | M | Phase 8 |
| VG-014 | P2 | Verification Gap | Add live Spotify Direct and Music Assistant backend fixtures/environments. | HA/Music Backend | `djconnect` | Blocks full backend scenarios | M | Phase 9 |
| VG-015 | P2 | Scenario Gap | Clarify client-specific scenario grouping for Apple/Windows/Pi/ESP examples. | Platform Verification | `djconnect` | Non-blocking | S | Phase 9 |
| VG-016 | P2 | Verification Gap | Add client capability consumer tests: no version inference, fallback on unsupported websocket. | Clients | `djconnect-app`, `djconnect-windows`, `djconnect-pi` | Blocks capability confidence | M | Phase 9/10 |
| VG-017 | P2 | Verification Gap | Add localization parity checks across all repos and release copy. | Platform Localization | all repos | Blocks localization score | M | Phase 11 |
| VG-018 | P2 | Unknown | Complete release repo artifact inventory. | Release | `djconnect-firmware`, `djconnect-app-releases`, `djconnect-pi-releases` | Blocks release adapter scope | S | Phase 11 |
| VG-019 | P3 | Documentation Gap | Keep technical design docs updated as adapter evidence finds drift. | Platform Docs | `djconnect` | Non-blocking | S ongoing | Phase 8+ |
| VG-020 | P3 | Foundation Gap | Consider ADR for central push/install-token trust boundary if APNs relay becomes long-term platform contract. | Platform Architecture | `djconnect` | Non-blocking | M | Future ADR phase |

## Phase 8 Progress

Completed:

- Verification Execution Environment implemented.
- Repository hygiene expanded with SHA validation, fetch/prune dry-runs,
  dependency inspection, toolchain inspection and GitHub CI inspection.
- Run identity, environment snapshots, toolchain discovery, dependency
  inspection, GitHub workflow discovery, cleanup safeguards and platform
  environment controllers added.
- CLI `prepare` and `restore` added under the existing verification namespace.

Still pending for Phase 9 Home Assistant Adapter:

- VG-001 remains open: implement first Home Assistant adapter.
- VG-002 remains open: define the HA executable scenario subset in adapter
  configuration.
- VG-003 remains open: connect HA adapter evidence to the redaction/evidence
  baseline.

## Adapter Phase Must Not Do

- Do not implement Apple/Windows/Pi/ESP adapters.
- Do not mark hardware or live-client scenarios as passing.
- Do not add runtime features to satisfy scenarios.
- Do not redesign pairing, profile identity or capability discovery.

## Phase 9 Home Assistant Adapter Recommended Scope

- HA adapter skeleton.
- Scenario loading/filtering for HA-owned categories.
- HTTP route calls with sanitized request/response evidence.
- Websocket producer checks.
- Profile resolver/storage checks.
- Export/import/privacy checks.
- Deterministic voice error/helper checks where no real STT device is needed.
