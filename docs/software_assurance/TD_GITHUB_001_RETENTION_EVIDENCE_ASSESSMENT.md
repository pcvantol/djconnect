# TD-GITHUB-001 — GitHub Actions Retention and Evidence Preservation Assessment

**Status:** Qualification complete
**Decision:** `GO_TD_GITHUB_001_QUALIFIED`
**Scope:** Existing GitHub Actions, Verification Platform, Software Assurance,
Trusted Delivery and Platform Release evidence contracts only. No workflow,
retention setting, GitHub configuration, Runtime, API, Renderer, release or
production-code change.

## Objective and repository evidence

This assessment classifies the current evidence required to reproduce a
qualification, release or governance decision. It does not define a new
retention policy or archive mechanism.

The existing `validate.yaml` cleanup job retains only the two latest completed
runs per workflow and deletes older completed workflow runs. GitHub Actions
artifacts and Job Summaries therefore cannot be the sole long-term source for
release, qualification or audit evidence. The Golden Qualification governance
already makes this distinction explicitly: its bounded report is developer
feedback, not a historical evidence store, and an optional downloadable copy
is limited to seven calendar days or the shorter workflow-run lifetime.

Conversely, the Release Runtime requires exact-main-SHA
`post_merge_release_evidence`, an immutable evidence digest and release
manifest identity; deployment smoke binds the candidate, manifest, artifact
checksum and workflow references. These are formal decision dependencies, not
optional CI output.

## Current evidence inventory and preservation class

| Evidence category | Current producer or contract | Preservation class | Canonical retention boundary |
| --- | --- | --- | --- |
| Release manifest, repository/version and compatibility matrices, certification, closure, rollback/recovery and published artifact identity/checksum | Platform Release Architecture and Release Evidence Contract | Permanent Evidence | Retain as immutable, redacted release records independently of Actions-run cleanup. Published release assets/tags remain channel evidence where the channel owns them. |
| Exact-main post-merge reconciliation record and immutable evidence digest | Post-Merge Release Evidence workflow/policy and Release Evidence Contract | Permanent Evidence | Retain the redacted structured record and its identity independently of the workflow artifact; it is required for fail-closed readiness. |
| Manifest-bound deployment and post-deployment smoke evidence | Deployment and smoke evidence contracts | Permanent Evidence | Retain the redacted target decision, manifest/artifact binding, result and recovery reference independently of Actions-run cleanup. |
| Release-bound Verification, Software Assurance and Trusted Delivery decisions; required governance/owner-authorization result | Verification Platform, Software Assurance and Trusted Delivery contracts | Long-term Retention | Retain the bounded decision, exact SHA/run identity, policy/version and applicable waiver or authorization reference. Raw logs and secrets are not part of this class. |
| Release-bound coverage qualification and provenance | Exact-SHA coverage artifact and post-merge policy | Long-term Retention | Retain the qualified state, source SHA and integrity/provenance reference needed by release readiness; the raw coverage file is not automatically permanent evidence. |
| Security, dependency, HACS, hassfest, test and lint outcomes | CI Qualification and Software Assurance producers | Long-term Retention when decision-bound; otherwise Short-term Retention | Preserve a redacted decision/reference when it supports a capability or release qualification. Routine run detail is not a permanent release record. |
| Golden Smoke/Regression bounded qualification report and advisory metrics | CI Qualification Report Governance | Short-term Retention | Job Summary follows its containing workflow run; any authorized downloadable projection is limited to seven days or the shorter run lifetime. It must never become a historical evidence store. |
| Routine pull-request test output, transient coverage XML, build intermediates and non-release artifact copies | CI workflows | Short-term Retention | Available only for review, rerun and immediate diagnosis unless separately selected as decision-bound evidence. |
| Job logs, runner workspaces, raw captures, diagnostics, temporary reports, raw audio, credentials, tokens, provider payloads and personal data | Workflow cleanup and redaction contracts | Ephemeral | Must be cleaned after use or retained only under their existing restricted operational boundary; they must never enter the qualification or release archive. |

## Qualification and audit dependency

A later reviewer can objectively establish a qualified capability only from its
bounded decision, exact source identity, applicable validation/assurance
references and immutable Prompt/Finalization records. A release additionally
requires the mandatory Release Manifest, version and compatibility matrices,
exact-main reconciliation record/digest, qualified evidence inputs, artifact
provenance/integrity, target deployment and smoke evidence, recovery posture,
and certification/closure records.

GitHub Actions run IDs, logs and short-lived artifacts may support immediate
inspection, but cannot substitute for those durable identities and decisions.
Likewise, a retained release record must remain redacted: it must not preserve
credentials, raw logs, user data, Runtime/Planner/Knowledge internals, raw
audio or prohibited Golden Qualification capture data.

## GitHub Actions constraint

The currently observed two-run cleanup and the seven-day Golden report rule
are compatible with ephemeral and short-term evidence only. They are not an
independent durable archive. Existing repository-tracked release, governance,
Prompt History and qualification records provide some durable decision
evidence, but the repository does not yet prove a complete configured path
that preserves every decision-bound Actions record independently of workflow
retention.

## Qualification completion evidence

The bounded implementation publishes one redacted, immutable record to the
existing exact-main internal release. For main
`f6e346018dadaccc8457dac7b5cadd19a03b80e7`, the release asset
`qualification-evidence-f6e346018dadaccc8457dac7b5cadd19a03b80e7.json` was
published, downloaded and validated with no findings. The record outcome is
`POST_MERGE_RELEASE_EVIDENCE_QUALIFIED`, its redaction status is `REDACTED`,
and publication fails closed before qualified status on invalid source,
collision, upload or read-back validation failure.

## Conclusion

`GO_TD_GITHUB_001_QUALIFIED`

The canonical evidence classes and decision dependencies are explicit, and the
configured publication path now provides the required durable, redacted
decision record independently of Actions cleanup. This does not alter the
existing native SHA-pinning compatibility exception.
