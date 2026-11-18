# Verification Runtime Metadata

Status: Canonical  
Runtime product: Verification Runtime  
Docker distribution: `ghcr.io/djconnect-music-dj/djconnect-verification-platform`

## Purpose

Runtime metadata is the Verification Runtime contract. It identifies the
product, version, source repository, Docker distribution and supported
capabilities that a consumer can negotiate against.

Runtime metadata is recorded in environment snapshots, run metadata and
reports under `verification_runtime`. Docker images must also expose enough
image metadata for bootstrap to verify identity, version and integrity.

## Canonical Metadata Shape

```yaml
runtime:
  product: Verification Runtime
  version: 1.1.0
  schema_version: 1
  repository: djconnect-music-dj/djconnect
  docker_repository: ghcr.io/djconnect-music-dj/djconnect-verification-platform
  release_cycle: independent
  versioning: semver
  compatibility: capability-driven
  architecture: frozen
  capabilities:
    - planner
    - execution
    - evidence
    - investigator
    - qualification
    - reporting
    - coverage
```

The current implementation also emits compact legacy runtime identity fields
under `verification_runtime`. Future metadata expansion must remain
backward-readable for Runtime `1.x` consumers.

## Required Fields

| Field | Requirement |
| --- | --- |
| `product` | Must be `Verification Runtime`. |
| `version` | Runtime semantic version. |
| `schema_version` | Metadata schema version. |
| `repository` | Current source reports `djconnect-music-dj/djconnect`; preserved 1.1.0 reports its historical value. |
| `docker_repository` | Current source reports `ghcr.io/djconnect-music-dj/djconnect-verification-platform`; preserved 1.1.0 reports its historical value. |
| `capabilities` | Stable list of supported capability identifiers. |

## Docker Image Metadata

The current consumer distribution is:

```text
ghcr.io/djconnect-music-dj/djconnect-verification-platform
```

The Docker repository is the distribution mechanism. It must not be renamed or
split for this runtime.

Docker image validation should inspect:

- image repository;
- tag;
- digest;
- runtime version label;
- release SHA label;
- build date label;
- license label;
- stable release status.

A local image build is a development artifact. Published Docker Hub images are
the canonical distribution for Docker-based consumers.

## Metadata Lifecycle

Metadata changes follow these rules:

- Additive fields are allowed in minor releases.
- Field removals require a major runtime version.
- Capability additions require a minor release when the capability is stable.
- Capability behavior changes follow each capability's breaking change policy.
- Metadata must not contain secrets, raw prompts, raw audio, tokens or private
  run evidence.

## Consumer Contract

Consumers may use runtime metadata to:

- resolve the latest compatible runtime;
- verify minimum version;
- validate required and optional capabilities;
- verify Docker image identity and digest;
- decide whether a run is compatible, warning-only or blocked.

Consumers must not use runtime metadata as a substitute for scenario evidence
or platform qualification results.

## Runtime 1.1.0 Metadata

Runtime `1.1.0` adds the stable `coverage` capability. Consumers that require
coverage ingestion should declare:

```yaml
verification_runtime:
  minimum_version: "1.1.0"
  required_capabilities:
    - coverage
```

The runtime metadata advertises capabilities automatically through
`tools.verification.runtime.runtime_metadata()`.

The existing byte-identical 1.1.0 image preserves its historical personal-namespace embedded metadata. These organization values describe current source metadata; they do not rewrite that historical image or its digest.
