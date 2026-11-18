# Persistence Foundation Test Matrix

The persistence foundation is infrastructure only.  This matrix records the
focused evidence required before product data is introduced.  The current
schema contains only platform metadata and migration history; it intentionally
contains no reference or user data.

| Area | Covered evidence | Deliberately not applicable yet |
| --- | --- | --- |
| Bootstrap | Fresh, latest, supported-old, future, missing and corrupt metadata; repeated startup; clean shutdown; concurrent Home Assistant bootstrap. | — |
| Database creation | Canonical `.storage/djconnect.sqlite3` location, metadata and migration-history creation. | Reference-data reconciliation: no reference-data set exists before a product capability owns one. |
| Migrations | Empty-to-latest chain, ordering/history/version advancement, retry after a planned failure and transactional rollback. | Nested migration transactions and rollback of an already committed migration are not supported by SQLite or the forward-only contract. |
| Reference data | The platform preserves the empty reference-data boundary; no user-data tables exist to modify. | Creation, reconciliation, additions and stable identifiers await the first owned reference-data capability. |
| Transactions | Commit boundary, rollback on failure, no raw connection exposure and no transaction leakage. | Nested transactions are intentionally unsupported. |
| Connections and concurrency | Private connection creation/reuse, clean/failure close, independent reads, short serialized writes, busy timeout configuration and bootstrap concurrency. | — |
| Integrity | Healthy-database integrity, corrupt metadata and missing-table detection. | Required-index detection has no current subject: metadata tables use primary-key constraints and there are no product indexes. It becomes mandatory with the first declared required index. |
| Security | No credentials or product rows in the schema/readiness projection; no database path or provider handle is exposed through the repository-facing API. | Product diagnostics/logging tests await product data and diagnostics surfaces. |
| Architecture | Source checks keep SQLite connection creation, transactions and migrations inside the persistence platform; repository abstraction remains provider-neutral. | — |

The executable evidence is in `tests/test_persistence_platform.py` and is run
with the repository validation suite.  This matrix does not authorize Session,
Profile, Music DNA or historical persistence.
