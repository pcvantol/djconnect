# ADR-0000: Why DJConnect exists

## Status

Accepted

## Date

2026-07-09

## Context

DJConnect needs a clear product identity before lower-level technical decisions can stay coherent across repositories.

DJConnect is not a Spotify clone. Spotify Direct is one Music Backend, not the product boundary.

DJConnect is not a Music Assistant frontend. Music Assistant can be an adapter, but DJConnect owns its own AI DJ experience, profile model and client contracts.

DJConnect is not just a Home Assistant integration. Home Assistant is the first local-first runtime for Community, but the platform includes clients, firmware, public release surfaces, a central trust boundary and future optional cloud surfaces.

DJConnect is not just an AI chatbot. Ask DJ is part of a broader AI music platform centered on playback, context, rooms, devices, profiles and durable intelligence.

DJConnect is an AI music platform centered on an AI DJ experience.

## Decision

DJConnect exists to make music playback feel more alive, intelligent, personal and room-aware.

Home Assistant is the first local-first runtime, not the product boundary.

Music Backends are adapters.

Clients are renderers and control surfaces.

DJConnect Profiles are identity and personalization boundaries.

## Consequences

Product decisions are evaluated by whether they strengthen the AI DJ experience.

Community must feel complete and useful as a local-first product.

Personal may add profile-level personalization, portability and richer intelligence without making Community feel like a trial or incomplete mode.

Cloud is an optional and future extension, not a requirement for local-first value.

Repository boundaries should protect this product model: backends adapt playback, clients render and control, profiles own personal state, and backend services own durable intelligence.

## Alternatives considered

### Spotify-only product

Rejected. It would make DJConnect dependent on one provider and weaken the Music Backend model.

### Generic Home Assistant media remote

Rejected. It would understate the AI DJ, profile, insight and room-aware product direction.

### Cloud-only AI assistant

Rejected. DJConnect Community must have local-first value without mandatory cloud.

### Client-specific feature silos

Rejected. They would fragment behavior, privacy controls, profiles and intelligence across clients.

## Affected repositories

- `pcvantol/djconnect`
- `pcvantol/djconnect-app`
- `pcvantol/djconnect-windows`
- `pcvantol/djconnect-pi`
- `pcvantol/djconnect-esp32`
- `pcvantol/djconnect-api`
- `pcvantol/djconnect-website`
- `pcvantol/djconnect-firmware`
- `pcvantol/djconnect-app-releases`
- `pcvantol/djconnect-pi-releases`

## Related documents

- `DJCONNECT_CONSTITUTION.md`
- `PRODUCT_VISION.md`
- `DESIGN_PRINCIPLES.md`
- `ARCHITECTURE_PRINCIPLES.md`
- `DOMAIN_MODEL.md`
- `FOUNDATION_INDEX.md`
