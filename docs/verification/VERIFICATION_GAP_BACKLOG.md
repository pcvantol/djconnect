# Verification Gap Backlog

Status: Phase 8A updated backlog
Date: 2026-07-10

Do not automatically create GitHub issues from this file.

> Historical verification-gap record. The current Product Development Epic is
> Automated Session Intelligence E2E Verification, defined in
> `docs/product/DEVELOPER_EXPERIENCE_ROADMAP.md`. Its Architecture and Developer
> Session Bootstrap are complete; Deterministic Scenario Driver is the next
> CI-enabling cell.
> Any later scenario, capture, accelerated execution or verification work must
> exercise the canonical server-owned pipeline rather than introduce alternate
> Runtime or business-logic paths.

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
| VG-021 | P0 | Verification Gap | Map canonical scenarios to Apple adapter executable cases after Phase 10E runtime qualification. | Verification Platform | `djconnect` | Blocks broad Apple scenario coverage | M | Phase 10E-R3 |

## Phase 8 Progress

Completed:

- Verification Execution Environment implemented.
- Repository hygiene expanded with SHA validation, fetch/prune dry-runs,
  dependency inspection, toolchain inspection and GitHub CI inspection.
- Run identity, environment snapshots, toolchain discovery, dependency
  inspection, GitHub workflow discovery, cleanup safeguards and platform
  environment controllers added.
- CLI `prepare` and `restore` added under the existing verification namespace.

## Phase 8A Progress

Completed:

- Verification Data Framework implemented under `verification/data/`.
- Canonical data categories, boundaries, domain generator metadata, security
  payloads, localization payloads, data profiles and example datasets added.
- Deterministic seed strategy and data versioning documented.

Still pending for future generator execution:

- Add executable generator code that consumes the catalog IDs.
- Add schema validation for data catalog files if the static JSON format grows.

## Phase 8B Progress

Completed:

- Verification Modes Framework implemented under `verification/modes/`.
- Verification Policies Framework implemented under `verification/policies/`.
- Canonical mode and policy catalogs added with traceability to scenario
  categories, matrix profiles, data profiles, risks and workflows.

## Phase 8C Progress

Completed:

- Verification Planning Engine implemented under `tools/verification/planning/`.
- Canonical planning metadata, strategies, templates and examples added under
  `verification/planning/`.
- CLI `plan` added under the existing verification namespace.
- Planning now composes scenarios, modes, policies, matrix profiles and data
  profiles into machine-readable execution plans without executing them.

Closed by Phase 9:

- VG-001: first Home Assistant adapter implemented.
- VG-002: first HA executable subset defined as PROFILE-001 through
  PROFILE-005.
- VG-003: HA adapter output uses the existing redaction baseline for runtime
  logs and structured data.

Still pending after Phase 9:

- Live HA validation remains opt-in and should be run against a configured local
  HA development environment.
- Extend live websocket capability matching through the existing adapter
  transport hook.
- Add evidence file emission for live adapter logs through the existing
  evidence pipeline.

## Adapter Phase Must Not Do

- Do not implement Apple/Windows/Pi/ESP adapters.
- Do not mark hardware or live-client scenarios as passing.
- Do not add runtime features to satisfy scenarios.
- Do not redesign pairing, profile identity or capability discovery.

## Phase 9 Home Assistant Adapter Recommended Scope

- Completed first HA adapter skeleton and runtime primitives.
- Completed first profile scenario runtime execution path.
- Keep future growth scenario-driven and inside the existing adapter/core
  subsystems.
