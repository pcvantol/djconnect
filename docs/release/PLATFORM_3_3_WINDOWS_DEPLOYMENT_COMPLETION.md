# Platform Release 3.3 — Windows ARM64 Deployment Completion

Date: 2026-07-17
Target: `windows_internal_arm64`
Result: `DEPLOYMENT_OPERATIONAL`

## Exact binding

- Manifest: `release-3.3.0-internal-20260714`
- Source candidate: `6c0c3c3478c81472e479184dc03e51fd095dc4b2`
- Artifact:
  `release-asset:pcvantol/djconnect-app-releases:windows/v3.3.0:DJConnect-Windows-arm64-3.3.0-unsigned.zip`
- SHA-256: `cbe379826731deb1d16c8af5510b4190a4f4949b1bf6589925de5d1eb66c5b47`

## Evidence

- Deployment workflow: [29583151393](https://github.com/pcvantol/djconnect-windows/actions/runs/29583151393)
  completed successfully after validating the approved manifest binding and
  exact artifact provenance.
- Post-deployment smoke: [29588039127](https://github.com/pcvantol/djconnect-windows/actions/runs/29588039127)
  completed successfully and was bound to that deployment evidence.
- Smoke observed installed version
  `3.3.0+6c0c3c3478c81472e479184dc03e51fd095dc4b2`; it verified health,
  process-alive startup evidence, the bounded interactive GUI relay, and a
  final result of `SMOKE_PASS`.
- The smoke ran on a Windows ARM64 self-hosted runner. Service orchestration
  remained separate from the interactive user-session relay; no elevated or
  broad user service identity was required for the release operation.

## Completion decision

The Windows ARM64 target is complete for this Internal Release. No other target
is implied by this result. Home Assistant and the required iPad target retain
their own independent authorization, deployment and immediate target-scoped
smoke prerequisites.
