# TD-GITHUB Evidence Preservation Conformance Repair

## Objective

Repair the bounded Evidence Preservation divergence found during the
platform Dependency Governance rollout without changing product, runtime or
release semantics.

## Repository evidence

- The exact pull-request checks required by post-merge reconciliation could be
  removed by the same main workflow's cleanup job before reconciliation began.
- Apple source reconciliation is push-only because its required
  `apple-xccov-coverage` artifact is produced only by the main push CI path.
- Distribution repositories reconcile from their existing
  `Post-Merge Distribution Integrity` artifact and require the originating
  pull request's Software Assurance evidence.

## Bounded change

- Preserve all completed workflow runs for the uniquely resolved originating
  pull-request head while its main workflow cleanup executes.
- Keep Apple post-merge reconciliation limited to successful `push`-originated
  CI runs on `main`.
- Do not add a workflow, a gate, a retention policy, product behavior or a
  dependency analyzer.

## Validation

- YAML parses successfully.
- `git diff --check` succeeds in every changed repository.
- Existing Trusted Delivery and post-merge evidence contracts remain
  fail-closed.
