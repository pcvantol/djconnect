# Epic 3B Phase 1 — Readiness Validation Report

Status: implemented in source, pending review/merge.

## Backend Readiness Status

The backend is ready for Apple and Windows profile adoption planning.

The backend is not ready for HA Voice Satellite rollout because explicit
satellite mapping and HA-derived satellite/area configuration are not yet
implemented.

## Fixes Made In This Phase

- Added profile capability/version discovery to existing
  `djconnect/capabilities`.
- Added reusable profile adoption fixtures under `examples/client_contracts/`.
- Added fixture tests for profile request, response, error, capability and
  privacy/secret behavior.
- Documented the canonical Profile Adoption Contract and endpoint inventory.

## Blockers

### Before Apple Adoption

No backend blockers found for initial Apple adoption.

Apple must still implement client-side profile selection and use backend errors
without recreating resolution logic.

### Before Windows Adoption

No backend blockers found for initial Windows adoption.

Windows should use the same fixture set as Apple.

### Before Raspberry Pi Adoption

No backend blocker for contract validation. Pi adoption should be careful to
default to shared/room/household profile semantics.

### Before ESP32 Adoption

No immediate backend blocker. ESP32 remains on registered `device_id` mapping
and does not need profile UI in this phase.

### Before HA Voice Satellite Adoption

Blocked.

Required follow-ups:

- satellite mapping storage/configuration;
- HA Assist satellite/device/area extraction;
- shared profile defaults for voice endpoints;
- contract tests for unmapped/ambiguous HA Voice contexts.

## Non-Blocking Follow-Ups

- Add richer `resolved_profile` metadata only where privacy-safe.
- Normalize profile-not-found wire code in a future compatibility window if
  desired; current wire code remains `invalid_profile`.
- Expand service-schema docs for profile-aware developer services.
- Add playback-zone/player mapping only when a client or voice flow requires it.

## Unresolved Follow-Up Work

- Epic 3B Phase 2 Apple adoption.
- Epic 3B Windows adoption.
- Epic 3B Pi adoption.
- Epic 3B HA Voice Satellite mapping phase.
- Cross-client fixture import in sibling repositories.

## Recommended Client Adoption Order

1. Apple Intelligence Client.
2. Windows Intelligence Client.
3. Raspberry Pi Ambient Client.
4. ESP32 compatibility verification.
5. HA Voice Assist Satellite mapping and shared-room rollout.

## Apple Go / No-Go

GO.

Apple adoption may start after this Phase 1 PR is merged. The backend exposes a
stable profile-context contract, fixtures, capability discovery and structured
error guidance sufficient for Apple profile selection and private-session work.

## Validation

Validated locally:

- `python3 -m unittest tests.test_client_contract_snapshots tests.test_websocket_api`

Additional profile-context and endpoint tests should remain part of normal PR
validation.
