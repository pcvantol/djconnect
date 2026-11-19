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

Every engineering prompt must execute `git switch main`, `git fetch origin main`
and `git merge --ff-only origin/main` before repository reading or planning.
Managed synchronization selects `origin/main` explicitly and must not depend on
local upstream, `branch.*.merge` or Git pull-policy configuration. It must then verify
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

When the completed increment is an assessment, Finalization also verifies that
`QUALIFICATION_REGISTER.md` records its merged Assessment Result, Qualification
Summary, objective Remaining Qualification Items and existing disposition. The
register is a current-state index only; this check never creates a backlog item,
changes the Execution Horizon or authorizes implementation.

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

## Long-running engineering operations

Engineering completion is determined only by objective repository evidence.
Execution characteristics never redefine completion: runtime or connector
limits, polling timeouts, transient GitHub/API failures, queued or pending CI,
release propagation, indexing and deployment-observation latency are not
terminal engineering states.

An asynchronous engineering activity remains active until objective evidence
establishes exactly one of: successful completion, terminal failure, or an
external dependency that cannot be progressed automatically, such as missing
permission or required human authorization. Temporary waiting is never
completion.

When execution is interrupted without terminal repository evidence, the active
engineering phase remains active. A later session synchronizes the repository,
verifies current Git and GitHub evidence, determines the last completed phase
and continues from that verified point. It must not restart work merely because
the prior execution ended, nor repeat completed work unless current repository
evidence requires it. Local execution memory is advisory only and never
overrides repository evidence or the Engineering Method.

### Owner-authorized local transactions

An explicitly owner-authorized local transaction may automate the bounded pull
request readiness, repair, merge and mandatory governance-only Finalization
steps already required by this method. Its checkpoint is advisory and records
only safe lifecycle evidence; current repository and GitHub evidence remain
authoritative on every resume. The authorization does not create a new
engineering phase or permit releases, deployments, publication, tags,
repository-settings changes, branch-protection bypass, roadmap selection or
scope expansion. Finalization remains limited to its established reconciliation
scope and must complete before the repository is `MERGED_RECONCILED`.

For an approved local transaction, successful Finalization reconciliation is
followed by the existing mandatory Workspace Cleanup procedure before the
transaction is complete. The local runner fetches/prunes first and may remove
only its objectively merged implementation and Finalization branches using
normal deletion; uncertainty preserves the branch and blocks completion.

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

### Finalization Rolling Horizon standard

Every post-Finalization and Workspace Cleanup management summary must use this
fixed order:

1. Repository Status
2. Management Summary
3. Roadmap Position
4. Rolling Horizon (Next 5 Planned)
5. Blocked Items
6. Deferred Items
7. Repository State
8. Workspace State

**Roadmap Position** states the authoritative Generation, Phase and active
engineering increment. **Repository Status** records the relevant merge
commit(s), CI and HACS outcome, `main == origin/main`, Repository State,
Workspace State and stale-local-branch result.

**Rolling Horizon (Execution Horizon)** contains the next five actually authorized execution items. Backlog order remains the default basis; an item may be skipped only for a recorded dependency, explicit management decision, or repository decision that changes execution order. Each skip includes a compact objective execution justification. Each item identifies
its backlog ID, title, canonical source, current status and direct dependency
when one is recorded, plus a one-line **Execution Rationale** explaining why it
is currently scheduled. Eligibility is limited to `Planned`, `Authorized`, or
`Ready` after direct dependencies. `Deferred`, `Blocked`, `Completed`,
`Merged`, `Rejected` and `Cancelled` items are never eligible. The horizon is
derived afresh from the canonical repository backlog records, never from chat
history, memory, a personal recommendation or a prior management summary. It
therefore advances automatically when a completed item is no longer eligible. It is not a Backlog Horizon and never skips work for personal or AI preference.

**Blocked Items** lists only current blocks, each with its subject, blocking
reason and deconditioning evidence. **Deferred Items** lists only consciously
deferred roadmap items. Neither section contributes items to the Rolling
Horizon.

This is a current-state handoff, not a delivery plan. It neither selects work
nor grants implementation authority; canonical roadmap and backlog records
remain authoritative when records conflict.

When the Execution Horizon differs from canonical backlog order, add one
compact **Execution Priority Override** after the horizon. It identifies the
item and objective dependency, management or repository decision causing the
deviation. Omit it when no deviation exists.

### Finalization pre-push consistency check

Before a Finalization pull request is pushed, derive its current-state handoff
once from the verified merged predecessor and the canonical backlog records.
Apply that result as one set to `ENGINEERING_STATUS.md`,
`REPOSITORY_STATUS.md`, `MANAGEMENT_SUMMARY.md` and `PROMPT_INDEX.md`; do not
copy a prior summary or update those records independently. Every record must
contain the predecessor's canonical Markdown pull-request link and exact merge
commit. The Execution Horizon must exclude the completed predecessor and must
be identical wherever it is rendered.

Run the focused lifecycle regression before push:

```sh
python3 -m unittest tests.test_capability_completion_lifecycle
```

The Finalization is not reviewable when that check, `git diff --check`, or the
four-record comparison fails. This is a documentation-consistency safeguard
only: it does not add a CI gate, alter merge semantics or change the canonical
backlog.

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
