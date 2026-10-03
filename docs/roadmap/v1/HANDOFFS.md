# Producer and consumer handoffs

This is a pinned planning projection for assignment `DJC-PLATFORM-ROADMAP-DAG-LANES-V1-20261003`. Owning roadmap, backlog, code and qualification records remain authoritative. It grants no product pickup, release, deployment or resource lease.

| Handoff | Producer → consumer | Phase | Subset | Artifact | Compatibility | Acceptance owner | State |
|---|---|---|---|---|---|---|---|
| `HA-DJC-APPLE` | `DJC-CORE` → `DJC-APPLE` | `integration_acceptance` | Profile-aware pairing, capabilities and backend-owned playback/Ask DJ subsets; preserve each host privacy and intentional absences | `UNKNOWN` | Consume only advertised supported contract; exact binding requires owning evidence | `DJC-APPLE` | DOCUMENTED; exact-version qualification not audited |
| `HA-DJC-ESP32` | `DJC-CORE` → `DJC-ESP32` | `integration_acceptance` | Profile-aware pairing, capabilities and backend-owned playback/Ask DJ subsets; preserve each host privacy and intentional absences | `UNKNOWN` | Consume only advertised supported contract; exact binding requires owning evidence | `DJC-ESP32` | DOCUMENTED; exact-version qualification not audited |
| `HA-DJC-PI` | `DJC-CORE` → `DJC-PI` | `integration_acceptance` | Profile-aware pairing, capabilities and backend-owned playback/Ask DJ subsets; preserve each host privacy and intentional absences | `UNKNOWN` | Consume only advertised supported contract; exact binding requires owning evidence | `DJC-PI` | DOCUMENTED; exact-version qualification not audited |
| `HA-DJC-WINDOWS` | `DJC-CORE` → `DJC-WINDOWS` | `integration_acceptance` | Profile-aware pairing, capabilities and backend-owned playback/Ask DJ subsets; preserve each host privacy and intentional absences | `UNKNOWN` | Consume only advertised supported contract; exact binding requires owning evidence | `DJC-WINDOWS` | DOCUMENTED; exact-version qualification not audited |
| `RELAY` | `DJC-API` → `DJC-CORE` | `integration_acceptance` | Server-side APNs relay boundary; no client provider credentials | `UNKNOWN` | Consume only advertised supported contract; exact binding requires owning evidence | `DJC-CORE` | DOCUMENTED; exact-version qualification not audited |
| `APPLE-CAST` | `DJC-APPLE` → `DJC-VIBECAST` | `integration_acceptance` | One runtime-scoped read-only Cast handoff; not pixel streaming | `UNKNOWN` | Consume only advertised supported contract; exact binding requires owning evidence | `DJC-VIBECAST` | DOCUMENTED; exact-version qualification not audited |
| `HA-CAST` | `DJC-CORE` → `DJC-VIBECAST` | `integration_acceptance` | Renderer-safe active Session Broadcast and lifecycle | `UNKNOWN` | Consume only advertised supported contract; exact binding requires owning evidence | `DJC-VIBECAST` | DOCUMENTED; exact-version qualification not audited |
| `FW-DIST` | `DJC-ESP32` → `DJC-DIST-FIRMWARE` | `distribution` | Source-generated firmware manifest, exact board asset and SHA-256 | `UNKNOWN` | Consume only advertised supported contract; exact binding requires owning evidence | `DJC-DIST-FIRMWARE` | DOCUMENTED; exact-version qualification not audited |
| `PI-DIST` | `DJC-PI` → `DJC-DIST-PI` | `distribution` | generic plus Pi profile bundles, manifest and pointer | `NOT_PUBLISHED_BY_THIS_ASSIGNMENT` | Exact source SHA, asset checksum, receiving repo writer slot and channel policy required | `DJC-DIST-PI` | WORKFLOW_PATH_READ; POLICY/RECEIPT_NOT_ACCEPTED_FOR_NEW_RELEASE |
| `APPLE-DIST` | `DJC-APPLE` → `DJC-DIST-APPLE` | `distribution` | iOS/macOS unsigned bundles, hashes and tags | `NOT_PUBLISHED_BY_THIS_ASSIGNMENT` | Exact source SHA, asset checksum, receiving repo writer slot and channel policy required | `DJC-DIST-APPLE` | WORKFLOW_PATH_READ; POLICY/RECEIPT_NOT_ACCEPTED_FOR_NEW_RELEASE |
| `WIN-DIST` | `DJC-WINDOWS` → `DJC-DIST-APPLE` | `distribution` | Windows x64/arm64 and conditional Mac Catalyst artifacts | `NOT_PUBLISHED_BY_THIS_ASSIGNMENT` | Exact source SHA, asset checksum, receiving repo writer slot and channel policy required | `DJC-DIST-APPLE` | WORKFLOW_PATH_READ; POLICY/RECEIPT_NOT_ACCEPTED_FOR_NEW_RELEASE |
| `WIN-SITE` | `DJC-WINDOWS` → `DJC-WEBSITE` | `distribution` | Windows and Mac Catalyst release notes | `NOT_PUBLISHED_BY_THIS_ASSIGNMENT` | Exact source SHA, asset checksum, receiving repo writer slot and channel policy required | `DJC-WEBSITE` | WORKFLOW_PATH_READ; POLICY/RECEIPT_NOT_ACCEPTED_FOR_NEW_RELEASE |
| `APPLE-SITE` | `DJC-APPLE` → `DJC-WEBSITE` | `distribution` | Versioned and latest Apple release notes from the same Apple publication workflow | `NOT_PUBLISHED_BY_THIS_ASSIGNMENT` | Exact Apple source SHA, notes locale set and receiving website writer slot | `DJC-WEBSITE` | WORKFLOW_PATH_READ; NO_PUBLICATION_AUTHORIZED |

## Resource and follow-up policy

One repository has at most one mutating assignment. A waiting assignment is not a free writer slot. Shared machines, signer, HA lab, API budget and devices require measured, bounded reservations and real quiescence evidence.

- `CORE_WRITER`: capacity `1`; state `planning assignment active on core`; release condition: Git branch and clean baseline readback.
- `APPLE_SOURCE`: capacity `1`; state `unrelated local WIP observed`; release condition: owning writer disposition required.
- `WINDOWS_SOURCE`: capacity `1`; state `unrelated local WIP observed`; release condition: owning writer disposition required.
- `APPLE_SIGNER`: capacity `UNKNOWN`; state `NOT_RESERVED`; release condition: exact bounded signing operation and explicit release evidence.
- `HA_LAB`: capacity `UNKNOWN`; state `NOT_RESERVED`; release condition: exact test target and quiescence evidence.
- `PI_AND_ESP_HARDWARE`: capacity `UNKNOWN`; state `NOT_RESERVED`; release condition: target serial/profile and release after real test.

Future monitoring uses fresh source and consumer evidence, names exact blockers, avoids duplicate comments and treats two unchanged checks as an investigation signal. No monitor is installed by this assignment.
