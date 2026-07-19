# Platform Release 3.3 — Home Assistant Deployment Completion

Date: 2026-07-19
Target: `home_assistant_pi5`
Decision: `HOME_ASSISTANT_DEPLOYMENT_CONSUMER_QUALIFIED`

## Exact binding

- Manifest: `release-3.3.0-internal-20260714`
- Source candidate: `30978862a2889bbf35925914e9e2fdb1a707f8a6`
- Artifact:
  `release-asset:pcvantol/djconnect:internal-ha-30978862a2889bbf35925914e9e2fdb1a707f8a6:djconnect-home-assistant-integration-30978862a2889bbf35925914e9e2fdb1a707f8a6.tar.gz`
- SHA-256: `03231ba00c3e21188e70efa3ec332042a942ba118e9663c424545f62fbe4c224`

## Evidence

- The artifact producer run [29683064845](https://github.com/pcvantol/djconnect/actions/runs/29683064845)
  produced the immutable release asset and its SHA-256 was independently
  verified before operation.
- Manifest-bound deployment run [29683604435](https://github.com/pcvantol/djconnect/actions/runs/29683604435)
  succeeded through the private-network relay. It validated authorization,
  manifest binding and artifact provenance, installed the exact integration
  into Home Assistant OS and restarted Home Assistant Core.
- Separate post-deployment smoke run [29683901389](https://github.com/pcvantol/djconnect/actions/runs/29683901389)
  succeeded against that deployment evidence. It verified the installed
  integration version `3.3.0`, an authenticated Home Assistant WebSocket
  handshake and bounded Home Assistant Core startup/crash health.

## Qualification notes

The deployment logic and manifest were not redesigned. Qualification exposed
two bounded smoke-consumer defects: WebSocket bytes received with the HTTP
upgrade response were discarded, and the smoke parsed the HA OS CLI JSON
envelope at the wrong level. PRs [#181](https://github.com/pcvantol/djconnect/pull/181)
and [#182](https://github.com/pcvantol/djconnect/pull/182) corrected those
verification defects before the successful final smoke run.

## Completion decision

`HOME_ASSISTANT_DEPLOYMENT_CONSUMER_QUALIFIED`

All required Internal Release 3.3 targets now have independently authorized,
manifest-bound deployment and post-deployment smoke evidence. This completion
does not start operational burn-in or Release Certification; both remain
separate later decisions.
