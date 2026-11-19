# Original server clock context continuation v3

Status: NORMATIVE DESIGN CONTRACT SOURCE CANDIDATE; runtime producer and native
client adoption are NOT delivered by this increment. Current runtime remains
its separately qualified v2 implementation until an owning implementation has
its own source/tests/actual paired HA evidence/reviews/protected source plus
separate Final and original qualification. No feature/owner/rate/native grant
follows from publishing this contract.

This full Markdown document is normative. The adjacent JSON summary is an
explicitly DERIVED NONNORMATIVE companion bound to these exact bytes; it cannot
relax omitted guards. Model vectors are synthetic reference math and declared
required outcomes, not actual producer/HA/native receipts or full coverage.

The exact privately reviewed R9 proposal SHA256
`0e1b7ab34b8b4da5ec25d2940fb6c315f3630f53bd8101718e59ee3473899432`
received bounded conditional Core, owning API and owning Apple design reviews.
Their scopes do not grant this source a future qualification. Original compiled
Apple offset RED144b remains open. Correction A only is selected; extension
restart/new render delegation B remains unsupported and needs a separate
accepted authorization design. All earlier proposals, failed counterexamples
and original v2 evidence remain byte-preserved with their own scopes.

## Exact version and wire

Use an explicitly version3 context request and an independent closed version3
response codec. Do not extend/coerce the historical version2 parser. A success
response has exactly these eleven keys: `success`, `contract_version`,
`available`, `context_handle`, `operation_id`, `purpose_ref`, `expires_at_ms`,
`context_expires_at_ms`, `purpose_remaining_at_original_start_ms`,
`context_remaining_at_original_start_ms`, `cache_policy`.

The existing opaque coordinate grammars and exact operation binding remain.
The first three values are true,3,true and cache_policy is private,no-store.
Absolute expiry fields retain their original identity/comparison meaning; a
client must never subtract its local UTC sample from them to mint authority.
Duration fields are strict finite JSON integers, not booleans/coerced numbers:
purpose1..28800000 and context1..30000, with context no greater than purpose.
Zero/expired/missing authority uses the existing typed closed error family;
there is no generic success fallback, optional duration, null or new capability.

## Complete paired-envelope version boundary

The existing admitted consumer scope remains WIDGET_ONLY. The actual widget
adoption port checks token_role=widget, activity_profile=null and
external_content_allowed=false; the original purpose authorizer independently
keeps those same fences. Preserve those guards and their original typed
phase-specific errors, including earlier scope/consent rejections; do not add a
role selector, widen authority or invent a credential to fit a response shape.
For a valid widget the existing registration validator requires
background_read=true, os_snapshot_cache=true, external_push_content=false and
allow_remote_start=false, with the existing explicit locked_display semantics.
Consequently the confirmed9-key response below describes only that already
admitted widget predicate. A widget with background_read=false is rejected by
the original invalid_widget_delivery_consent400 before registry mutation.
Possible future non-widget confirmed responses without background_read are
outside this current admitted scope; they are not unconfirmed success=false
responses, a new null field, or permission to activate an Activity profile.
All original v1 status/read/revoke and already-registered row lifetime semantics
remain unchanged. Any future Activity codec/rights extension requires its own
review and actual admission/native gates; hardware support alone grants none.

Both paired context AND paired register requests use strict integer version3.
Context request keys remain exactly contract_version, device_id, client_type,
session_id, operation_id. Register request keys remain exactly the historical
v1 registration key set plus context_handle, with version3: contract_version,
device_id, client_type, operation_id, session_id, platform, os_version, token_role,
target, apns_token, apns_environment, expected_registration, consent,
context_handle. No purpose_ref, durations, rho or clock-domain witness is imported
from the registration body. All original identity/token/consent/coordinate
validators and limits remain mandatory independently of the outer version.

A confirmed version3 register response has exactly contract_version,
context_handle, operation_id, purpose_ref, success, replayed, operation,
registration, background_read. An unconfirmed/replayed-unsuccessful response has
exactly the same set minus background_read, with success=false. The original
HTTP error remains exactly success=false,error with its original typed status.
All successful/unconfirmed outer versions are3; all opaque echoes match the
original context captured before awaits. Registration's original inner receipt,
revision, background credential and expires_at_ms rules remain unchanged; the
inner expiry equals context's original purpose expiry, not submit expiry. No
fresh durations or arrival-based budget are minted by registration responses.

