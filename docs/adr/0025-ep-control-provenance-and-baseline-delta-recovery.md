# ADR-0025 — EP control provenance and baseline-delta recovery

**Status:** Accepted for architecture authorization; not implemented
**Date:** 2026-08-31

## Context

Schema 40 records credential, consumer-registration and project-scope state,
but cannot establish the historical origin of a changed row.  That makes an
unexplained post-cutover central delta unsafe to recover over.  In contrast,
the active incident has an exact legacy quiescent baseline and a recorded
source-to-target equivalence proof.

## Decision

The next legitimate product schema is **41**.  The live contaminated database
marker `41` is not a product migration.  Schema 41 will add an append-only
`control_provenance_events` authority table, written in the same SQLite
transaction as every newly governed authority-independent mutation.  Existing
schema-40 state is explicitly `PRE_PROVENANCE_BASELINE`; no event is invented.

Each versioned event has an immutable id/time, domain/action, bounded subject
references (project, consumer, credential fingerprint/id), strict
`origin_class`, origin/control identity, versioned control-surface id,
correlation id, and before/after state digests.  Allowed origins are
`OPERATOR`, `MANAGED_RUNTIME`, `QUALIFICATION_CONTROL`, and `TEST_HARNESS`.
`TEST_HARNESS` can only be emitted by the hermetic installation authority,
never from prompt, provider, or user input.  Payloads are versioned and
bounded; credentials and prompts are never retained in plaintext.

Events cover credential issue/rotate/revoke, consumer
register/disable/revoke, and authority-relevant project registration/binding
changes.  Display-only project metadata is outside this authority event model.
UPDATE and DELETE are prohibited; corrections append a new event.

For the current incident only, recovery may combine immutable managed-run
lineage with a baseline-delta comparison and one external, immutable
historical-contamination attestation. Credentials, registrations, and project
scope that are exactly equal to the proven target-equivalence baseline are
`NO_POST_CUTOVER_MUTATION`, not retrospectively labelled production or test.
An attestation is allowed only for the exact migration/store fingerprints,
unchanged baseline rows, a deterministic authority-domain delta digest, and
fully covered components with at least two deterministic fixture signals plus
a known test writer. It is operator-owned forensic control, stored outside
CENTRAL, and never rewrites historical rows. Any fingerprint/delta change,
partial coverage, weak evidence, legitimate lineage, or unresolved component
is `CONTAMINATION_PROVENANCE_UNRESOLVED` and denies recovery. Future recovery
uses both deltas and immutable events; this exception is not schema-41
provenance.

The chosen order is: complete this bounded current recovery with the no-delta
rule, return safely to schema-40 LEGACY/MATCH, then implement and qualify the
schema-41 provenance infrastructure before a later fresh cutover.

## Consequences

- Current recovery remains fail-closed for any unprovenanced control delta.
- Dashboard/browser test children must receive the hermetic installation
  authority explicitly; product storage resolution is unchanged.
- No production schema migration is required before returning the contaminated
  pre-write incident to its pristine legacy baseline.
- The partial recovery controller may be completed by adding exact baseline
  comparisons for the three authority-independent domains.
- The provenance table and its controls are EP-owned and move with Phase 3.

## Test contract

Tests must cover no-delta acceptance; credential, registration and project
delta denial without events; managed-lineage denial; atomic state-plus-event
write; immutable event behavior; and hermetic-only `TEST_HARNESS` origin.

## Affected repositories

- `pcvantol/djconnect` until Engineering Platform extraction
- future `pcvantol/engineering-platform`

## Related documents

- [ADR-0019](0019-engineering-platform-central-installation-store.md)
- [ADR-0024](0024-ep-controlled-central-store-cutover.md)
- [Central-store migration guardrails](../engineering/EP_CENTRAL_STORE_MIGRATION_GUARDRAILS.md)
