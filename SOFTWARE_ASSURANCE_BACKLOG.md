# DJConnect Software Assurance Backlog

Status: canonical implementation backlog  
Scope owner: `pcvantol/djconnect`  
Phase: architecture and backlog only; no implementation

## Purpose

This backlog decomposes the Software Assurance themes into implementable
epics, feature groups, stories, acceptance criteria and definitions of done.

No functionality is implemented here. No CI workflows are modified. No scanners
or gates are introduced.

## Backlog Hierarchy

Every theme decomposes as:

```text
Theme
  -> Epic
  -> Feature
  -> Story
  -> Acceptance Criteria
  -> Definition of Done
```

## Theme 1: Static Quality

### Epic SA-E01: Static Quality Foundation

Goal: create a reusable static quality model across repositories.

#### Feature SA-E01-F01: Formatting and Linting

Story SA-E01-F01-S01: Define formatting evidence for every source repository.

Acceptance criteria:

- formatting evidence uses the Software Assurance evidence contract;
- repository-specific tools remain repo-owned;
- findings identify owner and severity.

Definition of done:

- `SA-SQ01` and `SA-SQ02` are documented, policy-mapped and fixture-ready.

#### Feature SA-E01-F02: Static Analysis

Story SA-E01-F02-S01: Classify CodeQL, Semgrep and future analyzer findings.

Acceptance criteria:

- existing analyzer signals can be referenced without changing workflows;
- language-specific analyzers use the same evidence contract;
- findings do not become gates until a later policy phase enables them.

Definition of done:

- `SA-SQ03` and `SA-SQ04` have evidence fixtures and severity mappings.

#### Feature SA-E01-F03: Code Quality and Complexity

Story SA-E01-F03-S01: Define maintainability and complexity metrics.

Acceptance criteria:

- metrics are advisory by default;
- metrics have units and trend semantics;
- hotspots map to owning repository.

Definition of done:

- `SA-SQ05` and `SA-SQ06` feed Platform Health without blocking releases.

### Epic SA-E02: Drift and Documentation Assurance

Goal: detect drift between repositories, docs, prompts and canonical
architecture.

#### Feature SA-E02-F01: Documentation Validation

Story SA-E02-F01-S01: Define required documentation and navigation checks.

Acceptance criteria:

- required docs are derived from canonical ownership;
- missing docs become owner-classified findings;
- documentation validation does not rewrite documents automatically.

Definition of done:

- `SA-SQ07` reports doc posture consistently.

#### Feature SA-E02-F02: Architecture and Repository Drift

Story SA-E02-F02-S01: Detect drift from architecture, ADRs and ownership.

Acceptance criteria:

- findings cite canonical source;
- repository-specific exceptions are explicit;
- no runtime behaviour is inferred from text alone.

Definition of done:

- `SA-SQ08` and `SA-SQ09` produce drift evidence.

#### Feature SA-E02-F03: Prompt Drift

Story SA-E02-F03-S01: Keep prompt library aligned with canonical docs.

Acceptance criteria:

- prompts remain execution instructions;
- prompt status aligns with repository status and prompt indexes;
- prompt drift findings do not redefine architecture.

Definition of done:

- `SA-SQ10` can identify stale or conflicting prompts.

## Theme 2: Supply Chain Assurance

### Epic SA-E03: Dependency and License Governance

Goal: create trustworthy dependency, advisory and license posture.

#### Feature SA-E03-F01: Dependency Governance

Story SA-E03-F01-S01: Inventory dependencies without upgrading them.

Acceptance criteria:

- manifests and lockfiles are identified;
- package ownership is repository-specific;
- update decisions remain implementation work.

Definition of done:

- `SA-SC01` and `SA-SC07` can report dependency posture and drift.

#### Feature SA-E03-F02: Vulnerability Posture

Story SA-E03-F02-S01: Map dependencies to advisory evidence.

Acceptance criteria:

