# Prompt History: TD-GITHUB-001 Retention and Evidence Preservation Assessment

**Generation and engineering program:** Generation 2, Phase 1 — DJ Intelligence
Evolution / Platform Evolution  
**Engineering mode:** Platform Architect capability assessment  
**Branch:** `codex/assess-github-evidence-retention`  
**Decision:** `GO_TD_GITHUB_001_PARTIALLY_QUALIFIED`  
**Execution date:** 2026-07-27  
**Scope:** Existing Actions, Verification Platform, Software Assurance, Trusted
Delivery and Platform Release evidence contracts only. No Runtime, API,
Renderer, workflow, Actions configuration, retention setting, archive, export,
release or production-code change.

## Archived prompt

Classify the existing GitHub Actions verification and release output as
Permanent Evidence, Long-term Retention, Short-term Retention or Ephemeral.
Determine what must remain available to reproduce capability qualification,
release authorization and governance history; distinguish GitHub Actions
retention from independently durable canonical records. Do not design or
implement retention configuration.

## Evidence and result

- `validate.yaml` retains only the two newest completed runs per workflow, so
  Actions artifacts and Job Summaries cannot alone be the durable evidence
  source.
- Golden Qualification reports are bounded developer feedback; optional
  downloadable reports have a seven-day or shorter run-bound lifetime and may
  not become historical evidence stores.
- Exact-main post-merge reconciliation, manifests, artifact identity/checksum,
  deployment/smoke records, recovery posture and release certification require
  durable redacted identities and decisions independent of Actions cleanup.
- Routine logs, raw captures, temporary reports and sensitive data remain
  ephemeral and prohibited from a qualification/release archive.

The assessment retains one Future Assessment: **Evidence Preservation
Qualification** must prove that every decision-bound Permanent or Long-term
item has an immutable, redacted, independently durable record and fails closed
when preservation is missing. No retention or archive implementation is
authorized.

## Validation and limitation

Repository synchronization, predecessor PR #542 merge/containment, Prompt
History and current development-host readiness were verified before mutation.
The assessment is documentation-only and leaves the Product Phase, supporting
engineering increment and Execution Horizon unchanged.

## Recommended next prompt

Finalize the merged TD-GITHUB-001 assessment, then resume the canonical
Execution Horizon from the current Platform Evolution backlog.
