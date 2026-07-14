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

For a deployment-eligible artifact, the evidence binds its immutable artifact
ID and SHA-256 checksum, exact main candidate SHA, platform version and
approved manifest ID. It records only the manifest allowlisted targets and
release profile. Publication in a distribution repository is required only
where that target's canonical distribution model requires publication: Pi and
ESP32 use their release repositories; the HA integration may use an immutable,
checksum-bound qualified internal artifact without a separate GitHub Release.
