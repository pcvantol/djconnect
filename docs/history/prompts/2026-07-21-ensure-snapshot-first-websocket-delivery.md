# Prompt History: Ensure Snapshot-First WebSocket Delivery

**Prompt ID:** `G2-PRODUCT-PR270-001`
**Prompt Title:** Ensure Snapshot-First WebSocket Delivery
**Generation:** 2
**Engineering Program:** DJConnect Product Development
**Branch:** `codex/websocket-delivery-correctness`
**Commit:** `3c636fe0d67af62eccf63d518167774cee9f85f6`
**Pull Request:** [#270](https://github.com/pcvantol/djconnect/pull/270)
**Decision:** `TRANSPORT_CELL_3_SNAPSHOT_FIRST_DELIVERY_CURRENT`
**Execution Date:** 2026-07-21
**Created:** 2026-07-21
**Updated:** 2026-07-21

## Objective

Complete Transport Cell 3 delivery correctness during owner WebSocket
subscription setup: register one pending callback before the canonical snapshot
is built, send that snapshot first and activate buffered setup-time events only
after the successful initial result.

## Repository evidence

- GitHub records PR #270 merged on 2026-07-21 at the commit above.
- The merged PR description is the preserved canonical scope and validation
  reference because the original prompt archive was absent at reconciliation.

## Validation

- Focused transport, Broadcast and authorization tests: 112 passed, 12
  subtests passed.
- Full pytest and Ruff passed.
- `git diff --check`.

## Known limitations

No replay, cursor, sequence, delta, acknowledgement, duplicate suppression,
reconnect protocol, endpoint, command, event type, Runtime, DJ Intelligence,
Session Flow, playback or renderer behaviour changed.

## Deferred work

Session Flow sequence, cursor/watermark, HTTP Flow delta, replay, ordering
beyond setup, duplicate/out-of-order handling, reconnect, Universal Receiver
HTTP, receiver audience-signal resolution, Session Detail and granular HTTP
Session resources remain separate work.

## Recommended next prompt

Synchronize current main and select one explicitly bounded transport or
maturity cell; no Transport Cell 4 is automatically authorized.
