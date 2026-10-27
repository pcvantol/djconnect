# Local status-bootstrap once journal preparation

`surface_bootstrap_once.py` is an uncomposed hash-only ordering primitive. It
has no shipping imports, concrete production store, HTTP route, owner lookup,
clock provider, secret generation or native instruction. Recording
`approval_recorded` is DATA, not proof of an authenticated owner action.

The original identity is retained across all stages: candidate, view reservation,
approval record and claim reservation. `begin` reserves the process-local slot
synchronously before scheduling. Each database transition must compare the
complete original row and revision atomically. A claim reservation precedes any
future response delivery; no credential or response is cached here. Unknown
commit/acknowledgement outcomes poison the original process handle, and a restart
has no live receipt. A different request identifier cannot reopen an existing
original identity. Capacity is bounded; no eviction or tombstone deletion permits
reissue. Local retirement fences pending work synchronously; persisted retirement
is separate bookkeeping and does not assert remote or OS erasure.

The required `BootstrapOnceStore` has no default implementation. Its insert
contract requires a unique original identity and bounded retained capacity in
one transaction; its CAS contract compares every original field. The temporary
SQLite adapter exists only in tests and uses the real persistence service. Its
DDL is fixture setup, never a runtime schema migration. Existing SQL15 journals
and their semantics are unchanged. SQLite WAL `synchronous=NORMAL` transactions
prove these ordering and CAS controls, **not power-loss durability**. A production
adapter requires a separately qualified stronger commit boundary, normal schema
migration and real storage evidence before any irreversible delivery.

The causal controls cover two adapters racing for one identity, stale revision
and binding, duplicate stages, lost claim acknowledgement after actual commit,
SQLite cancellation delivery being consumed while the task remains cancelling,
retirement during a held postcommit acknowledgement, restart, forged receipts,
capacity and grammar. All identifiers and comparison hashes are synthetic. No
test substitutes a successful callback for real owner or native authority.

Production composition still needs the actual trusted Home Assistant user and
auth-session continuity, an authoritative principal-to-Profile/source/Session
entitlement, qualified original clocks and the separately authenticated management
bridge. The current Profile resolver index is a routing hint, not that
entitlement. Ordinary administrator/device/paired credentials cannot fill this
gap. Missing prerequisites must close before a positive public context, claim
secret, management operation or SDK instruction. This primitive alone cannot
advertise push availability or change any default factory.

This preparation does not revise the private R9/API-v2 wire proposals or qualify
them as operative contracts. Independent whole-source and exact-commit review,
normal protected delivery and a separate original-qualified Final remain
required. No HA installation, provider configuration or device action is part of
this increment.
