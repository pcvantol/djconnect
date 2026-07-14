# Platform Release 3.3 — Operational Manifest Preparation

Date: 2026-07-14  
Decision: `PLATFORM_RELEASE_3_3_MANIFEST_APPROVED_DEPLOYMENT_DISPATCH_PENDING`

## Scope

This record contains the approved exact, artifact-bound manifest for the
requested `3.3.0` `INTERNAL_RELEASE`. It does not authorize or dispatch a
deployment, signing, installation, OTA or smoke workflow.

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

## Approval record and artifact rebinding

The maintainer explicitly approved the updated exact manifest bindings at
`2026-07-14T19:00:45Z`, including the Pi `v3.3.0` artifact republished from
qualified source SHA `661e26e78b45acb2bade57a63c0f68effc3652be` with SHA-256
`6fa3f2f3de6062b8d69c48886bf04374592bbbe404a2856b89450e1acbe1422a`.
That approval superseded the earlier binding approval. The API release
artifact was subsequently rebound to source
`6f6dee8a6edf72b8a48fa347ef587ede2976badd`, artifact `8323208436` and
SHA-256 `f9d8c29787297a939d16e6f3fab3f9cd4455518def4565830b5ca57f76a80819`
after its deployment and smoke contracts became operational. The old approval
is therefore superseded and a fresh exact-manifest approval is required.
Approval never runs a workflow; every deployment and smoke remains a
separately authorized, manifest-bound operation.

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

Obtain a fresh exact-manifest approval, then separate authorization for one
target-scoped deployment. Do not begin deployment or smoke automatically.
