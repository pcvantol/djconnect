# DJConnect Engineering Method

**Status:** Canonical operational governance
**Version:** 2.8
**Scope:** Entire DJConnect platform

## Purpose

DJConnect is repository-driven. Current `main` is the canonical engineering
truth. Repository reality always overrides historical plans, prompts and
conversations; neither conversation history nor a prior prompt is required to
continue engineering work.

The repository must remain self-describing: a new AI engineering session can
establish the current state and safely continue from repository contents.

## Engineering modes

The official engineering modes are Platform Engineering, Product Engineering
and Innovation Engineering. `docs/meta/INNOVATION_ENGINEERING.md` defines the
mode boundaries, lightweight Innovation Engineering governance profile,
innovation-branch conventions, deployment constraints, lifecycle, promotion
path and AI operating model. Engineering modes describe execution; the
Generation 2 program model describes portfolio ownership.

Innovation Engineering is part of this method, not an exception to it. Its
lighter governance never bypasses repository integrity, architectural
ownership, security/privacy controls, successful build or basic smoke
validation.

## Mandatory synchronization and operating sequence

```text
Switch to main
  -> Fast-forward synchronize
  -> Verify synchronization
  -> Verify current main
  -> Qualify development machine for repository mutation
  -> Verify previous pull request
  -> Classify post-merge engineering state
  -> Enter Finalization when required
  -> Canonical repository read
  -> ENGINEERING_STATUS
  -> REPOSITORY_STATUS
  -> Management Summary
  -> Roadmap Index
  -> active roadmap and backlog
  -> Prompt Index
  -> Prompt History only when historical context is needed
```

`BOOTSTRAP.md` is the canonical onboarding entry point. The supporting
operational contracts are `AI_SESSION_INITIALIZATION.md`,
`PROMPT_GOVERNANCE.md`, `PROMPT_FINALIZATION.md` and
`REPOSITORY_HYGIENE.md`. `REPOSITORY_SYNCHRONIZATION.md` defines the required
first phase. `PROMPT_INITIALIZATION.md` owns the exact prompt sequence so this
method does not duplicate operational detail.

Every engineering prompt must execute `git switch main` followed by
`git pull --ff-only` before repository reading or planning. It must then verify
the current branch, `HEAD`, upstream tracking branch, fast-forward status,
working tree and repository cleanliness. Synchronization or verification
failure is terminal for that prompt: stop and resolve repository state before
engineering begins.

## Qualified development machine gate

Before Codex accepts or performs an engineering increment that would make a
contentful tracked-repository mutation, the development machine doing that work
must be qualified. The developer must run the local desired-state verification
and provide its current-session readiness summary to Codex. Only
`READY FOR DJCONNECT DEVELOPMENT` with a zero verification exit code satisfies
the gate.

Codex must not infer this qualification from chat history, a previous session,
another machine, or incomplete copied output. Without qualifying evidence it
may inspect repository state read-only, but it must not alter content. The
precise command, required evidence, verdicts and narrow exceptions for
governance/backlog documentation and the onboarding package are canonical in
`BOOTSTRAP_CODEX_SESSION.md`. An exception bypasses only this gate; it never
bypasses synchronization, repository reality, authorization, review or the
rest of this Engineering Method.

## Capability Completion Lifecycle

Every implementation capability follows this mandatory lifecycle:

```text
PRE-FLIGHT
  -> IMPLEMENTATION
  -> VALIDATION
  -> MERGE
  -> FINALIZATION
  -> WORKSPACE CLEANUP
  -> Repository State: MERGED_RECONCILED
  -> Workspace State: WORKSPACE_READY
  -> NEXT CAPABILITY
```

`PRE-FLIGHT` is a mandatory decision gate before any production implementation
change. It verifies synchronized current main, a clean worktree, development
machine qualification where required, the required validation baseline,
predecessor, Repository State and Workspace State, current roadmap/architecture/
maturity evidence, the requested capability's pending status, absence of an
equivalent merged implementation, and absence of a superseding architecture
amendment. It ends with exactly one explicit decision:

- `GO`: the bounded implementation may begin.
- `NO-GO`: production changes are prohibited; resolve or record the blocking
  repository evidence first.

`IMPLEMENTATION` owns only the bounded production change and its focused
tests. `VALIDATION` is a separate mandatory phase before review and merge. It
runs all capability and regression tests plus applicable Ruff, architecture,
bootstrap and diff validation. Implementation does not itself complete the
capability.

`MERGE` is an external governance decision. A merged implementation enters
`MERGED_UNRECONCILED`; this expected temporary state is not a completed
capability. `FINALIZATION` is a separate governance-only increment after the
merge. It reconciles rolling records, immutable Prompt History, applicable
roadmap/governance records and repository bootstrap evidence. After its
governance reconciliation has merged successfully, `WORKSPACE CLEANUP` is
mandatory. The next capability may start only when both Repository State is
`MERGED_RECONCILED` and Workspace State is `WORKSPACE_READY`.

