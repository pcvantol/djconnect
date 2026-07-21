# Prompt History: Persistent Session Architecture

**Prompt ID:** `G2-PRODUCT-PR286-001`
**Prompt Title:** Persistent Session Architecture
**Generation:** 2
**Engineering Program:** DJConnect Product Development
**Branch:** `codex/persistent-session-architecture`
**Commit:** `fc68f98faf21c2974afe144ad738c992c9e30c9a`
**Pull Request:** [#286](https://github.com/pcvantol/djconnect/pull/286)
**Merge Commit:** `8828179ae042eaa672eb6af065dcefbe323ce79a`
**Decision:** `PERSISTENT_SESSION_ARCHITECTURE_ACCEPTED`
**Execution Date:** 2026-07-21
**Created:** 2026-07-21
**Updated:** 2026-07-21

## Objective

Define the first Persistent Session Architecture amendment: a durable,
Profile-owned DJ Session lifecycle aggregate with renderer-safe historical
DJMoment projections, while preserving the existing ephemeral Session Runtime
and Broadcast contracts. The increment is architecture and roadmap work only.

## Repository evidence

- PR #286 merged into current `main` on 2026-07-21.
- The persistent Session owns durable lifecycle truth and authorized historical
  projections; Runtime, Planner working state, Performance Memory, Broadcast
  delivery/recovery state, temporary audio and Playback Instance Identity
  remain ephemeral.
- The minimal lifecycle is `OPENING -> ACTIVE -> ENDED`, with either open state
  able to close as `INTERRUPTED`. `RESUMED` is a future lifecycle event, not a
  durable state.
- Startup must use fresh evidence for any future re-bootstrap; without the
  gated Continue Stage 2 observation contract it closes an open Session as
  interrupted and never restores a Python Runtime object.

## Validation

- Development-host desired-state verification: `MATCH`.
- Full local unit suite: 1240 passed, 7 skipped.
- Ruff and `git diff --check` passed.
- GitHub tests, Ruff, HASSfest, dependency audit, Bandit, Semgrep, CodeQL,
  Trusted Delivery and governance checks passed.
- A first HACS action run reported an invalid unchanged `hacs.json`; the
  focused re-run passed without repository changes, establishing it as an
  external non-deterministic validation failure rather than a PR defect.

## Known limitations

This architecture adds no SQLite service, schema, migrations, Session writes,
restart recovery, projection storage, retention job, backup/restore, import or
export implementation, TTS replay, providers, API, Runtime or renderer work.

## Deferred work

The approved sequence is Persistence Foundation; Persistent Session lifecycle
store; startup reconciliation; historical projections; retention; backup and
restore; versioned export/import; on-demand replay voice; autonomous room voice;
and renderer adoption. Continue Stage 2 re-bootstrap remains separately gated.

## Recommended next prompt

After this Finalization merge restores `MERGED_RECONCILED`, run a fresh
Pre-Flight for **Persistence Foundation** only. It may create the DJConnect
storage service, schema metadata, migration runner, integrity checks and test
harness, but no Session writes.
