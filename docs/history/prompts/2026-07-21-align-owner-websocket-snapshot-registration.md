# Prompt History: Align Owner WebSocket Snapshot Registration

**Prompt ID:** `G2-PRODUCT-PR268-001`
**Prompt Title:** Align Owner WebSocket Snapshot Registration
**Generation:** 2
**Engineering Program:** DJConnect Product Development
**Branch:** `codex/align-owner-websocket-snapshot`
**Commit:** `00f71025bbbea5ca9171bb70f65b54c3ed894ce5`
**Pull Request:** [#268](https://github.com/pcvantol/djconnect/pull/268)
**Decision:** `TRANSPORT_CELL_2_OWNER_WEBSOCKET_ALIGNMENT_CURRENT`
**Execution Date:** 2026-07-21
**Created:** 2026-07-21
**Updated:** 2026-07-21

## Objective

Complete Transport Cell 2 internal application-service and subscription
alignment. Keep the pure owner snapshot query as the sole initial owner
WebSocket snapshot source, then register live delivery without building an
unused second snapshot.

## Repository evidence

- The predecessor baseline was reconciled by PR #267 at
  `58cdb37c6ad32bae16e000e67481b75c0731806b`.
- GitHub records PR #268 merged on 2026-07-21 at the commit above.
- The merged PR description is the preserved canonical scope and validation
  reference because the original prompt archive was absent at reconciliation.

## Outcome

The explicit registration-without-snapshot operation preserves the existing
snapshot-returning subscription contract for all other consumers. Owner HTTP
behaviour and WebSocket command, response and event schemas are unchanged. If
initial WebSocket response delivery fails, the registered callback is released.

## Validation

- Focused Broadcast/HTTP/WebSocket/Runtime tests: 104 passed, 12 subtests
  passed.
- Full pytest and Ruff passed.
- `git diff --check`.

## Known limitations

No HTTP route, event type, Runtime, Planner, Knowledge Engine, DJ Moment
Engine, Session Flow, maturity, sequence, replay, ordering, reconnect,
Receiver or renderer behaviour changed.

## Deferred work

Session Flow sequence, cursor/watermark, HTTP delta, replay, ordering,
duplicate/out-of-order handling, reconnect, Universal Receiver HTTP access,
receiver audience-signal resolution and standalone Session resources remain
separate work.

## Recommended next prompt

Synchronize current main and select one explicitly bounded transport or
maturity cell; no Transport Cell 3 is automatically authorized.
