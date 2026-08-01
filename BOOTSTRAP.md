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
squash-merge patch-equivalence exception, plus the separate deterministic
Finalization-branch delta exception.

## Product & Platform Architect Sessions

`BOOTSTRAP.md` is the single canonical repository entry point for AI-assisted
Product & Platform Architecture work. The canonical session command is:

```text
Repository Sync + Developer Handoff
```

This command starts at this repository bootstrap. It directs a new ChatGPT
Product & Platform Architect session to:

1. read `docs/development/DEVELOPER_HANDOFF.md` for collaboration orientation;
2. synchronize and verify the current repository before planning or review;
3. treat repository evidence as the canonical source of truth;
4. adopt the Product & Platform Architect role defined by the Developer
   Handoff;
5. wait for the latest management summary supplied by the user;
6. validate repository continuity against that summary and current evidence;
7. execute the standard Product & Platform Architect review cycle; and
8. finish with exactly one repository-grounded Product Development prompt.

If repository evidence differs from previous conversations, repository
evidence always wins. The Developer Handoff continues repository evolution; it
does not preserve obsolete chat history, replace this bootstrap or establish a
second bootstrap mechanism.

The standard collaboration sequence is:

```text
New Chat
  ↓
Repository Sync + Developer Handoff
  ↓
BOOTSTRAP.md
  ↓
Developer Handoff
  ↓
Repository Synchronization
  ↓
Latest Management Summary
  ↓
Product & Platform Architect Review
  ↓
Next Product Development Prompt
```

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

## Engineering Platform

The local AI-assisted engineering environment is independently versioned by
`tools/engineering/ENGINEERING_PLATFORM_VERSION.json`. Its current canonical
contract is Engineering Platform `1.5.0`, runner `1.5.0`, Bootstrap Contract
`2026.12`, Checkpoint Format `1`, Engineering Memory Format `2`, Report Format
`2`, Engineering Inbox watcher `1.1.2` (Inbox Protocol `1`), private dashboard
`1.2.14`, Platform Identity
generation `2`, Workspace Identity schema `1`, provider model `1`, configuration
schema `1`, qualification registry `1` and minimum
supported Codex CLI `0.146.0`. On supported macOS workstations, the watcher
and its per-user LaunchAgent must satisfy this same contract before accepting
iCloud inbox work; incompatibility is blocked with corrective diagnostics.

Every future Platform Engineering prompt requires:

```text
Required Engineering Platform: >= 1.5.0
```

Engineering Platform 1.5 is the minimum supported platform for future
engineering prompts. Older versions are incompatible and compatibility
validation fails closed. The repository bootstrap is the authoritative
compatibility contract. Product & Platform Architect prompts require
Engineering Platform `1.5.0` or newer. The generated prompt
must state this minimum explicitly. `dj-engineer` must fail closed before any
repository mutation when the detected Engineering Platform is older than the
prompt's declared minimum.

When an older platform is detected, report the following diagnostic without
continuing:

```text
Engineering Platform detected:

<detected version>

Required:

>= 1.5.0

Status:

UPGRADE_REQUIRED

Action:

Upgrade the Engineering Platform before executing this engineering prompt.
```

`dj-engineer` validates this manifest at startup. Engineering compatibility is
determined from this Engineering Platform contract, not from individual runner
implementation details. A newer runner may execute an older repository only
when it explicitly supports the repository's platform major version, minimum
runner version, Bootstrap Contract, checkpoint, memory and report formats, and
minimum Codex CLI version. Any incompatible combination is blocked with the
expected version, detected version and required upgrade action; it is never
silently ignored.

## Engineering Platform Qualification

Engineering Platform capabilities are evidence-first: implementation alone does
not make a capability trusted. Run `./tools/engineering/dj-engineer qualify`
to execute the canonical local qualification registry in
`tools/engineering/ENGINEERING_QUALIFICATION.md`. Reports are local under
`.djconnect/qualification/`; they record scenario outcome, duration,
diagnostics, evidence, Engineering Platform version, repository version and
Codex CLI version.

## Engineering Platform Status

Engineering Platform Generation 1 is `FEATURE_COMPLETE`. Its stable capability
set, qualification-first closure and evidence-driven future-evolution policy
are canonical in `tools/engineering/ENGINEERING_PLATFORM_STATUS.md`.
