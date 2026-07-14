# Platform Workflow Separation Architecture

Status: `IMPLEMENTING`  
Decision: a merge to `main` qualifies software; it never deploys software.

DJConnect uses exactly three workflow classes:

```text
CI / Qualification (PR and main)
  -> Artifact / Release Evidence (after successful exact-main-SHA CI)
    -> Deployment (explicit qualified workflow_dispatch only)
```

GitHub Actions is the exclusive execution engine. The Platform Release Runtime
only dispatches bounded workflows, monitors them and reads their evidence; it
does not build, publish, tag, release or deploy directly.

## Separation invariants

1. CI / Qualification has no deployment credentials and cannot mutate an
   external target.
2. Artifact / Release Evidence consumes completed CI evidence only. It may
   publish GitHub evidence/status records, but never product artifacts.
3. Deployment has `workflow_dispatch` as its sole trigger, validates the
   qualified exact main SHA and is the only class allowed target credentials.
4. A workflow that both validates/builds and deploys/publishes is a mixed
   responsibility and must be split into an artifact/evidence producer and a
   deployment consumer.
5. Qualification, readiness and deployment use distinct status contexts.

## Canonical status contexts

| Class | Canonical context | Meaning |
|---|---|---|
| CI / Qualification | `CI Qualification / Qualify candidate` | Candidate technical and governance result. |
| Artifact / Release Evidence | `Release Evidence / Reconcile exact main SHA` | Exact main SHA is `READY` or `NOT_READY`. |
| Deployment | `Deployment / Execute approved release` | Explicit deployment result; it never changes qualification. |

The existing post-merge context remains the migration-compatible implementation
of the Release Evidence context until consumer naming is upgraded together.

## Credential boundary

CI has no Cloudflare, Docker Hub, App Store, GitHub Release or publication
token. Evidence workflows have only read access plus the minimal GitHub status
and artifact permissions needed to record immutable evidence. Deployment jobs
receive target credentials only in the job that mutates that target; they are
unavailable to PR and evidence jobs.

See [CI Qualification Workflow Policy](CI_QUALIFICATION_WORKFLOW_POLICY.md),
[Artifact / Release Evidence Policy](ARTIFACT_RELEASE_EVIDENCE_POLICY.md),
[Deployment Workflow Policy](DEPLOYMENT_WORKFLOW_POLICY.md) and the
[Repository Workflow Governance Matrix](../software_assurance/REPOSITORY_GOVERNANCE_MATRIX.md).
