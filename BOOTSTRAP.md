# DJConnect Repository Bootstrap

**Status:** Canonical repository onboarding

Every engineering prompt starts with repository synchronization. Run these
commands from the intended repository and stop if either fails:

```sh
git switch main
git pull --ff-only
```

`REPOSITORY_SYNCHRONIZATION.md` defines the canonical verification contract.

Immediately verify the checked-out branch, `HEAD`, upstream tracking branch,
fast-forward state, working-tree cleanliness and repository cleanliness. Do
not continue if any check fails. Then verify the predecessor pull request from
objective GitHub and Git evidence: merge state and commit, containment in
current `main`, and archived Prompt History. Do not use prior conversations as
a substitute.

Classify the engineering lifecycle using `ENGINEERING_METHOD.md`. If a verified
merged predecessor has rolling records still at its reviewable freeze point,
the expected state is `MERGED_UNRECONCILED`: only the dedicated Finalization
increment may reconcile the four rolling records named below. Never rewrite
Prompt History. Production implementation may begin only when Repository State
is `MERGED_RECONCILED`, Workspace State is `WORKSPACE_READY` and the
`GO` decision in `PROMPT_INITIALIZATION.md` is recorded. `WORKSPACE_READY` is
the independently verified result of the completed capability's local-only
cleanup; its exact procedure is canonical in `ENGINEERING_METHOD.md`. Other
unresolved merge, repository or workspace inconsistencies are terminal.
Workspace Cleanup supports topological merge completion and the approved
squash-merge patch-equivalence exception.

Only after required reconciliation, read the current repository in the
following order:

```text
BOOTSTRAP.md
  -> ENGINEERING_STATUS.md
  -> REPOSITORY_STATUS.md
  -> MANAGEMENT_SUMMARY.md
  -> ROADMAP_INDEX.md
  -> current active roadmap
  -> current active backlog
  -> PROMPT_INDEX.md
  -> docs/history/prompts/ only when historical context is required
```

The records have distinct responsibilities:

| Record | Responsibility |
| --- | --- |
| `BOOTSTRAP.md` | Repository onboarding and reading order. |
| `ENGINEERING_STATUS.md` | Operational engineering handoff, current increment, deferred work and recommended next prompt. |
| `REPOSITORY_STATUS.md` | Objective repository state. |
| `MANAGEMENT_SUMMARY.md` | Executive engineering summary. |
| `ROADMAP_INDEX.md` | Canonical roadmap navigation. |
| `PROMPT_INDEX.md` | Prompt lifecycle and navigation. |
| `docs/history/prompts/` | Immutable engineering history, never current-state authority or rewritten after merge. |

After reading, perform the implementation-reality check required by
`AI_SESSION_INITIALIZATION.md`. If reality differs from planning, stop and
update planning first. Continue with local `AGENTS.md`, applicable foundation
and Meta Engineering guidance only as required by the selected increment.

`BOOTSTRAP_CODEX_SESSION.md` remains the platform-wide supplemental bootstrap;
this file is the canonical repository-state entry point.
