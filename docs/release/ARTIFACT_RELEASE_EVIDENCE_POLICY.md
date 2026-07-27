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

## Durable qualification evidence

For a qualified exact-main reconciliation, the canonical durable evidence
destination is one append-only JSON release asset on the existing immutable
internal Home Assistant prerelease tag `internal-ha-<main-sha>`:

```text
qualification-evidence-<main-sha>.json
```

The asset is the canonical long-term qualification record; an Actions artifact
is only a transient producer copy. The workflow creates the existing prerelease
tag only when absent and verifies that its target is the exact main SHA. It
refuses to overwrite an existing evidence asset, downloads the just-published
asset and validates it again before publishing the qualified status. A
publication, target, read-back, schema, redaction or integrity failure is
fail-closed for that qualification.

The record is an allowlisted projection, not a CI archive. It contains only
repository and exact-SHA identity, release identifier when applicable,
schema/version, formal outcome and required check results, bounded workflow
references, source revision, source digest, redaction status and its own
canonical-JSON SHA-256 digest. It excludes logs, artifacts, environment data,
paths, credentials, tokens, raw captures, provider output and personal data.
Its `LONG_TERM` class is distinct from permanent release manifest/deployment
records, short-term diagnostics and ephemeral CI data.

For a deployment-eligible artifact, the evidence binds its immutable artifact
ID and SHA-256 checksum, exact main candidate SHA, platform version and
approved manifest ID. It records only the manifest allowlisted targets and
release profile. Publication in a distribution repository is required only
where that target's canonical distribution model requires publication: Pi and
ESP32 use their release repositories; the HA integration may use an immutable,
checksum-bound qualified internal artifact without a separate GitHub Release.
