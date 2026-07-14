# Platform Release 3.3 Execution Workflow Matrix

Status: historical execution-contract record; corrected by the current
[deployment-consumer inventory](PLATFORM_3_3_DEPLOYMENT_CONSUMER_INVENTORY.md).

The intended common bounded `workflow_dispatch` interface accepts `action`,
`candidate_sha`, `execution_mode`, `manifest_id`, `platform_version` and
`release_profile`; an operational deployment consumer additionally requires
the artifact and target bindings defined by
[Deployment Input Contract](DEPLOYMENT_INPUT_CONTRACT.md).

The earlier statement that every participating repository contained
`.github/workflows/platform-release-execution.yml` was not true for the
current local checkouts. It must not be used as qualification evidence.

| Repository class | Runner | Current contract position |
| --- | --- | --- |
| Home Assistant | GitHub-hosted Linux build; dedicated macOS private relay provisioned for deployment | Artifact, deployment and smoke workflows are implemented but fail closed pending an approved operational manifest, target credentials, installation contract and complete HA smoke checks. |
| Website | GitHub-hosted Linux | Artifact, deployment and smoke consumers are implemented; operational qualification remains blocked pending a manifest-bound authorized run. |
| API | GitHub-hosted Linux | Artifact, deployment and smoke workflows are implemented but fail closed pending an approved operational manifest and observable candidate-version/runtime-health smoke evidence. |
| Pi, ESP32 and distribution repositories | GitHub-hosted Linux | No platform-release execution contract found in the inspected checkout. |
| Apple | Qualified self-hosted macOS | Native build qualified; no inspected manifest-bound Apple Secure Distribution Relay consumer. |
| Windows | Qualified self-hosted Windows | Native build qualified; no inspected manifest-bound internal deployment consumer. |

Pi and ESP32 are deployment targets, never build runners. Apple artifacts
remain one universal iOS IPA (including the Watch companion) and one native
macOS application. A current release manifest determines which of these
potential consumers become required for a particular Internal Release.
