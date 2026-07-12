# Verification Runtime Compatibility

Status: Canonical  
Runtime product: Verification Runtime  
Related: `tools/verification/RUNTIME_CAPABILITIES.md`,
`tools/verification/RUNTIME_METADATA.md`

## Purpose

Compatibility is capability-driven.

Repositories should no longer request only a runtime version. A repository
declares the minimum runtime version it can use, the capabilities it requires
and the capabilities it can use opportunistically. Runtime bootstrap then
resolves the latest compatible runtime, not merely the latest runtime.

## Consumer Declaration

Runtime consumers declare:

```yaml
verification_runtime:
  minimum_version: "1.0.0"
  required_capabilities:
    - planner
    - execution
    - evidence
    - qualification
    - reporting
  optional_capabilities:
    - investigator
    - coverage
```

Required capabilities are hard gates. Optional capabilities may improve output
or enable richer workflows, but their absence must not make an otherwise
supported run incompatible.

## Compatibility Inputs

The deterministic compatibility decision uses only:

- minimum runtime version;
- required capabilities;
- optional capabilities;
- runtime metadata;
- supported runtime capabilities;
- Docker image metadata and integrity metadata when Docker is the distribution
  mechanism.

## Compatibility Outputs

| Output | Meaning |
| --- | --- |
| `compatible` | Runtime version and all required capabilities satisfy the consumer declaration. |
| `compatible_with_warning` | Runtime can run the required workflow, but optional capabilities, image metadata or non-blocking release signals are missing or older than preferred. |
| `not_compatible` | Runtime cannot safely run the requested workflow. |
| `missing_capability` | One or more required capabilities are not present in runtime metadata. |
| `unsupported_runtime` | Runtime version, metadata schema, product identity, release channel or Docker image integrity is unsupported. |

`missing_capability` and `unsupported_runtime` are specific forms of
`not_compatible`.

## Selection Algorithm

Runtime selection follows this order:

1. Read available runtime metadata.
2. Reject metadata that is malformed or has an unsupported schema.
3. Reject runtimes whose product identity is not `Verification Runtime`.
4. Reject runtimes below the declared minimum version.
5. Reject runtimes missing required capabilities.
6. Validate Docker image metadata, digest and release channel when Docker is
   used.
7. Prefer the highest stable runtime version that remains compatible.
8. Return `compatible_with_warning` when only optional capabilities or
   non-blocking metadata are missing.

Bootstrap must not assume that the `latest` Docker tag is compatible.

## Determinism

Compatibility decisions must be deterministic. The same consumer declaration
and same runtime metadata must produce the same result regardless of host,
operator, branch or local checkout state.

Network discovery may find candidate images or metadata, but it must not alter
the compatibility rules.

## Breaking Changes

Within a major runtime version:

- capability identifiers remain stable;
- existing metadata fields remain readable;
- existing report and evidence contracts remain backward compatible;
- new optional fields may be added.

Breaking changes require either:

- a new major runtime version; or
- a new capability identifier that consumers can opt into explicitly.

## Repository Guidance

Repositories should depend on:

- capabilities;
- compatibility decisions;
- runtime metadata;
- evidence contracts;
- qualification/reporting contracts.

Repositories should not depend on:

- internal Python module paths;
- local command implementation details;
- Dockerfile internals;
- temporary branch state;
- unversioned behavior behind a moving `latest` tag.
