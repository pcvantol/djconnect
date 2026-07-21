# Prompt History: Historical Projection Retention and Cleanup

**Prompt ID:** `historical-projection-retention`
**Pull Request:** [#311](https://github.com/pcvantol/djconnect/pull/311)
**Merge Commit:** `3d709a502bf543c4e5ade6352814dcb275848016`
**Decision:** `HISTORICAL_PROJECTION_RETENTION_CURRENT`
**Executed:** 2026-07-21

PR #311 adds the internal, versioned retention policy and bounded transactional
cleanup service for immutable historical Session and DJMoment projections.
Expired orphan and Session-owned Moments are deleted before their Sessions;
remaining projections are never mutated. No scheduler, client/API, backup,
export, replay, search, favorites or Runtime behaviour was added.

Validation: qualified host `MATCH`; focused retention/query/persistence tests;
full unit suite (1,269 passed, 7 skipped); Ruff and diff checks passed.

Deferred: scheduling, manual maintenance controls, backup/restore, export,
favorites, replay and client history remain separate capabilities.
