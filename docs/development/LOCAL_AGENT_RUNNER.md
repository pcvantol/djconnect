# Local Agent Runner

`dj-engineer` starts one foreground, bounded engineering transaction from this
repository. It is local-only developer tooling, not a product capability, CI
system, release engine, merge authority, daemon or remote control plane.

## Engineering Platform versioning

`tools/engineering/ENGINEERING_PLATFORM_VERSION.json` is the canonical,
deterministic Engineering Platform manifest. It versions the engineering
environment independently from the repository and declares the platform,
runner, watcher and dashboard versions; Bootstrap Contract; checkpoint,
memory, report, status-model and Inbox Protocol formats; and the minimum Codex
CLI version. Engineering Platform `1.5.0` is the current minimum supported
platform for future engineering prompts.

The local Inbox worker and private Dashboard are separately versioned
components of Engineering Platform 1.5. Their current versions are the
canonical `watcher_version` and `dashboard_version` manifest fields; neither
is a separate Engineering Platform release. The private dashboard displays
both component versions next to the Engineering Platform version and Git
commit to make local operational evidence unambiguous.

At runner startup, `dj-engineer` reads the manifest and rejects an unsupported
platform major version, older runner, older Bootstrap Contract, unsupported
checkpoint/memory/report format or unsupported Codex CLI. Diagnostics state the
repository requirement, detected runner or CLI value, and required action.
Newer runners remain compatible with older repositories only when they
explicitly advertise support for every declared contract. Compatibility is
therefore auditable and never inferred from individual implementation details.

## Capability-aware specialist reviewers

Engineering Platform 1.1 has four deterministic, read-only reviewer types:
Repository Governance, Validation, Documentation and Finalization. Before the
primary agent begins work, the runner classifies the objective, lifecycle state
and safe Engineering Memory and selects only relevant reviewers. Independent
reviewers may run in parallel; their recommendations are deduplicated and
advisory.

Reviewers may inspect, analyse and recommend only. They cannot edit, commit,
push, merge, create pull requests, finalize or alter lifecycle state. Reviewer
failure is recorded as advisory and the primary engineering agent continues
from repository evidence. Reports show selection reasons, contributions and
reconciled recommendation counts; Engineering Memory retains bounded reviewer
confidence, usage, outcome and duration metadata for future selection.

Engineering Platform 1.2 complements those generic reviewers with deterministic
product specialists for Apple Platform, Windows Platform, Home Assistant
Integration, ESPHome Firmware, Pi Renderer, Universal Receiver, Website and
API. Path and objective evidence select only the relevant specialist; each
reviewer receives an explicit capability scope and may not redesign another
product area without cross-capability repository evidence. Product and generic
reviewers can inspect independently in parallel, while recommendations remain
advisory and require primary-agent reconciliation.

## Engineering Platform Qualification

Run `./tools/engineering/dj-engineer qualify` to execute every deterministic
scenario in `tools/engineering/ENGINEERING_QUALIFICATION.md`. The local
qualification dashboard reports pass/fail, scenario coverage, failure and
blocked counts. Its JSON and Markdown evidence remains under the git-ignored
`.engineering/qualification/` directory. Terminal Engineering Reports include the
latest available qualification version, result, execution time and coverage.

## Generation 1 status

Engineering Platform Generation 1 is feature complete. Its stable capability
set and future evidence-driven governance are recorded in
`tools/engineering/ENGINEERING_PLATFORM_STATUS.md`. New capabilities require
demonstrated insufficient coverage, explicit architectural approval,
implementation, qualification and evidence; routine work remains limited to
maintenance, bug fixes, compatibility and qualification improvement.

## iCloud Engineering Inbox

The repository-owned local watcher accepts iPhone-submitted `.txt`, `.md` and
filename-neutral files whose bounded UTF-8 content is Markdown. It validates a
stable input file, selects the oldest eligible file by File Date Modified,
serializes jobs and invokes only the repository-owned runner. Its v1 protocol
is `tools/engineering/ENGINEERING_INBOX_PROTOCOL.md`; iCloud is transport
only.
After a prompt is claimed, its lifecycle archive, reports and status are stored
only in `.engineering/`. The iCloud workspace contains only `Inbox/`.
The default queue is strict and fail-closed: after a `BLOCKED` or `FAILED`
Inbox run, later prompts remain in Inbox as `WAITING_FOR_PREDECESSOR`.
Repair and explicitly resubmit the blocking prompt with
`Retry-Of: <blocking-run-id>` as its own line; only that corrected retry can
release the sequence.

Before the explicit per-user install, verify readiness:

```sh
python3 -m tools.engineering.inbox_watcher doctor
```

Install the watcher only for the current local user:

```sh
python3 -m tools.engineering.inbox_watcher install
```

The installed LaunchAgent starts at login and remains limited to the configured
local repository. `once`, `run`, `status`, `uninstall` and `doctor` remain the
supported commands. Tests never install the LaunchAgent.

