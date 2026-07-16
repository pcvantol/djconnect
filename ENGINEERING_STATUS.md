# DJConnect Engineering Status

**Status:** Operational handoff
**Updated:** 2026-07-16

## Current engineering increment

Native deployment-readiness preflight remediation. The shared preflight now
uses PowerShell 7 on Windows and Bash on non-Windows runners, removing its
implicit WSL dependency from Windows deployment consumers. This record does
not qualify Home Assistant or Windows. The separate PR #144 bootstrap SHA
repin remains deferred and is not changed by this remediation.

## Current engineering program

DJConnect Product Development remains the primary program; Platform Release
3.3 is separate temporary operational work.

## Current repository truth

PR [#144](https://github.com/pcvantol/djconnect/pull/144) was squash-merged
into `main` as `452bed7655e579d3fb12b7b379f8fc0b70a8c342`. Its pre-merge
candidate was `aee1687876c279d758f1404f9ca9e1563e310276`, with successful
required checks and Owner Authorization. Its complete evidence and the nine
temporary branch references are recorded in
`docs/release/MACOS_RUNNER_BOOTSTRAP_MERGE_READINESS.md`. The preparation is
reviewable in PR [#146](https://github.com/pcvantol/djconnect/pull/146).

Platform Release 3.3 remains separately operational and partially deployed.

The current manifest is
`release-3.3.0-internal-20260714`, status
`APPROVED_PARTIAL_DEPLOYMENT_OPERATIONAL`. Objective GitHub Actions evidence
confirms successful deployment and smoke for `cloudflare_workers_production`,
`cloudflare_pages_production`, `rbpi-djconnect`,
`esp32_lilygo_t_embed_s3`, `apple_private_device/macbook` and
`apple_private_device/iphone` with required paired-Watch validation. The
canonical execution ledger is
`docs/release/PLATFORM_3_3_CURRENT_MAIN_MANIFEST_PROPOSAL.json`.

## Known blockers and limitations

- Home Assistant and Windows lack final target-specific deployment and smoke
  qualification evidence. The Internal Release is therefore incomplete.
- PR #144 must retain its feature branch until all nine documented temporary
  references are repinned to an immutable SHA on merged `main`.
- Windows requires a machine-level PowerShell 7 installation visible to its
  service account, followed by an immutable consumer pin update to the merged
  shared preflight action. WSL is not a deployment prerequisite.

## Deferred work

- Update the Windows consumer to the merged shared preflight SHA, remove its
  Bash prerequisite and qualify the already authorized target through
  manifest-bound deployment and immediate target-scoped smoke.
- Repin the PR #144 bootstrap references to immutable current-`main` SHAs in a
  separately reviewed increment.

## Recommended next prompt

Draft only — Platform Release Engineering: after this shared-preflight
remediation merges, update the Windows consumer to its immutable SHA and
qualify the already authorized Windows target. The separate #144 bootstrap
repin remains required before its retained feature branch can be deleted. Do
not begin either follow-up automatically.
