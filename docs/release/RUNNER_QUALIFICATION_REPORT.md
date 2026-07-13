# Self-Hosted Runner Qualification Report

Date: 2026-07-13
Decision: `RUNNER_INFRASTRUCTURE_NOT_QUALIFIED`

## Evidence collected

The GitHub Actions REST endpoint
`repos/pcvantol/<repository>/actions/runners` was queried read-only for all ten
Repository Ownership repositories. Each returned an empty runner list. The
organization runner endpoint is unavailable for this personal-account scope.

## Qualification matrix

| Required role | Online | Trusted scope | Labels | Toolchain | Workspace / cleanup | Evidence upload | Result |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Apple | No runner | Not established | Not established | Not inspected | Not inspected | Not inspected | Not qualified |
| Windows | No runner | Not established | Not established | Not inspected | Not inspected | Not inspected | Not qualified |
| Firmware | No runner | Not established | Not established | Not inspected | Not inspected | Not inspected | Not qualified |
| Pi | No runner | Not established | Not established | Not inspected | Not inspected | Not inspected | Not qualified |
| Home Assistant | No runner | Not established | Not established | Not inspected | Not inspected | Not inspected | Not qualified |
| Deployment | No runner | Not established | Not established | Not inspected | Not inspected | Not inspected | Not qualified |

## Required qualification evidence

Each runner must produce a redacted evidence artifact containing its identity,
GitHub labels, runner version, operating-system and toolchain versions,
workspace-cleanup result, cache policy, artifact-upload probe and the exact
workflow SHA. For build roles it must also prove the platform compiler/SDK and
one representative build. Deployment runners additionally prove restricted
credential access without exposing credential values.

No runner is qualified by this report. This is an objective precondition, not
a waiver: `INTERNAL_RELEASE` remains blocked until every required role passes.
