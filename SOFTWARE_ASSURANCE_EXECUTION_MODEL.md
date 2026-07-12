# DJConnect Software Assurance Execution Model

Status: canonical execution architecture  
Scope owner: `pcvantol/djconnect`  
Phase: architecture only; no implementation

## Purpose

This document defines how Software Assurance work is planned across execution
targets without duplicating the Verification Runtime or Execution Environment.

Software Assurance specifies what quality work should execute. The Verification
Planning Engine and Execution Environment determine how execution happens.

The Verification Runtime is the independently versioned runtime product that
provides planning, execution, evidence, investigator, qualification and
reporting capabilities. Software Assurance consumes those capabilities through
runtime metadata and compatibility decisions; it does not own the runtime
release lifecycle or redefine runtime capability semantics.

## Execution Ownership

```text
Software Assurance Policy
  -> Execution Profile
  -> Verification Planning Engine
  -> Verification Execution Environment
  -> Execution Target
  -> Evidence
```

Software Assurance owns:

- execution policy;
- execution profiles;
- evidence expectations;
- retention posture;
- cost and resource constraints;
- runner qualification requirements;
- release impact and blocking semantics.

Planning Engine owns:

- plan generation;
- environment matching;
- batching;
- parallelism planning;
- resource allocation;
- retry planning;
- estimated runtime;
- expected evidence.

Execution Environment owns:

- runner and host inspection;
- toolchain and dependency discovery;
- Docker/lab orchestration;
- artifact paths;
- cleanup and restore;
- execution metadata;
- environment snapshots.

Execution Targets run selected work. They do not own policy.

## Canonical Execution Targets

| Target | Responsibility | Suitable work | Not suitable for |
| --- | --- | --- | --- |
| Developer workstation | Fast local feedback and author-side evidence. | Schema validation, dry-runs, local reports, narrow checks. | Release authority or hidden destructive work. |
| GitHub-hosted | Hosted, repeatable, non-mutating automation. | Unit checks, static validation, dry-run planning, report/schema validation, Docker runtime smoke checks. | Hardware, local HA lab mutation, signing secrets, device simulators that are unavailable. |
| Self-hosted | Controlled runner with local capabilities. | Apple simulator/device checks, signing-aware evidence, hardware-adjacent checks, privileged Docker/lab work. | Unqualified or unlabeled execution. |
| Docker | Portable Verification Runtime execution. | Engine smoke tests, scenario validation, planning, report checks and non-mutating dry-runs. | Product state, secrets, lab volumes or evidence baked into images. |
| Lab | Real or dedicated integration environment. | Home Assistant lab, hardware, audio, BLE, serial, SSH, resilience and recovery evidence. | Generic policy ownership. |
| Nightly | Scheduled broad assurance profile. | Slow, broad, expensive, trend-producing or cross-repository checks. | Immediate PR gating unless policy explicitly promotes. |
| Release | Release-candidate and promotion evidence. | Artifact provenance, checksums, compatibility, release evidence bundles, qualification inputs. | Experimental findings without policy classification. |
| Hybrid | Planned split across multiple targets. | Combining hosted checks, self-hosted runtime work, lab evidence and release evidence. | Duplicate evidence or circular execution. |

## Cost-aware Profiles

### Economy

Purpose: fast, low-cost feedback.

Default posture:

- preferred execution environment: developer workstation or GitHub-hosted;
- parallelism: low to moderate;
- artifact retention: short;
- retry policy: minimal;
- evidence level: summary or structured;
- hardware usage: none by default;
- cloud usage: low;
- developer experience: fast, readable, local-first.

### Balanced

Purpose: normal development confidence.

Default posture:

- preferred execution environment: GitHub-hosted plus qualified self-hosted or
  lab targets when needed;
- parallelism: moderate and resource-aware;
- artifact retention: moderate;
- retry policy: limited and classified;
- evidence level: structured;
- hardware usage: only for explicitly required capabilities;
- cloud usage: bounded;
- developer experience: reproducible and reviewable.

### Release

Purpose: release or promotion confidence.

Default posture:

- preferred execution environment: release target plus qualified self-hosted,
  Docker and lab targets as required;
- parallelism: resource-aware with exclusive locks where needed;
- artifact retention: stronger and policy-defined;
- retry policy: explicit and evidence-preserving;
- evidence level: full required redacted evidence;
- hardware usage: allowed where release policy requires it;
- cloud usage: allowed when cost and provenance are acceptable;
- developer experience: slower but auditable.

The Planning Engine consumes these profiles. Workflow files must not invent
profile semantics.

Execution plans should declare a minimum Verification Runtime version,
required capabilities and optional capabilities. The selected runtime must be
the latest compatible stable runtime, validated through runtime metadata,
Docker image metadata and digest when Docker is used. A moving `latest` tag is
not sufficient compatibility evidence.

## Self-hosted Runner Architecture

Self-hosted runners are execution targets with explicit capabilities.

Architecture concerns:

- capabilities: Xcode, simulators, Docker, serial, SSH, signing access,
  hardware, local network, lab volumes;
- labels: stable capability labels that Planning can match;
- qualification: runner metadata, version, trust boundary, toolchain state and
  last known health;
- lifecycle: registration, qualification, use, dequalification and retirement;
- health: availability, flakiness, stale toolchain, disk, network and cleanup
  posture;
- scheduling: exclusive resources, maintenance windows, release priority and
  nightly windows;
- security boundaries: secrets, signing identities, local network access,
  artifact paths and cleanup obligations;
- concurrency: locks for devices, simulators, lab ports, signing resources and
  mutable release artifacts.

Installation details are intentionally out of scope.

## GitHub-hosted Runner Architecture

GitHub-hosted runners are appropriate for work that is:

- non-mutating;
- reproducible from checkout and public dependencies;
- safe without private lab state;
- not dependent on local hardware;
- not dependent on signing secrets unless a release policy explicitly provides
  them through a safe route.

GitHub-hosted runners may execute future Software Assurance work only after
policy and Planning Engine integration define what should run.

## Developer Workstation Architecture

Developer workstations provide fast feedback and local evidence. They are
useful for:

- validating schemas;
- previewing plans;
- reviewing repository metadata;
- running advisory checks;
- reproducing findings before pushing.

Developer evidence is not release authority unless a policy explicitly allows a
manual attestation or local lab result.

## Nightly Architecture

Nightly execution is the home for broad, slow, expensive or trend-oriented work.

Nightly is suitable for:

- dependency drift;
- repository drift;
- broad static quality;
- dynamic runtime assurance;
- runner health;
- health trends;
- slow cross-repository checks.

Nightly findings are advisory unless a policy promotes them.

## Release Architecture

Release execution produces evidence for release qualification.

Release execution may include:

- release-equivalent builds;
- artifact provenance;
- checksums;
- signing metadata;
- compatibility evidence references;
- release evidence bundles;
- rollback and promotion evidence.

Release execution must preserve source SHA, artifact identity, runtime version,
policy status and any waivers.

## Hybrid Execution

Hybrid execution splits a planned assurance run across targets.

Example:

```text
GitHub-hosted: schema, static metadata, report validation
Docker: Verification Runtime smoke and dry-run planning
Self-hosted: Apple or signing-aware evidence
Lab: Home Assistant or hardware evidence
Release: artifact validation and qualification summary
```

Hybrid execution must avoid duplicate evidence. Each evidence item has one
producer and may have many consumers.
