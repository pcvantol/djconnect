# Run Qualification Evidence Contract

## Canonical run evidence

Before provider-backed work, the Execution Host persists one immutable
submission-lineage record keyed by `run_id`. It records `submission_id`,
producer submission identity, `fresh_submission`, `retry_parent_run_id` and
`resume_parent_run_id`. A fresh submission has `true`, `null`, `null`;
retry and resume records are non-fresh and cannot carry dual parents.

Validation persists the selected tier, profile version and exact required
control identities. Each control has a stable ID, category, execution status,
result, timestamp and evidence reference. Required Validation State is `PASS`
only when every required control has current `PASS` evidence; missing evidence
is `UNRESOLVED`, and a required failure is `FAIL`.

Legacy runs without these records remain `EVIDENCE_INSUFFICIENT`; projections
must not infer evidence from a merge, prompt text, or aggregate platform state.

## Evidence audit matrix

| Evidence | Status | Qualification use |
| --- | --- | --- |
| Submission lineage | Canonically persisted | Mandatory for fresh qualification |
| Validation profile and controls | Canonically persisted | Mandatory for fresh qualification |
| Telemetry uniqueness / daily aggregation | Canonically persisted | Operational; not an additional run gate |
| Commit timeline | Derived but sufficient | Delivery evidence gate |
| Codex / GitHub / host readiness | Canonically persisted | Existing Managed evidence gates |
| Capacity-reserve admission | Canonically persisted | Admission gate; not a replacement for validation |

## Schema activation

Schema 33 is delivered but is not activated by this increment. Existing shared
stores require the controlled post-merge storage activation command after
persistent components have stopped.
