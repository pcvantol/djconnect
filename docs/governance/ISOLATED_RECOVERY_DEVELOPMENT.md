# Isolated Recovery Development Authorization

**Status:** Active, incident-bounded governance authorization

**Incident:** `TEST-HARNESS LIVE-STORE MUTATION`

**Migration:** `41feb31e-2e25-42c4-bca1-bbfc97dde6f4`

## Decision

DJConnect authorizes the narrowly bounded mode
`ISOLATED_RECOVERY_DEVELOPMENT`. It permits recovery-enabling repository work
while the affected production development host deliberately remains in
desired-state `DRIFT`.

This is an exception only to the qualified-development-machine `MATCH` gate
for the work classes below. It is not a declaration that the host is healthy,
a general development bypass, or authorization to operate the live migration.

## Eligibility

All of the following must be true before each isolated-development task:

- the production desired-state drift is the incident being repaired;
- the authoritative store cannot safely be reconciled by the current runtime;
- the admission freeze is `ACTIVE`;
- no legitimate production execution is permitted;
- `main` equals its remote and the worktree is clean before branch creation;
- the production migration state and its artifacts can be fingerprinted
  read-only; and
- development and validation can be confined to temporary authority and data
  roots.

Otherwise the ordinary `MATCH` gate remains mandatory.

## Authorized and forbidden scope

Only these independently reviewable change classes are authorized:

1. hermetic Engineering Platform test-harness authority isolation;
2. the deterministic `CONTAMINATED_PRE_WRITE_CENTRAL_RECOVERY` controller;
3. `EP_READ_ONLY_FORENSIC_DELTA_EXPORTER_V1`; and
4. `EP_FORENSIC_PROVENANCE_ATTRIBUTION_V1`; and
5. tests, documentation and extraction-ownership updates exclusively required
   by an authorized item.

`EP_READ_ONLY_FORENSIC_DELTA_EXPORTER_V1` is recovery-enabling, generic
Engineering Platform forensic infrastructure. It compares persisted EP storage
snapshots deterministically for migration verification, incident analysis,
corruption/recovery diagnostics and evidence-lineage inspection. It is not
incident-only code and remains EP-owned through the later Phase 3 extraction.

Its V1 scope is limited to SQLite read-only opening; table/schema and row-key
discovery; deterministic added/removed/modified row comparison; normalized
safe digests; bounded evidence bundles; persisted graph references;
schema-difference reporting; versioned deterministic JSON; strict redaction;
an operator CLI that may write only its requested export file; synthetic tests;
documentation; and extraction-ownership updates.

It must not execute recovery, switch authority, mutate CENTRAL or LEGACY,
create a contamination attestation, decide production/test provenance, delete
or repair state, attribute source-code writers as a mandatory feature, change
the production resolver, or implement schema 41.

Unrelated Engineering Platform or product work is forbidden. The harness,
forensic exporter and recovery controller remain separate pull requests. The
forensic exporter precedes any provenance attribution or separately authorized
recovery-controller evolution; it does not resume recovery automatically.

`EP_FORENSIC_PROVENANCE_ATTRIBUTION_V1` is a separate, generic Engineering
Platform forensic and audit capability. It consumes a canonical
forensic-delta JSON report and deterministically attributes the evidence it
already contains for incident analysis, migration verification, writer
attribution, evidence audit and recovery planning. It remains EP-owned
through the later Phase 3 extraction; it is not disposable incident-only
code.

Its V1 model keeps these three fields independent for every changed
row/component:

- `ancestry_origin`: `PRODUCTION`, `TEST_HARNESS`, `OPERATOR`, `FORGE`, or
  `UNKNOWN`, describing the logical execution or control graph to which state
  belongs;
- `mutation_writer_origin`: `PRODUCTION_RUNTIME`, `TEST_HARNESS`,
  `OPERATOR_CONTROL`, `FORGE_CONTROL`, `MAINTENANCE`, or `UNKNOWN`, describing
  the actor that positively evidenced the changed write; and
- `state_semantics`: `IMMUTABLE_BUSINESS_STATE`, `EXECUTION_EVIDENCE`,
  `MUTABLE_PROJECTION`, `COMPONENT_LOG`, `RETENTION_STATE`, `CONFIGURATION`,
  `CONTROL_STATE`, `TEST_ONLY_STRUCTURE`, or `UNKNOWN`.