- CVE/advisory findings have severity and release impact;
- EPSS/KEV enrichment is separate from raw finding ingestion;
- no network scanner is introduced in this phase.

Definition of done:

- `SA-SC05` and `SA-SC06` have evidence and prioritization models.

#### Feature SA-E03-F03: License Compliance

Story SA-E03-F03-S01: Preserve MIT posture and third-party notice obligations.

Acceptance criteria:

- license evidence references `THIRD_PARTY_NOTICES.md`;
- Spotify trademark and non-affiliation obligations remain visible;
- incompatible or unknown license findings are owner-classified.

Definition of done:

- `SA-SC08` can feed release assurance.

### Epic SA-E04: Artifact and SBOM Assurance

Goal: make release artifacts traceable, verifiable and policy-consumable.

#### Feature SA-E04-F01: SBOM Formats

Story SA-E04-F01-S01: Define SBOM evidence with SPDX and CycloneDX support.

Acceptance criteria:

- SBOM format choice is repository-appropriate;
- both SPDX and CycloneDX can be represented;
- SBOM artifacts are evidence, not product logic.

Definition of done:

- `SA-SC02`, `SA-SC03` and `SA-SC04` share one evidence model.

#### Feature SA-E04-F02: Provenance and Checksums

Story SA-E04-F02-S01: Trace artifacts to source SHA and integrity metadata.

Acceptance criteria:

- provenance identifies repo, branch, SHA, workflow or build context;
- checksum evidence is artifact-specific;
- release repositories remain distribution surfaces only.

Definition of done:

- `SA-SC09` and `SA-SC10` can be consumed by Release Assurance.

#### Feature SA-E04-F03: Signing, Metadata and Containers

Story SA-E04-F03-S01: Define signing and container provenance evidence.

Acceptance criteria:

- signing evidence never exposes signing secrets;
- release metadata includes version and compatibility posture;
- container provenance covers the Verification Runtime image.

Definition of done:

- `SA-SC11`, `SA-SC12` and `SA-SC13` are ready for future implementation.

## Theme 3: Dynamic Runtime Assurance

### Epic SA-E05: Runtime Quality Signals

Goal: establish runtime quality evidence beyond behavioural correctness.

#### Feature SA-E05-F01: Performance, Load and Stress

Story SA-E05-F01-S01: Define performance, load and stress evidence.

Acceptance criteria:

- metrics have units and environment context;
- thresholds are policy-defined, not hardcoded in tools;
- evidence separates product failures from environment constraints.

Definition of done:

- `SA-DR01`, `SA-DR02` and `SA-DR03` can produce trendable reports.

#### Feature SA-E05-F02: Memory and Resource Usage

Story SA-E05-F02-S01: Define memory, CPU, disk, network and battery posture.

Acceptance criteria:

- runtime-specific metrics are normalized where possible;
- constrained-device evidence is not compared blindly with server evidence;
- resource usage can feed execution cost governance.

Definition of done:

- `SA-DR07` and `SA-DR08` are evidence-contract ready.

### Epic SA-E06: Robustness and Recovery

Goal: define how resilience, fuzzing and recovery evidence is collected and
classified.

#### Feature SA-E06-F01: Chaos, Mutation and Fuzz

Story SA-E06-F01-S01: Define advanced robustness evidence.

Acceptance criteria:

- fuzz repro data is redacted;
- mutation findings are advisory until policy-promoted;
- chaos tests do not redefine behavioural scenarios.

Definition of done:

- `SA-DR04`, `SA-DR05` and `SA-DR06` have clear boundaries.

#### Feature SA-E06-F02: Diagnostics, Recovery and Resilience

Story SA-E06-F02-S01: Define diagnostics quality and recovery evidence.

Acceptance criteria:

- diagnostics are useful and privacy-preserving;
- recovery evidence links to rollback or degraded-mode behaviour;
- resilience findings route behavioural questions to Verification.

