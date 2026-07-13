# DJConnect Platform Release Architecture

Status: `PLATFORM_RELEASE_ARCHITECTURE_COMPLETE`  
Generation: 1  
Scope owner: `pcvantol/djconnect`  
Phase: architecture only; no implementation, rollout or release execution

## Purpose

This document freezes the reusable release architecture for the DJConnect
platform. It defines one Platform Release that coordinates release-relevant
repositories while preserving their local build and distribution ownership.

It is intentionally not a release script, workflow, manifest schema or
repository rollout plan. Those are later implementation concerns and must
conform to this architecture.

## Principles

- The platform owns release policy, lifecycle, evidence meaning and promotion
  decisions; repositories do not independently define them.
- Major.Minor is a platform compatibility train. Patch is a repository-local
  delivery increment.
- Compatibility is evaluated on Major.Minor only, never patch.
- Repository membership is discovered from `REPOSITORY_OWNERSHIP.md`; no
  source, distribution, optional or future repository is hardcoded into the
  release system.
- A release plan is an immutable, scoped snapshot. It records which discovered
  repositories participate and why.
- Verification owns behavioural proof. Software Assurance owns quality-policy
  evidence. Platform Release consumes both; it does not duplicate their gates
  or raw evidence stores.
- Dry Run is a complete non-publishing execution mode, not a shortened test.
- Certification is objective and evidence-derived. An authorization to publish
  may record accountable intent, but cannot convert a failed certification into
  a pass.
- Release repositories are distribution surfaces, never product-logic owners.

## Ownership boundaries

| Concern | Owner | Platform Release consumes or coordinates | Does not own |
| --- | --- | --- | --- |
| Platform compatibility train and release policy | Platform Release | Major.Minor, lifecycle, scope, certification and closure | Product behaviour or repository implementation |
| Repository membership and role | Repository Ownership | Canonical ownership records and release-plan snapshot | A hardcoded repository list |
| Repository build, patch version and artifacts | Owning repository | Candidate version, artifact identity and local evidence | Another repository's code or distribution implementation |
| Behavioural correctness | Verification Platform | Qualification decisions, evidence references and compatible runtime metadata | Scenarios, adapters or expected behaviour |
| Engineering quality and trusted delivery | Software Assurance | Policy status, provenance, integrity and waiver references | Behavioural pass/fail or publishing |
| Publication and channel operation | Distribution repository/channel owner | Published artifact identity and post-release observation | Platform compatibility policy |

## Canonical version model

### Platform version

The Platform Version is `Major.Minor`.

It identifies the compatibility train shared by a scoped Platform Release.
For example, platform `3.3` means every participating repository candidate
declares a release version within `3.3.x`.

### Repository version

Every participating repository uses `Major.Minor.Patch`:

| Repository | Example version |
| --- | --- |
| HA | `3.3.4` |
| Apple | `3.3.2` |
| Windows | `3.3.7` |
| Pi | `3.3.1` |
| ESP | `3.3.5` |
| API | `3.3.2` |
| Website | `3.3.8` |

The examples illustrate the model only; they do not set actual versions.

### Increment rules

| Change | Required increment | Consequence |
| --- | --- | --- |
| Breaking platform contract or unsupported upgrade boundary | Major | New compatibility train; migration and support policy required. |
| Additive or changed shared platform contract/capability | Minor | New platform train; all scoped participating candidates align to it. |
| Repository-local compatible correction, packaging or documentation delivery | Patch | Only the owning repository increments; compatibility remains the same train. |

Patch skew is valid: `3.3.1` interoperates with `3.3.8` when all other
capability and qualification rules pass. A candidate outside the platform
Major.Minor train is incompatible even when its patch value is newer.

### Upgrade and combination policy

- Supported combinations are explicitly recorded in the Release Manifest and
  Compatibility Matrix for the release scope.
- The default supported upgrade path is an in-train patch upgrade.
- A Major or Minor transition requires declared migration, rollback and
  compatibility posture before qualification can pass.
- Mixed Major.Minor combinations, undeclared repository substitutions and
  artifacts without traceable source identity are unsupported.
- Protocol-specific rules may be stricter than this model. For example, an
  existing protocol may require exact Major.Minor agreement. Such rules are
  captured as compatibility evidence, not replaced by release policy.

## Repository discovery and release scope

`REPOSITORY_OWNERSHIP.md` is the canonical membership source. The future
planner derives a repository inventory from its ownership records and assigns
each discovered record a release role:

