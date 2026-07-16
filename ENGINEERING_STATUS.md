# DJConnect Engineering Status

**Status:** Operational handoff
**Updated:** 2026-07-16

## Current engineering increment

Platform Evolution — pre-merge preparation for PR #144, the macOS runner-host
bootstrap. This increment is documentation and merge-readiness only: it
corrects the PR description, identifies temporary candidate workflow pins and
records the mandatory post-merge repin sequence. It does not change bootstrap,
runner, CI, governance, release or deployment behaviour.

## Current engineering program

DJConnect Product Development remains the primary program; Platform Release
3.3 is separate temporary operational work.

## Current repository truth

PR [#144](https://github.com/pcvantol/djconnect/pull/144) is open and
mergeable for candidate `aee1687876c279d758f1404f9ca9e1563e310276`; its
required checks and Owner Authorization are successful. Its complete
pre-merge evidence and the nine temporary branch references are recorded in
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

## Deferred work

- Qualify the remaining required targets only through separately authorized,
  manifest-bound deployment and immediate target-scoped smoke.
- Repin the PR #144 bootstrap references only after its merge commit exists on
  `main`.

## Recommended next prompt

Draft only — after PR #144 merges, repin its nine temporary bootstrap workflow
references to an immutable `main` SHA and validate them before deleting the
feature branch. Do not begin that post-merge increment automatically.
