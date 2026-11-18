# DJConnect Software Assurance Capability Model

Status: canonical capability model  
Scope owner: `pcvantol/djconnect`  
Phase: architecture and backlog only; no implementation

## Purpose

This document decomposes the Software Assurance Platform architecture into
reusable implementation capabilities.

Capabilities describe what future implementation phases may build. They are
not implemented by this document. They do not enable CI gates, introduce
scanners or modify workflows.

## Capability Fields

Every capability uses these fields:

- ID
- Name
- Theme
- Description
- Owner
- Repository scope
- Dependencies
- Required execution environment
- Verification method
- Evidence produced
- Completion criteria

## Ownership Layers

| Layer | Responsibility |
| --- | --- |
| Canonical Platform | Owns Software Assurance contracts, capability IDs, policy model, evidence taxonomy, cross-repository governance and platform health. |
| Verification Runtime | Owns planning, execution-environment metadata, evidence references and reusable runtime plumbing where Software Assurance capabilities execute through the Verification stack. |
| Repository-specific extensions | Own repo-local tool adapters, language analyzers, build metadata, release scripts, artifact checks and local evidence production. |
| Release repositories | Own distribution artifact metadata and publication evidence only. |

## Execution Targets

Capabilities may support these targets:

- Developer
- GitHub-hosted
- Self-hosted
- Docker
- Lab
- Nightly
- Release

No capability requires every target. Future implementation must select targets
through Software Assurance policy and the Verification Planning Engine.

## Priority Model

| Priority | Meaning |
| --- | --- |
| P0 | Foundation capability required before meaningful Software Assurance implementation can start. |
| P1 | High-value capability needed for first useful repository and release assurance. |
| P2 | Expansion capability that improves depth, breadth or automation after P0/P1 exist. |
| P3 | Advanced or optimization capability that should not block earlier adoption. |

Priorities are based on dependency centrality, risk reduction and reuse across
themes, not arbitrary sequence.

## Capability Catalog

