# Platform Release Evidence Contract

For every mandatory participating repository, the Release Runtime requires a
schema-version `1` `post_merge_release_evidence` record whose `repository` and
`main_sha` equal the release-manifest repository and SHA. Its decision must be
`POST_MERGE_RELEASE_EVIDENCE_QUALIFIED` and its immutable evidence digest must
be present. PR-only evidence, a different SHA, a stale record, or an omitted
record makes readiness fail closed.

The record is produced only after the required successful `main` CI through an
evidence-safe event such as `workflow_run`. It is distinct from CI candidate
qualification and from deployment evidence. No deployment workflow may create,
replace or qualify this record.

## Post-deployment smoke evidence

After a successful authorized deployment, each manifest-allowlisted target
requires a schema-version `1` post-deployment smoke evidence record. It binds
the exact candidate SHA, platform version, manifest, artifact checksum,
deployment-workflow run and smoke-workflow run. For required targets, missing,
stale, inconsistent, `SMOKE_FAIL` or `SMOKE_INCONCLUSIVE` evidence makes the
deployment decision `DEPLOYMENT_SMOKE_FAILED`. A record is redacted, immutable
deployment evidence and cannot create, replace or qualify CI, Verification,
coverage, assurance or qualification evidence. See
[Post-Deployment Smoke Evidence Schema](POST_DEPLOYMENT_SMOKE_EVIDENCE_SCHEMA.md).
