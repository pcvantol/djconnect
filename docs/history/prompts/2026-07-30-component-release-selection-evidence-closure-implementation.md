# Component Release Selection and Evidence Closure Implementation

**Prompt ID:** `COMPONENT-RELEASE-SELECTION-EVIDENCE-001`
**Engineering mode:** Platform Engineering — bounded Runtime implementation
**Branch:** `codex/implement-component-release-selection-closure`

## Objective

Extend the existing Platform Release Runtime so it deterministically selects
the registered Component Release profiles and binds source SHA, artifact,
manifest and closure evidence fail closed. Preserve the existing platform-wide
simulation path and do not enable component execution, publication or release.

## Repository-grounded scope

The preceding Scope Refinement establishes HACS, API, website, ESP32,
iOS/watchOS, macOS, Windows and the shared Pi renderer family as selectable
release profiles. Pi 4-inch and Pi 10-inch are explicit non-selectable product
profiles until independent artifact and target evidence exists.

## Required outcome

- exactly one registered profile is selected from an immutable record;
- only its source and closure-required distribution participants enter the
  component plan;
- source SHA, version, artifact identity/checksum, manifest
  identity/checksum, channel, target and evidence are mutually bound;
- missing, mismatched or cross-component information fails closed;
- component selection cannot dispatch execute actions; and
- existing whole-platform simulation remains unchanged without a component
  record.

## Boundaries preserved

- no product, Runtime, API, Renderer, firmware or website behavior changes;
- no workflow, execution-route, release-channel, artifact, manifest,
  publication, deployment, rollback or version changes;
- no synthetic patch or operational release proof; and
- Component Release Execute Qualification remains a later, separate increment.
