# Deployment Workflow Policy

Deployment is an explicitly authorized external mutation. A deployment
workflow has only `workflow_dispatch`; it has no `push`, tag or
`pull_request` trigger. It is dispatched by the Platform Release Runtime or an
approved operator path using the bounded contract in
[Deployment Input Contract](DEPLOYMENT_INPUT_CONTRACT.md).

Before mutation it verifies exact main-SHA lineage, qualified post-merge
evidence, manifest and platform-version consistency, approved profile,
Software Assurance, Trusted Delivery, valid coverage and required artifact
hashes. A missing condition returns `DEPLOYMENT_NOT_AUTHORIZED` without a
partial mutation.

Target credentials are scoped to the deployment job only. Deployment failure
means the release is incomplete and fail-closed; it never rewrites CI or
release-evidence status.
