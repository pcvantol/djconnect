# DJConnect Engineering Status

**Status:** Operational handoff
**Updated:** 2026-07-16

## Current engineering increment

Post-merge repin of the macOS runner-host bootstrap workflow references. This
increment replaces the nine temporary PR #144 candidate references with the
immutable merged-`main` SHA `3d7d24a84b3aaacb8f2fb229e09c33da85e0545d`.
It changes no bootstrap behaviour, deployment logic, release manifest or
target authorization.

## Current engineering program

DJConnect Product Development remains the primary program; Platform Release
3.3 is separate temporary operational work.

## Current repository truth

PR [#144](https://github.com/pcvantol/djconnect/pull/144) was squash-merged
into `main` as `452bed7655e579d3fb12b7b379f8fc0b70a8c342`. Its pre-merge
candidate was `aee1687876c279d758f1404f9ca9e1563e310276`, with successful
required checks and Owner Authorization. The verified current-`main` repin
target contains that merge and the reusable governance fallback. The complete
evidence and repin inventory are recorded in
`docs/release/MACOS_RUNNER_BOOTSTRAP_MERGE_READINESS.md`.

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
- PR #144 must retain its feature branch until this reviewable repin is merged
  and its checks are green.
- Home Assistant and Windows remain independently unqualified Release 3.3
  targets; the Windows consumer adoption is reviewed separately.

## Deferred work

- Delete the retained PR #144 feature branch after this repin PR merges with
  green validation.
- Qualify the already authorized Windows target through manifest-bound
  deployment and immediate target-scoped smoke after its consumer update
  merges.

## Recommended next prompt

After this repin PR merges and its checks are green, delete the retained PR
#144 feature branch. Treat Windows deployment qualification as a separate
authorized Platform Release Engineering operation.
