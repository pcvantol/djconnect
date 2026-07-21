# Prompt History: Rolling Session Horizon Runtime Model

**Pull Request:** [#315](https://github.com/pcvantol/djconnect/pull/315)
**Merge Commit:** `6a22b0814fcfcd277a9a854fc78b5a28ed04eadd`
**Decision:** `ROLLING_SESSION_HORIZON_RUNTIME_CURRENT`

PR #315 adds the Planner-owned ephemeral Horizon model, empty provider-neutral
upcoming playback projection and deterministic invalidation generation. It
does not add planning, replanning, persistence, transport or provider logic.
