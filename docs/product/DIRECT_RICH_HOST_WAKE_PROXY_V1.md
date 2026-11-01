# Original direct-rich host wake Core proxy v1

Selected Core/API/Apple source contract. Normal Core service setup registers the
seven warm-owner proxy routes; this provides no operational native admission. The
current Direct rich frame/read/asset protocol and original native transcript are
unchanged. Host wake is content-free and does not grant Activity update/start
rights or replace original local display/clock custody.

All seven operations are POST below
`/api/djconnect/v1/session/rich/push/`: `prepare`, `native/challenge`,
`native/complete`, `native/status`, `register`, `status`, `withdraw`.
The closed validation-only envelope {method,path,direction,body} selects each
exact operation using the actual original HTTP method/path/direction. It is not
an extra HTTP wire wrapper: only its body is sent. The root rejects arbitrary
DATA, unknown routes/methods/directions/keys; explicit JSONPointer entrypoints
escape slash-routes with ~1. The exact perroute request/success/error shapes are in
`docs/verification/fixtures/host_wake_core_proxy_v1.schema.json`; the synthetic
examples are `host_wake_core_proxy_v1_vectors.json`. No synthetic proof, hash,
boolean, matching DTO or metadata row supplies authority.

## Original registered Broadcast wake

Only an original child with validated native-verification and registration API
ACKs, completed SQL stages and its SAME retained parent may subscribe. The
subscription has no snapshot replay. Actual Broadcast callbacks capture their
sequence, independent original wall/monotonic resource starts and one operation
UUID before scheduling; they retain no event payload. The bounded worker waits
for the actual Session manager lock and any original foreground request within
that same 30-second callback window. It checks current pair/Profile/Session,
source, owner and child clocks before projecting accepted semantic state.

Pure observation/progress and unchanged semantic projections do not send.
Playback, contribution, artwork identity/availability/attribution and rights
changes may produce one content-free private `direct_rich_refresh` wake. At most
eight workers run, with one later coalesced original callback each. An unsent
capacity loss, original resource timeout or uncertain projection drops only that
signal; it neither cancels a foreground request nor renews or revokes the parent.

The actual resolved role's send budget counts every durable `target_wake`
reservation, including uncertain attempts, before external HTTP. SQL once/CAS
and original-operation correlation precede the sole request. Unknown, rejected
or cancelled results after reservation close local positive custody and use only
the prebound once-only negative port; there is no retry or replacement operation.
Worker cleanup never retires the borrowed original pair. Child retirement
synchronously unsubscribes and scrubs retained owners before remote work.

This source connection does not establish operator enrollment, production API
mounting, Apple SDK verification, APNs delivery or native Widget/Activity rights.

## Original registered background read

The actual Source181 provider body remains exactly
`{"aps":{"content-available":1}}`. It contains no event type, purpose, Session,
generation, read credential or content. `direct_rich_refresh` is the private
Core-to-API wake operation, not an extra field in the APNs body. Original API
scope and correlation remain in that private HTTP request and response headers.

Before ordinary foreground suspension, the Apple owner may attenuate its
already acknowledged `registered` child and the SAME retained direct parent
into a read-only background continuation. This retains only the existing
parent read capability, original purpose/generation/Session/source ownership,
original local ContinuousClock/resource root and field rights. It creates no
new server grant or native SDK permit. The foreground SDK/effect task can close
without manufacturing a replacement parent or moving any original bound.
Without that completed foreground transfer, suspension still leaves only
negative/history custody. Cold process restart never reconstructs this port
from local key-reference files, defaults, OS payload DATA or status history.

The genuine OS callback is only a dirtiness signal to those already retained
registered continuations. Select no owner from payload fields. Coalesce work
within the bounded original callback execution budget and recheck the original
registration, pair/Profile/Session/source and read capability before dispatch,
after every await and before local Widget/Activity publication. Use the existing
direct `read`/`asset` routes and exact original frame/asset correlation; never
call authorize, prepare, challenge, register or key recovery in background.
The callback does not renew the original purpose, local resource root, field
expiry or external rights. Native publication and actual OS reception remain
separate qualification; delivery timing is not promised by provider acceptance.

