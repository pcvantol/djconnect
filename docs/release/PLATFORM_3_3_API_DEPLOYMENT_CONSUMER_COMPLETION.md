# Platform Release 3.3 — API Deployment Consumer Completion

Date: 2026-07-14
Decision: `API_DEPLOYMENT_CONSUMER_STATIC_IMPLEMENTATION_COMPLETE`

## Scope

The central API now has three independently scoped workflows in
`pcvantol/djconnect-api`:

1. `api-release-artifact.yml` runs after successful exact-`main` validation,
   produces a bundled Worker artifact plus D1 migrations and records its
   checksum-bound evidence.
2. `deploy-api-worker.yml` accepts only the canonical deployment inputs,
   verifies artifact provenance, applies the artifact's D1 migrations and
   deploys its pre-bundled Worker with Wrangler `--no-bundle`.
3. `api-worker-post-deployment-smoke.yml` is separate from deployment,
   validates its deployment evidence and makes a bounded read-only request to
   the public API health route.

The artifact form was locally verified with Wrangler `4.107.0`: a bundle made
by `wrangler deploy --dry-run --outdir` successfully completed a second
`wrangler deploy <bundle>/index.js --no-bundle --dry-run` run. The sourcemap
reference is removed before artifact packaging, so the release artifact does
not retain absolute source paths.

## Fail-closed boundary

No approved current-main operational release manifest exists. Consequently the
deployment workflow rejects every dispatch before artifact download, Cloudflare
credentials or mutation. The smoke workflow currently records
`SMOKE_INCONCLUSIVE` and fails after publishing evidence: `/health` proves
basic reachability but does not expose the candidate version or bounded runtime
startup/crash state.

The pre-existing API CI/CD deployment and E2E smoke remain separate normal
delivery automation. They are not Platform Release 3.3 deployment or smoke
qualification evidence.

## Verification

- API workflow YAML parses successfully.
- `git diff --check` passed in `pcvantol/djconnect-api`.
- `npm test -- --run` passed: 40 tests.
- `npx tsc --noEmit` passed.
- Prebuilt Worker dry-run with `--no-bundle` passed without deployment.

No production Worker, route, D1 database, credential, release or target state
was mutated.

## Remaining blockers

1. Create and make available a current approved operational release manifest
   that binds the API target, candidate SHA and artifact checksum.
2. Add an observable candidate/version read-back and bounded runtime-health
   source for the API smoke contract.
3. Obtain explicit authorization for one manifest-bound deployment and its
   separate smoke run. Only then may operational qualification be assessed.
