# Platform Release 3.3 — Deployment Consumer Inventory

Date: 2026-07-14
Scope: read-only inventory of the local checkouts named by
`REPOSITORY_OWNERSHIP.md`
Decision: `PLATFORM_RELEASE_3_3_DEPLOYMENT_CONSUMERS_NOT_QUALIFIED`

## Executive summary

Platform Release 3.3 cannot progress to candidate reconstruction or an
Internal Release. The approved current release manifest does not yet exist, so
no target may be asserted as required. The inspected checkouts also do not
provide a complete set of qualified, manifest-bound deployment and separate
post-deployment smoke consumers.

This inventory is evidence of the release-preparation gap only. It did not
dispatch workflows, create artifacts, deploy targets, publish releases or
access credentials.

## Implementation and review

The initial reviewed scope was limited to checked-in release documentation and
the current local workflow files of the ten ownership participants. The
inventory corrected the false rollout claim in
`PLATFORM_3_3_EXECUTION_WORKFLOW_MATRIX.md`. Follow-up work implemented the
Website and Home Assistant artifact/deployment/smoke workflow separation
without changing release architecture, target ownership or deployment policy.

## Basis and method

- Repository membership comes from `REPOSITORY_OWNERSHIP.md`.
- Deployment and smoke requirements come from `DEPLOYMENT_INPUT_CONTRACT.md`,
  `DEPLOYMENT_WORKFLOW_POLICY.md` and
  `POST_DEPLOYMENT_SMOKE_TEST_POLICY.md`.
- Every listed checkout was inspected at its local `HEAD` on 2026-07-14 for
  GitHub Actions workflow contracts. A regular CI, source build, legacy public
  release or release dry run is not a qualified deployment consumer.
- The applicable required/optional target set remains a property of the next
  approved, exact-SHA Internal Release manifest. This document does not infer
  it from repository names.

## Inventory

| Surface / owner | Observed local state | Required consumer gap | Status |
| --- | --- | --- | --- |
| Home Assistant (`djconnect`, `bea53ae7`) | Exact-main artifact producer plus separate private-relay deployment and smoke workflows are implemented; relay/environment are provisioned. Both workflows are fail-closed because no operational manifest source or HA credentials/install/smoke scope exists. | Supply the approved manifest source and target scope; complete HA WebSocket/startup/crash smoke checks; then explicitly qualify. | Implemented; operational qualification blocked |
| API (`djconnect-api`, `b333484`) | Exact-main Worker artifact, manifest-input deployment and separate public-health smoke workflows are implemented. Deployment and smoke fail closed pending an approved operational manifest; smoke also lacks version/runtime-health read-back. | Supply the approved manifest and complete observable version/runtime-health checks, then explicitly qualify. | Implemented; operational qualification blocked |
| Apple (`djconnect-app`, `465efc73`) | Qualified native builds and legacy/public release workflows exist. | Apple Secure Distribution Relay consuming a qualified artifact, typed allowlisted device and separate smoke evidence. | Missing |
| Windows (`djconnect-windows`, `fb7757e`) | Qualified native Windows artifact build and legacy/public release workflow exist. | Manifest-bound internal deployment plus bounded installed-version/launch smoke evidence. | Missing |
| Raspberry Pi (`djconnect-pi`, `b09b65d`) | CI and public-release workflow exist; Pi distribution repository is separate. | Private-network relay consumer that installs the manifest-bound Pi artifact, followed by separate runtime smoke evidence. | Missing |
| ESP32 (`djconnect-esp32`, `d86e752`) | CI and firmware-publication workflow exist; firmware distribution repository is separate. | Private-network relay consumer that invokes the HA Update entity for the manifest-bound firmware, followed by separate hardware smoke evidence. | Missing |
| Website (`djconnect-website`, `5630f0c`) | Separate current-main artifact, manifest-bound Pages deployment and post-deployment smoke workflows are implemented. | Operational qualification against a future approved manifest, exact artifact evidence and explicit dispatch authorization. | Implemented; operational qualification blocked |
| Firmware distribution (`djconnect-firmware`, `9225ac1`) | Governance and Trusted Delivery workflows only. | Manifest-bound firmware publication consumer and artifact evidence if firmware distribution is included. | Missing |
| Apple distribution (`djconnect-app-releases`, `427e77a`) | Governance and Trusted Delivery workflows only. | Manifest-bound distribution/publication consumer if that channel is included. | Missing |
| Pi distribution (`djconnect-pi-releases`, `d4d3903`) | Governance and Trusted Delivery workflows only. | Manifest-bound Pi artifact publication consumer and artifact evidence if Pi delivery is included. | Missing |

