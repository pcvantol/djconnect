# Prompt History: Finalization Branch Cleanup

**Pull Request:** [#307](https://github.com/pcvantol/djconnect/pull/307)
**Merge Commit:** `03a55fccc2f44e2646d813bb0bf6e4ab49e02b3d`
**Decision:** `FINALIZATION_BRANCH_DELTA_EXCEPTION_ESTABLISHED`

The canonical Workspace Cleanup policy now permits a stale Finalization branch
only when every branch-only commit passes the deterministic reverse-apply delta
check against clean canonical main. Failed checks preserve the branch.
