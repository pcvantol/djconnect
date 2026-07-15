# Prompt Initialization

**Status:** Canonical operational contract

Every engineering prompt must begin with this sequence, in order:

```text
Repository Synchronization
  -> Current Main Verification
  -> Previous Pull Request Verification
  -> Post-Merge State Classification
  -> Rolling State Reconciliation
  -> Canonical Repository Read
  -> Implementation Reality Check
  -> Engineering Planning
```

## Repository Synchronization

Run `git switch main` and then `git pull --ff-only`. If either fails, stop.

## Current Main Verification

Verify the checked-out branch, current `HEAD`, tracking branch, fast-forward
status, working-tree cleanliness and repository cleanliness. If any check
fails, stop.

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

For `MERGED_UNRECONCILED`, reconcile `ENGINEERING_STATUS.md`,
`REPOSITORY_STATUS.md`, `MANAGEMENT_SUMMARY.md` and `PROMPT_INDEX.md` with
current main before substantive engineering. Prompt History is immutable;
continue only after the state is `MERGED_RECONCILED`.

## Canonical Repository Read

Follow `BOOTSTRAP.md` exactly. Read current status, roadmap and backlog before
consulting history. Prompt History is optional immutable context only;
conversation history is never current-state authority.

## Implementation Reality Check

After synchronization, inspect the requested functionality, its validation,
qualification, documentation and implementation. Do not reimplement an
existing outcome; close only remaining evidence-backed gaps.

## Engineering Planning

Use synchronized current main to determine the current engineering increment,
program, repository truth, backlog, deferred work and recommended next prompt.
No prompt may assume those facts from its text, conversation context or
historical planning.
