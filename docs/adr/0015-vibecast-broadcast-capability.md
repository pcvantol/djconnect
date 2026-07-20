# ADR-0015: VibeCast is a Broadcast Capability

## Status

Accepted

## Date

2026-07-20

## Context

VibeCast must support shared DJ Session experiences across TV, browser,
Chromecast, Raspberry Pi, desktop and guest surfaces without turning
DJConnect into a video-streaming or server-rendered-video product.

## Decision

VibeCast is the Broadcast Capability of an active DJ Session. The
server-owned Broadcast Engine publishes an event-driven Broadcast Feed; one
Universal Session Receiver consumes that Feed and renders it locally in TV,
Guest, Desktop, Browser, Pi and Chromecast modes.

The Feed is capability- and privacy-scoped. It is not video streaming, does
not server-render visual output and does not expose Profile data unless the
active session policy permits it.

## Consequences

- Shared renderers share one feed contract while retaining local presentation.
- VibeCast is not an Apple-only feature or a standalone product.
- Receiver implementation must not recreate session planning or persist
  Profile state.
- This decision creates no transport, token, endpoint or rendering
  implementation.

## Alternatives considered

### Video streaming

Rejected. It adds unnecessary media infrastructure and prevents native local
rendering.

### Separate VibeCast applications per surface

Rejected. It duplicates contracts and fragments the shared-session model.

### Server-rendered visual output

Rejected. Rendering belongs to receivers; the server owns the session events.

## Affected repositories

- `pcvantol/djconnect`
- `pcvantol/djconnect-app`
- `pcvantol/djconnect-windows`
- `pcvantol/djconnect-pi`
- `pcvantol/djconnect-website`

## Related documents

- `DJCONNECT_V4_ARCHITECTURE.md`
- `DOMAIN_MODEL.md`
- `ARCHITECTURE_PRINCIPLES.md`
- `CLIENT_CAPABILITY_MATRIX.md`
