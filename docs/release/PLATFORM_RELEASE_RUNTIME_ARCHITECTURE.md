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
their qualified self-hosted native runners. Raspberry Pi (`rbpi-djconnect`) and
ESP32 remain deployment/runtime-validation targets, never source-build runners.

The qualified macOS runner has exactly three isolated capabilities: Apple
Native Build (CI / Qualification or Artifact Build), Private-Network Deployment
Relay (Deployment), and Apple Secure Distribution Relay (Deployment). They use
separate jobs, permissions, credentials, workspaces, target allowlists and
deployment evidence. The Runtime dispatches their bounded workflows and reads
their evidence only.

An authorized deployment is operational only after a separate bounded,
non-destructive smoke-evidence workflow validates its manifest-allowlisted
routes and runtime health. The Runtime consumes its redacted result; it does
not perform smoke requests itself or replace Verification Platform evidence.
The final deployment decision is `DEPLOYMENT_OPERATIONAL` only when all
required smoke targets pass, otherwise `DEPLOYMENT_SMOKE_FAILED`.

## Apple artifact model

Generation 1 has two Apple artifacts: one universal iOS IPA for iPhone, iPad
and its embedded Apple Watch companion app, and one native macOS application.
visionOS is deferred. The Runtime must not create separate iPad or Watch
artifact nodes. See [Apple Release Architecture](APPLE_RELEASE_ARCHITECTURE.md)
for the target and workflow evidence.

Apple direct deployment targets are the typed values `macbook`, `iphone` and
`ipad`. The manifest binds the direct target and typed companion relation
`paired_watch_validation=required|optional|disabled`. Apple Watch remains
embedded-companion validation, never a direct deployment target or a separate
release-manifest node in Generation 1.

Every operational deployment workflow must accept the bounded dispatch inputs
`action`, `candidate_sha`, `execution_mode`, `manifest_id`, `artifact_id`,
`artifact_sha256`, `target`, `platform_version`, and `release_profile`;
validate them; fail closed; and publish exactly one redacted deployment-evidence
JSON artifact. Deployment cannot create tags, create or publish GitHub Releases,
or choose artifacts. A draft internal GitHub Release, where used, is an
artifact-handling record created before relay dispatch; the relay only consumes
the manifest-bound artifact it references.

The repository deployment workflow defines the required input and deployment
evidence contract. CI and evidence workflows do not accept deployment
authority. The runtime rejects incomplete or inconsistent workflow evidence.

The canonical workflow-class boundary is documented in
[Platform Workflow Separation Architecture](PLATFORM_WORKFLOW_SEPARATION_ARCHITECTURE.md).
The private-target and Apple signing contracts are documented in
[Private Network Deployment Relay](PRIVATE_NETWORK_DEPLOYMENT_RELAY.md) and
[Apple Release Architecture](APPLE_RELEASE_ARCHITECTURE.md).
