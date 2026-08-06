# Show Workspace Free Disk Space

- Prompt ID and title: `ENG-DASHBOARD-WORKSPACE-FREE-DISK-SPACE` — Show Workspace Free Disk Space
- Generation and engineering program: Generation 2 — Platform Evolution
- Branch: `codex/workspace-free-disk-space`
- Commit: `54a5b4ea79113d5e931370ef42e3aef456710221`
- Pull request: [#769](https://github.com/pcvantol/djconnect/pull/769)
- Decision and execution date: 2026-08-06 — merged
- Created: 2026-08-06
- Updated: 2026-08-06

## Decision

Expose the remaining capacity of the filesystem that contains the Engineering
Platform workspace in the Workspace dashboard card. Format the read-only
value in GB and refresh it for every dashboard page request.

## Validation

- `python3 -m unittest tests.engineering.test_dashboard` (66 tests)
- `node --check tools/engineering/assets/dashboard.js`
- `node --check tools/engineering/assets/dashboard_locales.mjs`
- `git diff --check`
- GitHub Actions browser dashboard validation was retried after an unrelated
  missing-log-row flake; the focused browser assertion passed locally.

## Known limitations

The value is a point-in-time filesystem measurement and can change between
page requests as the volume is used.

## Deferred work

No capacity alerting, cleanup automation, Forge behavior, queue admission,
execution, runtime, scheduling or lifecycle behavior is introduced.

## Recommended next prompt

Merge and verify this governance-only Finalization, then perform the required
local workspace cleanup before starting another capability.
