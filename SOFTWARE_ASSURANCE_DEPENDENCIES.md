# DJConnect Software Assurance Dependencies

Status: canonical dependency graph  
Scope owner: `pcvantol/djconnect`  
Phase: architecture and backlog only; no implementation

## Purpose

This document defines the dependency graph for Software Assurance
implementation. Dependencies must be acyclic and must preserve existing
Verification ownership.

## Foundation Graph

```text
SA-X01 Evidence Contract
  -> SA-X02 Policy Catalog
  -> SA-X03 Reporting Contract
  -> SA-X04 Configuration Model
  -> SA-X05 Ownership Registry
  -> SA-X06 Metrics Contract
  -> SA-X07 Investigator Integration
  -> SA-X08 Backlog Integration
  -> SA-X09 Compatibility Model
  -> SA-X10 Notification Model
```

`SA-X01` is the root dependency for most capabilities because no theme can
produce durable Software Assurance evidence without a shared evidence contract.

## Theme Dependency Graph

```text
Static Quality
  SA-X01
    -> SA-X02
    -> SA-SQ01 Formatting
    -> SA-SQ02 Linting
    -> SA-SQ03 Static Analysis
    -> SA-SQ04 Language-specific Analyzers
    -> SA-X06
    -> SA-SQ05 Code Quality
    -> SA-SQ06 Complexity Analysis
    -> SA-SQ07 Documentation Validation
    -> SA-X05
    -> SA-SQ08 Architecture Drift Detection
    -> SA-SQ09 Repository Drift Detection
    -> SA-SQ10 Prompt Drift Detection
```

```text
Supply Chain Assurance
  SA-X01
    -> SA-SC01 Dependency Governance
    -> SA-SC02 SBOM
      -> SA-SC03 SPDX
      -> SA-SC04 CycloneDX
    -> SA-SC05 CVE Advisory Mapping
      -> SA-SC06 EPSS/KEV Risk Enrichment
    -> SA-SC07 Dependency Drift
    -> SA-SC08 License Compliance
    -> SA-SC09 Artifact Provenance
      -> SA-SC10 Checksums
      -> SA-SC11 Signing
      -> SA-SC12 Release Metadata
      -> SA-SC13 Container Provenance
```

```text
Dynamic Runtime Assurance
  SA-X01
    -> SA-X06
    -> SA-DR01 Performance
      -> SA-DR02 Stress
      -> SA-DR03 Load
    -> SA-DR06 Fuzz
    -> SA-DR07 Memory
    -> SA-DR08 Resource Usage
    -> SA-DR09 Runtime Diagnostics
      -> SA-DR10 Recovery
      -> SA-DR11 Resilience
    -> SA-X07
      -> SA-DR04 Chaos
      -> SA-DR05 Mutation
```

```text
Execution Strategy And Cost Governance
  SA-X02
    -> SA-EX01 Execution Profiles
    -> SA-EX12 Artifact Retention
    -> SA-EX14 Execution Budget
    -> SA-EX05 Scheduling
      -> SA-EX13 Nightly Strategy
    -> SA-EX02 Cloud Execution
    -> SA-EX03 Self-hosted Execution
      -> SA-EX09 Runner Qualification
      -> SA-EX10 Runner Health
      -> SA-EX11 Runner Cost Optimisation
    -> SA-EX06 Parallelism
      -> SA-EX07 Concurrency
      -> SA-EX08 Hardware Allocation
    -> SA-EX04 Hybrid Execution
```

```text
Release Assurance
  SA-X01
    -> SA-X02
    -> SA-X03
    -> SA-RA01 Release Gates
    -> SA-RA05 Release Evidence
    -> SA-SC09 Artifact Provenance
      -> SA-SC10 Checksums
      -> SA-SC11 Signing
      -> SA-SC12 Release Metadata
    -> SA-RA02 Release Signing
    -> SA-RA03 Promotion
    -> SA-DR10 Recovery
      -> SA-RA04 Rollback
    -> Verification Evidence Reference
      -> SA-RA06 Compatibility Validation
    -> SA-RA07 Release Qualification
    -> SA-RA08 Artifact Validation
```

```text
Platform Health
  SA-X03
    -> SA-X06
    -> SA-PH01 Health Metrics
    -> SA-PH02 Trend Analysis
    -> SA-PH03 Historical Baselines
    -> SA-PH04 Quality Budgets
    -> SA-SQ09 Repository Drift Detection
      -> SA-PH05 Repository Health
    -> SA-SQ05 Code Quality
      -> SA-PH06 Engineering Health
    -> Verification Report Reference
      -> SA-PH07 Verification Health
    -> SA-DR09 Runtime Diagnostics
      -> SA-PH08 Operational Health
    -> SA-SQ03 Static Analysis
    -> SA-SC05 CVE Advisory Mapping
      -> SA-PH09 Security Health
    -> SA-SC02 SBOM
    -> SA-SC08 License Compliance
    -> SA-SC09 Artifact Provenance
      -> SA-PH10 Supply Chain Health
    -> SA-PH11 Dashboard
    -> SA-PH12 Reporting
```

## Critical Paths

### Release Assurance Critical Path

```text
SA-X01 Evidence Contract
  -> SA-X02 Policy Catalog
  -> SA-X03 Reporting Contract
  -> SA-SC09 Artifact Provenance
  -> SA-SC10 Checksums
  -> SA-SC12 Release Metadata
  -> SA-RA05 Release Evidence
  -> SA-RA07 Release Qualification
```

### Supply Chain Critical Path

```text
SA-SC01 Dependency Governance
  -> SA-SC02 SBOM
  -> SA-SC05 CVE Advisory Mapping
  -> SA-SC08 License Compliance
  -> SA-SC09 Artifact Provenance
  -> SA-PH10 Supply Chain Health
```

### Platform Health Critical Path

```text
SA-X03 Reporting Contract
  -> SA-X06 Metrics Contract
  -> SA-PH01 Health Metrics
  -> SA-PH02 Trend Analysis
  -> SA-PH05 Repository Health
  -> SA-PH12 Reporting
```

### Execution Governance Critical Path

```text
SA-X02 Policy Catalog
  -> SA-EX01 Execution Profiles
  -> SA-EX12 Artifact Retention
  -> SA-EX14 Execution Budget
  -> SA-EX09 Runner Qualification
  -> SA-EX04 Hybrid Execution
```

## No Circular Dependencies

The graph is intentionally one-directional:

```text
Contracts
  -> Policies
  -> Capabilities
  -> Evidence
  -> Reports
  -> Health
  -> Backlog / Release Inputs
```

Backlog items may request future improvements, but backlog items must not
become prerequisites for the evidence that created them. That prevents cycles.

## Verification Runtime Dependencies

Software Assurance may depend on Verification Runtime capabilities for:

- Planning Engine integration;
- Execution Environment metadata;
- evidence references;
- run identity;
- runtime version metadata;
- investigator classification;
- compatibility and behavioural evidence references.

Software Assurance must not depend on Verification Runtime for:

- product expected results;
- feature implementation;
- client behaviour;
- release policy invention;
- duplicated raw evidence storage.

## Repository-specific Extension Dependencies

Repository-specific extensions may implement language analyzers, build
metadata extraction, artifact validation or release evidence production only
after canonical contracts exist.

Required order:

```text
Canonical contract
  -> repository extension design
  -> local evidence production
  -> canonical report aggregation
  -> health or release input
```

Skipping the canonical contract creates duplicated governance and is not
allowed.
