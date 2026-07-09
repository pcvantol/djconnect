# ADR-0011: Profile resolution uses Request Context

## Status

Accepted

## Context

DJConnect Profile is the primary identity for personal and shared state.

Not every interaction originates from a paired DJConnect Device. Requests may
come from Apple and Windows clients, Raspberry Pi, ESP32, Home Assistant Voice
Assist satellites, Home Assistant services, automations, Home Assistant user
context, room/area context, playback players/zones and future speaker
recognition.

Separate identity resolution implementations for clients, Assist, services or
future endpoints would create product drift, privacy bugs and inconsistent
fallback behavior.

## Decision

DJConnect keeps one canonical `ProfileResolver`.

The resolver accepts a Request Context. The current runtime type is named
`ProfileResolutionContext`.

Request Context treats device, satellite, Home Assistant user, Home Assistant
device/entity, area, room, playback player/zone, session and future speaker
identity as signals. The resolved DJConnect Profile remains the identity.

Explicit mappings are preferred over inferred mappings. Explicit profile
selection has highest priority. Invalid explicit profile selection returns a
structured error instead of falling through to another personal profile.

Shared voice endpoints should resolve to shared, room, household, guest-safe or
kids profiles by default unless explicitly configured otherwise.

Home Assistant `user_id` and future speaker identity are hints. They are not
unconditional authority and must not silently override explicit profile,
session or device selection.

## Consequences

- Services, API, Assist, websocket handlers and clients share one resolution
  path.
- Generic Home Assistant Voice Assist satellites do not have to become
  DJConnect Devices solely for Profile resolution.
- Satellite, area and playback-zone mappings become explicit configuration
  concepts.
- Shared satellite privacy behavior is deterministic.
- Future speaker recognition can be introduced without redesigning identity.
- Private-session rules still apply after Profile resolution.
- Current Epic 3 runtime support remains narrower and requires follow-up work
  for satellite, HA device/entity, area and player/zone signals.

## Alternatives considered

### Require every request source to be a DJConnect Device

Rejected. HA Voice Assist satellites, automations and service calls can provide
useful context without being DJConnect product devices.

### Use Home Assistant user as the primary identity

Rejected. HA user IDs are useful hints, but shared satellites and rooms often do
not have a meaningful HA user context.

### Implement a separate resolver for Voice Assist

Rejected. A second resolver would drift from services/API behavior and create
privacy inconsistencies.

### Infer personal identity from room alone

Rejected. Rooms are shared contexts by default and should normally resolve to
shared, room, household, guest-safe or kids profiles.

### Make speaker recognition authoritative by default

Rejected. Future speaker recognition may be a hint, but ambiguous or incorrect
recognition must fall back safely rather than expose personal state.

## Affected repositories

- `pcvantol/djconnect`
- `pcvantol/djconnect-app`
- `pcvantol/djconnect-windows`
- `pcvantol/djconnect-pi`
- `pcvantol/djconnect-esp32`
- future Android/web/VR clients

## Related documents

- `DOMAIN_MODEL.md`
- `ARCHITECTURE_PRINCIPLES.md`
- `PLATFORM_PRINCIPLES.md`
- `CLIENT_CAPABILITY_MATRIX.md`
- `REPOSITORY_OWNERSHIP.md`
