# Prompt History: Persistent Session Startup Reconciliation

**Pull Request:** [#300](https://github.com/pcvantol/djconnect/pull/300)
**Merge Commit:** `822468e10527aa07895a802c99fbcde7eeccd98c`
**Decision:** `PERSISTENT_SESSION_STARTUP_RECONCILIATION_CURRENT`

The capability deterministically transitions durable `OPENING` and `ACTIVE`
Sessions to `INTERRUPTED` during startup. It does not restore Runtime state,
inspect a music provider, or implement Continue Stage 2.
