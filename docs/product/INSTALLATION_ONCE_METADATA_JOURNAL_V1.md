# Original installation once metadata journal

This private source increment adds schema19 and an unused metadata journal to
the existing PersistenceService. It implements no key generator, signer,
registry caller, operator enrollment or production factory. Public R2 DATA
and R1 transcript bytes remain unchanged. Source, delivery, installation and
operational push qualification remain separate.

## Original reservation and acknowledgement

Custody generation uses its original custody_operation_id. Later bootstrap
signing uses its original registration_operation_id, complete primitive chain
and separately presented original admission intent. A required independent
owner must validate current policy/storage/positive context and, for signing,
the actual original API-intent acknowledgement. Matching JSON or hashes are
insufficient. No concrete production implementation of this owner exists here.

All owner ports return None or raise. Explicit capacity is required;128 is an
implementation ceiling, not an operational budget. The owner independently
qualifies actual policy. Both RAM attempt identities and SQL records retain
consumed capacity. There is no eviction, TTL, retry, reset or new ID generation.
The API registry remains a separate transaction domain.

The journal captures immutable original coordinates before the first await.
SQLite serializes global operation UUIDs across both kinds. A new reservation
checks original local revision where specified, increments the local ledger
revision, and reserves its terminal metadata row in one WAL/FULL transaction.
Required currentness is checked before staging and at the final commit fence.
Only an acknowledged new insert creates a process-local original handle.
Duplicate SQL, status, equal rows and restart never recreate that handle.

The phases are consumed-reservation0/revision0, metadata-result1/revision1 and
retired2/revision1or2. Fixed-length result metadata is allocated at reservation;
logical terminal capacity remains available at full row capacity. This is no
guarantee of host storage availability, power-loss behavior or restore freshness.

## Unknown and negative settlement

Commit-lost-ACK, uncertain storage and postcommit original storage replacement
return UNKNOWN without new authority or retry. SQL truth is preserved; a
retained consumed row is not proof of an acknowledged usable operation.
Cancellation retains its cancellation count and is delivered after definitive
SQLite settlement; the journal never calls uncancel or undoes a committed row.
Cancellation without an acknowledged handle cannot produce terminal authority.

Retirement first closes the exact original handle synchronously, before any
lock/storage await. The reserved negative terminal can still settle after
positive runtime permission is withdrawn, using only the original still-live
PersistenceService/provider/readiness identity and its storage-owner port.
It cannot borrow a new provider, create a row, adopt a key or revive a positive
result. Failure remains UNKNOWN and its attempted terminal is not retried.
Observation of original SQL truth is separate from actual reconciliation.

An acknowledged metadata result records only a supplied original digest.
It proves no key generation, signature, registry admission or APNs receipt.
Late positive completion after retirement stays closed. The future real
effect caller, actual installation/operator/clock/restore association, custodian
policy and API intent/withdrawal lifecycle require separate qualification.

## Qualification

The source has real disposable SQLite causal tests and an isolated actual HA
harness, verify_installation_once_journal_ha.py. Synthetic owners and expired
public fixtures never supply operational authority. The actual HA harness also
runs the preceding codec and original Session cases. A same-harness run against
the unchanged protected parent must fail at the genuinely absent journal.
Persistence changes require fresh affected predecessor HA receipts and exact
source joins; old277/278 receipts retain their original scopes and bytes.

One independent early review found a postcommit storage-close/reopen error
misclassified as a precommit input error. The narrow correction distinguishes
uncertain acknowledgement and has an actual close/reopen regression. The first
all13 regression also exposed its existing lifecycle harness's literal schema18
assertion; that assertion now checks actual schema19. Original failures remain
preserved, and final-source qualification must complete before delivery.

Whole-source review also demonstrated a self-consistent public DATA chain with
the generation and signing UUID equal on an empty journal. The journal now
rejects that known local namespace contradiction before any reservation. The
unchanged DATA codec remains a parser, and matching public metadata still grants
no authority. A complete recomputed-chain regression covers this distinction.
