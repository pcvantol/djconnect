# Post-Merge Release Evidence Architecture

The release identity is the exact commit SHA on `main`. Pre-merge evidence is
not silently reused: a canonical reconciliation validates that the `main`
commit is GitHub's recorded derivation of one qualified pull request, then
publishes fresh evidence for the real release SHA.

```text
qualified PR head SHA -> GitHub squash merge -> exact main SHA
  -> successful main CI -> evidence artifact -> reconciliation
  -> immutable evidence -> release manifest
```

For squash merges the two SHAs are deliberately different. Provenance requires
the GitHub merge record, target branch, final PR head, merge actor, timestamp,
changed-file equivalence and exact recorded merge commit. Direct pushes and
ambiguous provenance fail closed.

The reusable workflow is `post-merge-release-evidence.yml`. Every consumer
wrapper invokes it only from the successful `workflow_run` of its required
main CI through an immutable reference, and passes that same central commit
SHA as `policy_source_ref`. The explicit input prevents a caller SHA from
being mistaken for a central policy SHA inside a reusable workflow context.

Source repositories provide their required CI and coverage-artifact
identifiers. Distribution repositories instead provide their required
distribution-integrity workflow and its
`platform-release-distribution-integrity` artifact. They are qualified on
artifact integrity and metadata validation, never on source-code coverage. The
distribution integrity workflow runs on `push` to `main`; its reconciliation
wrapper invokes the reusable workflow only after that workflow has completed
successfully through `workflow_run`. Source wrappers follow the same sequence
after their required CI has produced coverage. This guarantees the evidence
artifact is available before it is read. The reusable workflow rejects direct
`push` callers and publishes the single canonical context
`Post-Merge Release Evidence / Reconcile release evidence` on the exact
workflow-run head SHA, even if a later commit reaches `main` while
reconciliation is running. It uploads `post-merge-release-evidence`.

Workflow-run cleanup is intentionally bounded, but it must preserve the
completed checks on the exact pull-request head that produced the current
`main` SHA. Those checks are the only valid pre-merge input for the following
reconciliation. A later cleanup invocation may remove them only after the
durable exact-main evidence has been published. Manual `workflow_dispatch`
runs are not releases and must not trigger a source repository's post-merge
reconciliation or require its push-only coverage artifact.
