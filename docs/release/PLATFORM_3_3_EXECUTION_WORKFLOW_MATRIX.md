# Platform Release 3.3 Execution Workflow Matrix

Every participating repository now contains
`.github/workflows/platform-release-execution.yml`. The common bounded
`workflow_dispatch` interface accepts only `action`, `candidate_sha`,
`execution_mode`, `manifest_id`, `platform_version` and
`release_profile`; it checks out and verifies the exact candidate SHA and
uploads one `platform-release-execution-evidence` artifact.

| Repository class | Runner | Contract state |
| --- | --- | --- |
| Home Assistant, API, website, Pi, ESP32 and distribution repositories | GitHub-hosted Linux | SHA/evidence contract installed |
| Apple | qualified self-hosted macOS | SHA/evidence contract installed |
| Windows | qualified self-hosted Windows | SHA/evidence contract installed |

Pi and ESP32 are deployment targets, never build runners. Apple artifacts
remain one universal iOS IPA (including the Watch companion) and one native
macOS application.

The contract deliberately accepts only `dry_run` at this stage. It
fail-closes `execute`, rather than falsely reporting deployment, publication
or rollback as complete before repository-native action workflows and their
secrets/environments are qualified.
