# Session For you source qualification — 5 November 2026

Scope: owner-selected [For-you replacement](../product/SESSION_FOR_YOU_V1.md),
on the separate `codex/session-for-you-20261105` branch. Visible title **Voor jou**.
No dependency change, paid execution, operator enrollment or device installation.

## Evidence

- Sixteen new owner-lifecycle/privacy/visual-recipe tests; existing30 first-play
  lifecycle/effect tests also pass in process isolation.
- Eleven new real paired HTTP scenarios,54 requests through HA2026.10.0,
  real SQLite and HA Store; synthetic Spotify response boundary and declared
  authored narrator fallback. Native/local-model/real-provider acceptance NOT_RUN.
- The new [original receipt](../../examples/client_contracts/session_for_you_v1/actual-ha-wire.json)
  includes exact hashes of all306 tracked component artifacts plus the actual
  producer inputs/harness. [Dutch Session start](../../examples/client_contracts/session_for_you_v1/session-start.nl.json)
  is extracted from the actual receipt, not manually invented.
- Twenty-three existing isolated HA producer groups rerun against the same
  unchanged product source; their current receipts are replaced with new actual
  outputs. The obsolete first-play v1/v2 harness and original receipts remain
  byte-for-byte historical; no hash-only rebinding or relabelled historical pass.
- Cases include all five titles, genuine-start preparation, stable no-provider
  polling, Watch exclusion, direct known-output selection, genre then speaker then
  the same mix, authenticated dismissal, stale-old-Session refresh rejection and
  explicit same-card refresh without effects.
- Unit cases additionally cover playing/nonempty queue replacement only on
  deliberate selection; lost/late acknowledgement without a second play;
  client-scoped dismissal including a held durable reservation; privacy/DNA
  revocation removing cached grants; settings changes disabling old choices;
  confirmed-only compact dedupe/clear and operation-ID exclusion from generic
  model memory; narrator generation plus independent rejection/fallback.

All containers use network:none, read-only candidate source and separate empty
external temporary configurations. No HA-dev volume, production identity,
actual provider, real local model or paid transport is used. Artwork's existing
browser case remains explicitly NOT_RUN_ISOLATED_CONTAINER. The source stayed
unchanged inside each qualification and across the complete run.

Full host repository suite:4556 tests,11 existing skips, zero failures/errors,
using the existing four-worker process-isolated runner with exact
requirements-dev dependencies staged in a separate temporary directory.
Ruff on changed Python and `git diff --check` pass. The planning snapshot's
current document references/rendered source view and the capability/avatar
semantic derivatives were regenerated through their real producers; frozen
historical receipts and planning acceptance states remain unchanged.

## Delivery boundary

Protected CI and whole/exact source review remain separate from these local
proofs. This source candidate is not a merged/released/installed acceptance
claim. Normal separate Finalization and actual qualified HA-dev/native gates
remain. Apple owns screen layout, three distinct stable local landscapes,
Foundation Models/SceneSpec validation and honest procedural fallback; its
reported app regressions take priority before separate adoption. This feature
adds no Watch card or APNs claim. The previous timer stays stopped.
