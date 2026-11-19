# Installation first key and original host-wake deadlines

This is the owning Core bootstrap contract for the existing rich surface's
content-free host wake. It creates no operational enrollment or device grant.
The first App Attest key is an installation operation before Core `prepare`:
`prepare` already requires its genuine 32-byte SDK key identifier. Requiring an
enrolled key or a Core Session/push purpose before that first operation would
make bootstrap circular.

## Concrete local custody boundary

The Apple owner captures an actual local operator intent under the reviewed
signing/install/first-key effect plan, the selected physical installation's
original identity and generation, the exact signed artifact, and the actual
on-device task/lifecycle and SDK support. The effect owner is private local
runtime custody. It has no JSON/Codable affirmative constructor; an incoming
pairing body, QR key, matching hash or `approved: true` cannot instantiate it.
Core supplies no first-key permission endpoint or replacement local owner.

Before SDK scheduling, the same installation records a unique durable SDK-start
claim and its parent-directory durability. The original task and installation
generation remain current immediately before `generateKey` and at callback.
Only the original canonical SDK result, decoded to exactly32 bytes, becomes the
installation's key-reference DATA. It is not a native verification receipt,
clock qualification, operator enrollment or push capability. The private key
stays in the OS; no export, account/key search or QR-key fallback is introduced.

Lost response, cancellation, process restart or missing original custody yields
UNKNOWN/CLOSED. It does not automatically call `generateKey` again, clear the
claim or manufacture a new installation generation. Any separately authorized
recovery preserves the earlier outcome and its own actual target/authority.
The OS/profile must genuinely support the explicit App Attest environment;
APNs environment, DEBUG, get-task-allow and local key existence do not establish
that environment or the eventual attestation certificate's category/AAGUID.

Signing, profile/capability changes, installation, launch, key creation and proof
submission are distinct concrete effects. Their actual candidate, profile and
target must be reviewed under current human effect authority. This source
contract and connecting a device are not substitute effect authorizations.

## From key reference to genuine enrollment

After the first key, the real paired owner requests Core `prepare` with the
original SDK identifier and APNs token digest. The actual API's existing role
and pending/enrolled native state select immutable `native_proof_kind`.
The client never derives attestation/assertion choice from local key presence.
Core retains the issuer ACK, prepared SQLite ACK and original warm RAM before
publishing the prepared tuple. Private capabilities and API job IDs stay server
side. The retained R31 transcript gains no fields.

The original challenge and kind must match before one durably claimed native
proof operation. The real local effect owner checks the original installation,
signed host, task/lifecycle, supported SDK and its own original local resource
window before SDK entry and callback. Only the API's genuine certificate,
AAGUID/category, key/counter, policy and original nonce verification can admit
the result. Only a distinct durable target-registration ACK means registered.

## Clock ownership and exact guarantee

API owns the UTC deadlines for issuer, challenge, verification, registration
and dispatch. It rejects an issued timestamp later than its ORIGINAL request
capture and enforces expiry no later than original issued time plus the approved
cap. Later callbacks, later UTC observations and status cannot move those bounds;
actual current UTC and the independent SQL guards still apply at every effect.
Core retains its genuine live context and its own original wall/monotonic
ceilings, including the child's shorter wake ceiling after prepared handoff.
Core also retains an independent 30-second local proof-submission resource
ceiling from the original challenge request's pre-body wall/monotonic capture.
Challenge replies and fresh complete requests cannot restart it. The same
ceiling guards SQL claims/ACKs and HTTP disclosure; earlier acknowledged pending
verification can still be checked by status. Passing this local check does not
establish API nonce currentness or native admission.

Apple captures one actual ContinuousClock root before the first authorize and
uses only that local clock/domain for elapsed local resource checks. Related
contexts/rotations retain the minimum ORIGINAL local ceilings; loss or restart
is closed. It never converts received remote UTC or remaining TTL into a new
local deadline. No cross-OS rate factor, rho=1 assertion, receive-time reanchor
or generic clock-qualified boolean is used as authority.

The guarantee is local-current/once-at-start SDK custody and server-only
admission of its result. It does **not** claim that a local SDK call can never
start after an unknowable remote expiry: a delayed challenge can outlive its
API window while a separate local resource window is still open. Such a result
must be rejected by API without enrollment/registration or a replacement nonce.
A strict no-SDK-effect-after-remote-expiry claim would additionally need a real
clock/roundtrip bound; that stronger claim is not made by this contract.

Provider queue timing and actual device presentation before expiry are not
promised. APNs expiration retains the API-owned original deadline. The accepted
stale OS play-status observation grants no new server permission. This is one
rich surface with field-specific evidence/rights, not another reduced product
variant. Private Moment/artwork/licensed-field expiry or immediate revocation
requirements keep their existing separate gates; they are not relaxed here.

The first-key source, Core routes, actual receiving composition, native SDK
execution, provider receipt and installed user acceptance each retain their
own normal review, protected delivery and qualification. Synthetic operators,
keys or callbacks qualify no real native or provider action.
