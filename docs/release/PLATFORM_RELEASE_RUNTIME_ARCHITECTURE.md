# Platform Release Runtime Architecture

Status: `OPERATIONAL`  
Architecture: `FROZEN`

The Platform Release Runtime is the DJConnect orchestration layer. It discovers
repositories, constructs the release graph, qualifies candidate evidence,
validates gates, dispatches approved workflows, monitors runs, reads their
evidence, and makes fail-closed readiness decisions.

It is not a build or execution engine. It cannot create tags or GitHub
Releases, upload artifacts, publish artifacts, deploy targets, or perform
rollback. Those actions are exclusively owned by GitHub Actions workflows and
their qualified runners.

Canonical flow:

`Runtime → GitHub Actions → qualified build runners → artifacts → deployment workflows → targets → evidence → decision`

Linux builds run on GitHub-hosted runners. Apple and Windows builds run only on
their qualified self-hosted native runners. Raspberry Pi and ESP32 remain
deployment/runtime-validation targets, never source-build runners.

Every operational repository workflow must accept the bounded dispatch inputs
`action`, `candidate_sha`, `execution_mode`, `manifest_id`,
`platform_version`, and `release_profile`; validate them; fail closed; and
publish exactly one `platform-release-execution-evidence` JSON artifact. The
workflow owns tag creation, draft-release creation, artifact publication,
deployment, and rollback where those actions are supported.

The repository workflow
[platform-release-execution.yml](../../.github/workflows/platform-release-execution.yml)
defines the required input and evidence contract. The runtime rejects
incomplete or inconsistent workflow evidence.