| Role | Meaning | Release-plan treatment |
| --- | --- | --- |
| Active source | Owns released platform implementation or a shared contract. | Included when its owned capability is in scope. |
| Release source | Produces artifacts or metadata consumed by a distribution surface. | Included after its source prerequisites qualify. |
| Distribution | Publishes a qualified artifact, manifest, store submission or public download. | Included only after corresponding producer artifacts qualify. |
| Optional | Supports a declared capability, channel or client that the release may omit. | Explicitly included or excluded with a reason. |
| Future | Known ownership record with no currently implemented release path. | Visible to planning, never silently assumed mandatory. |

No role is inferred from a repository name. A plan records a snapshot of the
ownership source, scope decision, dependencies, required/optional state and
the reason for exclusion. A later ownership change is a new plan input, not a
retroactive change to an existing release record.

## Dependency graph

The graph represents compatibility and evidence ordering. It is not a claim
that every repository deploys through another repository.

```text
Platform Release Control
  -> Release scope and version alignment
  -> Contract anchors (HA; API when the scoped capability uses central trust)
  -> Client source candidates (Apple | Pi | Windows | ESP32) in parallel
  -> Producer artifacts (firmware/app/Pi artifacts) in parallel where eligible
  -> Distribution surfaces (firmware | app | Pi | stores) in parallel
  -> Website and public release guidance
  -> Post-release verification and certification closure
```

### Node rules

- The release-control node, Release Manifest, version alignment, qualification,
  certification and closure are mandatory for every Platform Release.
- A source node is mandatory only when its owned capability or contract is in
  the approved scope.
- A distribution node is mandatory when the release promises that channel;
  otherwise it must be explicitly excluded.
- Website/public guidance is mandatory for releases that change public
  installation, support, compatibility or user-facing release information.
- Future nodes extend the graph by declaring role, owner, capability scope,
  dependency edges, artifact/evidence contract and rollback capability. They
  never require a release-orchestrator rewrite.

### Ordering and parallelism

Version alignment precedes all candidate preparation. Contract anchors must
provide compatible candidate evidence before dependent client candidates
qualify. Independent clients, artifacts and distribution channels may run in
parallel once their declared prerequisites are complete. Publication is ordered
by dependency and channel recovery constraints, while post-release observation
runs after each published node and before closure.

## Release lifecycle

```text
Release Planning
  -> Version Alignment
  -> Repository Preparation
  -> Verification
  -> Qualification
  -> Release Readiness
  -> Dry Run (when selected)
  -> Certification
  -> Publication Authorization
  -> Production Release
  -> Post-Release Verification
  -> Release Certification Closure
  -> Release Closure
```

| Stage | Outcome | Fail-closed rule |
| --- | --- | --- |
| Release Planning | Immutable scoped Release Manifest and discovered-node snapshot. | No scope, ownership, dependency or channel ambiguity. |
| Version Alignment | Repository Version Matrix and compatibility intent. | Every included candidate matches platform Major.Minor. |
| Repository Preparation | Traceable candidate sources and planned artifacts. | No untraceable source/artifact or unresolved prerequisite. |
| Verification | Referenced behavioural and release-equivalent evidence. | Verification-blocking result stops promotion. |
| Qualification | Release Qualification Report with pass/fail per required gate. | Missing required evidence or a policy failure is fail. |
| Release Readiness | Readiness report with exact publish set and recovery plan. | No incomplete rollback, compatibility or distribution evidence. |
| Dry Run | Complete non-publishing rehearsal result, when mode requires it. | A dry-run failure blocks the corresponding release candidate. |
| Certification | Objective certification decision. | Certification must be `CERTIFIED`; warnings must be policy-accepted and recorded. |
| Publication Authorization | Accountable authorization bound to certified manifest. | It cannot waive or reinterpret a failed certification. |
| Production Release | Ordered publication and durable publication evidence. | Stop affected downstream nodes on any publication failure. |
| Post-Release Verification | Observed installed/distributed artifact and compatibility posture. | Failed critical observation opens recovery, not closure. |
| Certification Closure | Final certification report includes post-release proof. | No closure without all required observations. |
| Release Closure | Immutable closure report and follow-up ownership. | No unresolved release-blocking finding. |

## Release modes

