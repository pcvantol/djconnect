# Prompt Initialization

**Status:** Canonical operational contract

Every engineering prompt must begin with this mandatory `PRE-FLIGHT` sequence,
in order:

```text
Repository Synchronization
  -> Current Main Verification
  -> Development Machine Qualification
  -> Previous Pull Request Verification
  -> Post-Merge State Classification
  -> Rolling State Reconciliation
  -> Workspace State Verification
  -> Canonical Repository Read
  -> Implementation Reality Check
  -> Golden Scenario Governance Check
  -> GO / NO-GO Decision
```

## Repository Synchronization

Run `git switch main` and then `git pull --ff-only`. If either fails, stop.

## Current Main Verification

Verify the checked-out branch, current `HEAD`, tracking branch, fast-forward
status, working-tree cleanliness and repository cleanliness. If any check
fails, stop.

## Development Machine Qualification

Before accepting or performing a contentful tracked-repository mutation, require
the local current-session desired-state verification summary from the machine
that will do the work. It must state `READY FOR DJCONNECT DEVELOPMENT` with a
zero exit code. Do not infer qualification from chat history, a previous
session, another machine or partial copied output.

Without qualifying evidence, do read-only inspection only and report the
required verification evidence. `BOOTSTRAP_CODEX_SESSION.md` owns the exact
command, evidence format and narrow exceptions; an exception bypasses only
this gate, not any other prompt-initialization requirement.

## Previous Pull Request Verification

Use objective GitHub and Git evidence to establish the predecessor, its merge
state and commit, containment in current `main`, and archived Prompt History.
Do not infer these facts from a prompt, conversation or AI memory. Unknown
merge candidates, missing history, divergence and stale main remain terminal.

## Post-Merge State Classification

Classify the repository as `REVIEWABLE_FROZEN`, `MERGED_UNRECONCILED` or
`MERGED_RECONCILED` using `ENGINEERING_METHOD.md`. A verified merged predecessor
whose rolling records still show its freeze point is the expected
`MERGED_UNRECONCILED` transition.

## Rolling State Reconciliation

For `MERGED_UNRECONCILED`, do not begin production implementation. Only the
dedicated Finalization increment may reconcile `ENGINEERING_STATUS.md`,
`REPOSITORY_STATUS.md`, `MANAGEMENT_SUMMARY.md` and `PROMPT_INDEX.md` with
current main. Prompt History is immutable; the next implementation capability
continues only after Finalization restores `MERGED_RECONCILED` and Workspace
Cleanup verifies `WORKSPACE_READY`.

## Canonical Repository Read

Follow `BOOTSTRAP.md` exactly. Read current status, roadmap and backlog before
consulting history. Prompt History is optional immutable context only;
conversation history is never current-state authority.

## Workspace State Verification

Before production implementation, independently verify Repository State
`MERGED_RECONCILED` and Workspace State `WORKSPACE_READY` as defined in
`ENGINEERING_METHOD.md`. `WORKSPACE_READY` requires canonical `main`,
synchronized `origin/main`, a clean working tree, removal of the just-completed
local implementation branch and pruned obsolete remote-tracking references.
The completed branch may be topologically merged or satisfy the Squash-Merge
Cleanup Exception in `ENGINEERING_METHOD.md`; stale Finalization branches may
use its separate commit-delta exception.
Workspace cleanup is not repository reconciliation. If either required state
is absent or cannot be verified, the decision is `NO-GO`.

## Implementation Reality Check

After synchronization, inspect the requested functionality, its validation,
qualification, documentation and implementation. Do not reimplement an
existing outcome; close only remaining evidence-backed gaps.

## Golden Scenario Governance Check

Before a Verification or Session Intelligence capability receives a `GO`, read
the [Golden Scenario Governance](docs/verification/GOLDEN_SCENARIO_GOVERNANCE.md)
and the canonical Golden Scenario Catalogue. A Verification capability names
the approved scenario relationship it enables, executes, captures, validates or
protects. A Session Intelligence capability names whether it preserves,
extends or introduces approved behavior.

When no direct scenario relationship exists, the prompt must contain an
explicit architectural justification and proportionate narrower validation
evidence. Verify the requested work preserves the applicable behavioral
contract unless a governed catalogue revision authorizes a change, and verify
it creates no duplicate Runtime, Scenario Driver, verification path or
browser-owned verification authority. Missing evidence is `NO-GO`.

## GO / NO-GO Decision

Use synchronized current main to determine the current engineering increment,
program, repository truth, backlog, deferred work and recommended next prompt.
Verify that the requested capability remains pending, no equivalent outcome is
already merged, and no superseding architecture amendment exists. Confirm that
the required validation baseline, current roadmap, architecture and maturity
records are applicable and current.

End Pre-Flight with exactly one explicit decision:

- `GO`: only from `MERGED_RECONCILED` and `WORKSPACE_READY`, authorizing the
  bounded implementation.
- `NO-GO`: production changes are prohibited; report and resolve the evidence
  that prevents the capability from starting.

No prompt may assume these facts from its text, conversation context or
historical planning.
