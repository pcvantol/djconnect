# Owner-confirmed individual content deletion v1

Core owns the selection, dependency closure, durable erasure and late-publication
fences for #1225. Clients present the actual server scope before confirmation.
This extends the separately delivered whole/archive deletion contract; it does
not end a Session, undo playback, erase Music DNA, or reset Profile settings.
Use synthetic disposable data for qualification. Installed/native/user acceptance
requires its own receipt; capability advertisement alone is not acceptance.

## Authority and target identity

Every request uses the existing paired `device_id`, `client_type` and bearer
credential. The server resolves the Profile, original device/entry generation,
pairing, source/privacy/grant and binding generation. No client-selected Profile,
HA-user fallback, administrative impersonation, text search or row adjacency.
Supported client families match history deletion, including Apple and Pi.

`session_content_delete: true` plus contract version `1` advertises these HTTP
routes. They are not generic Hybrid action operations and have no automatic
transport replay. Responses use `Cache-Control: no-store` and
`Referrer-Policy: no-referrer`. All identifiers below are opaque strings: clients
must retain exact bytes rather than parse or regenerate them.

POST `/api/djconnect/v1/session/content/delete/prepare` requires exactly the
paired identity, integer `contract_version: 1`, and `target` with three fields:

| Field | Type and semantics |
| --- | --- |
| `kind` | `entry`, `moment`, `message`, or `request` |
| `session_id` | Required string. Actual originating Session ID for Session content; **exactly `""`** for standalone Profile messages/attempts. Never null, omitted, or a guessed current Session. |
| `target_id` | Actual server `entry_id`, `moment_id`, or message `id`; for an uncertain attempt only the original `client_message_id`. Never a local presentation UUID, text, playback ID, new request ID or exchange adjacency. |

Selecting either accepted message role resolves the same complete server-defined
exchange. A standalone legacy unpaired contribution remains its own stable
server unit. An original uncertain request can be fenced before admission;
that means no new request with that ID can later publish, persist or dispatch a
new playback effect. It does **not** prove a previously dispatched music command
was undone. Accepted request/message content must match the supplied Session;
blank standalone context cannot target an accepted Session exchange.

## Prepare response and confirmation

The response contains `success: true`, integer `schema_version: 1`,
`owner_profile_id`, exact echoed `target`, opaque `confirmation_id`, and UTC ISO
`created_at`/`expires_at`. The nonrenewing confirmation lasts five minutes and is
bound to this paired authority. Restart invalidates unused confirmations.

| Field | Type and identity |
| --- | --- |
| `unit` | Object `{kind, session_id, target_id}`. Kind is resolved `moment`, `exchange`, or `attempt`. Exchange target is server exchange ID; attempt target is a server hash of the original ID. It is not a new sendable request. |
| `affected_entries` | Array of `{session_id: string, entry_id: string, disposition: "remove"\|"unavailable"}`. IDs are existing rows; unavailable preserves identity/order while withdrawing the dependent body. |
| `removed_message_ids` | Array of exact server message IDs, including both accepted roles when applicable. |
| `unavailable_message_ids` | Array of exact dependent message IDs to retain as unavailable, with body/media/actions/source grants withdrawn. |
| `affected_moments` | Array of `{session_id: string, moment_id: string}` for the explicit Moment closure. |
| `fenced_request_count` | Nonnegative integer count of original request identities fenced by the captured scope. No prompt bodies or raw request keys are returned. |
| `music_playback_undone` | Always `false`. |

Clients explain this actual scope and expiry. Do not deduce counts from visible
pages, substitute a new scope silently, or optimistically hide content as a
completed erasure. Capacity, changed revisions/retention/Runtime/source scope,
other ownership or expired confirmation fail before any destructive effect.
Prepare is read-only and never cancels an attempt by itself.

POST `/api/djconnect/v1/session/content/delete` requires exactly paired identity,
integer `contract_version: 1`, original `confirmation_id`, original UUIDv7
`operation_id`, and boolean `confirmed: true`. UUIDv7 carries the original
five-minute operation lifetime and existing 30-second future-skew bound.
Duplicate requests must retain **the same original body and ID**. A pending
operation can resume within that lifetime after loss of the process-local
preview; this is recovery of its original scope, not renewed confirmation.

