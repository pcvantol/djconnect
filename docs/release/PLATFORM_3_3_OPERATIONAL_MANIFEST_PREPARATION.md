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
after its deployment and smoke contracts became operational. The rebound exact
manifest was explicitly reapproved at `2026-07-14T20:03:33Z`. The prior Home
Assistant artifact later became unavailable from GitHub Actions; its binding is
therefore superseded by the verified current-main source
`0227e95ba10e8cc9256185a3bec6d22f86e286d4`, successful artifact workflow run
`29427139585`, artifact `8347737416` and SHA-256
`88c065ca672e7ba7155a30aa7b4737075d41e629cc748c8a60385ae1a3464aa9`. The
maintainer explicitly approved this exact `home_assistant_pi5` binding and
authorized its manifest-bound deployment followed by separate post-deployment
smoke. No other target is authorized by that approval.

The website source/artifact binding was then renewed to current
`pcvantol/djconnect-website` source
`64f95dcb8a2cf2da523c46f08ed5b07fdcdf6daa`, successful artifact workflow run
`29424048694`, artifact `8346470431` and SHA-256
`dff7ba59c2cf3cd299670487d09ba6e98d845659736dfd0e9770e884e8127027`. The
maintainer explicitly approved this exact `cloudflare_pages_production`
binding and its manifest-bound deployment followed by separate post-deployment
smoke.

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

After this manifest binding is merged to `main`, dispatch either authorized
target. Dispatch its separate smoke workflow only after that target's
deployment succeeds.
