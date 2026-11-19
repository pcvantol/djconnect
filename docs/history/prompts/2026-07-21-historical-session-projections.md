# Prompt History: Historical Session Projections

**Pull Request:** [#302](https://github.com/pcvantol/djconnect/pull/302)
**Merge Commit:** `0a224834aa685a3d57788e9aaf70d515a502cc0c`
**Decision:** `HISTORICAL_SESSION_PROJECTIONS_CURRENT`

Historical Session and DJMoment projections are immutable, owner-scoped and
renderer-safe. Runtime, Flow, Broadcast, provider payloads and audio remain
ephemeral and excluded.
