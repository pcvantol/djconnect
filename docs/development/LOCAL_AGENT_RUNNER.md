# Local Agent Runner

`dj-engineer` starts one foreground, bounded engineering transaction from this
repository. It is local-only developer tooling, not a product capability, CI
system, release engine, merge authority, daemon or remote control plane.

## Prerequisite and usage

Codex CLI must already be installed and authenticated in the developer's local
environment. From a clean DJConnect checkout, run:

```sh
./tools/engineering/dj-engineer path/to/engineering-prompt.md
```

For a bounded transaction with explicit owner authorization for the complete
PR and Finalization lifecycle, use:

```sh
./tools/engineering/dj-engineer path/to/engineering-prompt.md \
  --owner-authorized --run-id bounded-run
```

The authorization is checkpointed locally, applies only to that transaction,
and permits branch/PR readiness, bounded repair, merge and Finalization. It
does not permit releases, deployments, tags, packages, infrastructure changes,
repository-settings changes or branch-protection bypass.

The runner verifies the repository, builds a repository-first Codex prompt from
the supplied file and canonical repository instructions, then records an
advisory checkpoint in `.djconnect/engineering-runs/`. That directory is local
and Git-ignored. It stores identity and execution evidence only; it never
stores prompt content, credentials, tokens or agent output.

The runner retains at most the ten newest completed checkpoints for local
diagnosis and removes older completed checkpoints only from that owned local
directory. Blocked and malformed checkpoints are preserved for inspection.

To continue an interrupted non-terminal run, restart the foreground command:

```sh
./tools/engineering/dj-engineer path/to/engineering-prompt.md --run-id <run-id> --resume
```

There is no background continuation. A resume synchronizes and re-inspects
repository and GitHub evidence; that evidence overrides checkpoint phase and
next-action fields. Malformed, incompatible or conflicting state fails closed.
An abandoned checkpoint can be removed only after inspecting it locally, with
`rm .djconnect/engineering-runs/<run-id>.json`.

## Diagnostics

Codex may return an optional short `diagnostic` field with a `BLOCKED` or
`FAILED` structured result. The runner stores only a bounded, redacted,
human-readable reason in the local checkpoint and prints the reason and the
next action. Diagnostics are advisory: resume always recomputes phase from
repository and GitHub evidence.

If Codex CLI itself exits unexpectedly, the current console additionally shows
its exit code plus bounded, redacted stderr and stdout. Those command-output
details are never checkpointed; the checkpoint contains only a safe summary.

## Autonomous lifecycle and Finalization

With `--owner-authorized`, the runner treats implementation and its mandatory
governance-only Finalization as one resumable transaction. It checkpoints the
implementation and Finalization branch, PR, observed head, merge commit, safe
repository/GitHub evidence and repair count. Repository and GitHub evidence
always override those advisory fields on resume.

After objective evidence proves the implementation merge is in main, the
runner synchronizes local main and derives Finalization from the merged change
and current repository governance. Finalization may reconcile rolling status
records, management/repository summaries, prompt navigation/history and
lifecycle evidence. It cannot add capabilities, change runtime behavior,
select new roadmap work, release, deploy or publish.

The runner marks both PRs ready for review, polls until checks are terminal,
and merges only green PRs under the recorded authorization. A failed required
check starts a bounded repair cycle on the same PR; its check name and repair
count are safe diagnostic evidence. Missing permission, unsatisfied review,
out-of-scope merge conflict or another external dependency remains blocked
with a bounded reason and resume guidance. Waiting, queued CI and transient
API failures remain non-terminal.

On full authorized completion the console emits one management summary with
the implementation/Finalization PRs and merge commits, repair count, authority
boundary and confirmation that no release, deployment or publication occurred.
It does not expose prompt content.

## Repository cleanup

After merged Finalization evidence is contained in `main`, the runner enters
`REPOSITORY_CLEANUP` before it can report `COMPLETE`. It fetches with
`git fetch --prune`, checks out and fast-forwards `main`, and evaluates only
the implementation and Finalization branches recorded for that transaction.
It uses ordinary merged-branch deletion only after objective merge evidence;
missing branches are already-cleaned success, while an unmerged, current or
uncertain branch is preserved and reported as blocked. Resume repeats the same
idempotent evidence-based cleanup and never removes unrelated branches.

## Terminal reports and advisory sub-agents

Each terminal transaction writes an immutable local Markdown report beneath
`.djconnect/reports/` and best-effort opens it using `$EDITOR`, Visual Studio
Code, then Sublime Text. Reports are git-ignored; editor failure never changes
the engineering result. They summarize checkpoint evidence, PRs, repair and
cleanup evidence, diagnostics and the management summary. Optional sub-agents
are read-only, bounded advisory helpers for inspection or validation; they
cannot write, create/ready/merge PRs, create Finalization, alter governance or
perform cleanup. The primary runner validates and integrates every result.

## Terminal evidence and boundaries

Queued or running CI, pending checks, a polling interval, a temporary GitHub
failure and a Codex process exit are never successful completion. The runner
records waiting work and exits non-zero so the developer can resume it. It
returns success only after its structured agent result agrees with terminal Git
and GitHub evidence: either an authorized merged/reconciled result on `main`,
or an explicitly bounded open-PR objective with all required checks terminal.

The runner uses repository-scoped `workspace-write` Codex access. It does not
reset, stash, overwrite or discard unrelated work. A dirty workspace,
repository mismatch, missing Codex CLI, failed required checks, missing
approval or other external authority boundary is reported rather than bypassed.
Without `--owner-authorized` it does not merge. In every mode it does not
release or deploy.

This foreground process has no background continuation. It can be resumed from
repository evidence after an interruption.
