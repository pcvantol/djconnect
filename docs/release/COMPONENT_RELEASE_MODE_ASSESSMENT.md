# Component Release Mode Assessment

**Status:** Assessment complete  
**Decision:** `GO_COMPONENT_RELEASE_MODE_PARTIALLY_QUALIFIED`  
**Scope:** Repository-first assessment of existing Platform Release, Repository
Ownership, version and verification evidence. No Runtime, API, Renderer,
workflow, manifest, release-operation or production-code change.

## Objective and boundary

This assessment determines which existing DJConnect components are releaseable
units and the conditions under which one may be released independently. It does
not introduce a release mode, change the frozen Platform Release Architecture,
or authorize a component release.

`Component` means one Repository Ownership participant and its owned release
unit. It does not mean an arbitrary module, capability or document inside a
repository. The existing Platform Release Runtime remains the sole orchestrator
for every release scope.

## Repository evidence

The frozen Platform Release Architecture establishes one `major.minor`
compatibility train and repository-local patch delivery. Repository Ownership
is the canonical source for discovery, role and ownership; it distinguishes
active source, release source, distribution, optional and future participants.
The implemented Runtime consumes an immutable manifest and exact-main-SHA
evidence, dispatches only qualified repository workflows, and does not
recalculate scope or mutate a channel directly.

The 3.3 operational manifest provides an existing component-patch precedent:
the Home Assistant/HACS integration advanced alone to `3.3.1` while the other
3.3.0 participant bindings remained unchanged. Its HACS release record also
preserves the required source candidate, artifact, deployment and smoke
evidence. This proves an explicitly scoped component patch can be represented
inside the existing platform release model; it does not prove a generic
single-component selection mode.

## Component inventory and classification

| Existing component category | Canonical owner/release unit | Classification | Independent-release boundary |
| --- | --- | --- | --- |
| Home Assistant integration: Runtime, Knowledge, Planner, DJMoment, HA-facing API and integration packaging | `pcvantol/djconnect` as one integration release unit | Independent Release Candidate | Only as one repository patch; its internal modules are not separately releaseable. A shared contract, protocol or compatibility-train change is Platform-bound. |
| Central API trust/relay | `pcvantol/djconnect-api` | Independent Release Candidate | A compatible repository patch may release when its source, target and evidence are scoped. Trust, entitlement or shared-contract changes are Platform-bound. |
| Native Renderer Hosts | Apple, Windows, Pi and ESP32 source repositories | Independent Release Candidate | Each host may deliver an owned compatible patch. Shared renderer contracts, cross-host parity commitments or protocol changes are Platform-bound. |
| Website and public guidance | `pcvantol/djconnect-website` | Independent Release Candidate | A website-only compatible deployment may be scoped alone; public-installation, compatibility or support assertions require the affected release evidence. |
| Firmware and Pi/Apple release artifacts | Source repository plus its designated distribution repository/channel | Repository-bound | A distribution repository is an artifact/channel consumer, not an independent product-capability source. It may participate only with its qualified source artifact and channel evidence. |
| Verification profiles, Golden verification and qualification evidence | Verification Platform and owning repository evidence producers | Repository-bound | They qualify a selected candidate; they are not independently publishable product components. A profile change remains tied to its owner revision and governed validation. |
| CI, Software Assurance, Trusted Delivery and developer tooling | Owning repository and platform governance | Repository-bound | They may evolve as repository changes, but they do not constitute a standalone product release or bypass the selected candidate's evidence. |
| Governance and canonical documentation | Owning canonical repository | Repository-bound | They may be merged and recorded independently, but are not a component release unless an existing distribution surface is explicitly in scope. |
| Platform Release Runtime, manifest model, compatibility train and release policy | Platform Release / canonical governance | Platform-bound | These define scope and eligibility for every component release and may not be selected as a second independent release system. |
| A change spanning a shared protocol, API contract, release train, cross-repository capability or public channel commitment | A discovered multi-repository release scope | Platform-bound | It requires the existing coordinated Platform Release scope, not a component patch. |
| A prospective participant without a current ownership role, artifact/deployment path or verification target | Undetermined | Assessment Required | Its ownership, source/distribution relation, compatibility impact and evidence path must be qualified before it can be selected. |

