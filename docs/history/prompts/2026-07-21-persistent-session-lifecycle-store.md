# Prompt History: Persistent Session Lifecycle Store

**Prompt ID:** `G2-PRODUCT-PR298-001`
**Pull Request:** [#298](https://github.com/pcvantol/djconnect/pull/298)
**Merge Commit:** `dca7c85b61a3e001c3b642bd33536b9f4ca35455`
**Decision:** `PERSISTENT_SESSION_LIFECYCLE_CURRENT`
**Execution Date:** 2026-07-21

## Delivered

Profile-owned Session identity, v3 schema migration, owner-checked terminal
idempotency and the bounded `OPENING → ACTIVE → ENDED/INTERRUPTED` lifecycle.
Runtime start and normal end use the existing HA-owned persistence boundary.

## Deferred

Startup reconciliation, re-bootstrap, historical projections, retention,
backup/restore, export/import, Flow and Broadcast persistence remain separate
capabilities.
