# Provider Usage Run-Detail Regression Coverage

- Prompt ID: `inbox-992d374556a9412e8118a70fa8c28b2c`
- Title: Provider Usage Run-Detail Regression Coverage
- Generation: Engineering Platform Generation 1
- Engineering program: Platform Engineering
- Branch: `codex/provider-usage-run-detail-regression`
- Commit: `5b47075f7dddd2ca7682281826725a36f044f682`
- Pull request: [#862](https://github.com/pcvantol/djconnect/pull/862)
- Decision: merged implementation; dedicated governance-only Finalization required
- Execution date: 2026-08-18
- Created: 2026-08-18
- Updated: 2026-08-18

## Outcome

Added focused regression coverage for the existing Prompt History run-detail
provider-usage projection. The coverage verifies a selected persisted run's
summary includes cached and uncached input, invocation count, estimates,
maximum input and speed state, while unavailable invocation detail remains
unavailable rather than appearing as fabricated zero-valued metrics.

## Validation

- Engineering dashboard and provider-usage regression tests passed.
- `git diff --check` passed.
- Required GitHub pull-request checks reached terminal success or skipped state.

## Known limitations

The increment covers only the existing read-model projection. Historical
aggregate-only provider usage retains its established fallback behavior.

## Deferred work

No production telemetry change, storage change, dashboard redesign, Forge
change, lifecycle change or model-selection change is introduced.

## Recommended next prompt

Select the next bounded capability from canonical repository and backlog
evidence after this Finalization merges and Workspace Cleanup establishes
`WORKSPACE_READY`.
