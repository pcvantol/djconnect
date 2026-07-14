# Post-Deployment Production Smoke Test Policy

Status: `ARCHITECTURE_ALIGNED`  
Scope: Platform Release Engineering Generation 1

Post-deployment smoke validation is a bounded, non-destructive deployment
evidence capability. It runs only after an authorized deployment mutation has
completed. It proves canonical-route reachability, expected-version read-back,
basic startup health and absence of immediate crash behaviour. It is not CI,
qualification, product verification, functional testing, broad monitoring or
product acceptance testing.

The canonical sequence is:

`authorized deployment → bounded stabilization → smoke validation → redacted smoke evidence → DEPLOYMENT_OPERATIONAL | DEPLOYMENT_SMOKE_FAILED`

The qualified macOS Private-Network Deployment Relay executes only
manifest-allowlisted private-target checks that GitHub-hosted runners cannot
reach. It is not a network scanner: it may inspect only an allowlisted route,
endpoint class and bounded runtime source. Smoke checks are read-only and may
not create or revoke pairing credentials, restart a service, flash or reboot a
device, alter application state, invoke full Verification scenarios, or change
CI, qualification or release-readiness evidence.

## Preconditions and target selection

The smoke workflow consumes the same approved deployment manifest and exact
`candidate_sha`, `platform_version`, `manifest_id`, `artifact_id`,
`artifact_sha256`, `target`, `release_profile` and deployment-workflow run
reference as the completed deployment. It rejects a target not allowlisted by
that manifest, a candidate/version/artifact/checksum mismatch, missing
deployment success evidence, stale or superseded evidence, mutable artifact
selection, or a request to inspect a route outside the target contract.

Only an explicitly deployed target may be smoke checked. A target marked
`optional` in the manifest may report `SMOKE_NOT_APPLICABLE` or
`SMOKE_INCONCLUSIVE` without blocking the overall decision. For every required
target, `SMOKE_INCONCLUSIVE` fails closed.

## Route and health contract

ICMP ping is diagnostic context only and is never a pass condition. The smoke
workflow validates a canonical application route using the least invasive
meaningful read-only request: an HTTP health or version endpoint, authenticated
status endpoint, WebSocket handshake, local pairing handshake or
service-specific readiness response. It records the route class rather than a
sensitive complete URL.

| Target | Required bounded checks where applicable |
| --- | --- |
| Raspberry Pi runtime | Name/IP resolution, HTTP(S) or local API response, expected version/build identity, allowlisted service active, startup marker, no restart loop or new fatal marker in bounded recent logs. |
| ESP32 runtime | Name/IP resolution, web/status endpoint, expected firmware version, post-OTA reconnect, Home Assistant entity availability, no observed reboot loop or exposed crash/reset indicator. |
| Home Assistant and DJConnect integration | Local route, configured remote route, authenticated HTTP API, authenticated WebSocket handshake, core status, integration version/load result, required entities/platforms and read-only local pairing route. |
| Apple private deployment | Installed bundle identifier and version, accepted signing/install state, safe launch/read-back where supported, and paired-Watch companion validation when required by the manifest. |
| Windows internal deployment | Installed package/version, safe launch and bounded process-alive read-back, immediate crash-event absence and expected local route where applicable. |

Home Assistant smoke evidence distinguishes `local_route_failure`,
`remote_route_failure`, `authentication_failure`, `websocket_failure`,
`integration_setup_failure` and `entity_or_platform_absence`; HTTP and
WebSocket are independent checks. Local pairing uses an existing authenticated
read-only handshake and expected protocol-version read-back only. It may not
mutate pairing or tokens.

## Bounded logs and stabilization

Each target defines a finite stabilization contract: initial delay, bounded
retry count, interval or bounded backoff, and maximum window. The workflow
never waits indefinitely. It may inspect only a bounded recent startup window
through an allowlisted service/API read-back; it does not run broad shell
diagnostics or retain complete logs.

The smoke check fails for a new critical error, deployment-related startup
failure, missing required startup evidence, repeated fatal pattern, restart
loop, crash traceback, repeated watchdog/reset event or version mismatch.
Documented known non-blocking warnings are allowlisted and do not fail smoke.
Evidence contains only redacted findings, hashes or permitted bounded excerpts.

## Result and completion rule

Each target publishes exactly one result:

- `SMOKE_PASS`
- `SMOKE_FAIL`
- `SMOKE_NOT_APPLICABLE`
- `SMOKE_INCONCLUSIVE`

A deployment is `DEPLOYMENT_OPERATIONAL` only when its mutation succeeded,
artifact and manifest evidence match, every required smoke target passes,
required local and remote routes are reachable, expected versions are observed,
and no critical startup or crash finding exists. Otherwise it is
`DEPLOYMENT_SMOKE_FAILED`; release execution is incomplete, qualification
evidence remains unchanged, dependent deployment stages stop where required,
and the record includes recovery guidance. No destructive rollback is
automatic.

## Verification boundary

The Verification Platform owns functional and integration scenarios, hardware
qualification, cross-platform behaviour, destructive/state-changing tests and
burn-in. Post-deployment smoke validation owns only reachability, protocol
handshake, version read-back, startup health and absence of immediate crash
behaviour. The smoke workflow must not invoke full Verification.
