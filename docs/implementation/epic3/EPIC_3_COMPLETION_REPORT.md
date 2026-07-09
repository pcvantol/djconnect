# Epic 3 Completion Report

Status: complete in source, pending review/merge of Phase 4.

## Phases Completed

- Phase 1: Core Profile Domain.
- Phase 2: Persistence + Config Flow.
- Phase 3: Services + API Profile Resolution.
- Phase 4: Privacy + Export/Import + Completion Hardening.

## Architecture Delivered

Epic 3 makes Profile the primary DJConnect runtime identity. Devices remain
runtime mappings, Music Backends own provider playback, Music Accounts are
metadata bindings and Profile Resolver is the single identity resolution path.

## Runtime Behavior Changed

- Profile context is resolved before personal service/API work.
- Requests may use `private_session: true`.
- Private/shared/guest-safe policies suppress personal persistence where needed.
- Guest-safe and shared contexts avoid exposing personal Music DNA/history by
default.

## Services/API Changed

Profile-aware services/API paths support optional `profile_id` and `device_id`.
Phase 4 adds developer services:

- `djconnect.profile_export`;
- `djconnect.household_export`;
- `djconnect.integration_export`;
- `djconnect.profile_import`;
- `djconnect.household_import`;
- `djconnect.clear_profile_state`.

## Tests Added

Coverage includes:

- Profile resolver/context behavior;
- privacy policy behavior;
- guest-safe export redaction;
- household/full export secret exclusion;
- profile import collision handling;
- unsafe secret-field rejection;
- clear/reset without profile deletion.

## Known Follow-Up Work

- Move legacy Ask DJ history storage from HA-user primary key to Profile-native
  storage when the broader history migration is scheduled.
- Expand client UX for profile switching and private-session controls.
- Add cross-client fixture coverage for Profile privacy and export behavior.
- Add cloud/profile portability only in a later Cloud epic.

## Remaining Limitations

Current export/import is local Profile Platform portability, not Cloud sync.
Provider credentials are intentionally excluded and must be re-linked after
import. Existing clients do not yet expose full profile management UI.

## Readiness For Epic 4

Epic 4 can assume Profile identity, privacy policy, resolver, storage,
backend/account routing metadata and non-secret portability exist in the
canonical Home Assistant repository.

## Migration And Compatibility

Backward compatibility was not prioritized because DJConnect is not yet live.
Legacy no-profile test/runtime paths remain tolerated when no Profile Platform
state exists.

## Privacy And Security Notes

Exports exclude OAuth tokens, provider refresh tokens, provider secrets, Home
Assistant tokens, APNs tokens, device tokens and raw credentials. Imports reject
secret-like fields rather than silently storing them.

