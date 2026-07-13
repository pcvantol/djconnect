# Owner Authorization

Owner Authorization is an internal Trusted Delivery capability for the single
maintainer model. It is not a GitHub approving review and not a second
governance framework. Its only function is recording the owner decision for an
already technically qualified HIGH_RISK candidate.

For a HIGH_RISK pull request, run `Owner Authorization` in the target
repository with the exact `repository`, `pr_number`, `candidate_sha` and
target `branch`. The workflow accepts only owner `pcvantol`, validates the
current PR state and a passing Trusted Delivery technical check, and uploads
`trusted-delivery-owner-authorization-evidence`.

The evidence artifact includes repository, branch, PR number, candidate SHA,
classification, owner, GitHub actor, workflow run id, timestamp and PASS/FAIL
result. A changed candidate SHA cannot reuse the evidence.

Branch protection must require both the Trusted Delivery qualification check
and the `Owner Authorization` status. The latter is successful automatically
for LOW/NORMAL work and only after explicit authorization for HIGH_RISK work.
See `TRUSTED_DELIVERY_SINGLE_MAINTAINER_GOVERNANCE.md` for the canonical
decision model and rollout order.
