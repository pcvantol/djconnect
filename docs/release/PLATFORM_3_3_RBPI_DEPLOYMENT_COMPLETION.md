# Platform Release 3.3 — Raspberry Pi Deployment Completion

Date: 2026-07-14
Target: `rbpi-djconnect`
Result: `DEPLOYMENT_OPERATIONAL`

## Exact binding

- Manifest: `release-3.3.0-internal-20260714`
- Source candidate: `661e26e78b45acb2bade57a63c0f68effc3652be`
- Artifact: `release-asset:pcvantol/djconnect-pi-releases:v3.3.0:djconnect-pi-3.3.0.tar.gz`
- SHA-256: `6fa3f2f3de6062b8d69c48886bf04374592bbbe404a2856b89450e1acbe1422a`

## Evidence

- Deployment workflow: [29361051673](https://github.com/pcvantol/djconnect-pi/actions/runs/29361051673)
  validated the qualified source, approved central manifest, published artifact
  and target installation.
- Post-deployment smoke: [29361739009](https://github.com/pcvantol/djconnect-pi/actions/runs/29361739009)
  was bound to that deployment evidence and verified the Pi at version `3.3.0`.
- Smoke runtime evidence records `djconnect-api.service` and
  `djconnect-client.service` as `active`, with local device API identity
  `client_type: raspberry_pi` and `transport: local_only`.

## Completion decision

The Raspberry Pi target is complete for this Internal Release. No other target
is implied by this result. Each remaining target still requires its own
authorization, deployment and immediate target-scoped smoke.
