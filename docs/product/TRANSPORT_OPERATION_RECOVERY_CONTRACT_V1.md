# Transport operation recovery contract v1

Part of DJC-CORE-HYBRID-TRANSPORT-CONVERGENCE-V1-20261013. Design before code;
capabilities stay absent until the corresponding implementation is qualified.
One operation service surrounds existing application handlers, not new music/chat
implementations. HTTP and paired action WS normalize to that service.

## Identity, lifetime and bounded journal

Each deliberate user action receives a fresh UUIDv7 `operation_id`; retries keep
that exact ID, payload and original `operation_epoch`. UUIDv7's immutable creation
millisecond timestamp bounds eligibility:300s total lifetime, maximum30s future
clock skew. Expired IDs are rejected before dispatch even after journal cleanup.
Eligibility uses a nondecreasing effective clock: maximum of wall time, the
boot's wall-plus-monotonic anchor, and a durable journal high-watermark. Reservation,
phase transition and expired-record removal persist that high-watermark atomically
with the receipt update. A backwards wall-clock adjustment cannot re-admit an ID,
including after expiry/GC and restart. Server time metadata reflects this qualified
clock; an unqualified client clock fails closed instead of creating a new ID to
retry an uncertain action.
A subsequent deliberate skip has a new ID; changing an ID/epoch to replay an
uncertain action is forbidden. Server exposes its boot epoch and clock to an
authenticated client, without an HA credential or new account grant.

Scope binds authenticated device, Profile, entry/pairing generation, backend/account
context, boot epoch, operation name and SHA256 of canonical JSON payload. The
unexpired UUID itself has one global journal key; owner/device bindings are
checked on that record. Moving to another Profile/device can never create a
second journal key for the same intent or make an uncertain intent executable.
Identity
fields and authorization cannot be overridden inside nested payloads. Same ID with
other operation/payload/context returns409 operation_conflict/context_changed.
Operation IDs are not access credentials; status/retry revalidate the current
caller and original authority. No fallback across Profile/account/auth rejection.

Use existing HA Store primitives for one compact versioned receipt journal;
never persist request bodies, conversation text, artwork, raw audio or provider
payloads. Records contain only bound identity fingerprints, payload digest, clock,
epoch, phase, typed status/error and expiry. No full Runtime serialization or
new history engine. Total256 unexpired receipts,64 per owner,8 active executions;
capacity rejects new work, never evicts unexpired dedup evidence. Expired IDs
remain inadmissible from their own timestamp, so expired metadata may be removed.
Active tasks retain their fence until terminal; timeout cannot make work eligible
again. One journal owner and short async lock serialize load, capacity checks,
reservation and phase transitions; HA Store alone is not this transaction owner.
A failed/uncertain save freezes new dispatch until verified reload, so RAM cannot
forget a possibly committed reservation. Store failure before durable reservation
means no handler/provider dispatch.

## Phases and semantic boundary

| Phase | Meaning | Safe automatic behavior |
| --- | --- | --- |
| not_sent | Client has not handed request to a transport | May choose another qualified route, same intent/ID. |
| accepted | Durable server reservation exists before invoking the handler | Join/reconcile same ID; no second domain invocation. |
| sent_unknown | Actual provider dispatch boundary durably reserved, or crash/cancellation prevents proof | Query status; never blind replay, never infer failure/success from current playback. |
| confirmed | Handler returned a known accepted result and receipt commit succeeded | Render canonical result; duplicate returns receipt, never execute again. |
| rejected | Qualified pre-dispatch/domain rejection | Preserve typed authoritative error; no alternate transport/account bypass. |
| cancelled | Cancelled before dispatch with qualified proof | Report cancellation; do not invent a new ID automatically. |
| unknown | Restart before a terminal receipt or genuinely ambiguous execution/commit | Honest reconciliation; explicit new user action only, no hidden replay. |

The service reserves before Core invocation and revalidates at real provider send
hooks. Durable sent_unknown reservation precedes each first mutating provider
boundary. No adapter can claim provider exactly-once: a provider may accept before
its response or local completion commit is lost. Existing Ask DJ effect receipts
and client_message_id remain the owning conversation dedup/cost boundary, not a
second conversation log. Existing revision CAS still decides Mood/presence validity.

Caller/socket cancellation after admission does not cancel and redispatch a shared
execution. Await shielded bounded execution; disconnect stops delivery, not proof
of nonexecution. Owner revocation, source withdrawal, context/expiry fences remain
active before later effects. Provider timeouts and after-commit Broadcast failure
retain their actual acceptance meaning. Never retry after authoritative denial.

Execution phase and result availability are independent. A durably confirmed
operation stays confirmed after private content expires, RAM response loss or
restart; result_available:false never downgrades known acceptance to unknown.
A client keeps a known confirmed receipt when a later receipt query expires.

