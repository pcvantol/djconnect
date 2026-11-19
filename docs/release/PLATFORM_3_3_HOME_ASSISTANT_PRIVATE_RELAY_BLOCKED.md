# Platform Release 3.3 — Home Assistant Private Relay

Date: 2026-07-14
Decision: `HOME_ASSISTANT_PRIVATE_RELAY_HAOS_NATIVE_IMPLEMENTED`

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

The production target runs Home Assistant OS on the Pi 5. The private-network
relay therefore validates a host-key-pinned SSH route to HA OS and its
`/config` volume, then invokes only the supported `ha core` lifecycle commands.
It does not assume that the macOS relay can manage the target through Docker or
Compose. Required job-only environment secrets are the HA OS host, port, user,
private key and pinned `known_hosts` entry, together with the existing
read-only Home Assistant API URL/token for smoke. Missing scope remains a
fail-closed deployment-time condition. Using the Linux qualification runner,
reusing Apple build credentials or inventing target credentials/commands would
violate the frozen deployment boundary.

The required Environment secrets are
`DJCONNECT_HA_OS_DEPLOY_HOST`, `DJCONNECT_HA_OS_DEPLOY_PORT`,
`DJCONNECT_HA_OS_DEPLOY_USER`, `DJCONNECT_HA_OS_DEPLOY_SSH_PRIVATE_KEY` and
`DJCONNECT_HA_OS_DEPLOY_SSH_KNOWN_HOSTS`. Smoke additionally uses the existing
`DJCONNECT_HA_SMOKE_API_URL` and `DJCONNECT_HA_SMOKE_API_TOKEN`. The known-host
entry is supplied by the owner from the approved HA OS endpoint; the workflow
never accepts an unpinned host key or scans the network to discover one.

## Result

The checked-in deployment consumer and separate smoke workflow are
`.github/workflows/deploy-home-assistant-private-network.yml` and
`.github/workflows/smoke-home-assistant-private-network.yml`. They validate
the approved central manifest, exact artifact provenance and target scope
before target contact. The deployment workflow verifies the artifact both on
the relay and on HA OS, atomically replaces only
`/config/custom_components/djconnect`, retains a run-scoped pre-deployment
copy for operator-led recovery and runs `ha core check` plus `ha core restart`.
The separate smoke workflow verifies authenticated REST and WebSocket health,
the installed integration version read back from HA OS, HA Core information and
bounded DJConnect crash findings before publishing redacted evidence.

No credentials were accessed and no target was mutated while implementing this
contract. Operational qualification still requires a separately authorized,
manifest-bound deployment and post-deployment smoke.

## Next authorized action

Provide the approved operational manifest and isolated HA deployment/API scope
in `private-network-deployment`, then explicitly authorize a manifest-bound
deployment. Dispatch the separate read-only smoke only after deployment
success. Do not dispatch a workflow as release authorization.
