# ADR-0003: Backend owns intelligence

## Status

Accepted

## Context

DJConnect has multiple current and future clients: Apple apps, Windows, Pi, ESP32, VibeCast, future Android/web and future VR/MR.

If every client generates or persists intelligence independently, the platform will fragment:

- recommendations may differ per client;
- Music DNA may drift;
- Ask DJ history will not roam;
- privacy controls become inconsistent;
- provider-specific behavior leaks into clients;
- future Personal/Cloud capabilities become harder to reason about.

## Decision

Durable DJConnect intelligence is owned by the backend.

The Home Assistant integration is the local-first backend and orchestration layer for Community. Future cloud services may extend this model but should not replace local-first behavior by default.

Clients render intelligence, provide input and advertise capabilities. They may cache short-lived presentation state, but they must not own canonical Music DNA, Ask DJ history, recommendation memory or durable profile intelligence.

## Consequences

- Ask DJ history is server/profile-bound.
- Music DNA is backend/profile-bound.
- Discover recommendations are backend-owned.
- Track Insight, Lyrics Explain, Artist/Album Insight and VibeCast should publish through backend-owned contracts.
- Client differences are rendering/capability differences, not product logic forks.
- Privacy and export behavior can be enforced centrally.

## Alternatives considered

### Client-owned intelligence

Rejected. It makes consistency, privacy and cross-device continuity too difficult.

### Cloud-only intelligence

Rejected. DJConnect Community should remain local-first and useful without mandatory cloud.

### Provider-owned intelligence only

Rejected. Provider APIs can provide metadata, but DJConnect should own its own profile, insight and response model.

## Affected repositories

- `pcvantol/djconnect`
- `pcvantol/djconnect-app`
- `pcvantol/djconnect-windows`
- `pcvantol/djconnect-pi`
- `pcvantol/djconnect-esp32`
- `pcvantol/djconnect-api`

## Related documents

- `DJCONNECT_CONSTITUTION.md`
- `DOMAIN_MODEL.md`
- `ARCHITECTURE_PRINCIPLES.md`
- `CLIENT_CAPABILITY_MATRIX.md`
