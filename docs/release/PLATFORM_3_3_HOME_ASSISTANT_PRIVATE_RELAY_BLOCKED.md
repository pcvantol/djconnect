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

Read-only GitHub runner inventory for `pcvantol/djconnect` reports only the
online self-hosted runner `djconnect-home-assistant-linux` with labels
`self-hosted`, `Linux`, `ARM64`, `internal-release`, `qualification` and
`home-assistant`.

The frozen release architecture requires a distinct qualified macOS
Private-Network Deployment Relay for Home Assistant private-network deployment
and separate smoke evidence. No matching repository runner/capability is
currently configured. Using the Linux qualification runner or inventing runner
labels, target credentials or deployment commands would violate the frozen
deployment boundary.

The repository has no deployment environment and its configured secret names
contain only Trusted Delivery and Docker credentials. No Home Assistant
deployment/API or artifact-download credential scope is configured. Secret
values were not read.

## Result

No Home Assistant deployment or smoke workflow was created, no credentials
were accessed and no target was mutated. The deployment consumer remains
fail-closed pending a qualified macOS Private-Network Deployment Relay with
its separate deployment and smoke credential scopes.

## Next authorized action

Provision and qualify a distinct macOS relay registered for `pcvantol/djconnect`,
with an explicit private-network deployment label and isolated HA
deployment/API and artifact-download credential scopes. Then implement the
manifest-bound HA deployment and separate smoke workflows. Do not dispatch the
artifact workflow as release authorization.
