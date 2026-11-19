# Live Run Dashboard Projection

- Date: 2026-08-08
- Implementation PR: [#793](https://github.com/pcvantol/djconnect/pull/793)
- Merge commit: `7436b0a9f18c8550e3f4dba0de98160c7c912807`
- Scope: Engineering Platform only
- Execution mode: Managed

## Completed outcome

Engineering Status now treats a live execution lease as authoritative for the
active-run projection, even when the watcher has already become idle after an
older run. Operators can therefore see the current execution rather than an
outdated idle state.

## Preserved boundaries

The change only affects dashboard presentation. Queue admission, execution
scheduling, retry behavior, runtime behavior, Forge ownership and product
behavior remain unchanged.

## Verification

- Dashboard-state unit suite passed: 78 tests.
- Browser dashboard suite passed: 153 tests.
- `git diff --check` passed.

## Finalization state

The implementation is merged. This immutable record is part of the separate,
governance-only Finalization that reconciles the rolling repository records.
