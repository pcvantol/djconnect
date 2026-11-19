# HACS CI Alternating PR-Validation Reclassification

**Status:** Assessment complete

**Decision:** `HACS_CI_PR_SIGNAL_NOT_ACTIONABLY_CLASSIFIED`

## Evidence matrix

All rows use the pinned `hacs/action@1ebf01c408f29afcb6406bd431bc98fd8cbb15aa`, `category: integration` and `contents: read`. An em dash means the primary Actions job log or metadata is unavailable after retention; it is not inferred.

| PR | HACS run/job | Event | Merge | Result/failure phase | Checkout and external lookup | Digest/lifecycle |
| --- | --- | --- | --- | --- | --- |
| #280 | — | — | 2026-07-21 09:15:05Z | historical Not Found; repository loading | — | — |
| #456 | — | — | 2026-07-25 08:18:44Z | historical Not Found; repository loading | — | — |
| #457 | — | — | 2026-07-25 08:32:15Z | historical head and merge failures; repository loading | — | — |
| #458 | — | — | 2026-07-25 08:59:51Z | retained check metadata unavailable | — | — |
| #459 | 30152119528 / 89664155561 | PR | 09:03:15Z | success; HACS completed | head `5bbaf22c` | timestamp/digest unavailable |
| #459 | 30152172176 / 89664295332 | push main | 09:03:15Z | success; HACS completed | main `5b0fb81c` | digest unavailable |
| #460 | — | — | 10:18:19Z | HACS checks succeeded; job metadata unavailable | — | — |
| #461 | 30154272121 / 89669661171 | push | 10:20:09Z | failure; repository loading | checkout fetched head `2dce8be5`; lookup at 10:20:24Z | `sha256:4c042…8626a`; 15s after merge |
| #461 | 30154273632 / 89669665323 | pull_request | 10:20:09Z | failure; repository loading | checkout fetched merge `e9f3d546`; lookup at 10:20:34Z | `sha256:4c042…8626a`; 25s after merge |
| #461 | 30154287506 / 89669700627 | push main | 10:20:09Z | success; HACS completed | main `4603529d` | digest unavailable |

Both #461 logs record `Not Found` and `Repository pcvantol/djconnect not loaded properly in HACS`; neither reaches metadata or content validation. Both GitHub checkouts succeeded, and the remote branch was not deleted during checkout.

## Classification

PR #459 succeeded and PR #461 failed with the unchanged reusable workflow, source pin, category, permissions and repository visibility. #461 proves independent head and merge checkouts converge on the same external loading route. Main succeeds after merge, but this does not establish a cause.

The timing supports a possible post-merge lifecycle sensitivity, but does not confirm a lifecycle race: the refs were available to checkout, and retained earlier timestamps cannot prove that all failures followed merge or deletion while successes completed before merge. The mutable-image explanation is likewise unproven: only the #461 digest is retained. No repository-owned workflow defect is demonstrated.

The PR job is an unreliable combined signal: one failed status can represent loading or a content finding. A completed HACS validation remains meaningful, but a loading failure is not a repository-content verdict.

## Product impact and exactly one next step

HACS is advisory and independent from Golden Qualification, Smoke, Regression, repository tests and Software Assurance checks. The failure does not establish a defective development baseline. **Automated Session Intelligence E2E Verification may resume.**

**Exactly one recommended next step:** a bounded operational classification-guidance assessment for retaining and reporting observed HACS loading evidence, without changing workflows, pins, retries, gates, failure semantics or validators.
