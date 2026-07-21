# Session Flow Recovery Architecture

**Status:** Accepted architecture amendment
**Owner:** DJConnect Product Development
**Scope:** Canonical recovery contracts for an active DJ Session; no production,
transport, API or Runtime implementation

## Decision

Recovery has two distinct concerns and therefore two distinct canonical
contracts:

1. **Session Flow revision** is a Planner-owned domain identity for the
   canonical version of the active Session Flow.
2. **Broadcast delivery cursor and snapshot watermark** are Broadcast-owned,
   scoped delivery identities for an authorized projection of that active
   Session.

Neither concern belongs to a WebSocket, HTTP adapter, renderer, Profile or
Music Backend. Transport adapters carry the contracts; they do not define
them.

## Rationale

The existing Session Flow has a stable `flow_id` and immutable DJ Moments have
stable `moment_id`s, but neither identifies which canonical Flow version a
renderer has applied. Existing Broadcast events have `event_type`, `session_id`
and a payload, but no ordered delivery identity or bounded event history.
Consequently, a fresh snapshot is currently the only correct reconnect path.

Reconnect with a fresh snapshot is transport-only and remains valid without
this amendment. Lossless incremental recovery is not transport-only: it must
refer to the canonical semantic changes of a Session Flow and distinguish them
from protocol delivery. The contracts below make that boundary explicit.

## Session Flow revision

A **Session Flow revision** is a non-negative, monotonically increasing,
Runtime-scoped integer associated with exactly one `flow_id`.

- The Planner owns advancement when it publishes a new canonical Flow state.
- It describes semantic Flow state, not an HTTP response, a WebSocket frame,
  a renderer cache or a playback position.
- A Flow mutation carries its resulting revision. A Flow snapshot carries its
  current revision.
- `flow_id` plus `flow_revision` identifies the version to which a renderer's
  Flow view corresponds.
- A future **Flow delta** is a canonical Session Flow change from one known
  revision to a later revision, or an explicit `snapshot_required` result.
- A Flow revision is not a global sequence and does not order audience, mood,
  lifecycle or other non-Flow Broadcast publications.

The Runtime creates this identity with the Planner's Flow and destroys it with
the Runtime. It is never stored in Profile history, Music DNA, a provider or a
renderer, and does not survive a new Session or Runtime destruction.

## Broadcast delivery identity

A **Broadcast delivery cursor** is an opaque, server-issued position in one
authorized Broadcast projection. A **snapshot watermark** is the corresponding
last included delivery position in a returned Broadcast snapshot.

- Broadcast owns their issuance, validation and bounded retention.
- They are scoped at least to the active `session_id`, Runtime lifetime and
  visibility/authorization projection. A cursor for one projection must never
  expose or resume another projection.
- Their internal representation is deliberately unspecified. A transport must
  treat a cursor as opaque and must never synthesize one from timestamps,
  Moment IDs, Flow revisions or socket state.
- A watermark is not a standalone Session identity. The tuple of active
  `session_id`, `flow_id`, `flow_revision` and authorized Broadcast watermark
  is sufficient to describe a snapshot's recovery boundary.

The previously proposed concepts therefore classify as follows:

| Remaining gap | Canonical owner | Decision |
| --- | --- | --- |
| Flow revision | Session Flow / Planner | Required domain concept. |
| Flow delta | Session Flow / Planner | Required domain projection, based on Flow revision. |
| Broadcast delivery sequence | Broadcast | Required only for future ordered replay delivery. It is not a Session Flow sequence. |
| Snapshot watermark | Broadcast | Required only when Broadcast replay is implemented. |
| Recovery cursor | Broadcast | Required only when incremental recovery is implemented; opaque and scoped. |
| Bounded event history / replay window | Broadcast | Required only when replay is implemented; Runtime-scoped. |
| Recovery token | None | Rejected. A cursor is not a credential; every recovery request retains normal authorization. |

## Replay and recovery

**Broadcast replay** replays authorized, renderer-safe Broadcast publications
after a valid Broadcast cursor. It does not replay raw Runtime state, provider
observations, Planner internals or unscoped events. An individual DJ Moment is
not itself a replay protocol; it can appear inside a replayed Broadcast event.

**Flow delta** is different. It communicates canonical Flow changes from a
known Flow revision. It is not a replay of every Broadcast event and cannot
replace Broadcast replay for audience, mood or Runtime lifecycle projections.

Replay is bounded and exists only while the active Runtime exists. It does not
survive Session restart, Runtime destruction or a changed authorization scope.
On an absent, invalid, expired, out-of-window or scope-mismatched cursor, or
when the requested change cannot be represented safely, the server returns
`snapshot_required`; the renderer abandons local recovery and applies a fresh
authorized snapshot. A rejected active Session likewise returns the renderer
to its idle state.

## Ownership and interaction

```text
Planner
  -> Flow revision and canonical Flow delta
  -> Session Flow
  -> Broadcast projection
  -> Broadcast cursor / watermark / bounded replay window
  -> HTTP, WebSocket or future transport adapter
  -> Renderer
```

- **Runtime** orchestrates creation, publication and disposal but never owns a
  client cursor or client delivery state.
- **Planner / Session Flow** owns semantic ordering and Flow revisions.
- **DJ Moment Engine** continues to create immutable Moments; it neither
  sequences delivery nor mutates a published Moment for recovery.
- **Broadcast** distributes scoped projections and owns delivery ordering,
  watermarking and any bounded replay log.
- **Transport** authenticates, requests a snapshot/delta/replay and serializes
  the server result. It cannot decide Session meaning.
- **Renderers** keep only disposable recovery state and must accept a fresh
  snapshot as authoritative.

## Persistence and privacy

All recovery identities and retained publications are ephemeral Runtime state.
They are not Session History, Session Memory, Music DNA, a chat history or
Music Backend state. Replay and delta apply the same owner, visibility and
privacy filtering as an initial Broadcast snapshot; no cursor may widen access
to `owner_only` content or raw provider data.

## Recommended implementation order

1. Add Flow revision and a bounded, Runtime-scoped canonical Flow-change
   journal without a new transport surface.
2. Add a scoped Broadcast delivery sequence, snapshot watermark and bounded
   replay log without changing Planner or Moment semantics.
3. Add authorized WebSocket recovery using an opaque Broadcast cursor.
4. Add authorized HTTP Flow delta using `flow_id` and Flow revision.
5. Add recovery validation for cursor expiry, scope changes, Runtime disposal,
   snapshot fallback and reconnect ordering.

Each step remains a separate bounded capability. HTTP delta must not be
implemented before the Flow revision contract exists, and replay must not be
implemented before scoped Broadcast delivery identity and retention exist.

## Explicit non-goals

This amendment creates no sequence field, Flow revision field, cursor,
watermark, replay log, recovery endpoint, WebSocket acknowledgement, HTTP
delta, persistence model or renderer behaviour. It does not alter Runtime,
Planner, Knowledge Engine, DJ Moment Engine, Session Flow, Broadcast or
transport implementation.

## Risks

- Treating a Broadcast delivery sequence as Session history would leak
  transport mechanics into the domain and confuse scoped projections.
- Treating a Flow revision as a complete Broadcast cursor would omit valid
  non-Flow publications.
- Persisting recovery state beyond Runtime disposal would violate the
  ephemeral Runtime boundary and risk privacy leakage.
- Making a cursor a credential would bypass existing owner authorization.

These risks require contract-level tests before any implementation begins.
