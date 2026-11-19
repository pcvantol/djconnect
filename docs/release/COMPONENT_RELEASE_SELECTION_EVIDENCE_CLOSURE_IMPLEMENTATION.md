# Component Release Selection and Evidence Closure Implementation

**Status:** Implemented pending review and Finalization
**Decision:** `GO_COMPONENT_RELEASE_SELECTION_EVIDENCE_CLOSURE_IMPLEMENTED`
**Scope:** Existing Platform Release Runtime only; no release execution.

## Outcome

The Platform Release Runtime now accepts an optional immutable component
selection record and deterministically resolves exactly one registered profile:
HACS, API, website, ESP32, iOS/watchOS, macOS, Windows or the shared Raspberry
Pi renderer family. Pi 4-inch and Pi 10-inch are registered explicitly but
fail closed because neither has an independent release artifact or manifest.

When a component record is present, only its canonical source and
closure-required distribution participants are included in readiness, planning
and artifact inventory. All other repositories are recorded as non-selected.
The legacy platform-wide path is unchanged when no component record is given.

## Immutable selection and closure

The runtime rejects a selection unless it binds one registered profile to the
exact source repository, owner, platform train, source SHA, version, artifact
identity/checksum, manifest identity/checksum, channel, target and complete
participant set. It also requires nine `PASS` evidence records, each bound to
the same component ID, source SHA, artifact, manifest and version:

1. source qualification;
2. build and test;
3. Software Assurance;
4. Trusted Delivery;
5. artifact provenance;
6. manifest validation;
7. channel validation;
8. durable post-merge evidence; and
9. explicit owner authorization.

Missing, malformed or mismatched identity, evidence, checksum, participant or
profile data yields `NOT_READY` or `BLOCKED`. The Runtime neither substitutes a
platform-wide scope nor adds a cross-component dependency.

## Execution boundary

This implementation is qualification-only. A manifest containing component
selection rejects operational dispatch, even when its simulated readiness is
`READY`. The existing execution route remains unchanged for the existing
platform scope; component execute qualification remains a separate bounded
increment and no artifact, manifest, tag, publication, deployment or version
is created here.

## Validation

Focused release-runtime tests prove a ready macOS component selection, the
inclusion of only source plus release-handoff participants, rejection of
checksum/evidence identity drift, rejection of non-selectable Pi profiles and
the preserved execute boundary. Existing generic platform simulation tests
continue to cover the no-component path.
