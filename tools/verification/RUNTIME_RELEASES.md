# Verification Runtime Releases

Status: Canonical release model  
Runtime product: Verification Runtime  
Release notes: `tools/verification/RELEASE_NOTES.md`

## Purpose

Verification Runtime releases are independent from DJConnect platform
releases. The runtime is an engineering product distributed through Docker Hub
and consumed by local labs, CI workflows, future Software Assurance workflows
and repository bootstrap tooling.

## Release Separation

Keep these release streams separate:

| Stream | Owns |
| --- | --- |
| DJConnect Platform Releases | Product functionality, Home Assistant integration, client contracts, firmware compatibility and user-facing release notes. |
| Verification Runtime Releases | Runtime capabilities, metadata, evidence/report contracts, planning/execution behavior, Docker packaging and runtime qualification. |
| Platform Qualification | Evidence that DJConnect behaves as designed across approved scenarios and runtimes. |
| Software Assurance | Policy, governance, quality signals and future trusted delivery workflows. |
| Knowledge Base | Durable engineering guidance, reports, backlogs and completion records. |

## Distribution Channel

The canonical Docker distribution is:

```text
pcvantol/djconnect-verification-platform
```

Do not introduce another Docker Hub repository for the Verification Runtime.
Do not rename the existing distribution repository. The product name is
Verification Runtime; the Docker repository is the distribution mechanism.

## Release Policy

Runtime releases use Semantic Versioning:

- patch releases fix runtime defects without changing public capability
  contracts;
- minor releases add backward-compatible capabilities, metadata or report
  fields;
- major releases introduce breaking capability, metadata, evidence or report
  contract changes.

Changed runtime behavior that Docker consumers rely on must be published
through the Docker release workflow before those consumers treat it as stable.
Local builds remain development artifacts.

## Bootstrap Expectations

Runtime bootstrap should validate:

- runtime version;
- runtime metadata;
- required capabilities;
- optional capability warnings;
- Docker repository;
- Docker image digest;
- stable release channel;
- image labels and release SHA;
- compatibility decision.

Bootstrap must resolve the latest compatible runtime, not blindly download
`latest`.

## Runtime 1.1.0 Position

Runtime `1.1.0` adds the `coverage` capability. It ingests native repository
coverage reports, validates provenance, normalizes coverage metrics, writes
coverage evidence, qualifies coverage state, produces coverage reports and
adds coverage-specific investigator classifications.

Runtime `1.1.0` does not generate coverage. Repositories remain responsible for
native coverage production.

Coverage Baseline 1 was established as the first Runtime `1.1.0`
cross-platform coverage measurement. The baseline uses the Docker Hub image
`pcvantol/djconnect-verification-platform:1.1.0` with digest
`sha256:3f0b8d3ba5f07afa5c8f05cd305dd92c43806e0fed24395be96d832e7ef72619`.
The baseline decision is `CROSS_PLATFORM_COVERAGE_BASELINE_PARTIAL` because
Raspberry Pi coverage could not be reliably produced in the available Python
environment. Home Assistant and Apple Runtime coverage ingests returned
`COVERAGE_VALID`.

Docker tags for the stable release are:

```text
1.1.0
1.1
latest
```

Only stable releases may update `latest`.

## Runtime 1.0.0 Position

Runtime `1.0.0` positions the Verification Runtime as a first-class
engineering product and establishes stable runtime identity, Docker
distribution, planning, execution, evidence, investigator, qualification and
reporting capabilities.
