# Epic 3 Phase 2 — Persistence + Config Flow

Status: implemented in source, pending review/merge.

## Scope

Phase 2 persists the Phase 1 Profile Domain and exposes minimum Home Assistant
setup and management flows.

Included:

- `ProfilePlatformStorage` with explicit schema/versioning;
- Household/Profile/Device/Music Backend/Music Account/Playback Zone roundtrip
  serialization;
- storage validation for missing profiles, fallback profile, account/profile
  mappings and backend/account mismatches;
- first-run Profile setup after backend selection;
- `Later / manual` backend option for setup without provider credentials;
- options-flow profile management for add/edit/delete, fallback and device
  link/unlink;
- tests for storage roundtrip, CRUD, invalid references, config flow and options
  flow.

## Explicitly Not Included

Phase 2 does not implement:

- service layer rewiring;
- REST or websocket API changes;
- Ask DJ history storage migration;
- Music DNA storage migration;
- recommendations implementation;
- Insight Feed;
- export/import;
- cloud;
- premium/personal entitlement runtime;
- client changes;
- feature flag runtime.

## Architecture Notes

The storage manager is the only module that talks directly to the Profile
Platform store. Config and options flow call the manager instead of mutating
storage dictionaries directly.

Provider secrets are filtered from backend/account metadata. Spotify refresh
tokens stay in existing config-entry credential handling and are not written to
Profile Platform storage.

The options flow uses Phase 1 domain models and persisted mappings. Profile
resolution remains centralized through the Phase 1 `ProfileResolver`.

## Review Checklist

- Profile Platform state is durable.
- Devices link to Profiles but do not own personal state.
- Fallback Profile behavior is stored and validated.
- Storage validates missing/mismatched references.
- Config flow creates one backend, one profile, one account when applicable and
  one device mapping.
- Options flow can manage basic profiles and device mappings.
- No later-phase services/API/export/client work is present.