| Mode | Purpose | Publication | Minimum posture |
| --- | --- | --- | --- |
| Development | Fast repository-local candidate feedback. | Never. | Local checks; not a Platform Release certification. |
| Nightly | Broad recurring health and drift observation. | Never by default. | Planned broad evidence; findings classified before promotion. |
| Candidate | Build a scoped, traceable cross-repository release candidate. | Never. | Version alignment, candidate artifacts and required verification. |
| Dry Run | Rehearse the complete selected lifecycle without external mutation. | Never. | Same scope, graph, evidence and qualification as its target release. |
| Qualification | Produce a decision on a candidate or dry-run evidence set. | Never. | Required gates and evidence bundle. |
| Production | Publish a certified immutable candidate in graph order. | Only this mode. | Certification plus bound authorization. |
| Hotfix | Correct an urgent in-train issue with minimized, explicit scope. | Only after certification. | Patch-only unless an Architecture Review authorizes a train change; regression and recovery evidence remain mandatory. |
| Maintenance | Refresh supported train artifacts, metadata or channels without new shared capability. | Policy-defined. | Patch alignment, compatibility and channel evidence. |

Modes are policy selections over one lifecycle. They are not separate,
repository-defined release systems.

## Dry-run architecture

A Dry Run creates the same scope, dependency order, candidate identities,
artifact-generation plan, qualification inputs, reports, readiness decision and
recovery plan as its corresponding production release.

It must perform or validate:

- repository discovery and scope freeze;
- version alignment and compatibility evaluation;
- candidate preparation and artifact generation in non-publishing form;
- verification and qualification evidence collection;
- readiness, certification-preview and closure-report generation;
- orchestration ordering, retry/resume state and rollback rehearsal where it
  can be safely simulated.

It must not create production side effects: publication, deployment, tags,
public releases, store submission, announcements or production-channel
mutation. A dry-run artifact is clearly non-production and cannot be promoted
by relabeling; production requires a certified production candidate with its
own immutable identities.

## Release qualification architecture

Release Qualification answers whether the scoped candidate has complete,
policy-compliant evidence. It is a pass/fail decision on required evidence,
not a subjective release meeting.

### Required qualification inputs

- immutable Release Manifest and repository discovery snapshot;
- Repository Version Matrix and Compatibility Matrix;
- source, build, artifact, checksum, provenance and signing evidence as
  applicable to the repository/channel;
- Verification Runtime evidence references and behavioural qualification;
- Software Assurance and Trusted Delivery policy status;
- release-note, localization, legal, privacy and migration evidence where the
  scoped release changes those surfaces;
- rollback/recovery plan and known-limitations/waiver register.

### Qualification gates

| Gate | Decision owner | Required result |
| --- | --- | --- |
| Scope and ownership | Platform Release | Every node is discovered, classified and intentionally included/excluded. |
| Version and compatibility | Platform Release with owning contracts | All included nodes align to the train; supported combinations are explicit. |
| Behaviour | Verification Platform | Required release-mode scenarios qualify. |
| Assurance and trusted delivery | Software Assurance | No unwaived release-blocking policy failure. |
| Artifact and distribution readiness | Owning repository/channel | Artifact identity, integrity, required signatures and channel metadata are complete. |
| Recovery | Platform Release with channel owner | Applicable rollback or recovery route is proven or explicitly policy-accepted. |
| Evidence completeness | Platform Release | Every required evidence reference is present, redacted and immutable. |

The resulting Release Qualification Report is `PASS` or `FAIL`. A warning is
context, not a third passing state; it must either be non-blocking by policy or
become a documented, expiring waiver. A missing required item is `FAIL`.

## Release certification architecture

Certification consumes the completed qualification report plus the declared
Verification, Software Assurance, Trusted Delivery and readiness inputs. It
answers a narrower question: is this exact candidate objectively ready for the
declared release mode and scope?

```text
Verification qualification
  + Software Assurance / Trusted Delivery status
  + Release Qualification Report
  + Readiness and recovery evidence
  -> Release Certification Report
  -> CERTIFIED | NOT_CERTIFIED
```

`CERTIFIED` requires every required qualification gate to pass, all evidence to
refer to the same immutable candidate set, no unwaived release-blocking finding
and a complete post-release verification plan. `NOT_CERTIFIED` is mandatory
for any other condition. There is no subjective approval state between them.

Publication Authorization is deliberately separate. It records who authorizes
the already-certified release to use a production channel and confirms the
manifest identity. It must not change scope, versions, evidence, policies or
the certification result. Any such change invalidates certification and returns
the lifecycle to planning or qualification.

## Release evidence architecture

Evidence is referenced from its authoritative producer once and assembled into
an immutable, redacted release bundle. The bundle contains references and
identities; it does not copy secrets, raw logs, user data or Verification raw
evidence unnecessarily.