These are independent version3 codecs, not a permissive v2 parser extension.
The context state retains version3 provenance; visible handle grammar equality
cannot admit a v2 handle into a v3 registration. On the new producer, v1/v2
context/register acquisition/mutation requests close with the existing typed
surface_context_required409 before an asynchronous paired check or effect.
A new client receiving an older producer's typed rejection closes and never
falls back to v2 to recreate a positive lifetime. Existing retained v2 fixtures
and receipts remain historical; they are not relabeled as v3 wire evidence.
Already registered rows retain only their original server-enforced authority
and expiry; this version boundary does not erase rows, mint rotation operations
or require a replacement grant. Existing original v1 status/revoke/read retain
their separate actual authority. Internal issuer/registry/relay/API wire remains
v1, and neither context_handle nor new remaining-duration fields is forwarded
to the relay/provider. Only the paired outer Core/client context/register codec
is versioned here. A new owner/purpose, fresh extension restart and native rights
are still separate closed gates.

## Original server operation and root witness

After synchronous paired preauthorization and before the first await, retain the
original server wall W0, monotonic S0, operation identity, original service and
the bounded weak original-purpose candidates for that authenticated runtime,
source and Session. Retain the original root witnesses with the operation across
503/OSError/cancel/lost reply. A retry cannot sample a new S0 or replace that
candidate set. An initially absent root remains absent for that operation; an
issuer completing later cannot attach new authority to its retained start.

After the existing asynchronous authority resolution, the admitted purpose must
be one of those exact still-current original objects and retain its original
owner/device/source/Session/runtime/broadcast/generation fences. A visible-field
match, same expiry or A-to-B-to-A replacement cannot substitute a new root.
Weak-reference loss, server/service/process restart and lost RAM history close
the operation. Existing bounded reservations/tombstones/attempt budgets remain;
an exception never refunds or silently reissues an operation.

G0 is specifically SurfacePurposeCredential.original_monotonic. L0_ms is the
already admitted original_grant_expires_at_ms minus that credential's
original_wall_ms. It is not object construction/adoption time or current wall
time. The original server purpose deadline is G0+L0_ms/1000 in the same original
clock domain as S0. Capture and retain once:

    M0_ms = floor(L0_ms + 1000*(G0-S0))
    A0_ms = original_grant_expires_at_ms - W0
    P0_ms = min(M0_ms, A0_ms, every pre-existing original purpose bound)
    K0_ms = min(30000, P0_ms, UUID_created_ms+300000-W0,
                every pre-existing original submit bound)

Both original server wall and original server monotonic expiry are independent
existing authority bounds. Use the minimum of their remaining budgets at the
same retained original server start; a valid current wall bound cannot be
ignored because the monotonic bound is also valid. This is server-own W0, never
client UTC arithmetic. For G0=0/original_wall=1000ms/original_expiry=1001000ms,
S0=0.8s/W0=1000500ms, the monotonic remainder is999200ms but the already known
absolute-wall remainder is500ms: P0 and K0 may be at most500ms. An operation UUID
created at W0 satisfies the unchanged UUID window and cannot waive that bound.
A nonpositive bound closes. A later server wall jump still requires the original
live server wall/mono/current-owner guards; this captured budget is not proof of
future clock behavior, instant remote revocation delivery or an OS clock-rate
witness. Final server and client deadline construction and comparisons must
remain conservative through every conversion, as specified below for C0.

Use exact arithmetic on the represented finite clock samples, or prove an
equally conservative downward result; large-magnitude floating addition followed
by subtraction must not round a budget upward. Quantization cannot establish
physical clock-rate equality. Nonpositive/nonfinite/overflow/rollback/domain
mismatch closes. Preserve the existing UUID future-skew limit30000ms and
five-minute lifetime. In particular a client UTC240s ahead cannot receive a
positive fixture by weakening UUID admission; a near-five-minute UUID receives
its actual small remainder rather than a new30seconds.

P0 and K0 never increase on repeated responses. All server actions independently
enforce original purpose and submit wall/monotonic/current-owner fences before
and after awaits, and at the last no-await CAS/publication point. A remaining
field is not renewal, token rotation, new enrollment or Activity authority.

