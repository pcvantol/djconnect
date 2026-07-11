# DJConnect Software Assurance Versioning

Status: canonical versioning model  
Scope owner: `pcvantol/djconnect`  
Phase: architecture frozen; implementation deferred

## Purpose

This document defines lifecycle and semantic versioning expectations for
Software Assurance architecture, capability model, implementation, Platform
Health, release consumption and baseline updates.

## Lifecycle

```text
Software Assurance Architecture
  -> Capability Model
  -> Implementation
  -> Platform Health
  -> Release
  -> Baseline
  -> Continuous Improvement
```

## Versioned Artifacts

| Artifact | Version expectation | Owner |
| --- | --- | --- |
| Software Assurance Architecture | Semantic architecture version. | Canonical Platform |
| Capability Model | Semantic capability model version. | Canonical Platform |
| Verification Runtime integration | Runtime compatibility version and runtime release version. | Verification Runtime |
| Evidence contracts | Schema version. | Canonical Platform |
| Reporting contracts | Schema version. | Canonical Platform |
| Platform Health model | Health schema/model version. | Canonical Platform |
| Release evidence bundle | Bundle schema version. | Release Assurance |
| Repository extensions | Repository-local compatible version. | Owning repository |

## Semantic Versioning Expectations

Use semantic versioning principles:

- major: breaking change to architecture, capability IDs, evidence schema,
  reporting schema or compatibility contracts;
- minor: additive capability, evidence class, report field, repository support
  or policy class;
- patch: clarification, typo, non-breaking documentation or metadata update.

Architecture is currently frozen at:

```text
Software Assurance Architecture: 1.0.0
Capability Model: 1.0.0
```

Future implementation may introduce separate runtime or schema versions, but
must remain compatible with this architecture unless an accepted architectural
review changes it.

## Compatibility Rules

- Capability IDs are stable.
- Evidence schemas must declare version.
- Reports must declare schema and producer version.
- Runtime evidence must declare Verification Runtime version.
- Repository extensions must declare compatible Software Assurance architecture
  and capability model versions.
- Breaking changes require migration notes and architecture review.

## Baseline Update

Platform Baseline may be updated only after:

- implementation wave is complete;
- evidence is durable;
- release impact is known;
- Platform Health model can consume the result;
- completion report exists;
- maintainer accepts the new baseline.

## Continuous Improvement

Continuous improvement may refine thresholds, add evidence classes or update
repository extensions. It must not bypass architecture freeze rules.

New architectural subsystems require explicit architectural review.
