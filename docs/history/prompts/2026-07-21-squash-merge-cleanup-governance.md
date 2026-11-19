# Prompt History: Squash-Merge Cleanup Governance

**Pull Request:** [#306](https://github.com/pcvantol/djconnect/pull/306)
**Merge Commit:** `bed2c32dbfc64b4705f3c0498c6c80b822b5451a`
**Decision:** `SQUASH_MERGE_CLEANUP_EXCEPTION_ESTABLISHED`

The canonical Workspace Cleanup policy now permits a completed squash-merged
implementation branch only when merged-PR, absent-remote, clean-workspace and
unpublished-work evidence is present and `git cherry -v` reports only
patch-equivalent commits.
