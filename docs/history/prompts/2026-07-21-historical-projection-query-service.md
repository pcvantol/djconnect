# Prompt History: Historical Projection Query Service

**Prompt ID:** `historical-projection-query-service`
**Title:** Track A – Persistent Session Capability 5: Historical Projection Query Service
**Generation and engineering program:** Generation 2 / DJConnect Product Development
**Branch:** `codex/historical-projection-query-service`
**Commit:** `8941b83ae7d3b982c2685bb03749c34bcf69cee9`
**Pull Request:** [#309](https://github.com/pcvantol/djconnect/pull/309)
**Merge Commit:** `11ba4f76411f04aaba4bdb6f8e55988c7c14eb04`
**Decision:** `HISTORICAL_PROJECTION_QUERY_SERVICE_CURRENT`
**Executed:** 2026-07-21

## Outcome

PR #309 adds the canonical, transport-independent application query boundary
for immutable historical Session and DJMoment projections. The query service
uses the storage repository for reads, enforces owner-only authorization and
current owner-only Moment visibility, rejects unsupported projection versions,
and preserves canonical Session and Moment ordering. It returns only frozen,
renderer-safe projection models.

No HTTP, WebSocket, client browser, replay, search, filtering, pagination,
favorites, analytics, retention, export or renderer behaviour was added.

## Validation

- Current development-machine desired-state verification: `MATCH`.
- Focused query and persistent-session regression tests: 11 passed.
- Full unit suite: 1,266 passed, 7 skipped.
- Ruff check and `git diff --check` passed.
- GitHub merge evidence confirms PR #309 is merged and its remote branch is
  absent.

## Known limitations and deferred work

The current visibility policy is owner-only. Household/shared Session and
Moment visibility require a separate capability. Retention, cleanup,
backup/restore, export/import, replay and transport/client consumption remain
separate increments.

## Recommended next prompt

Run a fresh Pre-Flight from the reconciled baseline before selecting the next
bounded Track A capability, currently retention and cleanup.
