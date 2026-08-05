# Retry Lineage Finalization — Engineering Report

## Outcome

**YES. Retry Lineage Finalization is operational.**

Historical terminal executions remain immutable evidence. A retry creates a
separate child execution, and the parent cannot create a second child once that
relationship is present in Prompt History or pending in the Inbox.

## Delivered projection

- Prompt History derives retry parent, child, chain and current run from the
  immutable `retry_of` relationship.
- Historical blocked rows no longer expose Retry after a child exists.
- Retry submission rejects duplicate children before a new Inbox prompt is
  created.
- The dashboard shows a compact Run-ID suffix and keeps the historical table
  horizontally scrollable on iPad portrait.
- Producer type labels are localized for `en`, `nl`, `de`, `fr` and `es`.

## Verification

- `python3 -m unittest tests.engineering.test_inbox_watcher
  tests.engineering.test_prompt_history tests.engineering.test_dashboard`
  — 106 passed.
- `node --check tools/engineering/assets/dashboard.js` — passed.
- `git diff --check` — passed.

## Boundary

No Forge, execution lifecycle, Execution Host scheduling or runtime behavior
was changed. Retry remains distinct from Resume.