Every request has exactly contract_version=1, device_id, client_type=ios,
session_id, surface=widget/live_activity, original Direct purpose_id and the
original native REGISTER operation_id. The native operation is a canonical UUIDv4
retained before scheduling and differs from the original display-authorize UUID.
Use genuine paired Authorization and matching single device/client headers.
Never forward parent credentials to API or accept read/asset credentials here.

Prepare additionally carries target, platform, apns_environment, original SDK
native_key_id_b64 and SHA256 of original APNs token bytes. These are intentions
to compare with actual enrolled identity and separately admitted signed policy,
not authority inferred from an ios device name or App Attest environment.
Actual existing Core installation credentials must already be loaded; no install
bootstrap/auth learning on this path. Missing genuine origin/identity/deployment/
enrollment/clock policy closes the operation.

The initial SDK key is created under the distinct installation-bound local
effect owner in [First key and deadline ownership](HOST_WAKE_FIRST_KEY_V1.md),
before prepare. Its reference supplies no enrolled-key, native or clock grant.
Prepare cannot demand an already-created Session/push permission for that
separate bootstrap effect, and key creation cannot substitute for prepare.

The actual original RAM parent supplies owner/device/source/paired-subject
bindings, generation and original clocks. BEFORE body-read awaits capture the
original service/request-task/genuine header-pair lifetime and UTC/monotonic
request window; do not guess body-only purpose/Session/operation fields. After
strict bounded decode, compare body identity and recheck that SAME captured
service/pair/task lifetime and original budget, without reacquiring authority or
reanchoring clocks. Only then capture the genuine current parent/context and
reserve its exact child once scope/pending latch synchronously BEFORE the first
child/API/SQL await. Cancellation or prebody lifetime loss closes without a child.
Original revision
is1 initially, monotone at most256, without refund/reset. Each operation remains
bound to the same original tuple. Lost responses, restart, rotation, new UUIDs,
status and pushes cannot reissue permission, secrets, nonce or budget.

Prepare and challenge responses require `native_proof_kind`, selected ONLY by
the actual API native-enrollment receiving state/job. Its value is
app_attest_attestation or app_attest_assertion, immutable for the original child
and job and rechecked after awaits and at use. Apple compares prepared/challenge
kind before SDK use; local key existence or a Rendezvous journal cannot select
it. This response metadata remains OUTSIDE the frozen original signing
transcript; the original R31 transcript/vector gains no extra keys.

Native complete carries the original Core challenge_id and exact native_proof
{kind,bytes_b64}; canonical standard base64<=12288 characters and<=9216 decoded
bytes, no truncation/fallback. Register carries the same challenge_id and original
APNs token bytes as canonical standard base64, decoded16..2048 bytes, exact
original token digest. API job IDs/capabilities/install-token records and private
issuer authority remain server-only. Real native enrollment/trust/counter and
signed environment must pass independently. `registered` means original durable
API acknowledgement; it does not mean APNs delivery or native display.

Request correlation is exactly SHA256 of compact canonical UTF8 JSON:
`["DJC-HOST-WAKE-CORE-REQUEST-V1","POST",exact_original_path,closed_body]`.
Objects have sorted ASCII keys, no normalization/BOM/whitespace/floats/-0 or
duplicates. Method and exact route distinguish identical challenge/status/withdraw
bodies. This digest is correlation DATA, not authorization.

The body and reply bounds are16384 bytes; strict UTF8, unique/known ASCII keys,
maximum depth8 and safe actual integers excluding booleans/floats are mandatory.
Canonical base64 pad bits/decoded sizes, original timestamp inequalities, complete
transcript/hash and exact tuple/currentness require semantic checks in addition
to JSON Schema. No query, browser Origin/Cookie, Content-Encoding, redirects,
automatic retry or secret/body logging. All responses no-store/nosniff/no-referrer.

