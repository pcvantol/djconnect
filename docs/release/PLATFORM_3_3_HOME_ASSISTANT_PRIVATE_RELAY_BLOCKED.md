# Platform Release 3.3 — Home Assistant Private Relay

Date: 2026-07-14
Decision: `HOME_ASSISTANT_PRIVATE_RELAY_BLOCKED`

## Scope

The Home Assistant target was selected as the first private-network deployment
consumer. The safe artifact-producer portion is implemented in
`.github/workflows/home-assistant-release-artifact.yml`. It packages the exact
successful `main` integration source, records its SHA-256 and uploads redacted
artifact evidence. It has no target credentials and cannot deploy.

## Blocker

The distinct macOS runner `djconnect-private-network-relay` is registered and
online for `pcvantol/djconnect` with labels `self-hosted`, `macOS`, `ARM64`,
`internal-release` and `private-network-deployment`. The dedicated
`private-network-deployment` environment is also present. This capability is
separate from the existing Linux Home Assistant qualification runner and the
Apple native-build runner.

The environment has no deployment protection configuration and the repository
has no Home Assistant deployment/API or artifact-download credential scope;
the existing secret names contain only Trusted Delivery and Docker credentials.
Secret values were not read. The required target-specific credential and
installation scope is still absent. Using the Linux qualification runner,
reusing Apple build credentials or inventing target credentials/commands would
violate the frozen deployment boundary.

## Result

The checked-in deployment consumer and separate smoke workflow now exist in
`.github/workflows/deploy-home-assistant-private-network.yml` and
`.github/workflows/smoke-home-assistant-private-network.yml`. They are
intentionally fail-closed: the deployment workflow rejects every dispatch with
`PRIVATE_NETWORK_DEPLOYMENT_NOT_AUTHORIZED` until a canonical approved
operational manifest source exists. The smoke workflow records an inconclusive
result and fails after evidence publication until its required authenticated
WebSocket, startup-marker and bounded crash-log checks are implemented.

No credentials were accessed and no target was mutated. This is a static
consumer implementation, not operational qualification.

## Next authorized action

Provide an approved operational manifest source, then configure isolated HA
deployment/API and artifact-download credential scopes in
`private-network-deployment`, including the explicit target installation and
read-only smoke contract. Complete the required WebSocket, startup-marker and
bounded crash-log checks, then explicitly authorize a manifest-bound
operational qualification. Do not dispatch a workflow as release authorization.
