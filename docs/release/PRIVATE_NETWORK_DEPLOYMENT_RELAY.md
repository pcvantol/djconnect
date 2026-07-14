# Private Network Deployment Relay

Status: `ARCHITECTURE_ALIGNED`  
Scope: Platform Release Engineering Generation 1

The qualified self-hosted macOS runner has three independent, bounded roles:

1. Apple Native Build Runner
2. Private Network Deployment Relay
3. Apple Secure Distribution Relay

All roles execute only through separate GitHub Actions jobs. They have distinct
permissions, secrets and workspaces. The Platform Release Runtime remains
orchestration-only and never receives deployment or signing authority.

## Relay contract

The private-network deployment relay may consume an approved release manifest,
retrieve its exact qualified artifact, validate artifact identity and SHA-256,
initiate one allowlisted deployment action, perform bounded read-back and
upload redacted evidence. It cannot build source, generate artifacts, select a
`latest` release, publish artifacts, create tags or GitHub Releases, change
qualification evidence or perform unrelated private-network administration.

Every dispatch binds `candidate_sha`, `platform_version`, `manifest_id`,
`artifact_id`, `artifact_sha256`, `target`, `release_profile`, `action` and
`execution_mode`; an Apple dispatch additionally binds `target_device`. The
only mutation values are `action=deployment` and `execution_mode=execute`.
Missing, stale or unqualified evidence; a manifest/SHA/artifact/checksum/target
mismatch; an unknown target device; or a mutable selector returns
`PRIVATE_NETWORK_DEPLOYMENT_NOT_AUTHORIZED` before target mutation.

## Target capabilities

| Target | Allowed relay action | Required bounded read-back |
| --- | --- | --- |
| Raspberry Pi | Install the manifest-bound Pi artifact through the canonical updater or deployment procedure. | Installed version, artifact/build identity, allowlisted service, local API and restart persistence. |
| ESP32 | Initiate the approved Home Assistant Update-entity OTA for the manifest-bound firmware only. | Offered/reported firmware version, device/entity health, reconnect and internal web-server health. |
| Production Home Assistant Pi 5 | Install the manifest-bound qualified HA integration artifact and run only canonical restart/reload. | Integration version, setup success and entity/platform health. |
| Apple private devices | Locally sign the manifest-bound unsigned Apple artifact and deploy through Developer provisioning. | Bundle identifier/version, candidate identity where available, installation, device availability and supported launch health. |

Pi and ESP32 remain deployment and Verification targets; they never build
source. Pi and ESP32 artifacts use their canonical distribution repositories.
The HA integration uses an immutable checksum-bound qualified artifact; a
GitHub Release is required only if its approved internal distribution policy
requires publication.

## Apple signing boundary

The Apple Secure Distribution Relay consumes only artifacts from the qualified
Apple build workflow. Local signing occurs only in the macOS runner's local
signing environment. Certificates, private keys and provisioning profiles are
never placed in GitHub secrets, exported, uploaded or included in evidence.
The relay cannot compile source, build an IPA or macOS binary, create unsigned
artifacts, publish TestFlight, publish the App Store or choose arbitrary files.

## Credentials and evidence

Target credentials are job-only and least-privilege: Pi SSH, Home Assistant
deployment/API, artifact download and Apple local signing are separate scopes.
They are unavailable to CI, PR, artifact/evidence and unrelated target jobs;
they are never logged or persisted in the workspace after a job.

Evidence is immutable and redacted. It records repository, workflow/run and
runner identity/labels, candidate SHA, platform version, manifest/artifact ID,
artifact checksum, target, profile, action, timestamps, precondition outcome,
deployment result, post-deployment version, health read-back and recovery or
rollback reference. Apple evidence may identify the signing identity but never
contains signing material. Failure stops the target flow, preserves
qualification evidence and marks release execution incomplete.