V1 may consume the canonical forensic-delta JSON, repository production writer
paths, repository test fixtures, immutable ingress envelopes, operator/control
receipts, Forge producer evidence, deterministic fixture literals and known
lifecycle structures. Timestamps alone are never proof. Each attribution must
record its evidence type, source path or test, matched deterministic signals,
and a rule-based status of exactly `PROVEN` or `UNRESOLVED`; probabilistic or
"probably test" labels cannot authorize recovery.

Positive attribution is permitted only where the evidence proves a production
runtime writer, a bounded test fixture/family, an operator or Forge control
writer, or a benign maintenance operation such as component-log retention,
projection update or database-maintenance metadata. Production-like ancestry
does not override a proven test writer, and a run reference alone does not
prove a production writer.

The future V1 output is deterministic `forensic-attribution.json`, bound to
the input forensic-report digest, attribution version and repository revision.
For every delta/component it records the three independent fields, evidence,
and `PROVEN`/`UNRESOLVED` status. It reports totals by writer origin and
separately distinguishes business/evidence state from mutable
projection/configuration/log state. It is evidence only: it does not execute,
authorize, or recommend recovery, and a later recovery decision remains a
separate governed step.

The current incident target is limited to deterministic attribution of the
immutable canonical forensic report with digest
`f431333b23c9eb0770b8033375f494e68cc81c967c1643324a890bf0d99611ee`.
Implementation must not rerun live database differencing unless a digest
mismatch makes that report unusable and separate authorization permits it.
This work class never directly queries or mutates production databases.

This authorization does not permit a production recovery command, migration
creation, thaw, authority switch, backup, target creation, Managed work,
service restart, or manual mutation of a migration receipt, freeze, pointer,
central store, or legacy store.

## Production immutability envelope

Before work and after **every** validation run, collect read-only values for:

- the migration receipt fingerprint and state;
- the authority-pointer fingerprint;
- the central and legacy database fingerprints;
- freeze state; and
- service state.

The before and after values must compare exactly. Any unexpected production
change is a stop condition: halt work, preserve the evidence, and obtain a
separate operator decision. The real authority pointer may be read only for
this comparison; no validation may resolve or consume it.

## Isolation requirements

Every Python, unit, and integration validation invocation must explicitly use
a temporary `HOME` and a separate temporary Engineering Platform installation
root. That root must contain its own user-data directory, authority pointer,
database, migration receipts, admission freeze, backup directory, and
service-control fixtures.

A mandatory writable-path sentinel must fail immediately when test code tries
to write outside that approved temporary installation root. The sentinel is a
prerequisite for broad-suite qualification, not an optional diagnostic.

Tests must not use the live central or legacy databases as fixtures. Prefer
synthetic schema-40 legacy and contaminated schema-41 central fixtures; when
realistic content is necessary, obtain a read-only source copy and mutate only
the temporary copy.

No isolated task may invoke real `launchctl` bootstrap/bootout or restart a
watcher, Local API, dashboard, or dashboard relay. Service behavior must be
represented by deterministic fakes or an explicitly isolated integration
facility.

Each qualification record must name one project-supported Python executable
and version, and use that same executable for its focused and full-suite
comparison. Homebrew, PlatformIO, and system Python results must never be
mixed in one equivalence claim.

For the forensic exporter, `DEVELOPMENT_HOST_MATCH` is not required while this
incident qualifies under `ISOLATED_RECOVERY_DEVELOPMENT`. Production `DRIFT`
remains a safety signal and must not be normalized to healthy. Development
uses a separate clean worktree based exactly on current `origin/main`; the
preserved recovery worktree must not be altered. Every implementation test
uses the canonical hermetic test admission/context, including temporary
installation-root activation, safety wrapper, authority isolation and required
browser/cache isolation. A separate worktree alone is not a harness bypass.

After isolated qualification, the exporter may inspect the real LEGACY and
CENTRAL pair only in hard read-only mode. Fingerprints before and after must be
identical; JSON output may be written outside those databases. This permission
does not authorize a provenance verdict or any recovery action.

