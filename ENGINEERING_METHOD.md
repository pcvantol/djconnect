# DJConnect Engineering Method

**Status:** Canonical operational governance
**Version:** 2.6
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
  -> Reconcile rolling state when required
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

## Engineering lifecycle state

Every increment has one explicit engineering lifecycle state:

| State | Meaning |
| --- | --- |
| `REVIEWABLE_FROZEN` | The scoped pull request exists; implementation is frozen pending human review and merge. |
| `MERGED_UNRECONCILED` | Objective GitHub evidence proves the predecessor merged and current `main` contains it, while rolling records may still describe its freeze point. This is expected, not automatically inconsistent. |
| `MERGED_RECONCILED` | Rolling engineering records reflect the merged repository truth; normal planning and implementation may continue. |

The reviewable pull request is the freeze point. Human merge is external. The
next increment owns reconciliation after an objectively verified merge; it
never rewrites immutable Prompt History.

## Reality before planning

Before every engineering prompt, verify synchronized repository state, the
previous pull request, merge evidence, `ENGINEERING_STATUS`, the active
roadmap, the active backlog and implementation reality. A verified merged
predecessor whose rolling records remain at its freeze point is
`MERGED_UNRECONCILED`; reconcile it before substantive engineering. Other
unexplained divergence remains fail-closed.

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
classifies and reconciles post-merge state when needed, and plans only after
the implementation-reality check. If requested functionality already exists,
is validated or is qualified, do not reimplement it; close only the remaining
evidenced gaps.

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
