# Verification runtime GHCR publication recovery

A GHCR publication can stop after one or more tags were pushed. There is no
automatic resume and no automatic deletion. Treat an incomplete attempt as
unreconciled, including when the runner stops before uploading the journal.

Before any tag push, the workflow retains its exact OCI archive as a GitHub
Actions artifact. It computes and records the archive SHA-256, the independently
verified OCI manifest digest, candidate SHA, artifact ID and artifact digest.
The append-only journal records each push intent and confirmed readback; the
workflow attempts to upload it even after failure. Artifact upload and runner
storage can fail or expire, so a missing or incomplete journal is not evidence
that no tag was written.

For manual reconciliation, independently retrieve the workflow run and attempt,
archive artifact and journal from GitHub, verify their identities and digests,
and inspect every intended immutable and mutable tag in the actual registry.
Preserve the original archive, journal and historical 1.1.0 digest. Confirm the
package's authorized writers and stop competing publication before deciding any
next action. Do not delete a package version or overwrite an existing immutable
tag. If the evidence is incomplete, a tag points to an unexpected digest, or
writers cannot be accounted for, stop and investigate. A later continuation
requires a separately reviewed plan that recognizes each already-published tag
only after exact digest and provenance verification; this workflow does not
currently implement such continuation.

A workflow concurrency group serializes this workflow only. Registry lookups
and pushes are not an atomic compare-and-set, and outside writers can race them.
A GitHub run API record corroborates run identity but environment variables and
the record alone do not establish independent publisher authorization or
package-wide exclusivity. Mutable latest/minor promotion is explicit and
requires pre-existing expected state, recheck and post-push readback.
