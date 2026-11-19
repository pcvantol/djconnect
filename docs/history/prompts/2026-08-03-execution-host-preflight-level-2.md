# Execution Host Preflight Level 2 (Workspace Preflight)

Date: 2026-08-03

## Objective

Implement fail-closed Workspace Preflight after Execution Host Preflight Level
1 and before the local Engineering Inbox watcher claims work. Restrict checks
to target-workspace resolution and repository readiness; do not validate
missions, Engineering Actions, capabilities, Runtime Prompts or Forge.

## Delivered outcome

PR [#716](https://github.com/pcvantol/djconnect/pull/716), **Add Execution Host
Workspace Preflight**, merged as
`0bf81b152dcbf2c6c0021fcdc27e9e355535980a`.

The watcher now evaluates Workspace Preflight only after Host Preflight passes
and before moving an Inbox item to `Running`. It validates target resolution
under an approved workspace root, Git metadata access/write access, a clean
staged/unstaged/untracked worktree, unfinished Git operations and mode-aware
branch readiness. Managed mode requires the configured branch, origin and
upstream synchronization; Genesis accepts a local target repository without a
remote. A failure leaves the Inbox item unclaimed and records bounded evidence
with an identifier, reason and recovery recommendation.

The Engineering Report includes matching Workspace Preflight evidence and the
private dashboard displays only compact workspace status and last-check time.
No DJConnect Product, Runtime, Release, Deployment, Publication or Forge
behavior changed.

## Validation evidence

- `python3 -m unittest discover -s tests -p 'test_*.py'`: 1,686 passed, 7 skipped.
- Engineering Platform GitHub validation: passed.
- Browser-dashboard GitHub validation: passed.
- Verification framework, CodeQL, Semgrep and Trusted Delivery GitHub checks: passed.
- `ruff check` for changed Engineering Platform modules and tests: passed.
- `node --check tools/engineering/assets/dashboard.js`: passed.
- `git diff --check`: passed.

## Follow-up

Execution Host Preflight Level 3 (Capability Preflight) is the next bounded
increment. Forge capabilities may contribute workspace-specific readiness
checks without modifying the generic Execution Host; mission and Engineering
Action validation remain out of scope.