The canonical implementation-prompt structure is `PRE-FLIGHT`,
`IMPLEMENTATION`, `VALIDATION` and `FINALIZATION`, defined by
`docs/governance/PROMPT_TEMPLATE.md`. Prompts may reference that standard
instead of reproducing these rules.

## Engineering lifecycle state

Every increment has one explicit engineering lifecycle state:

| State | Meaning |
| --- | --- |
| `REVIEWABLE_FROZEN` | The scoped pull request exists; implementation is frozen pending human review and merge. |
| `MERGED_UNRECONCILED` | Objective GitHub evidence proves the predecessor merged and current `main` contains it, while rolling records may still describe its freeze point. This is expected, not automatically inconsistent. |
| `MERGED_RECONCILED` | Rolling engineering records reflect the merged repository truth; normal planning and implementation may continue. |

The reviewable pull request is the freeze point. Human merge is external.
`MERGED_UNRECONCILED` permits only the dedicated Finalization increment; no
production implementation may begin from that state. The next capability may
begin only from `MERGED_RECONCILED`. Finalization never rewrites immutable
Prompt History.

## Repository and workspace state

Repository State and Workspace State are independent. Repository State records
the reconciled engineering truth in the repository; Workspace State records
only the safe local development checkout. Repository reconciliation is not a
Workspace Ready responsibility.

Repository State is `MERGED_RECONCILED`: rolling records reflect merged
current-main truth.

Workspace State is `WORKSPACE_READY`: the canonical local workspace is safe
for the next capability.

Before production implementation, both required states are mandatory. If either
state cannot be objectively verified, Pre-Flight is `NO-GO`.

`WORKSPACE_READY` requires canonical `main`, synchronization with `origin/main`,
a clean working tree, removal of the just-completed local implementation branch
and pruned obsolete remote-tracking references.

## Workspace Cleanup

Workspace Cleanup is mandatory after successful Finalization and affects only
the local development workspace. It never changes repository history, discards
uncommitted files, force-deletes a branch or modifies production code. It
concerns exactly the completed capability; unrelated merged branches must not
be enumerated or removed.

Perform this procedure in order:

1. Check out canonical `main`.
2. Synchronize `origin/main` without rewriting history.
3. Verify the working tree is clean.
4. Verify the completed implementation pull request merged successfully and
   is contained in current `main`.
5. Verify its corresponding remote implementation branch has already been
   removed when repository policy requires automatic remote cleanup.
6. Verify the local implementation branch belongs to that completed capability,
   has no unpublished commits and is not checked out. A topologically merged
   branch may then be deleted without force.
7. For a squash-merged branch that is not a Git ancestor of canonical `main`,
   apply the Squash-Merge Cleanup Exception below before deletion.
8. Prune obsolete remote-tracking references.
9. Verify `WORKSPACE_READY`.

If any verification fails, do not delete the branch. Report the blocking
condition and leave Workspace State `NOT_READY` until it is resolved.

The cleanup report is deterministic and records: current branch, working tree,
repository synchronization, completed capability branch, remote branch status,
local branch deletion, remote prune, **stale local branch result**, Repository
State, Workspace State and the final `READY` or `NOT READY` decision.

### Stale local branch result

Every cleanup report must state whether stale local branches remain after the
completed capability branch is handled. A stale local branch is a non-current,
non-`main` local branch whose upstream has been removed or whose exact content
is already integrated into canonical `main`. The report records either `none`
or each branch name with its disposition: removed as the completed capability,
retained because it is outside this cleanup scope, or retained because a
required safety check failed.

This is an audit requirement, not broad cleanup authority. Workspace Cleanup
continues to delete only the just-completed capability branch after all
applicable checks pass. It must not delete an unrelated stale branch merely
because the report identifies it.

### Two-PR management feedback

After every Finalization and Workspace Cleanup, the user-facing completion
report must include a concise management summary of the two most recently
merged pull requests, newest first. This is the explicit feedback loop to the
Product & Platform Architect (ChatGPT). Each entry records, from repository and
GitHub evidence only:

- the product, platform or governance outcome;
- material decisions and boundaries preserved;
- validation or qualification status; and
- remaining risks, deferred work or the next decision required.

The report concludes with the combined architectural/product-planning feedback
for the next assessment. It is decision support only, never new authority: it
must not invent scope, priorities, ownership, architecture or implementation
commitments. Canonical repository records remain authoritative.

### Product and Platform roadmap projection

The same post-Finalization completion report must state where the repository is
in the current Product and Platform cycle: the authoritative program/cycle,
product-roadmap phase, active increment and relevant Platform Evolution backlog
state. It then lists the next three to five **tentative** candidate items from
the canonical Product Roadmap, Platform Evolution Backlog and their navigation
records. Each item must identify its source, current status and any recorded
gate or dependency.

