# Component Release Scope Refinement

**Status:** Architecture refinement complete
**Decision:** `GO_COMPONENT_RELEASE_SCOPE_REFINEMENT_PARTIALLY_QUALIFIED`
**Scope:** Canonical selection, participant, dependency and evidence closure
for the existing DJConnect release components. No Runtime, workflow, manifest,
artifact, release-channel or product change.

## Decision

DJConnect has one reusable Component Release Scope Contract. A component patch
is a closed release selection, not merely a source repository or a version
string. The existing Platform Release Runtime remains the only orchestrator;
it must reject a request unless the selected profile and every required closure
binding are present and mutually consistent.

The contract now has profiles for the Home Assistant integration (HACS), API,
website, ESP32, iOS plus watchOS, macOS, Windows and the Raspberry Pi renderer
family. The Pi 4-inch and Pi 10-inch products do **not** yet have independent
release profiles: current repository evidence provides one shared Pi source
and one shared Pi release bundle. Treating them as two independently
releasable components before hardware-specific artifacts exist would weaken
the fail-closed boundary.

This refinement itself authorized no release, publication, tag, deployment or
version change. Its bounded Runtime follow-through is now documented in
`COMPONENT_RELEASE_SELECTION_EVIDENCE_CLOSURE_IMPLEMENTATION.md`: canonical
selected-component and affected-evidence closure enforcement exists, while the
current platform execution dispatchers retain their documented `dry_run`
boundary.

## Canonical Component Release Scope Contract

Every future component-patch request must carry one immutable selection record
with all of these values. Free-text repository selection and globbing are not
valid selection mechanisms.

| Field | Requirement |
| --- | --- |
| `component_id` | One registered profile identifier from this document. |
| `component_owner` | The selected source owner named by `REPOSITORY_OWNERSHIP.md`. |
| `source_repository` and `source_sha` | One exact current-main candidate revision. |
| `version` and `platform_train` | A compatible `major.minor.patch` patch inside the approved `major.minor` train. |
| `artifact_identity` and `artifact_sha256` | Exact immutable artifact and checksum produced from the selected source SHA. |
| `manifest_id` and `manifest_sha256` | One immutable manifest binding this exact component, artifact, version and channel. |
| `release_channel` and `target_distribution` | The profile's named channel and only its declared target. |
| `participants` | Exactly the profile's closure-required source, artifact and distribution participants. |
| `evidence` | Source qualification, build/test, Software Assurance, Trusted Delivery, artifact/provenance, manifest, channel and durable post-merge records bound to the same identities. |
| `owner_authorization` | Explicit human authorization for the selected component and channel; it never follows implicitly from a successful dry run. |

Any missing field, SHA/artifact/manifest/version mismatch, unregistered
participant, cross-component dependency, ambiguous target, or absent required
evidence is `NOT_READY`. A scoped release must then fail only that component
selection; it must not promote unrelated components or fall back to a full
platform selection.

## Participant Classes

| Class | Meaning |
| --- | --- |
| **Selected source participant** | Owns the patch and is the sole selected release source. |
| **Closure-required participant** | Owns a required artifact handoff, publication or target deployment for that exact source artifact. |
| **Consumed platform contract** | Existing Platform Release Runtime, ownership, policy, assurance or verification contract. It is consumed, never released as a second component. |
| **Non-selected component** | Any other client, service, firmware or distribution surface. It must remain excluded. |
| **Forbidden cross-component dependency** | A shared protocol, API, compatibility train, public-channel commitment or artifact dependency that would require another source component to change. Its presence rejects a standalone component patch. |

## Profile Inventory

The profile identifier is stable. Its source/release boundary is discovered
from the repository ownership and current artifact evidence, not inferred from
repository names alone.

| Component ID | Selected source | Closure-required participant(s) | Artifact and channel | Scope status |
| --- | --- | --- | --- | --- |
| `hacs-integration` | `pcvantol/djconnect` | HACS repository/channel only; no second source repository | SHA-bound Home Assistant integration tarball and checksum; HACS release channel | Profiled; precedent exists in HACS 3.3.1. |
| `api-worker` | `pcvantol/djconnect-api` | API worker deployment target | SHA-bound Worker bundle and checksum; approved API production channel | Profiled. |
| `website` | `pcvantol/djconnect-website` | Website deployment target | SHA-bound static website bundle and checksum; approved Pages/website channel | Profiled. |
| `esp32-firmware` | `pcvantol/djconnect-esp32` | `pcvantol/djconnect-firmware` | Source-bound firmware artifact/checksum and public firmware channel | Profiled. |
| `apple-ios-watchos` | `pcvantol/djconnect-app` | `pcvantol/djconnect-app-releases`, Apple iPhone relay and paired Watch qualification where required | The existing unsigned iOS artifact, checksum and approved Apple iOS/watchOS channel | Profiled as one unit: the Watch is embedded in the iOS artifact path. |
| `apple-macos` | `pcvantol/djconnect-app` | `pcvantol/djconnect-app-releases`, Apple macOS relay | The existing unsigned macOS artifact, checksum and approved macOS channel | Profiled independently of iOS/watchOS. |
| `windows-client` | `pcvantol/djconnect-windows` | `pcvantol/djconnect-app-releases`, Windows deployment target | SHA-bound Windows artifact/checksum and approved Windows channel | Profiled; any incidental Mac Catalyst output is non-selected. |
| `pi-renderer-family` | `pcvantol/djconnect-pi` | `pcvantol/djconnect-pi-releases`, approved Pi target | One source-bound Pi bundle/checksum and public Pi channel | Profiled only as a shared family release unit. |
| `pi-4-inch` | None independently selectable | Would require a Pi-4-specific source artifact and target evidence | No current independent artifact or release manifest identity | `NOT_SELECTABLE`. |
| `pi-10-inch` | None independently selectable | Would require a Pi-10-specific source artifact and target evidence | No current independent artifact or release manifest identity | `NOT_SELECTABLE`. |