Definition of done:

- `SA-DR09`, `SA-DR10` and `SA-DR11` feed Operational Health.

## Theme 4: Execution Strategy and Cost Governance

### Epic SA-E07: Execution Planning Foundation

Goal: define cost-aware execution profiles and scheduling inputs.

#### Feature SA-E07-F01: Execution Profiles and Budgets

Story SA-E07-F01-S01: Define Economy, Balanced and Release execution posture.

Acceptance criteria:

- profiles map to policies and evidence levels;
- execution budget includes runtime, cost, hardware and retention;
- profiles do not modify workflows by themselves.

Definition of done:

- `SA-EX01`, `SA-EX12` and `SA-EX14` are canonical.

#### Feature SA-E07-F02: Scheduling and Nightly Strategy

Story SA-E07-F02-S01: Decide what belongs in local, PR, nightly and release
execution.

Acceptance criteria:

- expensive work is assigned to appropriate profiles;
- nightly strategy avoids duplicate release gates;
- scheduling remains architecture until implementation prompts.

Definition of done:

- `SA-EX05` and `SA-EX13` can inform the Planning Engine.

### Epic SA-E08: Runner and Resource Governance

Goal: qualify execution targets and allocate resources safely.

#### Feature SA-E08-F01: Runner Qualification and Health

Story SA-E08-F01-S01: Define hosted, self-hosted, Docker and lab runner
capabilities.

Acceptance criteria:

- runner capability evidence is explicit;
- runner failures are distinct from product failures;
- self-hosted trust boundaries are documented.

Definition of done:

- `SA-EX02`, `SA-EX03`, `SA-EX09` and `SA-EX10` are ready for future use.

#### Feature SA-E08-F02: Hybrid Execution, Concurrency and Hardware

Story SA-E08-F02-S01: Plan hybrid runs without double-booking exclusive
resources.

Acceptance criteria:

- exclusive resources have locks or reservations in the model;
- parallelism respects evidence ordering and resource constraints;
- hardware requirements are explicit.

Definition of done:

- `SA-EX04`, `SA-EX06`, `SA-EX07` and `SA-EX08` are planning-ready.

#### Feature SA-E08-F03: Runner Cost Optimisation

Story SA-E08-F03-S01: Define cost recommendations that preserve evidence.

Acceptance criteria:

- cost optimization never removes required evidence silently;
- optimization recommendations explain tradeoffs;
- cost metrics feed Platform Health.

Definition of done:

- `SA-EX11` can consume metrics from `SA-EX14`.

## Theme 5: Release Assurance

### Epic SA-E09: Release Qualification Model

Goal: define policy-driven release assurance without enabling gates.

#### Feature SA-E09-F01: Release Gates and Evidence

Story SA-E09-F01-S01: Define gate architecture and release evidence bundles.

Acceptance criteria:

- gates are policy-driven;
- evidence bundles reference canonical raw evidence;
- current workflows are not changed.

Definition of done:

- `SA-RA01` and `SA-RA05` are complete architecture artifacts.

#### Feature SA-E09-F02: Release Qualification and Compatibility

Story SA-E09-F02-S01: Consume Verification compatibility evidence in release
review.

Acceptance criteria:

- compatibility validation references Verification reports;
- release qualification does not redefine behavioural pass/fail;
- release impact is explicit for each finding.

Definition of done:

- `SA-RA06` and `SA-RA07` can feed release review.

### Epic SA-E10: Artifact Promotion and Recovery

Goal: define artifact validation, promotion, signing and rollback posture.

#### Feature SA-E10-F01: Artifact Validation and Promotion

Story SA-E10-F01-S01: Validate release artifacts before promotion.

Acceptance criteria:

- artifact naming, versioning, manifests and checksums are checked;
- promotion evidence cites source and artifact metadata;
- release repositories remain distribution surfaces.

Definition of done:

- `SA-RA03` and `SA-RA08` are implementation-ready.

