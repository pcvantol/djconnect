# Platform Release 3.3 — Static Deployment Consumers Completion

Date: 2026-07-14  
Decision: `PLATFORM_RELEASE_3_3_STATIC_DEPLOYMENT_CONSUMERS_NOT_QUALIFIED`

## Executive summary

The ESP32, Apple and Windows source repositories now contain separate,
manifest-input deployment and post-deployment smoke workflow entrypoints. The
Apple and Windows interfaces accept the canonical immutable identity; Apple
adds a schema-bound direct-device target and paired-Watch validation. ESP32
uses the canonical HA Update target and firmware artifact naming contract.

The API consumer's release artifact, deployment and smoke workflows were
rechecked on current `main`. Its legacy manual production workflow now refuses
execution because it does not carry the manifest-bound artifact and checksum
inputs required by the frozen deployment contract.

No workflow was dispatched and no target, artifact publication, credential,
firmware, database or production service was mutated.

## Scope

- `pcvantol/djconnect-esp32`: `deploy-esp32-firmware.yml` and
  `esp32-post-deployment-smoke.yml`;
- `pcvantol/djconnect-app`: `apple-secure-distribution-relay.yml` and
  `apple-post-deployment-smoke.yml`;
- `pcvantol/djconnect-windows`: `windows-internal-deployment.yml` and
  `windows-post-deployment-smoke.yml`;
- `pcvantol/djconnect-api`: release-artifact/deployment/smoke workflows and
  the blocked legacy production path.

## Verification and evidence

- All ten changed GitHub Actions workflow files parsed successfully.
- `git diff --check` passed in API, ESP32, Apple and Windows repositories.
- API: `npx tsc --noEmit`, `npm test -- --run` (40 tests) and
  `npx wrangler deploy --dry-run` passed.
- ESP32: `test/native/test_release.sh` passed.
- Apple current-main CI run
  [`29329610951`](https://github.com/pcvantol/djconnect-app/actions/runs/29329610951)
  passed, including Swift tests and unsigned macOS/iOS builds.

## Known blockers

1. No approved current-main operational manifest declares required targets,
   artifact IDs or SHA-256 bindings.
2. No target credential, signing, installation or hardware scope has been
   authorized for operational dispatch.
3. No deployment evidence exists to permit a smoke run; required runtime
   health/version read-back contracts are incomplete.
4. Distribution consumers remain deferred until an approved manifest makes
   them required.

## Qualification decision and next action

`PLATFORM_RELEASE_3_3_STATIC_DEPLOYMENT_CONSUMERS_NOT_QUALIFIED`.

The static implementation is reviewable and fail-closed, but it is not an
operational deployment capability. Do not dispatch these workflows or begin
candidate reconstruction. The next authorized release-engineering action is
to provide a complete approved operational manifest with target, artifact,
checksum and evidence bindings; only then may the required consumers be
qualified through separate deployment and smoke dispatches.