## Dependency and governance boundary

An Independent Release Candidate is eligible only when all of the following
are true:

1. Repository Ownership discovers exactly one active or release-source
   participant as the selected component.
2. The candidate is a patch increment within the current platform
   `major.minor` compatibility train; no shared contract, protocol, ownership
   or public-channel commitment changes.
3. Any dependent distribution repository, deployment target and verification
   target are included only because the selected component requires them;
   unrelated repositories are excluded with the existing scope rationale.
4. The immutable manifest binds the exact main candidate SHA, version, artifact
   identity, affected verification evidence, Software Assurance and Trusted
   Delivery result, and recovery posture.
5. The applicable repository workflow, qualified runner and channel remain the
   only execution path. The Runtime dispatches and reads evidence; it does not
   build, publish, tag, deploy or roll back directly.

Repository-bound categories cannot be independently selected as a product
release unit. Platform-bound categories require the existing coordinated scope.
This preserves the release-architecture rule that releases are discovered from
ownership records rather than inferred from file layout, repository names or
individual capabilities.

## Version ownership

Existing semantic versioning is sufficient for a compatible repository-local
patch: `major.minor.patch` identifies the owned delivery while the platform
train remains `major.minor`. The 3.3.1 HACS patch is the concrete recorded
example.

Existing platform versioning, rather than a new capability-versioning system,
is required when a change alters a shared platform contract or compatibility
train. Existing immutable candidate SHA, manifest identity and evidence schema
versions are the necessary verification-version identifiers. This assessment
finds no evidence that a separate capability-version or verification-version
scheme is needed.

## Minimum verification impact

| Selected change type | Minimum existing evidence | Release boundary |
| --- | --- | --- |
| Documentation or governance repository change | Owning-repository CI/governance validation and exact-main provenance where release evidence is claimed | Not a standalone product release by default. |
| Verification profile or qualification change | Owning validation plus the existing Verification Platform governance and affected profile evidence | Does not self-certify a product candidate. |
| Independent component patch | Exact-main candidate SHA; scoped behavioural verification; Software Assurance and Trusted Delivery; version/compatibility alignment; artifact, channel/deployment and recovery evidence where applicable | May be considered only through the existing Platform Release Runtime and certification path. |
| Platform-bound change | The same evidence for the complete discovered coordinated scope | Must not be reduced to a component patch. |

HACS, Golden Verification, CI qualification, Software Assurance and Trusted
Delivery retain their existing distinct ownership. No single validator,
including a successful HACS check, authorizes a component release.

## Public-distribution readiness

Component Release Mode is a necessary architectural qualification before the
planned Apple, Windows and public HACS distribution work: those channels need a
reliable answer to which one source component, artifact, channel and evidence
set is being promoted. It is not sufficient for public distribution. The
existing channel-specific authorization, certification, signing, artifact,
deployment and public-release work remains independently required.

## Remaining qualification item

The component categories and their governance boundaries are qualified, but
the existing simulation manifest and Runtime do not yet prove a generic,
fail-closed single-component selection and affected-only qualification path.

1. **Component Release Qualification** — use an existing Repository Ownership
   participant and the current manifest/runtime model to assess whether exactly
   one source participant, its necessary distribution/target dependency, its
   patch-only version handling, affected-only Verification/Software Assurance/
   Trusted Delivery evidence, qualified runner routing and recovery evidence
   can be represented without changing coordinated Platform Release semantics.

This is a future assessment only. It authorizes no release-mode implementation,
workflow change, component release, tag, publication, deployment or rollback.

## Conclusion

`GO_COMPONENT_RELEASE_MODE_PARTIALLY_QUALIFIED`

DJConnect already has canonical releaseable repository units, a patch-only
compatibility boundary and one recorded HACS component-patch precedent. The
single remaining question is whether the existing manifest/runtime can qualify
the generic one-component selection path fail closed. The sole next step is the
bounded **Component Release Qualification** assessment.