For `EP_FORENSIC_PROVENANCE_ATTRIBUTION_V1`, `DEVELOPMENT_HOST_MATCH` is also
not required while this incident qualifies under
`ISOLATED_RECOVERY_DEVELOPMENT`; production `DRIFT` remains a safety signal.
Development uses a separate clean worktree based exactly on current
`origin/main`, and the preserved recovery worktree must not be altered. All
implementation tests use the canonical hermetic admission/context, including
temporary installation-root activation, safety wrapper, authority isolation
and any required browser/cache isolation. Worktree isolation never bypasses
the harness.

## Qualification and merge policy

`ISOLATED_VALIDATION_PASS` is distinct from `DEVELOPMENT_HOST_MATCH`. A
recovery-enabling pull request may be review-ready and may merge while this
incident leaves the production host in `DRIFT` only when all of the following
are evidenced:

- isolated full suite and affected focused tests pass;
- the sentinel proves ordinary tests cannot reach the installed authority;
- every production before/after fingerprint is identical;
- the pull request is limited to an authorized work class; and
- no live production command was run.

For `EP_READ_ONLY_FORENSIC_DELTA_EXPORTER_V1`, this additionally requires
focused exporter tests, the canonical full hermetic suite, changed-file Ruff,
`git diff --check`, the extraction audit, and an unchanged production
immutability envelope. This outcome is `ISOLATED_VALIDATION_PASS`, not
`DEVELOPMENT_HOST_MATCH`.

For `EP_FORENSIC_PROVENANCE_ATTRIBUTION_V1`, a later implementation pull
request additionally requires focused attribution tests, the canonical full
hermetic Engineering Platform suite, changed-file Ruff, `git diff --check`,
the extraction audit, an unchanged production immutability envelope, and no
production host `MATCH` claim. This outcome is likewise
`ISOLATED_VALIDATION_PASS`, not `DEVELOPMENT_HOST_MATCH`.

Operator review and merge remain mandatory. Watcher and Local API are
correctly unavailable while they reject the unsupported schema-41 central
store; this authorization does not normalize that drift.

## Required sequence and termination

**Retirement override:** ADR-0026 retires migration
`41feb31e-2e25-42c4-bca1-bbfc97dde6f4` for clean-slate extraction. The
authorized recovery-controller, forensic-exporter and attribution work remains
preserved historical evidence, but this exception authorizes no further
incident recovery expansion, live forensic export, reverse reconciliation,
attestation, thaw, service action, or authority operation. Remaining forensic
unknowns are not a Phase-3 extraction prerequisite.

The required sequence is:

1. implement and qualify the hermetic harness repair;
2. prove ordinary full-suite isolation and merge that repair under this mode;
3. implement and qualify the forensic exporter using the repaired harness,
   then produce its deterministic live forensic report;
4. implement and qualify provenance attribution against the immutable canonical
   forensic report only, then obtain a separate recovery architecture decision;
5. if needed, separately authorize recovery-controller evolution or operation;
6. restore supported `LEGACY` schema-40 authority, ready services, and desired
   state `MATCH`; then resume ordinary governance.

The mode automatically terminates when the authoritative store is supported,
services are `READY`, and desired state is `MATCH`. It cannot be extended to
later work by precedent. ADR-0026 does not normalize current `DRIFT`; it
instead retires the current migration and requires a separately governed
standalone service/cutover transition.

## Audit record

Each authorized pull request must cite this document, the incident migration,
its authorized class, the production before/after fingerprint record, the
selected Python runtime, and the termination condition. It must not contain
secrets. For the forensic exporter, record authorization reason `active
contaminated-central recovery incident`, work class
`EP_READ_ONLY_FORENSIC_DELTA_EXPORTER_V1`, worktree isolation, merge-under-
DRIFT criteria and the shared exception termination condition. This document
is the authorization record for the exception; a later architecture decision
record or implementation document remains subject to the normal
repository-mutation gate unless it is itself within an existing explicit
exception path.

For provenance attribution, record authorization reason `active
contaminated-central recovery incident`, work class
`EP_FORENSIC_PROVENANCE_ATTRIBUTION_V1`, the input forensic-report digest,
worktree isolation, `ISOLATED_VALIDATION_PASS` criteria, and the shared
exception termination condition. A report may reduce unresolved evidence, but
it cannot by itself select recovery class B1, B2, C, or D.
