# ADR-0014: DJ Session Runtime is the v4 active-session boundary

## Status

Accepted

## Date

2026-07-20

## Context

DJConnect has established the DJ Session as its primary product experience,
but persistent Profile state, active listening context and client presentation
still need a single ownership model. Treating a session as another Profile,
giving it a Music Backend, or distributing active planning across clients would
mix durable identity with temporary orchestration.

## Decision

DJConnect v4 introduces a server-owned, ephemeral DJ Session Runtime for every
active DJ Session. A Runtime owns Playback Context, Session Planner,
Conversation Engine, Session Memory, Session Flow, Broadcast Engine, Audience
Signals and Runtime State.

Profiles remain the only owner of persistent identity, exactly one Music
Backend binding, Music DNA, settings, preferences, conversation history and
session history. Music Backends never belong to Session Runtimes. On session
end, a Runtime is discarded and writes back only permitted durable outcomes to
its owning Profile.

The Session Planner continuously plans approximately the next fifteen minutes.
Its Session Flow—not the provider queue—is the primary DJConnect expression of
what the DJ plans next. Provider queues remain backend-owned advanced views.

## Consequences

- Clients cannot store Profile state or recreate Planner behaviour.
- Runtime, event, privacy and lifecycle contracts must precede implementation.
- Existing components should be reused or refactored to their canonical owner;
  v3 compatibility layers and migrations are out of scope because v3 was not
  publicly released.
- This decision creates no implementation API, storage schema or protocol.

## Alternatives considered

### Profile as the active-session owner

Rejected. Persistent identity and short-lived session state have different
lifecycles and privacy obligations.

### Session-owned Music Backend

Rejected. It breaks the Profile ownership model and makes provider identity
part of a temporary listening experience.

### Client-side Planner

Rejected. It fragments orchestration, privacy policy and cross-renderer truth.

## Affected repositories

- `pcvantol/djconnect`
- `pcvantol/djconnect-app`
- `pcvantol/djconnect-windows`
- `pcvantol/djconnect-pi`
- `pcvantol/djconnect-esp32`

## Related documents

- `DJCONNECT_V4_ARCHITECTURE.md`
- `DJ_SESSION_RUNTIME_CONTRACTS.md`
- `DOMAIN_MODEL.md`
- `ARCHITECTURE_PRINCIPLES.md`
- `docs/product/PRODUCT_DEFINITION.md`