## Client pin, cross-context minimum and clock qualification

The client retains its original monotonic request start C0 before its first
await. It must associate C0 with the exact operation, authenticated server,
original-purpose reference, owner/target and client process/clock domain. Arrival
time, response completion and a new UUID are not replacement anchors. Lost C0,
unknown original-purpose history, rollback or process/domain loss closes.

For every independently qualified mapping witness with conservative lower bound
rho_min on client-clock progress divided by server-clock progress over ALL
relevant intervals, including suspension, derive candidates:

    client_purpose_candidate = C0 + floor(rho_min*P0_ms)/1000
    client_submit_candidate  = C0 + floor(rho_min*K0_ms)/1000

The final addition to C0 is itself part of the conservative calculation. Keep
C0 plus the mapped duration in an exact rational/integer representation, or
choose the greatest representable deadline no greater than that exact sum.
Do not perform an unchecked floating addition after downward duration flooring.
For represented C0=2^48 seconds and mapped duration937ms, ordinary float addition
produces C0+937.5ms and is therefore forbidden: it extends authority by0.5ms.
A downward representable deadline is C0+875ms in that modeled domain. If no
positive representable interval remains, close immediately rather than round up.
Apply this rule independently to both purpose and submit candidates and every
subsequent conversion/storage/comparison. Domain/range/finite guards remain.

For the same authentic purpose, preserve the minimum of every accepted purpose
candidate across ALL contexts, operation UUIDs, retries and native-token
rotations, including the first original pin. Never replace it with a later pin.
An unknown/lost earlier purpose pin cannot be treated as first use. A genuine
new first-purpose association requires its separately established original
owner flow; cold start or a fresh response is not that flow.

rho_min is NOT a JSON field, runtime boolean, arbitrary client input, fixed UTC
margin or newly fabricated owner attestation. The actual owning platform must
qualify the clock-domain/rate/suspend assumptions. Unknown mapping admits no
positive local lifetime. Modeled equal-rate vectors use rho_min=1 only as an
explicit model assumption, never as physical/OS acceptance or production GO.
A slower-client counterexample at ratio0.999 must reject unqualified ratio1;
the downward0.999 mapping is positive only under that declared modeled bound.
If suspension permits client progress0 while server progress is positive, no
positive lower bound or pin is admitted. Original wall offsets are irrelevant
to this duration mapping, but remain relevant to the unchanged UUID policy.

Reason: causal request ordering establishes physical start(C0) no later than
start(S0), without comparing foreign numeric monotonic timestamps. Under a
qualified lower bound, client progress by the original server deadline is at
least rho_min*P0; anchoring the downward candidate at the earlier C0 is therefore
conservative. This is conditional mathematics, not an empirical rate proof.

## Required causal vectors and delivery

Versioned producer/client vectors must cover: original G0=0/L0=1000ms with
object creation700ms/S0=800ms gives200ms, never900ms; same-purpose candidates900
then990 retain900 through a different UUID/token rotation; lost original pin
closes. Capture root A then503/OSError/cancel followed by root B, absent initial
root, equal-field ABA, owner/source/Session change and RAM loss all deny reuse.
Include client UTC offsets0/-240/+240seconds with the original UUID policy,
arbitrary network delay, already-expired arrival, repeated identical replies,
exact five-minute and submillisecond/floor/large finite boundaries,
including upward rounding in the final client C0-plus-duration addition,
bool/NaN/Infinity/overflow, rollback/epoch loss, unqualified/slow/suspended clock
mapping, cancellation and final no-await delivery fences.

Publish the accepted exact contract, SYNC and versioned vectors as a bounded
Core source increment with normal independent whole/exact reviews, protected
source plus separate Final and original receipts. Then owning Core/Apple/API
implement their exact scopes and join actual paired HA/client codec proofs.
The existing v2 proofs remain historical and byte-preserved. No issuer wirev1
change, device action, new paid call or operational setup is implicit. Real
clock mapping, Activity/export/display rights, enrollment/custody, provider and
native/physical receipt remain separate gates; no closed source fixture grants
them. This proposal supplies a concrete review target, not a claim that the
initial-clock defect is already fixed in a deployed client.
