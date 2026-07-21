# Prompt History: Broadcast Recovery Cursor

**Prompt ID:** `G2-PRODUCT-PR280-001`
**Prompt Title:** Recovery Cell 3 — Broadcast Recovery Cursor
**Generation:** 2
**Engineering Program:** DJConnect Product Development
**Branch:** `codex/broadcast-recovery-cursor`
**Commit:** `ccddf5eb72becde8e7de662446e487c43d70b7f3`
**Pull Request:** [#280](https://github.com/pcvantol/djconnect/pull/280)
**Decision:** `BROADCAST_RECOVERY_CURSOR_CURRENT`
**Execution Date:** 2026-07-21
**Created:** 2026-07-21
**Updated:** 2026-07-21

## Objective

Implement Recovery Cell 3: one Broadcast-owned immutable, Runtime-scoped and
owner-scoped Recovery Cursor after a retained Broadcast publication, without a
replay protocol, recovery transport, external API or renderer behaviour.

## Repository evidence

- GitHub records PR #280 merged on 2026-07-21 at the commit above.
- Broadcast issues its internal cursor only after the corresponding publication
  is retained in the bounded Replay Log. The cursor contains the active Session
  identity, delivery position, snapshot watermark and fixed owner scope.
- The cursor is immutable, is never serialized in Broadcast snapshots or events
  and is released with the Session Runtime. Planner semantic Flow Revision and
  Change Journal remain independent.

## Validation

- Development-host desired-state verification: `MATCH`.
- Focused Runtime, Broadcast snapshot, WebSocket and playback-observation
  regression: 116 passed, 12 subtests passed.
- GitHub tests, Ruff, Hassfest, dependency audit, Bandit, Semgrep, CodeQL and
  Trusted Delivery passed. The required HACS check failed before repository
  validation because HACS reported `Repository pcvantol/djconnect not loaded
  properly in HACS`; this merged record preserves that external validation fact.
- Ruff and `git diff --check` passed.

## Known limitations

The Recovery Cursor is internal delivery identity only. There is no public
cursor issuance, validation or transport; no replay query/service/transport;
no HTTP Flow delta; no WebSocket recovery; no reconnect continuation,
acknowledgement, duplicate suppression, out-of-order correction, persistence,
cross-Session replay or Universal Receiver recovery expansion.

## Deferred work

A future bounded capability may add authorized WebSocket recovery using the
existing opaque cursor, with separately specified validation, replay-window,
authorization and `snapshot_required` fallback semantics. Fresh snapshots
remain the only public recovery fallback.

## Recommended next prompt

Synchronize current main, verify this reconciled baseline, then define or
select only the bounded authorized WebSocket recovery capability using the
existing opaque Broadcast cursor.
