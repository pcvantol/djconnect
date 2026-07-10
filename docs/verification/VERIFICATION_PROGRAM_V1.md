# DJConnect Verification Program V1

Status: Active verification program  
Date opened: 2026-07-10  
Scope owner: `pcvantol/djconnect`  
Platform baseline: `PLATFORM_BASELINE_v1.md`  
Epic gate: Epic 4 must not begin until `VERIFICATION_REPORT.md` reaches GO.

## Purpose

Verification Program V1 validates the accepted Profile Platform against real
usage across backend, clients, devices, voice entrypoints, music backends,
privacy and capability discovery.

This is not an implementation sprint. New features are out of scope unless a
verification failure requires the smallest practical fix. Architecture changes
require an ADR proposal.

## Source Documents

Verification starts from these accepted documents:

- `FOUNDATION_INDEX.md`
- `PLATFORM_BASELINE_v1.md`
- `PLATFORM_PRINCIPLES.md`
- `DOMAIN_MODEL.md`
- `CLIENT_CAPABILITY_MATRIX.md`
- `PLATFORM_BACKLOG.md`
- `EPIC_3_FINAL_REPORT.md`
- `docs/implementation/epic3/EPIC_3_COMPLETION_REPORT.md`
- `docs/implementation/epic3b/01-profile-adoption-contract.md`
- `REPOSITORY_OWNERSHIP.md`

## Verification Principles

- Validate behavior with real devices, real clients and real Home Assistant
  runtime flows where possible.
- Treat passing unit tests as necessary but insufficient.
- Record evidence for every scenario.
- Do not infer client support from app or integration versions when capability
  discovery exists.
- Keep personal state attached only to DJConnect Profile.
- Keep Request Context free of tokens, raw prompts, raw audio, Ask DJ history
  and Music DNA contents.
- Preserve repository ownership boundaries while collecting cross-repo evidence.

## Result States

| State | Meaning |
| --- | --- |
| PASS | Expected behavior observed with acceptable evidence. |
| FAIL | Expected behavior did not occur, data leaked, state corrupted or a blocker exists. |
| WARNING | Behavior works with caveat, degraded path, missing polish or non-blocking risk. |
| NOT TESTED | Scenario has not yet been executed or evidence is missing. |

## Required Evidence

Each executed scenario records:

- date, tester and environment;
- Home Assistant version and DJConnect integration version;
- client app/firmware/runtime version and commit when available;
- music backend and account state;
- profiles, mappings and privacy mode used;
- expected behavior;
- observed behavior;
- sanitized logs;
- screenshots or screen recordings where useful;
- root cause for failures;
- recommendation and owner.

## Failure Policy

When a failure is found, classify it as:

- Implementation bug;
- Architecture issue;
- Documentation issue;
- Test issue.

Implementation bugs may receive minimal fixes inside the relevant repository.
Architecture issues require an ADR proposal before redesign work. Documentation
issues update the canonical docs or repository-local docs according to
`REPOSITORY_OWNERSHIP.md`.

## Environment Matrix

| Area | Minimum environment |
| --- | --- |
| Backend | Fresh HA test instance plus upgraded existing HA instance with DJConnect `3.2.50` or current branch build. |
| Apple | iOS/iPadOS, macOS and watchOS builds that implement Profile Adoption Contract v1. |
| Windows | Windows build that implements the same Profile Adoption Contract v1 fixtures as Apple. |
| Raspberry Pi | Pi Ambient Client connected to the same HA instance. |
| ESP32 | DJConnect ESP32 firmware with `client_type:"esp32"`, PTT, status and OTA support. |
| Voice Endpoint | Home Assistant Voice Satellite or Voice Preview Edition mapped through HA Assist. |
| Music backend | Spotify Direct and Music Assistant configured separately. |
| Accounts | At least one personal account, one household/shared account path and one relink flow. |

## Deliverables

- `PROFILE_PLATFORM_VERIFICATION.md`
- `LIVE_SCENARIOS.md`
- `KNOWN_LIMITATIONS.md`
- `VERIFICATION_REPORT.md`

## Completion Gate

Epic 4 may begin only when `VERIFICATION_REPORT.md` records:

- overall result: GO;
- no blocking FAIL scenarios;
- all required live categories completed or explicitly accepted as known
  limitations;
- privacy and capability discovery categories PASS;
- backend restart and export/import categories PASS or accepted with documented
  non-blocking limitations.
