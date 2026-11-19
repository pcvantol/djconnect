# Prompt History: Authorized WebSocket Recovery

**Prompt ID:** `G2-PRODUCT-PR284-001`
**Prompt Title:** Recovery Cell 4 — Authorized WebSocket Recovery
**Generation:** 2
**Engineering Program:** DJConnect Product Development
**Branch:** `codex/authorized-websocket-recovery`
**Commit:** `471dfba8a3d02f4348c648995909ce3f2c5e828d`
**Pull Request:** [#284](https://github.com/pcvantol/djconnect/pull/284)
**Decision:** `AUTHORIZED_WEBSOCKET_RECOVERY_CURRENT`
**Execution Date:** 2026-07-21
**Created:** 2026-07-21
**Updated:** 2026-07-21

## Objective

Implement Recovery Cell 4: owner-authorized WebSocket recovery using the
existing opaque Broadcast Recovery Cursor and bounded Runtime-scoped Replay
Log. No HTTP recovery, Flow delta, persistence, cross-Session recovery,
provider work or renderer-specific behaviour is included.

## Repository evidence

- GitHub records PR #284 merged on 2026-07-21 as
  `01e0756c3745a57b63857d71ece57cbeabfbbaf4`; its implementation branch is
  removed from the remote.
- The authenticated owner recovery command accepts only the active Session and
  existing opaque cursor. The cursor remains a Broadcast delivery boundary,
  never a credential or source of internal delivery data.
- Broadcast replays only retained renderer-safe entries after a valid cursor.
  A cursor that is no longer retained or a replay that cannot be made
  continuous returns `snapshot_required` with a fresh owner snapshot.
- Runtime disposal releases the cursor and bounded Replay Log. Recovery cannot
  cross Session or Runtime boundaries.

## Validation

- Development-host desired-state verification: `MATCH`.
- Focused Session Runtime, Broadcast snapshot and WebSocket tests: 114 passed,
  12 subtests passed.
- Full unit suite and Ruff passed locally.
- Initial CI identified stale transport capability and client-contract
  expectations. The bounded correction at `471dfba` updated those contracts;
  its GitHub tests, Ruff, HACS, Hassfest, dependency audit, Bandit, Semgrep,
  CodeQL and Trusted Delivery checks passed.
- `git diff --check` passed.

## Known limitations

Recovery is owner-authorized WebSocket replay only. There is no HTTP recovery
or Flow delta, public replay/query API, acknowledgement, duplicate or
out-of-order correction, persistent replay, cross-Session recovery, Universal
Receiver recovery or renderer-specific recovery policy.

## Deferred work

Future recovery work must remain separately authorized. The next candidate is
an authorized HTTP Flow delta using existing `flow_id` and Flow Revision, with
its own Pre-Flight, ownership review and bounded validation. Fresh owner
snapshots remain the mandatory fallback.

## Recommended next prompt

Synchronize current main, verify this Finalization merged as
`MERGED_RECONCILED`, then run a fresh Pre-Flight before selecting one bounded
next capability.