This is a current-state projection for the Product & Platform Architect, not a
delivery plan. It must say that the order can change through later evidence,
assessment, dependency resolution or authorized reprioritization. It neither
selects work nor grants implementation authority; canonical roadmap and backlog
records remain authoritative.

### Squash-Merge Cleanup Exception

A completed implementation branch may be removed after a squash merge even
when it is not topologically merged. This exception applies only to the branch
unambiguously associated with the completed capability and requires a merged
PR, absent remote branch, clean working tree, non-checked-out branch and no
unpublished work.

Patch equivalence is determined only with:

```sh
git cherry -v <canonical-main> <implementation-branch>
```

Every branch-only commit must have a leading `-`, meaning Git found an
equivalent patch on canonical main. A `+`, failed comparison, ambiguous PR
association or failed verification blocks deletion. When all checks pass,
deletion is authorized despite non-ancestry; this is evidence-based cleanup,
not forced deletion. Report PR merge, remote absence, patch equivalence,
unpublished work, deletion result and Workspace State; otherwise preserve the
branch and require manual attention.

### Finalization Branch Delta Exception

A stale Finalization branch may be deleted only when every commit not on
canonical main has its exact delta already present there. Verify each commit in
oldest-first order with:

```sh
git diff <commit>^ <commit> | git apply --reverse --check
```

Run the command from a clean canonical-main workspace. Every command must
succeed; any failed reverse apply preserves the branch. This is a stricter
content-presence check for Finalization records that later status updates may
have made ineligible for `git cherry` patch matching. It applies only to a
merged, remote-removed, non-checked-out Finalization branch with no unpublished
work, and its report must identify every verified commit and deletion result.

## Reality before planning

Before every engineering prompt, verify synchronized repository state, the
previous pull request, merge evidence, `ENGINEERING_STATUS`, the active
roadmap, the active backlog and implementation reality. A verified merged
predecessor whose rolling records remain at its freeze point is
`MERGED_UNRECONCILED`; only Finalization may proceed. Other unexplained
divergence remains fail-closed.

Before proposing implementation, establish whether the requested capability
already exists, is validated, is qualified, or is already supported by
repository evidence. Do not reimplement an existing outcome: close only the
remaining gaps, validate and qualify them, record documentation that changed,
then advance to the next increment.

Future work must be supported by current status, roadmap, backlog, accepted
audits, validated gaps or repository evidence. Current `main` overrides
conversation history, historical prompts, prior assumptions, engineering
memory, example prompts and historical planning. Historical prompt order is
informational only; engineering work is never invented from chat context.

Every increment begins from synchronized current main, qualifies the
development machine before contentful mutation, verifies repository truth,
classifies post-merge state and enters Finalization when needed, and plans only
after the implementation-reality check. If requested functionality already
exists, is validated or is qualified, do not reimplement it; close only the
remaining evidenced gaps.

## Safe bounded subagent parallelization

Codex may use subagents only for independent, bounded subtasks that improve
throughput without weakening the one-prompt/one-increment/one-reviewable-PR
contract. The coordinator remains the sole owner of scope, branch selection,
implementation integration, final validation, evidence, commit and pull
request.

Subagents may parallelize read-only discovery, log and evidence analysis,
independent test preparation, documentation research and non-overlapping
validation. They must not independently merge, deploy, authorize operations,
change governance, create competing prompts, or make overlapping writes.
There must be one writer for each file or bounded artifact set at a time; the
coordinator integrates every accepted change and resolves all conflicts.

Parallelization must respect real execution capacity. Independent GitHub-hosted
checks may run concurrently, but a single self-hosted runner is a serial
resource unless its registered runner capacity and resource isolation have been
objectively verified. Do not create parallel jobs merely to queue behind one
runner. Security-sensitive work, secrets, signing identities and operational
deployments remain coordinator-controlled and require their existing explicit
authorizations.

Every delegated subtask must state its objective, owner, allowed files or
read-only boundary, expected evidence and completion condition. The coordinator
records material delegation decisions and consolidates validation in the one
reviewable pull request. If independence, ownership or safety is uncertain, do
not delegate the work.

## Ownership and protection

One prompt equals one engineering increment equals one reviewable pull request.
Every increment owns one coherent objective. The Engineering Method itself is
protected: normal implementation prompts must not modify it. Method changes
require a dedicated Engineering Governance prompt.

The Platform Architect owns repository analysis, architecture, prioritization,
engineering planning, prompt generation, governance and review. Codex owns
repository synchronization, implementation, validation, documentation, tests,
engineering evidence and a reviewable pull request. Neither role may silently change architecture;
architecture changes require dedicated governance prompts.

Detailed execution rules live in the linked operational contracts so that this
document stays the single canonical method, not a duplicate playbook.
