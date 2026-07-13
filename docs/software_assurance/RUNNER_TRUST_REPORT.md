# Runner Trust Report

Date: 2026-07-13
Status: post-enforcement validation finding

The representative Raspberry Pi validation run `29230909878` used a
GitHub-hosted Ubuntu runner with a read-only `GITHUB_TOKEN`. No self-hosted
runner, secret, signing, deployment or production publication path was used.

The run failed before checkout because Actions SHA enforcement evaluated the
contents of canonical reusable workflows pinned by immutable commit. The
caller reference was immutable, but the historical reusable workflow source
contained `actions/checkout@v7` and `actions/setup-python@v6`. This is a
workflow supply-chain closure defect, not a runner-trust defect.

SHA enforcement was rolled back on all active repositories after live
read-back. Future enforcement requires recursive inspection of every referenced
reusable workflow commit before policy activation.
