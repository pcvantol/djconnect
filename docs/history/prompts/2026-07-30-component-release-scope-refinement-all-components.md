# Component Release Scope Refinement — All Components

**Prompt ID:** `COMPONENT-RELEASE-SCOPE-ALL-001`
**Engineering mode:** Platform Engineering — architecture and documentation refinement
**Branch:** `codex/refine-component-release-scopes`
**Decision:** `GO_COMPONENT_RELEASE_SCOPE_REFINEMENT_PARTIALLY_QUALIFIED`

## Objective

Define one reusable, fail-closed Component Release Scope Contract for every
currently identified DJConnect release component. Record a deterministic
component identity, participant/dependency closure, evidence closure and
dry-run/execute boundary without changing Runtime, workflows, artifacts,
channels or product behavior.

## Requested components

- Home Assistant/HACS integration;
- central API;
- website;
- Raspberry Pi 4-inch and 10-inch;
- ESP32 firmware;
- iOS plus watchOS, separately from macOS; and
- Windows.

## Repository-grounded result

The current Apple source/release evidence supports separate `apple-ios-watchos`
and `apple-macos` profiles: the Watch is part of the existing iOS artifact
path. The current Pi source/release evidence supports only the shared
`pi-renderer-family` profile. Pi 4-inch and Pi 10-inch cannot truthfully be
declared independently selectable until separate artifact, manifest, checksum,
target and recovery evidence exists.

The refinement records all applicable profiles, but does not authorize a
component release. The existing Runtime accepts only a supplied scope and the
current execution dispatchers remain dry-run only. The only recommended next
step is to implement deterministic selection and exact evidence closure within
the existing Platform Release Runtime.

## Boundaries preserved

- no Runtime, manifest-schema, workflow, artifact, release, tag, publication,
  deployment or rollback change;
- no product, API, Renderer, firmware or website behavior change;
- no new release engine or versioning model;
- no synthetic patch or operational proof.
