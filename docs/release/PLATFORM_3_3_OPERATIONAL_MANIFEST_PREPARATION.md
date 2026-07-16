# Platform Release 3.3 — Operational Manifest Preparation

Date: 2026-07-15
Decision: `PLATFORM_RELEASE_3_3_MANIFEST_APPROVED_PARTIAL_DEPLOYMENT_OPERATIONAL`

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

The maintainer authorized the exact ESP32 firmware binding for
`esp32_lilygo_t_embed_s3`: source
`9f8a32482b8ea9fb322a29688955f5a4f26b001d`, public firmware artifact
`release-asset:pcvantol/djconnect-firmware:v3.3.0:djconnect-lilygo-t-embed-s3-v3.3.0.bin`
and SHA-256 `c25444d3ef414489848fd2d8de624785c82eb90195cc861bcb63085e0df3ceeb`.
Its separately merged consumer accepts only this manifest-bound operation and
performs read-back smoke after deployment.

The maintainer authorized the exact Windows ARM64 binding for
`windows_internal_arm64`: source
`6c0c3c3478c81472e479184dc03e51fd095dc4b2`, public artifact
`release-asset:pcvantol/djconnect-app-releases:windows/v3.3.0:DJConnect-Windows-arm64-3.3.0-unsigned.zip`
and SHA-256 `cbe379826731deb1d16c8af5510b4190a4f4949b1bf6589925de5d1eb66c5b47`.
The Windows ARM64 service runner was qualified successfully in run
[`29481814760`](https://github.com/pcvantol/djconnect-windows/actions/runs/29481814760).
This authorization record does not dispatch deployment; the manifest-bound
deployment and separate smoke remain required after its merge.

## Operational execution evidence

The authorized website deployment completed successfully through the bounded
Cloudflare Pages consumer. Deployment run
[`29441732130`](https://github.com/pcvantol/djconnect-website/actions/runs/29441732130)
validated the exact artifact checksum before publishing; post-deployment smoke
run [`29441809581`](https://github.com/pcvantol/djconnect-website/actions/runs/29441809581)
then verified deployment-evidence identity and the read-only production route.
The website target decision is `DEPLOYMENT_OPERATIONAL`.

The first dispatch failed safely before Cloudflare contact because the workflow
assumed an artifact root path that `download-artifact` does not provide. Website
PR [#25](https://github.com/pcvantol/djconnect-website/pull/25) remediated the
path handling by locating exactly one archive before checksum verification and
unpacking. The successful retry is the operational evidence above.

The authorized ESP32 OTA deployment then completed successfully through the
Home Assistant Update-entity consumer. Deployment run
[`29446964025`](https://github.com/pcvantol/djconnect-esp32/actions/runs/29446964025)
validated the approved manifest binding and requested the exact firmware
artifact. Its separately dispatched smoke run
[`29447045601`](https://github.com/pcvantol/djconnect-esp32/actions/runs/29447045601)
passed after bounded polling for the OTA restart. The smoke verified the
expected `3.3.0` version through Home Assistant and by direct local-device
read-back. The ESP32 target decision is `DEPLOYMENT_OPERATIONAL`.

The authorized Apple MacBook deployment completed through the Secure
Distribution Relay in run
[`29452344685`](https://github.com/pcvantol/djconnect-app/actions/runs/29452344685),
followed by successful post-deployment smoke in run
[`29452385823`](https://github.com/pcvantol/djconnect-app/actions/runs/29452385823).
The authorized iPhone deployment with required paired-Watch validation
completed in run
[`29453894383`](https://github.com/pcvantol/djconnect-app/actions/runs/29453894383).
That relay explicitly installed the embedded Watch companion. Its successful
post-deployment smoke run
[`29455024770`](https://github.com/pcvantol/djconnect-app/actions/runs/29455024770)
verified the installed iPhone and Watch applications against manifest version
`3.3.0`. Both Apple target decisions are `DEPLOYMENT_OPERATIONAL`.

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

Do not dispatch a target automatically. The recorded `home_assistant_pi5`
authorization remains pending environment-readiness verification. Windows now
has its own exact target-scoped authorization and qualified service-runner
evidence, pending only the manifest-bound deployment and separately dispatched
post-deployment smoke after this record is merged. Every operation requires
successful deployment and separately dispatched post-deployment smoke.
