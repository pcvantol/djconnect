# Platform Release Runtime Execution

Status: `IMPLEMENTED`

The existing Release Planner, version validator, discovery model and readiness
engine remain the sole source of release scope and eligibility. The operational
executor consumes their immutable manifest; it does not recalculate scope or
embed repository-specific release behaviour.

## Allowed operations

| Operation | Runtime action | Safety boundary |
| --- | --- | --- |
| Build, artifact publication or deployment | Dispatch an existing GitHub Actions workflow | Workflow/ref must be explicit and the repository must be discovered in scope. |
| Tag creation | Create an explicit lightweight tag at a full candidate SHA | Only after all release gates pass. |
| GitHub Release | Create a draft prerelease only | Public releases are not representable. |
| Rollback | Preserve completed-operation and source rollback-plan evidence | No automatic rollback mutation. |

Build execution is delegated to the frozen runner model. Codex and this Python
runtime never compile platform software.

## Fail-closed execution gate

The executor accepts only `INTERNAL_RELEASE` requests in `production` or
`hotfix` mode with a `READY` manifest. The existing readiness engine makes
candidate SHA, version alignment, Verification, Software Assurance, Trusted
Delivery, coverage and platform qualification required evidence. A missing,
failed or out-of-scope action stops execution before downstream mutation.

## Evidence

Every operation records time, repository, category, action receipt and result.
The resulting execution report separates deployment, publication and
post-release evidence and includes preserved rollback preparation evidence.
