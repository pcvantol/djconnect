# Platform Release 3.3 — ESP32 Deployment Consumer

Date: 2026-07-14
Decision: `ESP32_DEPLOYMENT_CONSUMER_STATIC_IMPLEMENTATION_BLOCKED`

## Scope

`pcvantol/djconnect-esp32` now contains a separate manifest-input deployment
workflow and post-deployment smoke workflow. Firmware remains an artifact from
`pcvantol/djconnect-firmware`; the deployment workflow never builds or flashes
firmware directly. Its only intended mutation is a Home Assistant
`update.install` request for the manifest-bound ESP32 Update entity.

## Fail-closed state

No approved current-main operational manifest, target-specific Home Assistant
credential scope, Update entity identifier or verified deployment-evidence
source exists. The deployment workflow rejects every dispatch before it can
read HA secrets or invoke the Update entity. The separate smoke workflow also
fails closed without contacting the ESP32 target.

No OTA, Home Assistant service call, firmware release, credential or device
state was changed.

## Verification

- Workflow YAML parses successfully.
- `git diff --check` passed in `pcvantol/djconnect-esp32`.
- `bash test/native/test_release.sh` passed.

## Required completion work

1. Provide an approved operational manifest binding the public firmware asset,
   checksum, candidate and ESP32 target.
2. Configure isolated HA API and ESP32 Update-entity scope on the private
   deployment relay.
3. Add deployment evidence plus read-only reconnect, offered/installed
   version, HA entity and local device-health smoke checks.
4. Qualify only through an explicitly authorized deployment and separate smoke
   dispatch.
