# ADR-0001: DJConnect Profile is the primary identity

## Status

Accepted

## Context

Early DJConnect flows were naturally shaped around devices, Spotify credentials, Home Assistant users and client-specific runtime identity.

That model becomes limiting as DJConnect grows into a multi-client platform:

- one user can have several devices;
- shared household devices should not expose personal state;
- one music account may be shared by multiple profiles;
- Personal/Paid capabilities are profile-level, not device-level;
- Ask DJ continuity should roam across personal devices;
- future cloud sync and profile portability need a stable identity abstraction.

Home Assistant `user_id`, Spotify account identity and device identity are useful signals, but none of them should define the DJConnect user experience.

## Decision

DJConnect Profile is the primary identity for personal and shared DJConnect state.

A Profile owns:

- Music DNA;
- mood state;
- DJ personality / response style;
- Ask DJ history;
- recommendations;
- likes/dislikes;
- preferred backend/account;
- privacy mode;
- tier/entitlement state;
- feature flags where personal.

Devices link to profiles. Music accounts bind to profiles. Home Assistant users may map to profiles as hints.

## Consequences

- Device state must not contain durable personal intelligence.
- Ask DJ history should be profile-bound.
- Shared devices should normally resolve to household/room/guest/kids profiles.
- Personal devices should normally resolve to a personal profile.
- Future Personal/Paid capabilities can be sold and explained as profile-level capabilities.
- Export/import can become profile-centered.

## Alternatives considered

### Device as identity

Rejected. It fragments memory and makes multi-device continuity hard.

### Spotify account as identity

Rejected. DJConnect is music-backend agnostic and Spotify accounts may be shared.

### Home Assistant user as identity

Rejected as primary identity. Useful as a hint, but not all devices and flows have an HA user. Voice satellites and shared displays are often room/device-based.

## Affected repositories

- `pcvantol/djconnect`
- `pcvantol/djconnect-app`
- `pcvantol/djconnect-windows`
- `pcvantol/djconnect-pi`
- future Android/web/VR clients

## Related documents

- `DJCONNECT_CONSTITUTION.md`
- `DOMAIN_MODEL.md`
- `ARCHITECTURE_PRINCIPLES.md`
- `CLIENT_CAPABILITY_MATRIX.md`
