# Epic 3 Phase 3 — Services + API Profile Resolution

Status: implemented in source, pending review/merge.

## Scope

Phase 3 wires existing service/API entrypoints through the Profile Platform.

Included:

- shared `DJConnectRequestContext` in `profile_context.py`;
- canonical Profile Resolver use at service/API boundaries;
- structured profile errors;
- profile-scoped adapter key for existing Music DNA/Ask DJ/Discovery paths;
- profile-derived backend/account/zone context hints for the use-case layer;
- API handling for command, Ask DJ message/idle/history, Track Insight, Music
  DNA and Music Discovery entrypoints;
- tests for explicit profile, device mapping, fallback, failure and backend
  routing.

## Explicitly Not Included

Phase 3 does not implement:

- export/import;
- privacy clear/reset flows;
- full private session behavior;
- full Insight Feed;
- Lyrics Explain implementation;
- cloud;
- premium entitlement runtime;
- feature flag runtime;
- client repository updates;
- major UI changes.

## Architecture Notes

Runtime entrypoints should call the shared context helper instead of deciding
identity locally. The helper resolves `profile_id`, `device_id`, HA user hint,
room mapping and fallback through the Phase 1 resolver and Phase 2 storage.

When Profile Platform storage is not configured yet, legacy test/runtime paths
remain a no-op unless an explicit `profile_id` is provided. Once profiles exist,
profile resolution failures return structured errors.

Existing Ask DJ, Music DNA and Discovery stores are not migrated in this phase.
Payloads are profile-addressed through `profile:<profile_id>` so Phase 4 can
complete durable state migration without changing public signatures again.