| Evidence artifact | Purpose |
| --- | --- |
| Release Manifest | Immutable identity, mode, scope, ownership snapshot, graph, candidate source identities and declared policy versions. |
| Repository Version Matrix | Platform train and each scoped repository candidate version. |
| Compatibility Matrix | Supported combinations, protocol constraints, upgrade paths and exclusions. |
| Artifact Inventory | Artifact identity, source/build provenance, checksum/signature state and distribution target. |
| Release Qualification Report | Required-gate results and authoritative evidence references. |
| Release Readiness Report | Exact publication set, order, channel prerequisites, communications and recovery posture. |
| Release Certification Report | Objective `CERTIFIED` or `NOT_CERTIFIED` decision for the exact manifest. |
| Publication Ledger | Ordered production publication outcomes; absent from dry runs. |
| Post-Release Verification Report | Observed channel/install/update/compatibility results. |
| Rollback and Recovery Record | Decision, scope, actions, outcomes and residual risk when recovery is used. |
| Release Closure Report | Final outcome, evidence index, follow-ups and next eligible action. |

All evidence declares producer, timestamp, candidate identity, schema/version
where defined, retention posture and redaction status. Later automation may
define schemas, but must preserve these semantic fields.

## Orchestration architecture

The future Platform Release Orchestrator is a control plane, not a replacement
for repository CI, Verification Runtime or distribution systems.

### Responsibilities

- plan an immutable release scope from Repository Ownership;
- resolve dependency ordering and safe parallel groups;
- request repository-local candidate preparation through declared interfaces;
- collect authoritative evidence references and calculate lifecycle state;
- stop downstream work on blocking failures;
- retain a resumable, auditable state record;
- produce reports without publication logic embedded in a repository workflow.

### Failure, retry and resume

- Failures are classified as candidate/repository, verification, assurance,
  orchestration, execution-environment, distribution-channel or external
  dependency failures.
- Retrying never overwrites evidence. A retry has a new attempt identity linked
  to the failed attempt.
- A node may resume only when its inputs, source/artifact identities, policy
  versions and prerequisite evidence remain valid. Otherwise the plan is
  invalidated and requalified.
- Partial completion is explicit: completed independent nodes remain recorded,
  but no dependent publication can proceed past a failed prerequisite.
- Publication is never retried blindly. The orchestrator first reconciles the
  channel's actual state against the Publication Ledger.

## Rollback and recovery architecture

Rollback is a controlled recovery lifecycle, not deletion of history.

| Scope | Use | Recovery rule |
| --- | --- | --- |
| Repository rollback | A single compatible repository patch causes a defect. | Publish a corrective patch or restore a prior channel artifact according to that channel's immutable-artifact rules; requalify affected combinations. |
| Platform rollback | A released train has cross-repository incompatibility or critical systemic failure. | Freeze promotion, define an affected scoped set, recover each channel in dependency-aware order and issue a corrective in-train patch release unless a new train is required. |
| Artifact rollback | A specific artifact is corrupt, unsigned, mispackaged or unsafe. | Withdraw/deprecate where the channel permits; replace with a newly qualified artifact, never mutate immutable evidence. |
| Qualification rollback | Qualification evidence is invalidated before publication. | Mark candidate `NOT_CERTIFIED`, preserve the evidence, correct the cause and restart at the earliest invalid stage. |
| Release recovery | A production publication partially completes or post-release verification fails. | Reconcile actual channel state, stop dependent publication, invoke the scoped recovery plan and produce a Rollback and Recovery Record. |

Every production release must declare a recovery posture per distribution node:
revert, supersede, halt, disable/withdraw, or no technical rollback with
documented user/operator remediation. A channel that cannot roll back is not
exempt; its recovery path must be qualified before publication.

## Future automation boundaries

The following are intentionally future implementations, each requiring an
explicit prompt and policy/evidence contract:

- Release Planner: repository discovery, scope and graph calculation;
- Version Manager: train alignment and compatibility-matrix validation;
- Artifact Manager: inventory, provenance, integrity and channel hand-off;
- Release Orchestrator: lifecycle state, parallelism, retries, resume and
  publication ledger;
- Release Qualification Runtime: gate aggregation and qualification reports;
- Release Dashboard: read-only operational visibility over authoritative
  evidence and lifecycle state.

Automation must not hardcode repository membership, redefine release policy,
embed secrets in reports, publish from dry-run mode, or silently broaden scope.

## Architecture decision

The canonical release model is now:

```text
One Platform Release
  -> discovered repository scope
  -> Major.Minor compatibility train
  -> repository-local Major.Minor.Patch candidates
  -> evidence-based qualification and certification
  -> ordered publication and post-release proof
```

Decision:

```text
PLATFORM_RELEASE_ARCHITECTURE_COMPLETE
```
