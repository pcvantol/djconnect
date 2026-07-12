# Verification Runtime Capability Model

Status: Canonical  
Runtime product: Verification Runtime  
Repository: `pcvantol/djconnect`  
Docker distribution: `pcvantol/djconnect-verification-platform`

## Purpose

Capabilities are the public API of the Verification Runtime.

Consumers should depend on named capabilities, compatibility decisions,
metadata, evidence contracts and qualification outputs. They should not depend
on internal module paths, command implementation details, local checkout
layout or Docker image internals.

The Verification Runtime remains physically located in this repository. It is
nevertheless an independently versioned engineering product with its own
release lifecycle and Docker distribution channel.

## Product Positioning

| Field | Value |
| --- | --- |
| Product name | Verification Runtime |
| Source repository | `pcvantol/djconnect` |
| Docker distribution | `pcvantol/djconnect-verification-platform` |
| Repository role | Source of implementation |
| Docker role | Canonical runtime distribution |
| Release cycle | Independent from DJConnect platform releases |
| Versioning | Semantic Versioning |
| Compatibility | Capability-driven |
| Architecture | Frozen |

## Responsibility Boundary

The Verification Runtime owns:

- planning;
- execution;
- execution orchestration;
- evidence;
- evidence normalization;
- investigator workflow;
- qualification;
- reporting;
- coverage;
- future runtime capabilities.

The Verification Runtime does not own:

- platform architecture;
- repository governance;
- Software Assurance policies;
- business features;
- application implementations.

## Capability Registry

Every public runtime capability must be represented in the Capability
Registry. The registry is the durable contract used by repositories,
bootstrap tooling and future Software Assurance workflows.

Initial capabilities:

| Identifier | Display name | Description | Since | Dependencies | Compatibility | Maturity | Status | Breaking change policy | Future extensibility |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `planner` | Planner | Resolves scenarios, matrices, policies, data profiles, modes and execution batches into deterministic plans. | `1.0.0` | None | Required for scenario execution consumers. | Stable | Active | Breaking changes require a major runtime version unless hidden behind a new capability. | Can add strategy, matrix and policy extensions without changing the identifier when existing plan contracts remain valid. |
| `execution` | Execution | Executes qualified plans through the runtime orchestration layer and thin adapters. | `1.0.0` | `planner` | Required for any mutating or non-mutating scenario run. | Stable | Active | Changes that alter result semantics require a major runtime version or a replacement capability. | Can add execution surfaces, scheduling policies and adapter primitives through sub-capabilities. |
| `evidence` | Evidence | Collects, stores and references run evidence in structured, redacted form. | `1.0.0` | `execution` | Required for qualification-grade runs. | Stable | Active | Evidence schema removals require a major runtime version. Additive metadata is allowed in minor releases. | Can add evidence types, retention hints and integrity metadata. |
| `investigator` | Investigator | Classifies failures by owner, confidence, blocking status and rerun scope. | `1.0.0` | `evidence` | Required for failure triage consumers. | Stable | Active | Classification meaning cannot be changed without a major runtime version. | Can add owner classes, confidence metadata and links to evidence. |
| `qualification` | Qualification | Produces readiness decisions from scenario results, gates, evidence and warnings. | `1.0.0` | `planner`, `execution`, `evidence` | Required for platform qualification workflows. | Stable | Active | Decision values cannot be repurposed without a major runtime version. | Can add policy inputs and richer warning metadata. |
| `reporting` | Reporting | Generates human-readable and machine-readable reports from runtime results. | `1.0.0` | `evidence`, `qualification` | Required for completion reports and CI artifacts. | Stable | Active | Existing report fields remain backward compatible within a major version. | Can add report formats, sections and indexes. |
| `coverage` | Coverage | Ingests native repository coverage reports, validates provenance, normalizes metrics, writes coverage evidence, qualifies coverage state and renders coverage reports. | `1.1.0` | `evidence`, `investigator`, `qualification`, `reporting` | Required for runtime consumers that use coverage as verification evidence. | Stable | Active | Normalized coverage status and qualification values cannot be repurposed within Runtime `1.x`. New formats must be additive parser plugins. | Can add diff coverage, trends, mutation coverage, repository/platform aggregation and quality gates as new capabilities. |

Future capabilities:

| Identifier | Display name | Target | Notes |
| --- | --- | --- | --- |
| `diff_coverage` | Diff Coverage | `1.2.0` | Change-aware coverage selection and reporting. |
| `coverage_trends` | Coverage Trends | `1.3.0` | Historical coverage movement and regression signals. |
| `mutation_testing` | Mutation Testing | `1.4.0` | Mutation execution and survivor reporting. |
| `quality_budget` | Quality Budget | `2.0.0` | Runtime support for budgeted quality policy enforcement. |
| `security_scanning` | Security Scanning | Future | Security scanner integration point. |
| `sbom` | SBOM | Future | Software bill of materials evidence support. |
| `vulnerability_analysis` | Vulnerability Analysis | Future | Vulnerability evidence and qualification support. |

## Capability Metadata Contract

Every capability entry defines:

- identifier;
- display name;
- description;
- since runtime version;
- dependencies;
- compatibility meaning;
- maturity;
- status;
- breaking change policy;
- future extensibility.

Capability identifiers are stable lowercase machine-readable names. Display
names are user-facing labels. Dependencies must reference other registered
capabilities. Future capabilities may be reserved before implementation, but
they must remain marked as future until a runtime release supports them.

## Coverage Parser Plugins

Runtime `1.1.0` includes parser plugins for:

- Cobertura XML;
- LCOV;
- Apple `xccov` / `xcresult` JSON exported coverage.

Repositories still produce native coverage. The runtime consumes native
reports, validates them and normalizes them into coverage evidence.

## Adapter Execution Surfaces

Runtime `1.1.0` supports thin platform adapter execution through the stable
`execution`, `evidence`, `qualification` and `reporting` capabilities.

Current adapter surfaces:

- Home Assistant: live backend REST/WebSocket/runtime/storage/log primitives.
- Apple: simulator/runtime primitives for Apple-only adapter scenarios.
- Raspberry Pi: local/SSH runtime primitives for Pi adapter scenarios.
- Windows: local/remote runtime primitives for Windows adapter scenarios,
  registered as `windows_native_arm64` and mapped to canonical client
  repository `pcvantol/djconnect-windows`.

Adapters execute primitives only. Scenario assertions and expected behavior
remain owned by the Scenario Engine and scenario catalog.

## Extensibility Rule

Runtime growth should happen through explicit capabilities rather than
monolithic feature expansion. A repository may require a capability only after
that capability is present in stable runtime metadata.
