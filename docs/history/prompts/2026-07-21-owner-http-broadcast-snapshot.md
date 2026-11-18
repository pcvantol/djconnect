# Prompt History: Owner HTTP Broadcast Snapshot

**Prompt ID:** `G2-PRODUCT-PR266-001`
**Prompt Title:** Owner HTTP Broadcast Snapshot
**Generation:** 2
**Engineering Program:** DJConnect Product Development
**Branch:** `codex/http-broadcast-snapshot`
**Commit:** `610be0ba7c776b9c581e7be90237ca6addfe5266`
**Pull Request:** [#266](https://github.com/pcvantol/djconnect/pull/266)
**Decision:** `TRANSPORT_CELL_1_OWNER_HTTP_SNAPSHOT_CURRENT`
**Execution Date:** 2026-07-21
**Created:** 2026-07-21
**Updated:** 2026-07-21

## Objective

Implement exactly one transport cell: an owner-authorized HTTP Broadcast
snapshot. Reuse existing owner device, Profile and active Session
authorization; return only the canonical renderer-safe owner Broadcast
projection; and share one pure snapshot query with the initial owner WebSocket
snapshot.

## Repository evidence

- GitHub records PR #266 merged on 2026-07-21 at the commit above.
- The merged PR description is the preserved canonical scope and validation
  reference because the original prompt archive was absent at reconciliation.

## Validation

- `pytest -q tests/test_session_broadcast_snapshot.py tests/test_websocket_api.py tests/test_session_runtime.py`: 100 passed, 12 subtests passed.
- Full pytest and Ruff passed.
- `git diff --check`.

## Known limitations

No DJ Intelligence, Runtime ownership, Planner, Knowledge Engine, DJ Moment
Engine, Session Flow or playback behaviour changed. The fallback exposes no
delta, cursor, replay or Receiver HTTP interaction. WebSocket ordering,
deduplication and reconnect semantics are unchanged.

## Deferred work

Transport Cell 2 remains separate: make the pure owner snapshot query the sole
initial owner WebSocket snapshot source and register its live callback without
constructing an unused second snapshot. Sequence, replay, ordering and
reconnect work remain later cells.

## Recommended next prompt

After current-main synchronization, implement Transport Cell 2 as one bounded
transport-internal increment.
