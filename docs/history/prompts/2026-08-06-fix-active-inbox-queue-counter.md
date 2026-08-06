# Fix Active Inbox Queue Counter

- Prompt ID and title: `ENG-DASHBOARD-ACTIVE-QUEUE-COUNTER` — Fix Active Inbox Queue Counter
- Generation and engineering program: Generation 2 — Platform Evolution
- Branch: `codex/fix-active-queue-counter`
- Commit: `fad303136e87f05bd20b8066ad28fe83632e4b15`
- Pull request: [#767](https://github.com/pcvantol/djconnect/pull/767)
- Decision and execution date: 2026-08-06 — merged
- Created: 2026-08-06
- Updated: 2026-08-06

## Decision

Keep the watcher as the authoritative owner of the Inbox queue depth while a
runner contributes live execution details. The active dashboard projection
must therefore preserve the watcher-provided queued count.

## Validation

- `python3 -m unittest tests.engineering.test_dashboard_state`
- `git diff --check`

## Known limitations

The queue count remains a watcher projection and can change between dashboard
updates as Inbox files are claimed or added.

## Deferred work

No queue admission, execution, runtime, scheduling or lifecycle behavior is
introduced or changed.

## Recommended next prompt

Merge and verify this governance-only Finalization, then perform the required
local workspace cleanup before starting another capability.