`pi-4-inch` and `pi-10-inch` are product capability profiles, not currently
release-component identities. A future hardware-specific release split must
first establish distinct artifact, manifest, checksum, target and recovery
evidence; it must not reuse the shared bundle while claiming isolated release
closure.

## Profile Closure Requirements

Every profiled component requires the common contract plus the following
profile-specific bindings.

| Profile | Required closure | Explicitly excluded |
| --- | --- | --- |
| `hacs-integration` | Integration source SHA, packaged tarball/checksum, HACS metadata/release validation, HACS-specific qualification, assurance, Trusted Delivery and durable evidence. | API, native clients, firmware, Pi and website. |
| `api-worker` | API source SHA, Worker bundle/checksum, migration/worker deployment evidence, API target smoke where applicable, assurance, Trusted Delivery and durable evidence. | HACS, clients, firmware, Pi and website. |
| `website` | Website source SHA, static bundle/checksum, deployment integrity and website smoke, assurance, Trusted Delivery and durable evidence. | Runtime, API, clients, firmware and Pi. |
| `esp32-firmware` | Firmware source SHA, firmware artifact/checksum, `djconnect-firmware` publication binding, selected OTA channel and rollback evidence, assurance, Trusted Delivery and durable evidence. | HACS, API, Apple, Windows, Pi and website. |
| `apple-ios-watchos` | App source SHA, iOS artifact/checksum, app-releases handoff, iPhone target and paired Watch qualification when the patch affects the embedded Watch path, Apple signing/authorization and durable evidence. | macOS, Windows, Pi, firmware, HACS, API and website. |
| `apple-macos` | App source SHA, macOS artifact/checksum, app-releases handoff, macOS relay/signing/notarization evidence where the selected channel requires it, authorization and durable evidence. | iOS/watchOS, Windows, Pi, firmware, HACS, API and website. |
| `windows-client` | Windows source SHA, selected Windows artifact/checksum, app-releases handoff, Windows target deployment/smoke where applicable, assurance, Trusted Delivery and durable evidence. | Apple and Mac Catalyst output, Pi, firmware, HACS, API and website. |
| `pi-renderer-family` | Pi source SHA, Pi bundle/checksum, pi-releases handoff, selected Pi target deployment/smoke and rollback evidence, assurance, Trusted Delivery and durable evidence. | Separate Pi 4-inch or Pi 10-inch selection until their own artifacts exist; all other components. |

## Evidence Closure

Evidence is valid only when it identifies the same `component_id`, source SHA,
artifact identity/checksum, manifest and version. The following records are
mandatory where the existing profile/channel uses them:

1. source qualification and repository-local build/test evidence;
2. Software Assurance and Trusted Delivery qualification;
3. qualified host/target evidence for native, firmware or deployment paths;
4. artifact provenance and checksum evidence;
5. manifest and release-channel validation;
6. explicit owner authorization; and
7. durable post-merge qualification/release evidence.

HACS, Golden Verification, target smoke and release evidence retain their
existing distinct authority. None is independently sufficient to authorize a
component release.

## Dry Run and Execute Boundary

The current Runtime and repository dispatchers establish a useful safety
boundary: they validate an already-supplied immutable scope and reject missing
readiness, mismatched SHAs, absent evidence and out-of-scope actions. They do
not derive this document's component selection or closure, and the current
dispatcher contract rejects `execute` while platform-native execution remains
unqualified.

Consequently, a successful dry run proves only that a supplied candidate can
be checked against existing inputs. It does not authorize a release, mutate a
channel or prove that a one-component closure was derived canonically.

## Bounded Follow-up Sequence

1. **Component Release Selection and Evidence Closure implementation** —
   completed pending Finalization. The existing Runtime now supports the
   registered profile IDs, deterministic participant closure and exact evidence
   binding without enabling release execution.
2. **Component Release Execute Qualification** — separately qualify the
   existing execute route for each profile only when its platform-native
   execution prerequisites and human authorization are present.
3. **Component Patch Operational Proof** — use a real bounded patch for one
   already execute-qualified profile. A documentation-only, synthetic or
   invented patch is prohibited.

No profile may skip from this refinement to public release. A cross-profile
change remains a coordinated Platform Release scope.

## Result

`GO_COMPONENT_RELEASE_SCOPE_REFINEMENT_PARTIALLY_QUALIFIED`

The canonical closure contract and profile boundaries are now explicit. The
shared Pi artifact evidence prevents separate Pi 4-inch and Pi 10-inch
selection, and the current Runtime/dispatch execution boundaries prevent every
profile from being claimed operationally release-ready. The next work is the
bounded Runtime selection-and-evidence-closure implementation, not an
individual component release.
