# Deployment Consumer Implementation Template

Status: implementation template for the frozen Platform Release architecture.

Each repository-specific deployment consumer uses three separately scoped
GitHub Actions workflows:

1. **Artifact producer** — triggered after successful exact-main CI, produces
   one immutable artifact and its SHA-256 evidence. It has no deployment
   credentials and does not mutate a target.
2. **Deployment consumer** — `workflow_dispatch` only; validates every field
   in `DEPLOYMENT_INPUT_CONTRACT.md`, verifies the artifact provenance and
   checksum, performs one allowlisted target mutation, then uploads redacted
   deployment evidence with `DEPLOYED_PENDING_SMOKE`.
3. **Post-deployment smoke consumer** — separate `workflow_dispatch`; accepts
   the same identity plus the deployment run, validates deployment evidence,
   performs only bounded read-only checks and publishes one `SMOKE_*` record.

The template is fail-closed. CI, artifact generation, deployment and smoke
must never share credentials or claim each other’s qualification result.

## Required deployment inputs

`action`, `candidate_sha`, `execution_mode`, `manifest_id`, `artifact_id`,
`artifact_sha256`, `target`, `platform_version` and `release_profile` are
mandatory. A consumer may add only documented, schema-bound, target-specific
inputs such as `deployment_workflow_run` for smoke evidence.

## Qualification checklist

- static workflow validation and pinned-action validation pass;
- invalid input/provenance/checksum paths fail before credentials or mutation;
- a non-production artifact workflow run produces redacted evidence;
- deployment and smoke are qualified through an explicitly authorized,
  manifest-bound operational run; and
- the canonical release inventory and backlog are updated with the outcome.

## Website reference implementation

`pcvantol/djconnect-website` implements this template through
`website-release-artifact.yml`, `deploy-pages.yml` and
`website-post-deployment-smoke.yml`. Its operational qualification remains
blocked until a current approved manifest, artifact evidence and explicit
deployment authorization exist.