#### Feature SA-E10-F02: Signing and Rollback

Story SA-E10-F02-S01: Define signing posture and recovery evidence.

Acceptance criteria:

- signing evidence excludes secrets;
- rollback and recovery are documented or explicitly accepted as limitations;
- emergency release paths have release impact classification.

Definition of done:

- `SA-RA02` and `SA-RA04` have acceptance criteria and evidence contracts.

## Theme 6: Platform Health

### Epic SA-E11: Platform Health Foundation

Goal: define metrics, baselines, budgets and trends.

#### Feature SA-E11-F01: Metrics and Trends

Story SA-E11-F01-S01: Define health metrics and trend semantics.

Acceptance criteria:

- metrics have stable IDs, units and dimensions;
- trends distinguish stale, missing, improving and degrading evidence;
- health does not override release gates.

Definition of done:

- `SA-PH01`, `SA-PH02` and `SA-PH03` are canonical.

#### Feature SA-E11-F02: Quality Budgets

Story SA-E11-F02-S01: Define quality budgets for risk, debt, cost and evidence
freshness.

Acceptance criteria:

- budgets guide prioritization;
- budget exhaustion does not silently create gates;
- budget exceptions are owner-classified.

Definition of done:

- `SA-PH04` can inform backlog and release review.

### Epic SA-E12: Health Reporting

Goal: compose repository, engineering, verification, operational, security and
supply-chain health.

#### Feature SA-E12-F01: Repository and Engineering Health

Story SA-E12-F01-S01: Define repository and engineering scorecards.

Acceptance criteria:

- scorecards are comparable across repos;
- repo-specific exceptions are visible;
- findings have owners and backlog path.

Definition of done:

- `SA-PH05` and `SA-PH06` are reporting-ready.

#### Feature SA-E12-F02: Verification, Operational, Security and Supply Chain
Health

Story SA-E12-F02-S01: Compose health dimensions from existing evidence.

Acceptance criteria:

- Verification health references Verification evidence only;
- operational health references diagnostics and recovery posture;
- security and supply chain health classify release impact.

Definition of done:

- `SA-PH07`, `SA-PH08`, `SA-PH09` and `SA-PH10` can feed Platform Health.

#### Feature SA-E12-F03: Dashboard and Reporting

Story SA-E12-F03-S01: Define dashboard data and health report composition.

Acceptance criteria:

- dashboard is data-model only in this phase;
- reports are redacted and durable;
- report summaries remain advisory unless policy marks them blocking.

Definition of done:

- `SA-PH11` and `SA-PH12` are ready for future implementation.

## Cross-cutting Epic SA-E00: Assurance Foundation

Goal: avoid duplicated implementation across themes.

Features:

- evidence contract;
- policy catalog;
- reporting contract;
- configuration model;
- ownership registry;
- metrics contract;
- investigator integration;
- backlog integration;
- compatibility and versioning;
- notification model.

Stories:

- define common evidence and report schemas;
- define owner and severity classification;
- define compatibility and versioning rules;
- define backlog conversion rules;
- define notification routing architecture.

Acceptance criteria:

- every theme references common evidence and reporting contracts;
- findings have one owner;
- reports do not duplicate raw evidence;
- no implementation starts during architecture sprint.

Definition of done:

- `SA-X01` through `SA-X10` are accepted as reusable cross-cutting
  capabilities.

## Blocking Status And Release Impact

| Status | Meaning | Release impact |
| --- | --- | --- |
| Advisory | Informational or trend-only. | Does not block release. |
| Warning | Requires acknowledgement or backlog item. | May require release note or maintainer sign-off. |
| Blocking | Must be fixed or explicitly waived for the scoped policy. | Blocks the policy scope. |
| Release-blocking | Cannot release without fix or formal release waiver. | Blocks release qualification. |

Future implementation must not invent new blocking semantics in scripts or
workflow files.