A completed response has `state: "completed"`, `deleted: true`, `operation_id`,
`confirmation_id`, `owner_profile_id`, `unit`, exact affected entry/message
arrays, `schema_version: 1`, `music_playback_undone: false`, and
`request_digest`: SHA256 of canonical compact sorted JSON containing only the
original `confirmation_id`. The opaque confirmation binds the full prepared
scope; clients compare it and the owner/unit/operation against their journal.
Only completion of Store, SQLite and Runtime/grant withdrawal produces this
receipt. A lost acknowledgement is an unknown outcome, never a synthetic GO.

## Read-only original operation status

GET `/api/djconnect/v1/session/content/delete/status` requires paired identity,
query `contract_version=1`, original `operation_id` and `confirmation_id`.
It returns the same owner, operation, confirmation and request digest, with:

| `state` | `definitive` | Meaning |
| --- | --- | --- |
| `unknown` | `false` | No matching durable intent found within the original lifetime. Not proof that a request cannot still arrive. |
| `pending` | `false` | Durable erasure obligation exists. No successful receipt; original unit may be included. |
| `completed` | `true` | `receipt` contains the original completed result and matching confirmation/body binding. |
| `expired_unknown` | `false` | Original transport lifetime expired. No renewal, optimistic removal, new operation, or inference from receipt eviction. |

Status never runs recovery, performs deletion, replays a provider/tool call,
creates a confirmation, writes the durable clock, or extends an expiry. It can
update an in-memory monotonic clock anchor. Unknown/expiry never means
"definitively rejected"; no such state is advertised. A definitive validation
error for one HTTP request does not settle an earlier ambiguous delivery.
Changed body or device/source authority is a conflict/denial, not a successful
readback. UI remains uncertain until a bound receipt plus qualified readback;
no automatic new-ID retry.

## Separate archive operation status v1

`session_history_delete_status: true`, version `1`, advertises GET
`/api/djconnect/v1/session/history/delete/status`. This is **not** content/status:
archive operations have no `confirmation_id` and cannot borrow one.

Query exactly paired identity, `contract_version=1`, original `operation_id`,
`operation=single` plus original `session_id`/`expected_revision`, or
`operation=all` plus original `snapshot_id`. No `confirmed` query field.
The request digest is SHA256 of compact sorted JSON of the original single
`{session_id, expected_revision}` or bulk `{snapshot_id}` confirmation body.
An exact completed receipt is identical to the original archive POST response.
Owner/operation/body fields are echoed outside the receipt. The four states,
nonrenewal, read-only behavior and unknown policy are the same as above.
Content and archive intents cannot be reconciled through each other's route.

The existing archive POST's optional `history_contract_version` remains `1` or
`2`, omitted meaning `1`. The opaque detail revision is representation
independent. A fixture with explicit `2` does not make that version mandatory
or authorize rebuilding an ambiguous original request with different fields.

## Durable effects, fences and limits

The existing Runtime manager lock precedes the existing serialized HA Store
writer and short canonical SQLite transactions. No alternate storage owner,
private provider, new model call or paid budget. Schema12 adds identifier-only
intent scope/tombstones/request fences; previous schema11 archive intents remain
valid. Intent precedes body/grant changes. Store acknowledgement and SQL effect,
revision changes, receipt and pending-fence retirement must settle before
reopening. Pending obligations survive expiry, restart and lost acknowledgements;
bootstrap/maintenance resume those obligations independently of client status.
Both durable request/source caches are reconciled before recovery reopens.

Selected content disappears; directly dependent stable rows become unavailable.
Dependency closure follows server exchange IDs, actual historical entry IDs,
persisted Moment/request provenance and bounded operational dialogue lineage.
It never matches prose. Preserve independent history, original playback effect
receipts, Profile/DNA/settings, Session header/lifecycle and observation rows.
Current Moment deletion does not promote a previous Moment to current. Retire
old Flow/recovery snapshots and fence out-of-lock candidates so late provider,
Planner, HTTP/WS, speech/artwork and saved-result work cannot resurrect content.

An operation is bounded to 1000 combined affected units. Confirmations: at most
128 globally,16 per owner,20000 total bounded identifiers, no body retention.
The shared intent owner keeps its existing1024-record capacity; no eviction of
pending obligations. Durable tombstones/request fences each have a10000 global
bound and requests a1000-per-owner bound. Capacity fails closed; never evict a
still-useful request fence to permit a retry. These limits are not a claim of
unbounded archival deletion or physical secure erasure of storage backups.
