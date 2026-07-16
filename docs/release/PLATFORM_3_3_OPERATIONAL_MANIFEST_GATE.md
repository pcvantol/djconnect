# Platform Release 3.3 — Operational Manifest Gate

Date: 2026-07-15
Decision: `PLATFORM_RELEASE_3_3_MANIFEST_APPROVED_PARTIAL_DEPLOYMENT_OPERATIONAL`

## Result

The `3.3.0` Internal Release now has an exact-SHA, checksum-bound manifest
candidate: [`PLATFORM_3_3_CURRENT_MAIN_MANIFEST_PROPOSAL.json`](PLATFORM_3_3_CURRENT_MAIN_MANIFEST_PROPOSAL.json).

| Gate | Result |
| --- | --- |
| Required target set | Complete |
| Exact source SHA and artifact ID/checksum bindings | Complete and verified |
| Artifact publication | Complete for the applicable distribution repositories |
| Deployment evidence | Partial: API, Website, Raspberry Pi, ESP32, Apple MacBook and Apple iPhone with paired Watch succeeded |
| Post-deployment smoke evidence | Partial: API, Website, Raspberry Pi, ESP32, Apple MacBook and Apple iPhone with paired Watch succeeded |
| Explicit operational-manifest approval | Updated manifest approved at `2026-07-14T19:00:45Z` |

## Consequence

The updated manifest is approved, including the qualified Pi artifact
rebinding: source `661e26e7`, checksum
`6fa3f2f3de6062b8d69c48886bf04374592bbbe404a2856b89450e1acbe1422a`.
Six required targets are operationally complete: `cloudflare_workers_production`,
`cloudflare_pages_production`, `rbpi-djconnect` and
`esp32_lilygo_t_embed_s3`, `apple_private_device/macbook` and
`apple_private_device/iphone` with required paired-Watch validation. Each
result is manifest-bound and has a separate successful post-deployment smoke
run. Home Assistant and Windows remain open; this is not a complete Internal
Release.

## Next action

Verify the Home Assistant environment readiness before using its already
recorded exact target authorization. Windows now has an exact target-scoped
authorization and a qualified Windows ARM64 service runner; its deployment may
be dispatched only after this authorization record is merged. Its
post-deployment smoke may run only after that target's successful deployment;
all remaining targets remain independent.
