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
3. tests and documentation exclusively required by either item.

Unrelated Engineering Platform or product work is forbidden. The harness and
recovery controller must be separate pull requests, in that order.

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

Operator review and merge remain mandatory. Watcher and Local API are
correctly unavailable while they reject the unsupported schema-41 central
store; this authorization does not normalize that drift.

## Required sequence and termination

The required sequence is:

1. implement and qualify the hermetic harness repair;
2. prove ordinary full-suite isolation and merge that repair under this mode;
3. implement and qualify the contaminated pre-write recovery controller using
   the repaired harness, then merge it under this mode;
4. obtain separate authorization to execute production recovery;
5. restore supported `LEGACY` schema-40 authority, ready services, and desired
   state `MATCH`; then resume ordinary governance.

The mode automatically terminates when the authoritative store is supported,
services are `READY`, and desired state is `MATCH`. It cannot be extended to
later work by precedent.

## Audit record

Each authorized pull request must cite this document, the incident migration,
its authorized class, the production before/after fingerprint record, the
selected Python runtime, and the termination condition. It must not contain
secrets. This document is the authorization record for the exception; a later
architecture decision record or implementation document remains subject to
the normal repository-mutation gate unless it is itself within an existing
explicit exception path.
