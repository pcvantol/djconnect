# Verification Runtime Roadmap

Status: Canonical planning model  
Runtime product: Verification Runtime  
Scope: capability-oriented runtime evolution

## Purpose

The Verification Runtime roadmap describes capability evolution for the
runtime product. It does not define DJConnect product features, platform
architecture, repository governance or Software Assurance policy.

Coverage implementation belongs to Runtime `1.1.0` and is now active as the
first post-`1.0.0` runtime capability.

## Roadmap

| Runtime version | Capability focus | Notes |
| --- | --- | --- |
| `1.0.0` | Planning, Execution, Evidence, Qualification, Reporting | Stable runtime identity and Docker distribution. Includes Investigator as an active failure-classification workflow. |
| `1.1.0` | Coverage, Capability Registry, Coverage Evidence | Current stable runtime. Adds platform-independent native coverage ingestion, validation, normalization, evidence, qualification, investigator signals and reporting. |
| `1.2.0` | Diff Coverage | Change-aware coverage and reporting. |
| `1.3.0` | Coverage Trends | Historical coverage movement, trend evidence and regression signals. |
| `1.4.0` | Mutation Testing | Mutation execution, survivor classification and evidence. |
| `1.5.0` | Coverage Quality Gates | Capability-backed quality gate inputs for coverage policies. |
| `2.0.0` | Quality Budget Runtime | Runtime support for quality budget enforcement and higher-order policy integration. |

## Roadmap Rules

- Each roadmap item should map to one or more named capabilities.
- Runtime releases remain independent from DJConnect platform releases.
- Future runtime capabilities must not silently become platform architecture.
- Software Assurance may consume runtime outputs, but it does not own runtime
  implementation.
- A capability is not available to consumers until stable runtime metadata
  advertises it.

## Deferred Capabilities

The following capabilities are reserved for future modelling and scheduling:

- `security_scanning`;
- `sbom`;
- `vulnerability_analysis`.

These are not part of Runtime `1.1.0` coverage implementation unless a later
prompt explicitly changes the roadmap.
