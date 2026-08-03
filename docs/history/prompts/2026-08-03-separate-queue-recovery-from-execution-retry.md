# Separate Queue Recovery from Execution Retry

- Prompt ID: `EP-QUEUE-RETRY-001`
- Generation and engineering program: Generation 2, Platform Evolution
- Engineering mode: Platform Engineering
- Branch: `codex/separate-queue-recovery-retry`
- Commits: `fd05e19bfbf2812c626e2517046d5b7cdddd63d0`, `5c15c06bf4b4a0b1a09b0cd783c2cc54bb31e42e`
- Pull request: [#710](https://github.com/pcvantol/djconnect/pull/710)
- Merge commit: `8b657af8fc4598b0174ef28d73c8fd55e1953f8f`
- Decision: `MERGED_UNRECONCILED`; dedicated Finalization required.
- Execution date: 2026-08-03
- Created: 2026-08-03T08:25:00Z
- Updated: 2026-08-03T08:31:13Z

## Objective

Separate Queue Recovery from Execution Retry in the local Engineering Platform.
Queue Recovery restores blocked dependent Inbox progression. Execution Retry
creates a new engineering execution for every terminal `BLOCKED` run without
changing the original execution.

## Delivered outcome

- Dashboard terminology and actions are explicit: **Resume Queue** and
  **Retry Execution**.
- Retry creates a new Run ID and persists `retry_of`, `original_run_id`,
  `retry_generation` and `retry_timestamp`.
- Engineering Reports and telemetry retain retry lineage while preserving
  immutable original evidence.
- Queue recovery is unavailable when no dependent Inbox work is waiting.

## Validation

- `ruff check tools/engineering tests/engineering`
- `python3 -m unittest discover -s tests -p 'test_*.py'` — 1,671 passed, 7 skipped.
- Engineering Platform validation and browser dashboard validation passed on PR #710.
- `git diff --check`

## Known limitations

Retry is intentionally manual. No automatic retry or queue-scheduling change
was introduced.

## Deferred work

No new deferred work was discovered. Existing backlog priorities and the
Execution Horizon remain unchanged.

## Recommended next prompt

Complete the dedicated governance-only Finalization for PR #710, then perform
the mandatory Workspace Cleanup after that Finalization merges.