| ID | Name | Theme | Description | Owner | Repository scope | Dependencies | Required execution environment | Verification method | Evidence produced | Completion criteria | Priority |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| SA-X01 | Evidence Contract | Cross-cutting | Canonical evidence schema, redaction rules, references and ownership metadata. | Canonical Platform | All repos | None | Developer, GitHub-hosted, Docker | Schema review and fixture validation | Evidence schema fixtures and redaction examples | Evidence can be referenced by every theme without duplication. | P0 |
| SA-X02 | Policy Catalog | Cross-cutting | Canonical Software Assurance policies, severities, release impact and execution profile mapping. | Canonical Platform | All repos | SA-X01 | Developer, GitHub-hosted | Static policy validation | Policy catalog and validation report | Policies can classify advisory, warning, blocking and release-blocking findings. | P0 |
| SA-X03 | Reporting Contract | Cross-cutting | Report layers from evidence reference to theme, repository health and platform health. | Canonical Platform | All repos | SA-X01, SA-X02 | Developer, GitHub-hosted, Docker | Report fixture validation | Report schema examples | Reports can aggregate evidence without owning raw evidence. | P0 |
| SA-X04 | Configuration Model | Cross-cutting | Shared configuration for capability selection, repository scope, execution profile and retention posture. | Canonical Platform | All repos | SA-X02 | Developer, GitHub-hosted, Docker | Config fixture validation | Config examples | Configuration is stable and separate from workflow implementation. | P0 |
| SA-X05 | Ownership Registry | Cross-cutting | Registry that maps findings to platform, Verification, repository or release owners. | Canonical Platform | All repos | REPOSITORY_OWNERSHIP.md, SA-X02 | Developer | Documentation and registry validation | Ownership map | Findings always identify an owner and escalation path. | P0 |
| SA-X06 | Metrics Contract | Cross-cutting | Canonical metrics names, units, dimensions and trend semantics. | Canonical Platform | All repos | SA-X01, SA-X03 | Developer | Schema review | Metrics taxonomy | Metrics can feed Platform Health consistently. | P1 |
| SA-X07 | Investigator Integration | Cross-cutting | Software Assurance finding classification routed through or aligned with Verification Investigator semantics. | Verification Runtime | All repos | SA-X01, SA-X05 | Developer, Docker, Lab | Dry-run classification fixtures | Classification report | Findings classify owner, confidence, severity and rerun/follow-up scope. | P1 |
| SA-X08 | Backlog Integration | Cross-cutting | Durable conversion of unresolved findings into platform or repository backlog items. | Canonical Platform | All repos | SA-X05, SA-X07 | Developer | Documentation validation | Backlog item examples | Non-fixed findings have consistent backlog placement. | P1 |
| SA-X09 | Compatibility Model | Cross-cutting | Capability versioning and compatibility rules for Software Assurance artifacts. | Canonical Platform | All repos | SA-X01, SA-X04 | Developer | Schema compatibility fixtures | Version matrix | Future schema changes remain backward-compatible or explicitly migrated. | P1 |
| SA-X10 | Notification Model | Cross-cutting | Architecture for advisory/report notifications without implementing delivery. | Canonical Platform | All repos | SA-X03, SA-X05 | Developer | Documentation review | Notification routing model | Future notifications have owner, severity and privacy boundaries. | P3 |
| SA-SQ01 | Formatting | Static Quality | Repository-format checks and formatting evidence. | Repository-specific extensions | Source repos | SA-X01, SA-X02 | Developer, GitHub-hosted | Existing or future formatter dry-run evidence | Formatting result reference | Repo can report formatting status without changing code. | P1 |
| SA-SQ02 | Linting | Static Quality | Language and framework lint result ingestion and classification. | Repository-specific extensions | Source repos | SA-X01, SA-X02 | Developer, GitHub-hosted | Lint fixture/report validation | Lint result reference | Lint findings map to severity and owner. | P1 |
| SA-SQ03 | Static Analysis | Static Quality | General static analyzer evidence such as CodeQL or Semgrep results. | Repository-specific extensions | Source repos | SA-X01, SA-X02, SA-X03 | GitHub-hosted, Nightly | Analyzer report fixture validation | Static-analysis report reference | Existing analyzer signals can be classified without redefining gates. | P1 |
| SA-SQ04 | Language-specific Analyzers | Static Quality | Swift, Python, TypeScript, C/C++, .NET or platform-native analyzers. | Repository-specific extensions | Source repos | SA-SQ03 | Developer, GitHub-hosted, Self-hosted | Analyzer-specific fixture validation | Analyzer evidence | Each repo can add analyzers through the same evidence contract. | P2 |
| SA-SQ05 | Code Quality | Static Quality | Code quality posture beyond lint, including maintainability findings. | Canonical Platform | Source repos | SA-X06, SA-SQ02 | Developer, Nightly | Metrics fixture review | Code quality metrics | Quality metrics have thresholds or advisory budgets. | P2 |
| SA-SQ06 | Complexity Analysis | Static Quality | Complexity metrics and hotspot evidence. | Repository-specific extensions | Source repos | SA-X06, SA-SQ05 | Developer, Nightly | Metrics fixture validation | Complexity report | Complexity can be trended without blocking by default. | P2 |
| SA-SQ07 | Documentation Validation | Static Quality | Documentation link, navigation and required-doc presence checks. | Canonical Platform, repository extensions | All repos | SA-X01, SA-X02 | Developer, GitHub-hosted | Documentation fixture validation | Documentation validation report | Missing or stale docs are classified consistently. | P1 |
| SA-SQ08 | Architecture Drift Detection | Static Quality | Detects divergence from canonical architecture docs and accepted ADRs. | Canonical Platform | All repos | SA-X05, SA-SQ07 | Developer, Nightly | Drift fixture review | Architecture drift report | Drift findings cite canonical source and owning repo. | P1 |
| SA-SQ09 | Repository Drift Detection | Static Quality | Detects repo-local bootstrap, ownership, license or required-file drift. | Canonical Platform | All repos | SA-X05, SA-SQ07 | Developer, GitHub-hosted, Nightly | Repository inventory fixture validation | Repository drift report | Repos can be compared against canonical baseline. | P1 |
| SA-SQ10 | Prompt Drift Detection | Static Quality | Detects prompt library drift from canonical docs and active phase state. | Canonical Platform | Prompt library | SA-X05, SA-SQ08 | Developer | Prompt inventory validation | Prompt drift report | Prompts remain execution instructions, not architecture truth. | P2 |
| SA-SC01 | Dependency Governance | Supply Chain Assurance | Dependency inventory, ownership and update policy evidence. | Repository-specific extensions | Source repos | SA-X01, SA-X02 | Developer, GitHub-hosted, Nightly | Dependency fixture validation | Dependency inventory | Dependencies can be inventoried without upgrading. | P0 |
| SA-SC02 | SBOM | Supply Chain Assurance | Canonical SBOM evidence contract. | Canonical Platform, repo extensions | Source and release repos | SA-SC01 | GitHub-hosted, Release | SBOM fixture validation | SBOM reference | SBOM evidence can be generated by future tools and consumed consistently. | P1 |
| SA-SC03 | SPDX | Supply Chain Assurance | SPDX output support and validation posture. | Repository-specific extensions | Source and release repos | SA-SC02 | GitHub-hosted, Release | SPDX fixture validation | SPDX document reference | SPDX artifacts validate against the evidence contract. | P2 |
| SA-SC04 | CycloneDX | Supply Chain Assurance | CycloneDX output support and validation posture. | Repository-specific extensions | Source and release repos | SA-SC02 | GitHub-hosted, Release | CycloneDX fixture validation | CycloneDX document reference | CycloneDX artifacts validate against the evidence contract. | P2 |
| SA-SC05 | CVE Advisory Mapping | Supply Chain Assurance | Maps dependencies or artifacts to CVE/advisory findings. | Repository-specific extensions | Source and release repos | SA-SC01, SA-X02 | Nightly, Release | Advisory fixture validation | Advisory report | Advisory findings have severity, owner and release impact. | P1 |
| SA-SC06 | EPSS/KEV Risk Enrichment | Supply Chain Assurance | Enriches vulnerability findings with exploit likelihood and known exploitation. | Canonical Platform | All repos | SA-SC05, SA-X06 | Nightly, Release | Enrichment fixture review | Risk-enriched advisory report | Advisory risk can be prioritized beyond raw severity. | P2 |
| SA-SC07 | Dependency Drift | Supply Chain Assurance | Tracks stale, unpinned, diverged or outdated dependencies. | Repository-specific extensions | Source repos | SA-SC01, SA-X06 | GitHub-hosted, Nightly | Drift fixture validation | Dependency drift report | Drift findings become advisory or backlog work. | P1 |
| SA-SC08 | License Compliance | Supply Chain Assurance | License inventory and compatibility posture. | Canonical Platform, repo extensions | All repos | SA-SC01, THIRD_PARTY_NOTICES.md | GitHub-hosted, Release | License fixture validation | License compliance report | License findings preserve MIT and Spotify non-affiliation obligations. | P0 |
| SA-SC09 | Artifact Provenance | Supply Chain Assurance | Build source, SHA, workflow and artifact origin metadata. | Verification Runtime, repo extensions | Release-producing repos | SA-X01, SA-SC01 | GitHub-hosted, Release | Provenance fixture validation | Provenance metadata | Artifacts can be traced to source and build context. | P1 |
| SA-SC10 | Checksums | Supply Chain Assurance | Artifact checksum generation and validation evidence contract. | Repository-specific extensions | Release repos | SA-SC09 | Release | Checksum fixture validation | Checksum manifest | Release artifacts have verifiable integrity metadata. | P1 |
| SA-SC11 | Signing | Supply Chain Assurance | Signing evidence model for app, firmware, container or release artifacts. | Repository-specific extensions | Release-producing repos | SA-SC09 | Self-hosted, Release | Signing metadata fixture review | Signing attestation | Signing status is visible without exposing secrets. | P2 |
| SA-SC12 | Release Metadata | Supply Chain Assurance | Release notes, version, compatibility, manifest and asset metadata validation. | Canonical Platform, repo extensions | Release repos | SA-SC09, SA-SC10 | Release | Metadata fixture validation | Release metadata report | Release metadata is complete and traceable. | P1 |
| SA-SC13 | Container Provenance | Supply Chain Assurance | Provenance for Verification Runtime or future container artifacts. | Verification Runtime | Container-producing repos | SA-SC09 | Docker, Release | OCI label/provenance fixture validation | Container provenance report | Containers identify source SHA, runtime version and build context. | P1 |
| SA-DR01 | Performance | Dynamic Runtime Assurance | Latency, throughput and responsiveness quality signals. | Verification Runtime, repo extensions | Runtime/client repos | SA-X01, SA-X06 | Developer, Lab, Nightly, Release | Performance fixture and scenario reference validation | Performance report | Performance evidence is traceable and trendable. | P2 |
| SA-DR02 | Stress | Dynamic Runtime Assurance | Sustained or high-volume runtime stress posture. | Verification Runtime, repo extensions | Runtime/client/firmware repos | SA-DR01 | Lab, Nightly | Stress run fixture validation | Stress report | Stress findings classify owner and resource limits. | P2 |
| SA-DR03 | Load | Dynamic Runtime Assurance | Multi-user, multi-client or backend load posture. | Verification Runtime, repo extensions | Runtime/API/client repos | SA-DR01 | Lab, Nightly | Load fixture validation | Load report | Load evidence separates product defects from environment limits. | P3 |
| SA-DR04 | Chaos | Dynamic Runtime Assurance | Fault injection and degraded dependency posture. | Verification Runtime | Runtime/API/client repos | SA-X07, SA-DR01 | Lab, Nightly | Chaos fixture validation | Chaos evidence | Degraded-path findings preserve behavioural Verification ownership. | P3 |
| SA-DR05 | Mutation | Dynamic Runtime Assurance | Mutation testing or behaviour mutation signal model. | Repository-specific extensions | Source repos | SA-X02, SA-X06 | Developer, Nightly | Mutation report fixture validation | Mutation score report | Mutation findings are advisory until explicitly promoted. | P3 |
| SA-DR06 | Fuzz | Dynamic Runtime Assurance | Fuzzing evidence for parsers, endpoints, payloads or protocols. | Verification Runtime, repo extensions | Runtime/API/firmware repos | SA-X01, SA-X02 | Developer, Self-hosted, Nightly | Fuzz corpus/report validation | Fuzz finding report | Fuzz findings have repro data without secrets. | P2 |
| SA-DR07 | Memory | Dynamic Runtime Assurance | Memory leak, footprint or pressure evidence. | Repository-specific extensions | Client/firmware/runtime repos | SA-X06, SA-DR01 | Developer, Self-hosted, Lab, Nightly | Memory report fixture validation | Memory report | Memory signals are comparable per runtime. | P2 |
| SA-DR08 | Resource Usage | Dynamic Runtime Assurance | CPU, disk, network, battery or runner resource telemetry. | Verification Runtime | All repos with runtime checks | SA-X06, SA-DR01 | Developer, Lab, Nightly | Resource report fixture validation | Resource usage report | Resource evidence feeds execution cost and health. | P2 |
| SA-DR09 | Runtime Diagnostics | Dynamic Runtime Assurance | Diagnostic evidence quality and redaction posture. | Canonical Platform, repo extensions | Runtime/client/firmware repos | SA-X01, SA-X02 | Developer, Lab, Release | Redaction and diagnostics fixture validation | Diagnostics quality report | Diagnostics are useful and privacy-preserving. | P1 |
| SA-DR10 | Recovery | Dynamic Runtime Assurance | Recovery path evidence after failure, rollback or degraded runtime. | Verification Runtime, repo extensions | Runtime/release repos | SA-X07, SA-DR09 | Lab, Release | Recovery fixture validation | Recovery evidence | Recovery findings map to release impact. | P2 |
| SA-DR11 | Resilience | Dynamic Runtime Assurance | Aggregated robustness posture across timeout, retry and degraded modes. | Canonical Platform | All runtime repos | SA-DR01, SA-DR09, SA-DR10 | Nightly, Release | Resilience report validation | Resilience report | Resilience posture can feed Platform Health. | P2 |
| SA-EX01 | Execution Profiles | Execution Strategy and Cost Governance | Economy, Balanced and Release profile definitions and policy mapping. | Canonical Platform | All repos | SA-X02 | Developer | Profile fixture validation | Execution profile catalog | Profiles are usable by future planning without workflow logic. | P0 |
| SA-EX02 | Cloud Execution | Execution Strategy and Cost Governance | Hosted runner or future cloud runner capability model. | Verification Runtime | All repos | SA-EX01 | GitHub-hosted, Docker | Capability fixture validation | Cloud execution capability report | Cloud execution has explicit limits and supported work types. | P2 |
| SA-EX03 | Self-hosted Execution | Execution Strategy and Cost Governance | Self-hosted runner capability and trust model. | Verification Runtime | Hardware/client/runtime repos | SA-EX01, SA-X04 | Self-hosted | Runner capability fixture validation | Self-hosted runner qualification | Self-hosted execution declares capabilities and boundaries. | P1 |
| SA-EX04 | Hybrid Execution | Execution Strategy and Cost Governance | Split plans across hosted, self-hosted, Docker, lab and release targets. | Verification Runtime | All repos | SA-EX02, SA-EX03 | GitHub-hosted, Self-hosted, Docker, Lab | Plan fixture validation | Hybrid execution plan | Hybrid plans avoid duplicate evidence and circular execution. | P2 |
| SA-EX05 | Scheduling | Execution Strategy and Cost Governance | Scheduling architecture for nightly, release and hardware work. | Verification Runtime | All repos | SA-EX01, SA-X04 | Nightly, Release | Schedule fixture review | Schedule metadata | Scheduling can be planned without activating workflows. | P1 |
| SA-EX06 | Parallelism | Execution Strategy and Cost Governance | Planned parallel execution limits and grouping rules. | Verification Runtime | All repos | SA-EX01 | Developer, GitHub-hosted, Self-hosted | Plan fixture validation | Parallelism plan | Parallelism is bounded by resources and evidence ordering. | P1 |
| SA-EX07 | Concurrency | Execution Strategy and Cost Governance | Cross-run concurrency, locks and exclusive resource model. | Verification Runtime | Lab/hardware/release repos | SA-EX05, SA-EX06 | Self-hosted, Lab, Release | Concurrency fixture validation | Lock/resource report | Exclusive resources cannot be double-booked. | P1 |
| SA-EX08 | Hardware Allocation | Execution Strategy and Cost Governance | Hardware capability, reservation and release confidence model. | Verification Runtime, repo extensions | Apple, Pi, ESP32 | SA-EX03, SA-EX07 | Self-hosted, Lab, Release | Hardware capability fixture validation | Hardware allocation report | Hardware requirements are explicit and schedulable. | P2 |
| SA-EX09 | Runner Qualification | Execution Strategy and Cost Governance | Runner capability and trust qualification evidence. | Verification Runtime | All repos | SA-EX03, SA-X01 | GitHub-hosted, Self-hosted, Docker, Lab | Runner qualification fixture validation | Runner qualification report | Runners can be accepted or rejected before execution. | P1 |
| SA-EX10 | Runner Health | Execution Strategy and Cost Governance | Runner reliability, failure and drift trend model. | Verification Runtime | All repos | SA-EX09, SA-X06 | Nightly | Runner health fixture validation | Runner health report | Runner failures can be separated from product failures. | P2 |
| SA-EX11 | Runner Cost Optimisation | Execution Strategy and Cost Governance | Cost signals and optimization recommendations. | Canonical Platform | All repos | SA-EX01, SA-EX10 | Nightly | Cost metric fixture review | Cost report | Cost recommendations preserve required evidence. | P3 |
| SA-EX12 | Artifact Retention | Execution Strategy and Cost Governance | Retention posture by evidence class, severity and profile. | Canonical Platform | All repos | SA-X01, SA-EX01 | Developer, GitHub-hosted, Release | Retention fixture validation | Retention policy | Evidence is retained long enough without hoarding. | P0 |
| SA-EX13 | Nightly Strategy | Execution Strategy and Cost Governance | What belongs in nightly versus PR/local/release execution. | Canonical Platform | All repos | SA-EX01, SA-EX05, SA-EX12 | Nightly | Strategy review | Nightly strategy report | Slow and expensive work has a canonical home. | P1 |
| SA-EX14 | Execution Budget | Execution Strategy and Cost Governance | Runtime, money, hardware and retention budgets by policy/profile. | Canonical Platform | All repos | SA-EX01, SA-X06 | Developer, Nightly, Release | Budget fixture validation | Budget report | Plans can reason about cost before execution. | P1 |
| SA-RA01 | Release Gates | Release Assurance | Release gate architecture and relationship to Software Assurance evidence. | Canonical Platform | All repos | SA-X02, SA-X03 | Release | Gate fixture review | Release gate model | Gates are policy-driven and not workflow-invented. | P1 |
| SA-RA02 | Release Signing | Release Assurance | Release signing evidence consumption across artifacts. | Repository-specific extensions | Release-producing repos | SA-SC11, SA-RA01 | Release | Signing evidence fixture validation | Release signing report | Signing posture is visible in release qualification. | P2 |
| SA-RA03 | Promotion | Release Assurance | Promotion path from candidate to published artifact. | Canonical Platform, repo extensions | Release-producing repos | SA-RA01, SA-SC12 | Release | Promotion fixture review | Promotion evidence | Promotion decisions cite required evidence. | P1 |
| SA-RA04 | Rollback | Release Assurance | Rollback, recovery and downgrade evidence model. | Repository-specific extensions | Release-producing repos | SA-DR10, SA-RA03 | Release | Rollback fixture review | Rollback evidence | Releases document recovery path or accepted limitation. | P1 |
| SA-RA05 | Release Evidence | Release Assurance | Canonical release evidence bundle contract. | Canonical Platform | All repos | SA-X01, SA-X03, SA-RA01 | Release | Bundle fixture validation | Release evidence bundle | Release qualification has one reusable evidence bundle. | P0 |
| SA-RA06 | Compatibility Validation | Release Assurance | Cross-version, cross-client and protocol compatibility evidence. | Verification Runtime | All repos | Verification scenarios, SA-X03 | Lab, Nightly, Release | Verification report reference validation | Compatibility report | Compatibility findings reference Verification evidence. | P1 |
| SA-RA07 | Release Qualification | Release Assurance | Final release assurance input model. | Canonical Platform | All repos | SA-RA01, SA-RA05, SA-RA06 | Release | Qualification fixture review | Release qualification report | Release review can consume Software Assurance evidence. | P1 |
| SA-RA08 | Artifact Validation | Release Assurance | Artifact naming, version, manifest, checksum and metadata validation posture. | Repository-specific extensions | Release repos | SA-SC10, SA-SC12, SA-RA05 | Release | Artifact fixture validation | Artifact validation report | Release artifacts match expected metadata. | P1 |
| SA-PH01 | Health Metrics | Platform Health | Canonical health metrics and score semantics. | Canonical Platform | All repos | SA-X06, SA-X03 | Developer, Nightly | Metrics fixture validation | Health metrics catalog | Metrics can be compared across repos and time. | P0 |
| SA-PH02 | Trend Analysis | Platform Health | Trend computation and interpretation model. | Canonical Platform | All repos | SA-PH01 | Nightly | Trend fixture validation | Trend report | Trends separate improvement, regression and stale data. | P1 |
| SA-PH03 | Historical Baselines | Platform Health | Baseline snapshots for quality comparison. | Canonical Platform | All repos | SA-PH01, SA-PH02 | Nightly, Release | Baseline fixture validation | Baseline report | Health can compare current posture with accepted baseline. | P1 |
| SA-PH04 | Quality Budgets | Platform Health | Allowed debt, risk and cost budget model. | Canonical Platform | All repos | SA-PH01, SA-EX14 | Nightly, Release | Budget fixture review | Quality budget report | Budgets guide priorities without silently creating gates. | P2 |
| SA-PH05 | Repository Health | Platform Health | Per-repository health model and scorecard. | Canonical Platform | All repos | SA-SQ09, SA-PH01 | Nightly | Repository health fixture validation | Repository health report | Each repo has comparable quality posture. | P1 |
| SA-PH06 | Engineering Health | Platform Health | Code quality, CI reliability, docs, maintainability and delivery posture. | Canonical Platform | All repos | SA-SQ05, SA-EX10, SA-PH01 | Nightly | Engineering report fixture validation | Engineering health report | Engineering risks are visible and owned. | P2 |
| SA-PH07 | Verification Health | Platform Health | Verification evidence freshness, pass/warn/block posture and runtime health. | Verification Runtime | All repos | Verification reports, SA-X03 | Nightly, Release | Verification report reference validation | Verification health report | Behavioural evidence health is reported without redefining Verification. | P1 |
| SA-PH08 | Operational Health | Platform Health | Runtime diagnostics, recovery, release operations and support readiness posture. | Canonical Platform | Runtime/release repos | SA-DR09, SA-DR10, SA-RA04 | Nightly, Release | Operational fixture review | Operational health report | Operational risks are separable from functional failures. | P2 |
| SA-PH09 | Security Health | Platform Health | Static security, secret safety, vulnerability and auth-risk posture. | Canonical Platform | All repos | SA-SQ03, SA-SC05, SA-PH01 | Nightly, Release | Security health fixture validation | Security health report | Security posture trends are visible and release impact is explicit. | P1 |
| SA-PH10 | Supply Chain Health | Platform Health | Dependency, SBOM, license, provenance and artifact integrity posture. | Canonical Platform | All repos | SA-SC02, SA-SC08, SA-SC09, SA-PH01 | Nightly, Release | Supply-chain health fixture validation | Supply chain health report | Supply chain risk is trended across repos. | P1 |
| SA-PH11 | Dashboard | Platform Health | Dashboard architecture for health reports without implementing UI. | Canonical Platform | All repos | SA-PH02, SA-PH05 | Nightly | Dashboard data fixture review | Dashboard data model | Future UI can render health without recomputing rules. | P3 |
| SA-PH12 | Reporting | Platform Health | Platform Health report composition and release-review summaries. | Canonical Platform | All repos | SA-X03, SA-PH01 | Nightly, Release | Report fixture validation | Platform Health report | Health reports are stable, redacted and non-gating by default. | P1 |

