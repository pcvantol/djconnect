# Epic 3 Phase 1 — Core Domain

Status: implemented in source, pending review/merge.

## Scope

Phase 1 creates the runtime-neutral Profile Domain only.

Included:

- Profile domain model;
- Device domain model;
- Household domain model;
- Music Backend model;
- Music Account model;
- Playback Zone model;
- canonical Profile Resolver;
- canonical domain errors;
- focused unit tests.

## Explicitly Not Included

Phase 1 does not implement:

- persistence;
- storage migration;
- config flow;
- options flow;
- services;
- REST or websocket API changes;
- Ask DJ history migration;
- Music DNA migration;
- recommendations implementation;
- privacy implementation;
- feature flags implementation;
- client changes.

## Architecture Notes

The core domain lives under `custom_components/djconnect/domain/`.

Profile is the primary identity and owns personal references such as Music DNA,
conversation history, recommendations, mood, response style, voice style,
likes/dislikes, privacy mode, preferences and entitlements.

Device owns only hardware, client and runtime context. Devices link to
profiles, but do not own durable personal state.

Music Backend registrations model provider adapters and capabilities. Music
Accounts model provider account bindings without OAuth or persistence behavior.

Playback Zones model targets only; playback execution remains out of scope.

`ProfileResolver` is the single canonical resolver and follows the foundation
priority exactly:

1. explicit `profile_id`;
2. `device_id` mapping;
3. Home Assistant user hint;
4. room mapping;
5. fallback profile;
6. `ProfileRequired`.

## Review Checklist

- Personal state belongs to Profile.
- Runtime state belongs to Device.
- Provider playback capability belongs to Music Backend.
- Account binding belongs to Music Account.
- Playback target belongs to Playback Zone.
- Resolution logic exists in exactly one resolver.
- No later-phase runtime behavior is implemented.