A10s body limit and30s WHOLE attempt budget start at genuine Core pre-body UTC/
monotonic capture for EACH inbound HTTP callback. All its internal awaits share
the remaining budget. It is not a replacement deadline for prepare→SDK→register.
The original parent maximum and original challenge<=30s window remain separate.
A late SDK proof closes/expires; do not restart its nonce window or automatically
request a replacement. Status preserves original pending/registered/withdrawn/
expired/unknown history without positive restoration.

Withdraw synchronously fences ONLY the matching original push child and cancels
pending work before Profile/SQL/network awaits, bound to actual paired device/
entry/auth generation/Session/surface. No purpose-only cross-Session cancellation.
Negative remote withdrawal keeps separate bounded original authority after bearer
expiry; late/failed bookkeeping never reopens local custody. Push-only withdrawal
does not itself retire the separately owned parent rich display.

The owning Core child captures its negative issuer port before issuer IO from
its retained authenticated resolver reply and exact consumed SQL issuer claim.
The port retains only the original installation credential and fixed original
issuer tuple, never the positive PairACK, Session or parent. It can issue one
capless `issuer/withdraw` after local child closure. Its 30-second execution
window starts before scheduling; a duplicate cannot cancel the original attempt.
Entry unload fences this port before any unload await; service shutdown and
installation/configuration replacement also close it without recapturing secrets.
Unsent cancellation and completed/failed attempts release retained references.
An `unknown` reply remains inconclusive and never restores permission or quota.
Positive prepare requires the real original local owner, authenticated resolver
and issuer ACK, prepared SQL ACK and retained RAM capability. Native verification
and registration require their distinct exact API ACKs. This composition supplies
no operator enrollment, SDK proof, provider activation or device acceptance.

Local management captures the same pre-body paired request and the actual
committed linked-profile snapshot. It joins the retained child's immutable
reservation against all owner/device/entry/pair/Session/surface bindings and
the native operation ID before any child closure. An ended Session or retired
positive parent does not prevent this negative/history check; a status-request
failure or cleanup cannot retire the child. SQL metadata is not a remote
withdrawal acknowledgement, a native challenge result or restored permission.

The [owning-clock contract](HOST_WAKE_FIRST_KEY_V1.md#clock-ownership-and-exact-guarantee)
uses API's original UTC/SQL execution bounds, Core's original local ceilings and
Apple's actual pre-authorize ContinuousClock root. No remote Instant is
converted into a fresh local deadline and no directional-rate qualification,
rho=1 or JSON clock permit is inferred. Local SDK once/currentness and server
admission are distinct: a late SDK result supplies no enrollment or registration.
A no-SDK-effect-after-remote-expiry guarantee is not claimed without an actual
additional clock/roundtrip bound. Receiving/native/signed-policy qualification
and physical provider/device acceptance remain separate.

## Genuine native proof ACK and registration are distinct

Native complete/status states are pending, native_verified, withdrawn, expired,
unknown. Only the actual durable original proof verification, enrolled key and
counter, same tuple and signed policy can emit native_verified. An internal
verifying once claim remains publicly pending; terminal unknown is never
reopened by a later generic success. No positive verifier/enrollment factory is
created by this schema.

Register/status states are pending, registered, withdrawn, expired, unknown.
Registered is exclusively the original Source181 durable target registration
ACK, never a synonym for native enrollment. Withdraw returns only pending
bookkeeping, withdrawn, expired or unknown; its local synchronous closure cannot
be undone by a registered/native_verified response. No management response alone
restores positive client RAM/native custody.

First register may consume an original, still-unconsumed proof that was genuinely
verified and durably recorded BEFORE its ORIGINAL challenge expiry, even if that
challenge window has since closed, within the unchanged original wake/display
maximum and actual warm Core parent/currentness. Recheck native key/counter,
signed policy, target and original installation record at register and dispatch.
Native_verified/status supplies no fresh deadline. A late verification, unknown
proof, consumed claim or changed tuple closes; no automatic replay or nonce
replacement. An already registered original target can remain usable after the
nonce window only while the same original purpose and actual policy guards hold.
This is neither nonce reuse nor proof/cold-process permission restoration.
