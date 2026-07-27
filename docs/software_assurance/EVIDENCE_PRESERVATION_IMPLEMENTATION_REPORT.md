# Evidence Preservation Qualification Implementation Report

**Status:** Implemented; post-merge qualification pending

## Scope

This bounded implementation resolves the technical path identified by
TD-GITHUB-001. It does not change Runtime, product behavior, Renderer Hosts,
API contracts, verification semantics, Actions retention cleanup or public
distribution.

## Canonical destination

The existing repository-native internal Home Assistant prerelease for the
exact main SHA is the sole canonical destination for durable qualification
evidence. A qualified post-merge reconciliation publishes exactly one asset:

```text
internal-ha-<main-sha>/qualification-evidence-<main-sha>.json
```

The release asset is a durable, public/audit-addressable repository record and
does not depend on Actions log, Job Summary, cache or workflow-artifact
retention. Any Actions artifact remains a transient producer copy only.

## Evidence contract

`tools.trusted_delivery.evidence_preservation` creates schema version 1
`durable_qualification_evidence` records only from a qualified exact-main
post-merge reconciliation. The record contains:

- repository, role, exact commit SHA and policy source revision;
- release identifier, qualification profile/outcome and required formal check
  results;
- bounded producer and post-merge workflow identifiers;
- source evidence digest and a canonical-JSON SHA-256 integrity digest;
- `REDACTED` status, retention class and bounded supplemental digest reference.

It uses an automatic allowlist projection and rejects forbidden sensitive
patterns. No source logs, environment, path, credential, token, raw capture,
provider payload or personal data is copied into the record.

## Publication and failure behavior

The existing post-merge evidence workflow generates and validates the record,
then creates or verifies the exact-main internal prerelease target. It refuses
an existing asset with the deterministic name, uploads without overwrite,
downloads it and validates the read-back before it emits the existing qualified
status. Missing source evidence, failed checks, invalid schema/redaction or
integrity, target mismatch, collision, upload failure or read-back failure
fails the qualification path closed.

The workflow runs only for a successful `main` producer workflow. It uses the
existing repository `GITHUB_TOKEN` with only the added `contents: write`
permission required to publish that existing repository release asset; all
other permissions remain bounded to Actions, checks, pull requests and status
read/write needs. It never runs from pull-request or fork context.

## Historical boundary

No historical Actions run is reconstructed. The first merged implementation
SHA is the prospective baseline: it may claim only its own generated and
read-back record. Existing release records remain historical evidence under
their own contracts and are not retroactively asserted to meet this format.

## Qualification evidence required after merge

The post-merge workflow must complete on the merged SHA and expose a readable
asset with a valid schema, `REDACTED` status and matching integrity digest. The
separate qualification Finalization may then promote TD-GITHUB-001 only if
that objective read-back succeeds.
