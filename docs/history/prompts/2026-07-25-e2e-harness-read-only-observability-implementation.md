# Prompt History: E2E Harness Read-only Observability Implementation

Implement the separately authorized E2E-only Read-only Developer Overlay
Harness Implementation after the Delivery Guard decision
`GO_E2E_HARNESS_ONLY`.

The implementation is limited to process-local composition in the existing
Universal Receiver Browser E2E harness. The Universal Receiver HTML, CSS,
JavaScript, renderer lifecycle, Broadcast contract, Runtime, Planner, Session
Flow, release artifacts and HACS content remain unchanged. The panel exists
only during a Browser E2E run, retains no artifact and has no qualification
authority.

Its allowlist is restricted to renderer-safe Session identity/state/mood,
Planner summary, current Moment identity/type, Flow revision/count, Broadcast
watermark/started-at metadata and local WebSocket lifecycle. It excludes Start
Strategy, Persona, capability policy/registry, renderer identity or
capabilities, profile data, credentials, provider payloads and all mutation
paths.

Required evidence: harness presence and release/Receiver absence, read-only
allowlist behavior, preserved Browser E2E and Receiver behavior, governance
validation, immutable Prompt History and HACS validation. The single recorded
implementation decision is `E2E_HARNESS_OBSERVABILITY_IMPLEMENTED`.
