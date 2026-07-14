# Platform Release 3.3 — Home Assistant Private Relay

Date: 2026-07-14
Decision: `HOME_ASSISTANT_PRIVATE_RELAY_SMOKE_IMPLEMENTED`

## Scope

The Home Assistant target was selected as the first private-network deployment
consumer. The safe artifact-producer portion is implemented in
`.github/workflows/home-assistant-release-artifact.yml`. It packages the exact
successful `main` integration source, records its SHA-256 and uploads redacted
artifact evidence. It has no target credentials and cannot deploy.

## Relay boundary

The distinct macOS runner `djconnect-private-network-relay` is registered and
online for `pcvantol/djconnect` with labels `self-hosted`, `macOS`, `ARM64`,
`internal-release` and `private-network-deployment`. The dedicated
`private-network-deployment` environment is also present. This capability is
separate from the existing Linux Home Assistant qualification runner and the
Apple native-build runner.

The private-network relay validates its own target-specific configuration at
dispatch time without reading or disclosing secret values. It requires isolated
installation, API-token and container scope. Missing scope remains a
fail-closed deployment-time condition. Using the Linux qualification runner,
reusing Apple build credentials or inventing target credentials/commands would
violate the frozen deployment boundary.

## Result

The checked-in deployment consumer and separate smoke workflow are
`.github/workflows/deploy-home-assistant-private-network.yml` and
`.github/workflows/smoke-home-assistant-private-network.yml`. They validate
the approved central manifest, exact artifact provenance and target scope
before target contact. The smoke workflow verifies authenticated REST and
WebSocket health, installed integration version, container startup/restart
state and bounded DJConnect crash findings before publishing redacted evidence.

No credentials were accessed and no target was mutated while implementing this
contract. Operational qualification still requires a separately authorized,
manifest-bound deployment and post-deployment smoke.

## Next authorized action

Provide the approved operational manifest and isolated HA deployment/API scope
in `private-network-deployment`, then explicitly authorize a manifest-bound
deployment. Dispatch the separate read-only smoke only after deployment
success. Do not dispatch a workflow as release authorization.
