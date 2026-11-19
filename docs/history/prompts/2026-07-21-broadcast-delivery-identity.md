# Prompt History: Broadcast Delivery Identity

**Prompt ID:** `G2-PRODUCT-PR278-001`
**Prompt Title:** Recovery Cell 2 — Broadcast Delivery Identity
**Generation:** 2
**Engineering Program:** DJConnect Product Development
**Branch:** `codex/broadcast-delivery-identity`
**Commit:** `fe36439bad56792e520fb21df706bd64028c065e`
**Pull Request:** [#278](https://github.com/pcvantol/djconnect/pull/278)
**Decision:** `BROADCAST_DELIVERY_IDENTITY_CURRENT`
**Execution Date:** 2026-07-21
**Created:** 2026-07-21
**Updated:** 2026-07-21

## Objective

Implement Recovery Cell 2: Broadcast-owned Delivery Sequence, snapshot
watermark and a bounded Runtime-scoped Replay Log, without a cursor, replay
protocol, Flow delta or reconnect capability.

## Repository evidence

- GitHub records PR #278 merged on 2026-07-21 at the commit above.
- Every Broadcast publication receives exactly one strictly monotonic Delivery
  Sequence. Snapshot and subscription establishment do not advance it.
- Broadcast snapshots carry their authorized projection boundary as a snapshot
  watermark. The bounded immutable Replay Log retains one internal entry per
  publication and is removed with the Session Runtime.
- Planner-owned Flow Revision and Change Journal remain semantic identities and
  are independent of Broadcast delivery identity.

## Validation

- Development-host desired-state verification: `MATCH`.
- Focused Runtime, Broadcast snapshot, WebSocket and playback-observation
  regression: 116 passed, 12 subtests passed.
- Required GitHub CI validation passed, including tests, Ruff, HACS, Hassfest,
  dependency audit, Bandit, Semgrep, CodeQL and Trusted Delivery.
- Ruff and `git diff --check` passed.

## Known limitations

The Replay Log is internal infrastructure only. There is no recovery cursor,
cursor validation, replay query/service/transport, HTTP Flow delta, WebSocket
recovery, reconnect continuation, acknowledgement, duplicate suppression,
out-of-order correction, persistence, cross-Session replay or Universal
Receiver recovery expansion.

## Deferred work

The next recovery cell may add authorized WebSocket recovery using an opaque
Broadcast cursor only under a separately bounded authorization, replay-window
and snapshot-required contract. Fresh snapshots remain the only public recovery
fallback.

## Recommended next prompt

Synchronize current main, verify this reconciled baseline, then define or
select only the bounded authorized WebSocket recovery cell using an opaque
Broadcast cursor.
