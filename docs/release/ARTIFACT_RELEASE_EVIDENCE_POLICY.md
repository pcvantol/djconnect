# Artifact Release Evidence Policy

Artifact / Release Evidence workflows run after the successful required CI for
the exact `main` SHA, normally through `workflow_run`. They collect coverage,
checksums, manifests and GitHub provenance, reconcile the final main SHA and
publish immutable evidence/status records.

They fail closed on missing, stale or ambiguous evidence and are idempotent for
the same read-back. They may use `actions: read`, `checks: read`, `contents:
read`, `pull-requests: read` and narrowly scoped status/artifact write access.
They never use deployment credentials or mutate an application environment.

Evidence failure means `NOT_READY`; it does not change the historical CI
qualification result.
