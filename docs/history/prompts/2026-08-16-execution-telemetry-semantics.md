# Execution Telemetry Semantics and Projection Reconciliation

- Prompt ID: `inbox-7e7e1710bbff493ab0a5e9da1fe489ea`
- Title: Engineering Platform — Execution Telemetry Semantics & Projection Reconciliation
- Generation and engineering program: Generation 2 / Platform Evolution
- Branch: `codex/execution-telemetry-semantics`
- Commit: `e9eed31ead43d72439b5a7f9395d216b25251d98`
- Pull request: [#833](https://github.com/pcvantol/djconnect/pull/833)
- Decision: merged implementation; Finalization pending
- Execution date: 2026-08-16
- Created: 2026-08-16T08:46:10+02:00
- Updated: 2026-08-16T08:46:10+02:00

## Completed outcome

Execution telemetry now distinguishes total wall time, non-overlapping
phase-category aggregates and independent individual spans. Reports and
read-model consumers use the same aggregation semantics, explicitly label
provider execution, retain historical compatibility and project per-control
validation evidence with its execution source. Report generation and evidence
persistence are measured at their bounded terminal lifecycle operations without
recursive report timing.

## Preserved boundaries

This is measurement and projection reconciliation only. Forge, execution
lifecycle, queue admission, retry/resume/dismiss behavior, validation policy,
model selection and performance policy remain unchanged. No performance budget,
optimization recommendation or new dashboard UI was introduced.

## Verification

- Focused execution timing, host and telemetry suites passed (131 tests).
- Ruff, Bandit and `git diff --check` passed.
- Implementation pull-request checks passed, including Engineering Platform,
  browser dashboard, Home Assistant, CodeQL, Semgrep and dependency-audit
  checks.
- The local full discovery suite has known unrelated inbox-watcher failures;
  the dependency-audit command was unavailable locally.

## Known limitations

Historical runs retain only their observed phase records; this increment does
not fabricate report-generation or evidence-persistence spans for them.

## Deferred work

Performance optimization, performance budgets and dashboard redesign remain
outside this increment.

## Recommended next prompt

Complete this dedicated governance-only Finalization and Workspace Cleanup;
then select any future capability from current repository and backlog evidence.