### Component logging

The watcher and dashboard write private, structured application events to
`engineering_component_logs` in `.engineering/engineering.db`. Each record has
a UTC timestamp, severity, component and, where applicable, run ID. Event and
diagnostic text are redacted and bounded before persistence.

In Engineering Status, open **Logs** to inspect a bounded, live view of these
redacted records. They are never loaded or streamed outside the private
dashboard.

The existing `inbox.out.log`, `inbox.err.log`, `dashboard.out.log` and
`dashboard.err.log` remain the LaunchAgent process streams. They complement,
rather than replace, the application logs. Rotating `.engineering/logs/*.log`
files are created only as a private fallback if SQLite is unavailable during
early startup or a crash.

Set `DJCONNECT_ENGINEERING_LOG_LEVEL` to `DEBUG`, `INFO`, `WARNING` or `ERROR`
before installing a watcher or dashboard LaunchAgent; the selected value is
stored in its LaunchAgent environment. The default is `INFO`; an invalid value
fails closed to `INFO`. Reinstall the relevant LaunchAgent after changing it.

## Remote Engineering Experience

Engineering Platform 1.5 projects canonical watcher status as bounded, atomic
`status.json` and an iPhone-readable private dashboard. The dashboard is
strictly read-only. It binds only to loopback and, when Tailscale reports one,
the workstation's explicit Tailscale IPv4 address; it never binds a wildcard,
LAN or public address. It uses server-sent events for status changes and has no
execution, release, deployment or publication authority.

Before the explicit per-user dashboard install, verify readiness:

```sh
./tools/engineering/dj-engineering-dashboard doctor
```

Then install it for the current local user:

```sh
./tools/engineering/dj-engineering-dashboard install
```

Tailscale may provide private reachability, but this repository never enables
Funnel, public binding, ACL changes, port forwarding or remote command
execution. `docs/engineering/runs/latest.md` and `index.json` are the durable,
sanitized discovery records for successfully finalized transactions; local
reports and prompt contents remain local.

The dashboard's **Codex gesprek** is a separate, private advice surface. It is
available only through the same loopback/Tailnet listener and uses the repository
identity, last executed prompt and matching Engineering Report as bounded context.
Each reply uses an ephemeral `codex exec` process in a separate read-only
workspace. It has no Inbox, runner, repository write, pull-request, merge,
release, deployment or publication authority. A requested change must still be
submitted as a new explicit Engineering prompt. The displayed chat model is
explicitly selected as `gpt-5.6-terra` by default; a local
`DJCONNECT_ENGINEERING_CHAT_MODEL` override may select another valid Codex
model before the dashboard is started.

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
advisory checkpoint in `.engineering/engineering-runs/`. That directory is local
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
`rm .engineering/engineering-runs/<run-id>.json`.

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
It first uses ordinary deletion. If Git refuses solely because a squash merge
made the transaction branch non-ancestral, reconciled PR/main evidence and
checkpoint ownership authorize a safe local force deletion for that exact
branch. Missing branches are already-cleaned success; uncertain ownership or
failed reconciliation remains blocked. Resume repeats the same idempotent
evidence-based cleanup and never removes unrelated branches.

## Terminal reports and advisory sub-agents

Each terminal transaction writes an immutable local Markdown report beneath
`.engineering/reports/`. Reports are never opened automatically in an editor;
they remain available through Engineering Status and the local report path.
Reports are git-ignored. When the Inbox watcher owns the
transaction, it validates the report against the terminal checkpoint and keeps
the safe terminal report locally under `.engineering/reports/`. If correction is
needed, the watcher writes a corrected checkpoint-consistent local copy; it
never publishes a report to iCloud. Reports summarize checkpoint evidence,
PRs, repair and cleanup evidence, diagnostics and the management summary.
Optional sub-agents
are read-only, bounded advisory helpers for inspection or validation; they
cannot write, create/ready/merge PRs, create Finalization, alter governance or
perform cleanup. The primary runner validates and integrates every result.

Every report records the Engineering Platform Version, Runner Version,
Bootstrap Contract, Checkpoint Format, Memory Format, Report Format and the
detected Codex CLI version alongside the transaction evidence.

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

## Live progress

The runner emits concise terminal and cleanup phase updates and atomically
maintains `.engineering/status/current.json`. The Inbox watcher projects bounded
dashboard status to `.engineering/status/status.json`. Both are git-ignored local
advisory records; resume recomputes from repository and GitHub evidence. iCloud
carries only a submitted Inbox file and never receives status, reports or prompt
archives. Run
`./tools/engineering/dj-engineer status` to display the current phase, PRs,
repair count and action.

## Engineering Memory

Successful transactions store bounded metadata under `.engineering/memory/`,
which is already covered by the local `.engineering/` ignore rule. Memory never
stores prompts, source snapshots, credentials or personal data. Retrieved
patterns are advisory context only: repository and GitHub evidence override
them, and they cannot change scope, validation or authority.
