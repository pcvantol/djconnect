# Platform Release 3.3 — Operational Manifest Preparation

Date: 2026-07-14  
Decision: `PLATFORM_RELEASE_3_3_MANIFEST_PREPARED_PENDING_EXPLICIT_APPROVAL`

## Scope

This record prepares the exact, artifact-bound manifest for the requested
`3.3.0` `INTERNAL_RELEASE`. It does not approve that manifest and does not
authorize or dispatch deployment, signing, installation, OTA or smoke work.

## Prepared manifest

Manifest ID: `release-3.3.0-internal-20260714`
Canonical binding: [`PLATFORM_3_3_CURRENT_MAIN_MANIFEST_PROPOSAL.json`](PLATFORM_3_3_CURRENT_MAIN_MANIFEST_PROPOSAL.json)

The manifest binds these required targets: `home_assistant_pi5`,
`cloudflare_workers_production`, `cloudflare_pages_production`,
`esp32_lilygo_t_embed_s3`, `rbpi-djconnect`, Apple `macbook`, `iphone`
(with paired Watch validation) and `ipad`, plus `windows_internal_arm64`.

All target artifacts have an exact source SHA, immutable artifact identifier,
download location and SHA-256. The consolidated ledger is in
[`PLATFORM_RELEASE_ARTIFACT_MANIFEST.md`](PLATFORM_RELEASE_ARTIFACT_MANIFEST.md).

## Approval gate

The manifest remains unapproved until the maintainer explicitly approves this
exact manifest ID and its listed target/artifact bindings. Approval does not
run a workflow. It merely permits separately authorized, manifest-bound
deployment and post-deployment smoke dispatches.

## Known operational gates

- Each deployment consumer must independently validate its least-privilege
  credential/install scope without exposing a secret in this manifest.
- Existing fail-closed consumers remain authoritative: a consumer that lacks
  an approved-manifest source or target capability must stop before mutation.
- Apple artifacts are unsigned handoff artifacts. Local Developer signing is
  limited to the Apple Secure Distribution Relay; no TestFlight, App Store or
  Mac App Store publication is in scope.
- Apple Watch remains a required paired-iPhone companion validation, not a
  direct target or independent artifact.

## Next action

Request explicit approval of `release-3.3.0-internal-20260714`. Do not begin
deployment or smoke automatically.
