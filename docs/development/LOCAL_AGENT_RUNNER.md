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

ChatGPT cannot directly control this local process. Architectural discussion
may continue separately while the developer leaves this foreground command
running or later resumes it.
