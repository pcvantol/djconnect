# DJConnect Software Assurance Implementation Strategy

Status: canonical implementation strategy  
Scope owner: `pcvantol/djconnect`  
Phase: architecture frozen; Software Assurance Generation 1 active; Prompt 1 ready for explicit execution

## Purpose

This document defines how future Software Assurance implementation should begin
after prerequisites are satisfied.

It does not implement tooling, workflows, scanners or gates.

## Transition Rule

Implementation intentionally begins only after:

- all primary platform adapters are complete;
- cross-platform qualification has completed;
- Verification Runtime is released as stable;
- Platform Baseline is updated.

## Strategy Overview

```text
Architecture
  -> Capability Model
  -> Governance
  -> Prerequisite Qualification
  -> Wave Implementation
  -> Advisory Evidence
  -> Policy Promotion
  -> Release Consumption
  -> Baseline Update
```

Implementation starts with advisory evidence and repository visibility. It
does not start with blocking gates.

## CI/CD Strategy

Execution strategy evolves in this order:

```text
Cloud
  -> Self-hosted
  -> Hybrid
  -> Release
```

Cloud/GitHub-hosted execution is preferred for non-mutating, low-risk,
reproducible checks. Self-hosted execution is introduced only for capabilities
that require local toolchains, devices, simulators, signing-aware metadata or
lab access. Hybrid execution combines targets after runner qualification and
concurrency rules exist. Release execution consumes mature evidence after
release-assurance policy is explicit.

No workflow is modified by this strategy.

## Capability Placement By Lifecycle

| Lifecycle | Suitable capabilities | Default posture |
| --- | --- | --- |
| Developer | schemas, dry-runs, formatting/lint evidence previews, documentation checks, plan previews | Advisory and fast. |
| Commit | local static checks and metadata validation where repo tooling exists | Advisory unless repo-local development rules say otherwise. |
| Push | non-mutating static validation and report/schema checks | Advisory or repository gate only after policy promotion. |
| Pull Request | changed-scope static quality, dependency drift, documentation drift, report validation | Advisory first; blocking only after explicit future policy. |
| Main | baseline evidence refresh, repository health refresh, runtime smoke metadata | Advisory trend input. |
| Nightly | broad static quality, dependency drift, dynamic runtime checks, runner health, platform health | Advisory trend input unless policy promotes. |
| Release | artifact provenance, checksums, release evidence bundles, compatibility references, qualification input | Release-impacting only after explicit release policy. |

## Implementation Ownership

| Work type | Owner |
| --- | --- |
| Canonical contracts and governance | `pcvantol/djconnect` |
| Verification Runtime integration | Verification Runtime owner in `pcvantol/djconnect` |
| Repository-specific analyzers and build metadata | Owning source repository |
| Release artifact evidence | Owning release repository |
| Platform Health aggregation | Canonical platform owner |
| Release Qualification consumption | Release governance owner |

## Implementation Readiness

A future implementation prompt must include:

- targeted wave;
- prerequisite status;
- capability IDs;
- owning repository;
- expected evidence;
- execution target;
- policy posture;
- release impact;
- verification method;
- completion report path;
- rollback or disablement posture for any new automation.

## Definition Of Done For Implementation Waves

Each wave is complete only when:

- all scoped capabilities have evidence contracts;
- implementation remains within its owner boundary;
- tests or validation match the capability verification method;
- reports are redacted and durable;
- findings are classified before backlog conversion;
- no hidden gates are introduced;
- navigation and completion reports are updated.

## Roadmap Transition

After the architecture sprint, the platform returns to the active Verification
roadmap.

The prerequisites in this document are satisfied. Software Assurance
Generation 1 is active with Prompt 1 ready for explicit execution; Prompts 2
through 4 remain blocked in sequence. No implementation has started.
