# Epic 3 Phase 4 — Privacy + Export/Import

Status: implemented in source, pending review/merge.

## Scope

Phase 4 completes the Profile Platform identity layer.

Included:

- central Profile privacy policy;
- private session persistence suppression;
- shared and guest-safe personal-state guards;
- Profile personal-state clear/reset helpers;
- single Profile export;
- household Profile Platform export;
- full non-secret integration export;
- profile and household import validation;
- Home Assistant developer services for export/import/reset;
- tests for privacy, export/import, secret filtering and reset behavior.

## Explicitly Not Included

Phase 4 does not implement:

- Insight Feed;
- Lyrics Explain;
- VibeCast hybrid mode;
- Cloud sync;
- Premium runtime;
- Voice Personas;
- Android;
- Apple, Windows, Pi or ESP client changes;
- Feature Flag platform.

## Architecture Notes

`profile_privacy.py` owns the runtime policy for Profile privacy modes and
private sessions. Entry points resolve the policy once through
`DJConnectRequestContext`; handlers read that policy rather than recreating
privacy decisions locally.

`profile_export.py` owns non-secret Profile Platform portability. Export uses
the explicit Phase 2 storage schema and redacts secret-like keys. Import rejects
secret-like fields, validates schema/version, avoids silent overwrites and
requires re-linking provider credentials after import.

Clear/reset flows remove profile-owned personal references without deleting the
Profile or moving personal state to Device.

