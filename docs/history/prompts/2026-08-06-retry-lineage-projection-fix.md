# Retry Lineage Projection Fix

- Prompt ID and title: `ENG-RETRY-LINEAGE-PROJECTION-FIX` — Retry Lineage Projection Fix
- Generation and engineering program: Generation 2 — Platform Evolution
- Branch: `codex/retry-lineage-projection-fix-pr`
- Commit: `7ff5565d7e6c06ff9ad3b0987051b4288144aa15`
- Pull request: [#759](https://github.com/pcvantol/djconnect/pull/759)
- Decision and execution date: 2026-08-06 — merged
- Created: 2026-08-06
- Updated: 2026-08-06

## Decision

Make the server-side Prompt History projection authoritative for retry actions.
A terminal blocked parent can expose Retry only when it has no persisted queued,
active or terminal retry child.

## Validation

- `python3 -m unittest tests.engineering.test_prompt_history tests.engineering.test_inbox_watcher tests.engineering.test_dashboard`
- `npm run test:engineering-dashboard`
- `node --check tools/engineering/assets/dashboard.js`
- `git diff --check`

## Known limitations

Repository-wide Ruff still reports an existing unused import in
`tools/engineering/inbox_watcher.py`; that issue is outside this bounded fix.

## Deferred work

No new product or platform capability is introduced. Existing retry execution
and duplicate-retry rejection remain unchanged.

## Recommended next prompt

Merge and verify the governance-only finalization increment for PR #759, then
perform the required local workspace cleanup.
