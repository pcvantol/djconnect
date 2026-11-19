# Terminal Execution Dismiss

Date: 2026-08-03

## Objective

Introduce a confirmed operator acknowledgement for the current terminal
Execution Host run. Dismiss ends operational attention without restarting
engineering, altering repository history, resuming queues or deleting
historical evidence.

## Delivered outcome

PR [#724](https://github.com/pcvantol/djconnect/pull/724), **Add terminal
execution dismiss**, merged as
`3155283f8f7d9ae8aa2f9e05bb39d9aa149d8274`.

The Execution Host records `dismissed`, `dismissed_at` and `dismissed_by` in a
durable audit record, clears the active operational state and returns the
watcher to idle when no queue is present. Reports, telemetry, prompt history,
retry relationships and repository truth remain unchanged. The dashboard
offers the confirmed action only for the current terminal execution from
Prompt History, alongside Retry for blocked executions. Dismiss is distinct
from Retry, which creates a new engineering run, and Queue Recovery, which
restores only blocked dependent queue flow.

## Validation evidence

- Pull-request checks: passed, including Engineering Platform validation and
  browser-dashboard validation.
- `python3 -m unittest discover -s tests/engineering`: 242 passed.
- `npm run test:engineering-dashboard`: 60 passed.
- `node --check tools/engineering/assets/dashboard.js`: passed.
- `git diff --check`: passed.

## Follow-up

The recommended next bounded Execution Host increment is Preflight Level 3
(Capability Preflight). It remains separate from operational acknowledgement,
transport resolution and Forge.
