# Canonical Engineering Prompt Template

Use exactly one complete copy-pasteable prompt in one code block for each
engineering increment. Populate every applicable field from current repository
evidence; do not infer scope from historical chat.

```text
Prompt ID:
Title:
Generation and engineering program:
Engineering mode: Platform Engineering | Product Engineering | Innovation Engineering

PRE-FLIGHT (mandatory; no production change before an explicit GO):
- Repository Synchronization: `git switch main`, then `git pull --ff-only`; stop on failure.
- Current Main Verification: branch, HEAD, upstream, fast-forward status, working tree and repository cleanliness; stop on failure.
- Development Machine Qualification: require current-session readiness evidence where the mutation gate applies; stop on an unsatisfied gate.
- Previous Pull Request Verification: use objective GitHub/Git evidence for predecessor, merge state/commit, current-main containment and archived Prompt History; stop on missing evidence.
- Post-Merge State Classification: determine `REVIEWABLE_FROZEN`, `MERGED_UNRECONCILED` or `MERGED_RECONCILED` under `ENGINEERING_METHOD.md`.
- Repository State Gate: an implementation capability requires `MERGED_RECONCILED`; `MERGED_UNRECONCILED` permits only its dedicated Finalization.
- Workspace State Gate: verify `WORKSPACE_READY` independently from Repository
  State: canonical `main`, synchronized origin, clean tree, the just-completed
  local implementation branch removed and obsolete remote references pruned.
  Either unmet state is `NO-GO`.
- Canonical Repository Read: follow `BOOTSTRAP.md` through active roadmap/backlog and `PROMPT_INDEX.md` only after required reconciliation.
- Implementation Reality Check: inspect existing functionality, validation, qualification and documentation; do not reimplement an existing outcome.
- Capability Evidence: verify the requested capability is pending, the roadmap/architecture/maturity records are current, the validation baseline applies, and no superseding architecture amendment exists.
- Decision: record exactly one `GO` or `NO-GO`. `NO-GO` prohibits production changes.

Objective:
Repository truth verified:
Current roadmap and backlog evidence:

In scope:
Out of scope:
Architecture and ownership constraints:

Acceptance evidence:
Required documentation updates:
Deferred-work handling:

IMPLEMENTATION:
- state the one bounded production capability and its ownership constraints
- list in-scope production changes and focused tests
- state explicit non-goals and deferred work

VALIDATION:
- list capability tests, regression tests and required validation baseline
- include applicable Ruff, architecture, bootstrap and diff validation
- retain objective evidence before review and merge

Finalization checks:
- do not assume predecessor, current increment or repository status from chat
- preceding PR merged and remote branch removed
- after Finalization merges, cleanup identifies only the just-completed local
  implementation branch; it is fully merged, has no unpublished commits and is
  not checked out before non-forced deletion
- for a squash merge, require canonical `git cherry -v` output with only `-`
  patch-equivalent commits, plus merged PR and absent remote evidence
- prior Prompt History archived
- predecessor merge and current-main containment objectively verified
- the merged implementation entered `MERGED_UNRECONCILED`
- synchronized current main and status records verified
- repository clean

Finalization:
- after the implementation merge, create one governance-only Finalization increment
- update ENGINEERING_STATUS, REPOSITORY_STATUS, MANAGEMENT_SUMMARY, PROMPT_INDEX and applicable roadmap/governance records
- create or verify one immutable Prompt History record
- run governance and repository-bootstrap validation
- merge Finalization to restore `MERGED_RECONCILED`, then run Workspace Cleanup
  and issue its deterministic report: current branch, working tree,
  synchronization, completed branch, remote status, local deletion, prune,
  Repository State, Workspace State and `READY`/`NOT READY`
- only `MERGED_RECONCILED` and `WORKSPACE_READY` permit the next
  implementation capability
```

For Innovation Engineering, use `docs/meta/INNOVATION_ENGINEERING.md` in
addition to this template. The prompt must name the bounded learning objective,
use an `innovation/` branch by default, identify only explicitly requested
deployment targets, retain successful-build and basic-smoke evidence, and end
with an Innovation Review outcome of Abandon, Archive, Continue or Promote.
Do not add roadmap, release, qualification or versioning work unless it is
independently required outside the experiment. Promote starts a new normal
Product Engineering increment; it does not silently extend the innovation
scope.