Boot epoch changes on restart. Old nonterminal reservations project unknown and
cannot run again; no Runtime/job restoration. Confirmed/rejected terminal receipts
retain their known phase while still valid and authorized. An old epoch execute is rejected.
A status read may explain the previous bound outcome but cannot dispatch, generate
or rewrite history. No fresh epoch/ID is fabricated to conceal an unknown outcome.

## HTTP and WS wire

New transport context/operation/status and paired action routes require an
authenticated TLS/server identity before any paired secret. Legacy plaintext
HTTP remains separately bounded compatibility, not a new automatic trust grant.

POST `/api/djconnect/v1/transport/operation` uses ordinary paired bearer/device
headers and closed JSON `identity:{device_id,client_type}`, `contract_version:1`,
`operation_epoch`, `operation_id`, `operation`, `payload`. The HTTP adapter removes
the required identity envelope after authenticating its exact device binding;
the shared service accepts only the remaining closed operation fields.
WS `djconnect/operation/execute` carries the same operation fields
plus its connection/request envelope; both invoke one dispatcher and the existing
handler. A first completed response carries its canonical result/status plus a
versioned operation receipt only while its original owner delivery admission
remains valid. Ask DJ and Track Insight register the existing RAM-only result
guards; no callback is serialized. At actual HTTP/WS delivery those guards run
again. A queued pure read is projected by its existing owner at actual send.
If an original rich-result guard is unavailable or has become invalid, return
only the compact semantic receipt with `result_available:false`; confirmation
is retained, never promoted into renewed content rights. Repeat execution requests return status/receipt and
`result_available:false` where content cannot be safely replayed; they do not
regenerate a private answer or create a new publication. Clients may use a
qualified existing history/query owner where available; absence remains honest.
`result_available` describes content included in this particular response after
its delivery admission: true on an admitted first body, false on receipt-only
fallback, duplicate and status responses. The receipt in the same envelope uses
the same value. No durable body is implied by a true first-response value; the
journal stores no body and a later status still returns false.

Initial response policy by family: Ask DJ and Track Insight use their original
joined/source/target guards; Session start requires the same still-active owner
Session, and end uses its existing private owner fence for the immutable ended
Session result. Mood/presence use the original owner guard and committed setting
revision; a superseded setting result becomes receipt-only. Ordinary commands
reuse the existing synchronous paired/Profile/source owner fence, capture the
result's current Session/playback identity and add a maximum five-second in-flight
delivery window. Query bodies such as outputs/queue/search remain renderable;
context change, a slow queue or source withdrawal yields only the receipt. This
window never extends original media/selection expiry or proxy-grant rights.
Consumers reconcile unavailable bodies via an existing authorized query owner,
never by resending the command. No provider query is authorized where the selected
function forbids one.
Only the existing Mood/presence CAS conflict is currently qualified as a returned
pre-write `rejected` receipt. Other handler failures remain conservatively unknown
unless a specific operation proves its non-execution boundary; HTTP status alone
does not establish that proof. A typed authority rejection before handler entry
is rejected; an after-entry/after-send ambiguity is never relabelled pre-send.

POST `/api/djconnect/v1/transport/operation/status` and WS status use version,
original ID/epoch, plus the HTTP identity envelope. POST
`/api/djconnect/v1/transport/context` accepts only `contract_version:1` and that
identity envelope; its owner response includes the existing paired installation
ID, boot operation epoch, effective server clock, lifetime and declared operation
sets. It neither issues credentials nor creates an installation identity.
No secrets in query parameters. All responses no-store,
no-referrer. Typed errors include operation_expired, operation_conflict,
operation_context_changed, operation_epoch_changed, operation_capacity,
operation_unavailable and operation_unknown. Unknown is not a successful playback
readback and not authorization to retry. Response source rights/expiry remain
those of the original handler, not the receipt lifetime.

Initial closed policy: shared command actions, Ask DJ text and Track Insight;
Session start/end (HTTP only), Mood/presence (HTTP/paired actions). Pure active,
Forecast, Broadcast snapshot reads are separately declared and safely repeatable.
Other management/paging/voice/binary/file routes remain HTTP-only with their
existing domain identity/revision and explicit no-automatic-after-send-retry rule.
No unsupported command is advertised. New operations require a versioned policy
entry, source/right/effect qualification and parity/failure tests.

## Privacy and resource withdrawal

A receipt cannot grant expired private/media data. Return only compact status
on repeat/status; no durable rich result body. Recheck device/Profile/source/entry
binding before receipt delivery and current handler result delivery. Pairingrotation
or deleted/reassigned Profile withdraws old material; leaseexpiry alone permits
reconnection with current pairing. Legacy clients keep existing HTTP behavior,
but get no new cross-transport idempotency promise unless using this contract.