## Definition Of Done For Capabilities

A Software Assurance capability is done only when:

- the capability has an owner;
- dependencies are satisfied;
- evidence contract is defined;
- supported execution targets are documented;
- verification method exists;
- acceptance criteria are met;
- release impact is classified;
- unresolved findings have backlog placement;
- no duplicate evidence or governance owner is introduced.

Future implementation phases may satisfy capability completion. This Prompt 2
only defines the model.

## Blocking Status And Release Impact

Every capability starts advisory until a future Software Assurance policy
explicitly promotes it. Scripts, workflow files and repository-local extensions
must not invent blocking status.

| Capability IDs | Default blocking status | Default release impact | Promotion rule |
| --- | --- | --- | --- |
| `SA-X01` through `SA-X10` | Blocking for Software Assurance implementation readiness. | Blocks Software Assurance implementation milestones, not product release. | May become release-impacting only when consumed by a release policy. |
| `SA-SQ01` through `SA-SQ10` | Advisory. | No release impact by default. | May become warning/blocking by PR or release policy after evidence is stable. |
| `SA-SC01` | Blocking for supply-chain implementation readiness. | No release impact by default. | May become release-impacting when dependency inventory is required by release policy. |
| `SA-SC02` through `SA-SC04` | Advisory. | Warning for release candidates once SBOM policy is adopted. | May become release-blocking after an explicit release policy. |
| `SA-SC05` and `SA-SC06` | Advisory. | Warning or release-blocking depending on advisory severity and policy. | CVE/KEV findings require policy classification before blocking. |
| `SA-SC07` | Advisory. | No release impact by default. | May become warning when dependency drift exceeds a quality budget. |
| `SA-SC08` | Warning. | Potential release-blocking for incompatible, unknown or missing required license evidence. | Release policy decides exact blocking threshold. |
| `SA-SC09` through `SA-SC13` | Advisory until release policy consumes them. | Warning for release candidates; potentially release-blocking for missing provenance, checksum or required metadata. | Release Assurance policy promotes required artifact evidence. |
| `SA-DR01` through `SA-DR11` | Advisory. | No release impact by default; warning or blocking for release policies that require runtime quality evidence. | Dynamic evidence becomes blocking only by explicit profile/policy. |
| `SA-EX01`, `SA-EX12`, `SA-EX14` | Blocking for execution-governance implementation readiness. | No direct product release impact. | Release policy may require profiles, retention and budgets before release execution. |
| `SA-EX02` through `SA-EX11`, `SA-EX13` | Advisory. | No release impact by default. | May block a specific execution plan when required runner/lab capability is unavailable. |
| `SA-RA01`, `SA-RA05`, `SA-RA07` | Blocking for release-assurance implementation readiness. | Release-impacting once release assurance is adopted. | Product release blocking only after explicit release gate enablement. |
| `SA-RA02`, `SA-RA03`, `SA-RA04`, `SA-RA06`, `SA-RA08` | Advisory until release policy consumes them. | Warning or release-blocking depending on artifact class and policy. | Release Qualification policy sets blocking threshold. |
| `SA-PH01` through `SA-PH12` | Advisory. | Platform Health never unblocks or blocks release by itself. | Health may recommend backlog or release review, but gates remain policy-driven. |

## Capability Acceptance Criteria Summary

For every capability ID in this model:

- Done: the capability has the fields in the catalog, a satisfied dependency
  path and a definition of done in `SOFTWARE_ASSURANCE_BACKLOG.md` or a future
  implementation report.
- Evidence: the capability produces the evidence named in the catalog through
  the shared evidence contract.
- Verification: the capability is verified through the method named in the
  catalog, typically fixture, schema, report or reference validation.
- Owner: the capability owner is the canonical platform, Verification Runtime,
  repository-specific extension or release repository listed in the catalog.
- Blocking status: defaults to the matrix above until promoted by policy.
- Release impact: defaults to the matrix above until promoted by policy.
