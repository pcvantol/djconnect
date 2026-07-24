# CI Qualification Report Governance

**Status:** Canonical governance for future Golden Qualification CI reporting
**Scope:** Publication governance only; no workflow, qualification or product
implementation is authorized by this document.

## Purpose

This document is the single authority for publication of Golden Qualification
results from repository Continuous Integration. It governs the publication
model, artifact model, permitted report content, access, retention, cleanup and
future promotion of CI qualification execution.

It does not change Golden Scenario behavior, Golden Qualification semantics,
the Runtime, the Scenario Driver, Capture, Structural Validation, Advisory
Metrics or CI implementation.

## Architectural authority

The [Golden Qualification Foundation](../verification/GOLDEN_QUALIFICATION_FOUNDATION.md)
remains the sole qualification execution path. The Structural Validator remains
the sole authority for scenario and overall PASS / FAIL. A CI report is a
read-only projection of the immutable bounded `GoldenQualificationReport`; it
is not a new evidence model, validation layer, diagnostic dump, Runtime capture,
replay artifact or evidence store.

Advisory Intelligence Quality Metrics v1 remains advisory. Its presence in a
published report cannot alter qualification execution, PASS / FAIL, workflow
classification, merge eligibility or release eligibility.

## Artifact classification

Golden Qualification reports are **redacted verification evidence**. They are
bounded projections for developer feedback, not retained platform evidence.

They must never be classified or used as:

- diagnostic dumps;
- Runtime, Planner, Knowledge or renderer captures;
- replay or snapshot artifacts;
- baseline or historical evidence stores; or
- release assets.

## Publication model

The default publication form is a Markdown GitHub Actions Job Summary. It is
the canonical human-readable view of one CI qualification invocation.

A future downloadable artifact is optional. When authorized by a workflow, it
must contain exactly the same bounded report projection as the Job Summary.
It may use a machine-readable representation of that same projection, but may
not add diagnostics, captures, logs, traces, object serializations or any other
information.

No report may be published until it passes the allowlist and redaction checks
in this document.

## Permitted report contents

The report schema is allowlist-only. Its only permitted information is:

- `profile`;
- `profile_version` when present in the existing Qualification Report;
- ordered scenario outcomes, limited to scenario identifier, Session
  Verification status, applicable Presentation Verification status,
  determinism status and overall scenario status;
- overall PASS / FAIL status;
- applicable Presentation Verification summary;
- invariant failure identifiers; and
- Advisory Intelligence Quality Metrics v1 as already defined by the existing
  bounded report projection.

The report may include fixed schema or report-format version identifiers needed
to interpret this allowlist. It may not introduce a second qualification result,
score, threshold, recommendation, trend or historical comparison.

The following are explicitly prohibited in every publication form:

- prompts, Moment text or raw captured evidence;
- Runtime objects or state;
- Planner or Knowledge internals;
- provider state or provider payloads;
- credentials, tokens, authorization material or secrets;
- session memory, Music DNA or user/profile data;
- renderer state, renderer configuration or browser data;
- raw audio; and
- internal diagnostics, logs, traces or serialized implementation objects.

## Mandatory redaction validation

Every future CI implementation must validate the report projection against the
allowlist before writing a Job Summary or artifact. Publication must fail
closed when a prohibited field, an unknown nested field or an invalid schema
version is detected.

The validation is a publication-safety control only. It must not reinterpret
or change Foundation execution, Structural Validator output, scenario status or
the authoritative PASS / FAIL result.

## Access model

Reports may exist only within this repository's GitHub Actions context. They
are not release deliverables and may not be published through:

- release assets;
- public or externally shared URLs;
- external storage or telemetry systems; or
- cross-repository publication, synchronization or aggregation.

Job Summaries and optional downloadable artifacts inherit the repository's
Actions access controls. A workflow must not widen that access, attach a public
link or transfer report content outside the repository Actions context.

## Retention policy

Job Summaries follow the retention of their containing GitHub Actions workflow
run. They are not separately archived.

If a downloadable artifact is authorized, its retention is **seven calendar
days** from upload. It must be deleted with its workflow run when the existing
workflow-run cleanup policy removes that run, even if seven days have not
elapsed. The shorter applicable lifetime wins.

No workflow may rely on a platform default retention period, extend retention
for Golden Qualification reports, preserve a report after workflow cleanup or
copy it into a historical store.

## Cleanup requirements

The existing Foundation cleanup remains mandatory after both PASS and FAIL.
Future CI workflows must also remove temporary report files after the Job
Summary and any authorized artifact have been emitted. A failed qualification,
failed publication validation or failed artifact upload does not excuse
Foundation or temporary-file cleanup.

Cleanup evidence may state only that cleanup completed or failed. It may not
publish the prohibited data categories listed above.

## Initial workflow classification

The first CI rollout is explicitly:

- advisory;
- non-blocking; and
- non-required.

It must not modify merge protection, required checks, branch protection,
release qualification or release gates. A workflow may display the Structural
Validator's PASS / FAIL result, but the workflow classification remains
advisory until separately promoted.

The intended profile placement remains the existing qualification policy:
Golden Smoke for routine pull-request feedback and Golden Regression for
broader `main`, scheduled or manually invoked qualification. This governance
document does not itself authorize a workflow trigger or implementation.

## Future promotion

Any change from advisory to required execution, including a required check,
merge protection or release-gate use, requires a separate Platform Evolution
governance decision. That decision must specify the affected profile, trigger,
failure handling, access and retention effects, and prove that it does not
change qualification semantics.

No promotion may make Advisory Metrics authoritative. The Structural Validator
remains the sole PASS / FAIL authority, and the Foundation remains the sole
qualification path.

## Implementation entry criteria

Product Development may implement Full CI Qualification and Readable Reports
only when it reuses the existing Foundation, profiles, Structural Validator,
bounded report and Advisory Metrics projection exactly as defined by their
current contracts. The implementation must demonstrate deterministic bounded
publication, allowlist validation, cleanup on PASS and FAIL, and the advisory
workflow classification in this document.

## References

- [Session Intelligence Qualification Policy](../verification/SESSION_INTELLIGENCE_QUALIFICATION_POLICY.md)
- [Golden Qualification Foundation](../verification/GOLDEN_QUALIFICATION_FOUNDATION.md)
- [Golden Scenario Governance](../verification/GOLDEN_SCENARIO_GOVERNANCE.md)
- [Automated Session Intelligence E2E Verification Architecture](../verification/SESSION_INTELLIGENCE_E2E_ARCHITECTURE.md)
- [Developer Experience Roadmap](../product/DEVELOPER_EXPERIENCE_ROADMAP.md)
