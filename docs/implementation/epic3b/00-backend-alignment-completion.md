# Epic 3B Phase 0 — Backend Alignment Completion

Status: implemented in source, pending review/merge.

## Goal

Phase 0 aligns the Home Assistant backend with the foundation decision that
Profile resolution uses a general request context, not only a DJConnect Device.

This phase does not implement client adoption, HA Voice Satellite management UI,
speaker recognition, cloud identity or new public API contracts.

## Context Model Introduced

`ProfileResolutionContext` is now the canonical typed input for the
`ProfileResolver`.

It is:

- immutable;
- typed;
- normalized on construction;
- temporary request input only;
- free of personal state and provider secrets.

The resolver keeps `resolve(context)` as the canonical call for existing code
and adds `resolve_with_result(context)` for safe diagnostics.

## Active Resolution Signals

The implemented Epic 3A behavior remains the baseline:

1. explicit profile selection through `explicit_profile_id`;
2. DJConnect `device_id` mapping;
3. Home Assistant `ha_user_id` mapping/hint;
4. `area_id`/`room_id` mapping through the existing room mapping index;
5. configured fallback profile;
6. structured `ProfileRequired` failure.

Invalid explicit profiles still raise `ProfileNotFound` and do not fall through
to another profile. Explicit device mapping still beats inferred room/area
mapping.

## Reserved Future Signals

The typed context also carries reserved request-source fields:

- `client_type`;
- `satellite_id`;
- `ha_device_id`;
- `player_id`;
- `playback_zone_id`;
- `session_id`;
- `request_source`;
- `speaker_identity_hint`.

These fields do not yet implement satellite, playback-zone or speaker-recognition
resolution. They create a clear integration path for later Epic 3B phases.

## Runtime Entrypoints Aligned

Runtime entrypoints now construct `ProfileResolutionContext` through
`profile_resolution_context_from_payload()`.

Aligned surfaces include:

- Home Assistant service handlers that route through `api_handlers`;
- REST/HTTP handlers that route through `api_handlers`;
- websocket handlers that route through `api_handlers`;
- command/playback entrypoints;
- Ask DJ message, history, idle suggestion and clear/state entrypoints;
- Music DNA profile/settings/clear/import/export entrypoints;
- Music Discovery feed/refresh/play/feedback entrypoints;
- Track Insight entrypoints;
- Profile export/household export/integration export/clear state entrypoints;
- voice/PTT Ask DJ entrypoint header extraction.

No public payload field is required to change. Existing `profile_id`,
`device_id`, `user_id` and `room_id` inputs are translated internally into the
typed context.

## Diagnostics

The resolver can return a safe `ProfileResolutionResult` with:

- resolved profile;
- resolution reason;
- signal used;
- fallback-used flag.

Current resolution reasons are:

- `explicit_profile`;
- `device_mapping`;
- `satellite_mapping` (reserved);
- `ha_user_mapping`;
- `area_mapping`;
- `playback_zone_mapping` (reserved);
- `fallback`.

Debug logging records source, reason, profile id, device id, satellite presence,
area/room and fallback use. It does not log tokens, provider secrets, raw
conversation history, profile content or Music DNA.

## HA Voice Satellite Limitations

Phase 0 can carry optional voice request metadata from headers into the internal
Ask DJ payload and typed resolution context:

- profile ID;
- satellite ID;
- Home Assistant device ID;
- area ID;
- room ID;
- player ID;
- playback zone ID;
- session ID.

Home Assistant Assist satellite/device/area metadata is not yet automatically
derived from Assist internals. There is no satellite mapping UI, no voiceprint
storage and no speaker recognition. Shared voice endpoints therefore continue to
resolve through explicit profile/device/user/area-room/fallback signals only.

## Contract Changes

No intentional public REST, websocket, service or client contract changes.

Optional voice headers may now be translated into existing internal request
context fields when present. Existing clients do not need to send them.

## Tests

Validated:

- `python3 -m unittest tests.test_domain tests.test_profile_context tests.test_profile_storage`
- `python3 -m unittest tests.test_http_voice_helpers`
- `python3 -m unittest tests.test_websocket_api`

`tests.test_api_handlers` does not exist in this repository; API handler coverage
is currently represented by the profile context, Music DNA, HTTP voice and
websocket tests.

## Readiness For Epic 3B Phase 1

The backend is ready for Epic 3B Phase 1 — Readiness and Contract Validation.

Phase 1 can verify cross-source fixtures against one typed resolver context
without first redesigning Profile identity or adding client-specific resolver
paths.
