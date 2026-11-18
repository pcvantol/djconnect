# Post-Merge Release Evidence Policy

`POST_MERGE_RELEASE_EVIDENCE_QUALIFIED` requires all of the following:

- one merged PR into `main` with a final qualified candidate SHA;
- successful required pre-merge Verification, Software Assurance, Trusted
  Delivery, workflow integrity and checks; HIGH_RISK work also needs exact-SHA
  Owner Authorization;
- GitHub-recorded merge derivation and matching changed-file sets;
- successful post-merge CI, tests, lint, static analysis, build validation and
  governance for the exact main SHA;
- coverage artifact and coverage report bound to that same SHA.

Distribution-only repositories do not build source and therefore require
post-merge CI, governance, distribution-integrity and metadata-validation
evidence instead of coverage. This role is determined by Repository Ownership.

Any missing, stale, ambiguous, fork-originated or direct-push evidence yields
`POST_MERGE_RELEASE_EVIDENCE_NOT_QUALIFIED`.
