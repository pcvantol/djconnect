# Platform Release Runtime Architecture

Status: `OPERATIONAL`  
Architecture: `FROZEN`

The Platform Release Runtime is the DJConnect orchestration layer. It discovers
repositories, constructs the release graph, qualifies candidate evidence,
validates gates, dispatches approved workflows, monitors runs, reads their
evidence, and makes fail-closed readiness decisions.

Release manifests consume only exact-main-SHA post-merge reconciliation
evidence. Qualified PR-head evidence is provenance input, never a substitute
for releaseable `main`-SHA evidence.

It is not a build or execution engine. It cannot create tags or GitHub
Releases, upload artifacts, publish artifacts, deploy targets, or perform
rollback. Those actions are exclusively owned by GitHub Actions workflows and
their qualified runners.

Canonical flow:

`Runtime → CI / Qualification → Artifact / Release Evidence → explicit Deployment → targets → deployment evidence → decision`

Linux builds run on GitHub-hosted runners. Apple and Windows builds run only on
their qualified self-hosted native runners. Raspberry Pi and ESP32 remain
deployment/runtime-validation targets, never source-build runners.

## Apple artifact model

Generation 1 has two Apple artifacts: one universal iOS IPA for iPhone, iPad
and its embedded Apple Watch companion app, and one native macOS application.
visionOS is deferred. The Runtime must not create separate iPad or Watch
artifact nodes. See [Apple Release Architecture](APPLE_RELEASE_ARCHITECTURE.md)
for the target and workflow evidence.

Every operational deployment workflow must accept the bounded dispatch inputs
`action`, `candidate_sha`, `execution_mode`, `manifest_id`,
`platform_version`, and `release_profile`; validate them; fail closed; and
publish exactly one `platform-release-execution-evidence` JSON artifact. The
workflow owns tag creation, draft-release creation, artifact publication,
deployment, and rollback where those actions are supported.

The repository deployment workflow defines the required input and deployment
evidence contract. CI and evidence workflows do not accept deployment
authority. The runtime rejects incomplete or inconsistent workflow evidence.

The canonical workflow-class boundary is documented in
[Platform Workflow Separation Architecture](PLATFORM_WORKFLOW_SEPARATION_ARCHITECTURE.md).
