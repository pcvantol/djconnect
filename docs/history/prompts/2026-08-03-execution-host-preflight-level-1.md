# Execution Host Preflight Level 1

Date: 2026-08-03

## Objective

Implement fail-closed Execution Host Preflight Level 1 before the local
Engineering Inbox watcher claims work. Restrict checks to the Execution Host;
do not inspect an engineering workspace, Git, Engineering Actions, missions,
capabilities or Forge.

## Delivered outcome

PR [#713](https://github.com/pcvantol/djconnect/pull/713), **Add Execution
Host Preflight Level 1**, merged as
`ed478840a41dbd3e25f65ebc7a16461a4c7ed99f`.

The watcher now completes host preflight before moving an Inbox item to
`Running` or starting the Execution Host. It verifies readable configuration,
required runtime directories and write access, configurable free disk capacity,
Codex CLI presence and invocation, enabled telemetry SQLite availability,
structured logging initialization, and Execution Host identity/version/Bootstrap
Contract. A failure leaves the Inbox item unclaimed and records bounded local
evidence with an identifier, reason and recovery recommendation.

The Engineering Report includes matching host preflight evidence. The private
dashboard displays only compact status and last-preflight time. No Product,
Runtime, Release, Deployment, Publication or Forge behavior changed.

## Validation evidence

- `python3 -m unittest discover -s tests -p 'test_*.py'`: 1,678 passed, 7 skipped.
- Focused Engineering Platform regression suite: 171 passed.
- Engineering Platform GitHub validation: passed.
- Browser-dashboard GitHub validation: passed.
- `ruff check tools/engineering tests/engineering`: passed.
- `node --check tools/engineering/assets/dashboard.js`: passed.
- `git diff --check`: passed.

## Follow-up

Execution Host Preflight Level 2 (Workspace Preflight) is the next bounded
increment. It must remain separate from Level 1 and must not introduce Git,
mission, action, capability or Forge validation without a new explicit scope.