## Findings

1. The current release contract is incomplete before target-specific work:
   there is no approved current-main manifest that declares the exact required
   target set, artifacts and SHA-256 bindings.
2. Existing release-oriented workflows generally combine source build or
   publication with other responsibilities. They cannot substitute for a
   separate deployment consumer under the frozen workflow-separation policy.
3. The Home Assistant artifact producer, relay and static deployment/smoke
   consumers are implemented, but operational execution is blocked by the
   absent operational-manifest, target credential and installation scopes.
4. The API consumer now implements canonical artifact, deployment and smoke
   separation, but it has no operational evidence and its health route lacks
   candidate-version/runtime-health read-back.
5. The Website consumer now implements the canonical artifact, deployment and
   smoke separation, but it has no operational evidence and is not qualified.
6. The historical execution-workflow matrix overstated rollout coverage. It
   has been corrected and this inventory is its current evidence source.

## Verification and evidence

- All relative documentation links introduced by this inventory resolve.
- `git diff --check` passed after the documentation updates.
- Evidence is the inspected local workflow inventory and the recorded local
  HEAD identifiers in the table above. It is not operational evidence and
  cannot qualify a candidate or deployment.

## Assessment

| Area | Result |
| --- | --- |
| Architecture | No impact. The frozen execution/deployment architecture remains the governing contract. |
| Technical design | Website and Home Assistant now have static artifact/deployment/smoke workflow separation; both remain operationally unqualified. |
| Verification Platform | No impact. Deployment smoke remains distinct from Verification scenarios. |
| Meta Engineering | No process change. The inventory follows evidence-first and repository-as-memory practice. |
| Technical debt | Manifest-bound deployment and smoke consumers are missing or incomplete. |
| Product debt | None identified. |

## Recommended implementation order

1. Define one reusable, fail-closed repository deployment-consumer template
   that implements the canonical input contract, redacted deployment evidence
   and hand-off to a separate smoke workflow. Do not broaden the frozen
   architecture.
2. Qualify the Website consumer only when a current approved manifest and
   explicit deployment authorization exist.
3. Supply and validate the API operational manifest, implement observable
   version/runtime-health read-back and qualify it explicitly if the API is
   required by the manifest.
4. Supply and validate the Home Assistant operational-manifest and target
   credential/installation scope, then complete its bounded smoke contract and
   qualify it explicitly; then implement the Raspberry Pi and ESP32 consumers
   with the same boundary.
5. Implement and qualify the Apple Secure Distribution Relay and the Windows
   internal deployment consumer using their already-qualified native artifacts.
6. Add only the distribution consumers that the explicitly approved manifest
   makes required. Then reconstruct the candidate from exact current `main`
   SHAs and collect fresh evidence.

## Known blockers

- No approved current-main Internal Release manifest or required-target set.
- No complete manifest-bound deployment and separate smoke consumer has been
  qualified for the inspected scope.
- No current candidate artifacts, checksum-bound deployment evidence or
  post-deployment smoke evidence exists.
- Internal Release workflow dispatch remains explicitly unauthorized.

## Qualification decision

`PLATFORM_RELEASE_3_3_DEPLOYMENT_CONSUMERS_NOT_QUALIFIED`

## Readiness and next phase

The Website, Home Assistant and API static implementation steps are complete.
The release remains not ready. The next phase is not started: it requires an
explicit implementation prompt for another consumer or an explicitly
authorized operational qualification with a current approved manifest.

The Website and API implementation evidence is recorded in
`PLATFORM_3_3_WEBSITE_DEPLOYMENT_CONSUMER_COMPLETION.md` and
`PLATFORM_3_3_API_DEPLOYMENT_CONSUMER_COMPLETION.md`. Any operational
qualification requires an explicit prompt and must not dispatch deployment or
release workflows implicitly.
