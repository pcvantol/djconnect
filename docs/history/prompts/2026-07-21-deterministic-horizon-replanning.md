# Prompt History: Deterministic Horizon Replanning

**Pull Request:** [#330](https://github.com/pcvantol/djconnect/pull/330)
**Merge Commit:** `881619f15a845d87fa2951704b0b871282a6c6dd`

PR #330 adds bounded deterministic replanning of runtime-scoped Planned
Intents. Equivalent inputs are a no-op; valid commitments remain stable and
obsolete provisional intents are superseded without persistence or transport.
