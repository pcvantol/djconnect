# HA installation-management preparation v1

`POST /api/djconnect/v1/installation/{entry_id}/management/prepare` captures
an original, current Home Assistant administrator decision for one selected
loaded DJConnect entry. It prepares a later management step; it cannot generate
or use a key, establish installation/service custody, enroll with API, or enable
push. It adds no per-device setup screen or device-pairing requirement.

## Authentication and context

The route uses the actual HA HTTP authentication middleware and independently
revalidates one explicit `Authorization: Bearer <normal HA access token>`. The
same actual AuthManager, refresh-token object/ID and user must match middleware.
Only an active, non-system administrator with a normal HA refresh-token session
is accepted. Long-lived access tokens, device pairing tokens and signed URLs
do not qualify. A normal token does not prove fresh human presence or MFA.

The selected ConfigEntry and runtime must remain the exact loaded, enabled,
non-retired objects, with unchanged original data/options objects and existing
`ha_install_id` metadata. No installation ID is generated or promoted into a
global trust root. Administration is independent of transient Profile/Session
state. Later display/read admission must check its own original scopes.

## Closed request and preparation-only reply

No query, content encoding, extra JSON fields, duplicate JSON keys or invalid
UTF-8 are accepted. The JSON body is at most 4,096 bytes, read within five seconds:

```json
{
  "contract_version": 1,
  "operation_id": "00000000-0000-4000-8000-000000000001",
  "action": "prepare_custody",
  "policy_id": "software_p256_ha_file_v1",
  "acknowledgement": "preparation_only_no_key_effect"
}
```

The operation must be a canonical lowercase UUIDv4 for this original attempt.
The fixed policy name selects no filesystem path, key or executed configuration.
An accepted reply has exactly `success:true`, `contract_version:1`,
`state:"prepared"`, `classification:"HA_ADMIN_PREPARATION_ONLY"`, the original
`operation_id`, an opaque `djcmgmt_…` RAM handle, integer `expires_at_ms`, and
`execution_available:false`. Responses are `no-store`. No authorization value,
user, Profile, selected entry data, key material or raw request is returned.

The original wall/monotonic pair is captured before the first await. Preparation
lasts at most 120 seconds and closes on either original bound, rollback,
cancellation, token/user changes, unload, shutdown or selected-context changes.
Every body-read await is followed by a currentness check; a final synchronous
check follows reply serialization. No await separates that check from return.

Real runtime retirement closes pending and prepared management scopes before
temporary-entry or token mutation. Restoring the previous entry cannot revive
them. Cleanup failures cannot preserve sibling scopes. HA public config updates
create new immutable mapping objects; restoring equal values cannot restore an
original captured mapping. Neither mechanism creates positive pairing authority.

The per-HA-process RAM registry allows 16 pending requests and 64 original
operation slots. Original slots are not evicted or reset after expiry; duplicates
are `409`, capacity is `429`. Invalid requests are `400`, authentication/admin
failures `401`/`403`, unavailable selected entries `409`, retired originals `410`,
oversize `413`, body timeout `408`; unavailable implementation context is closed.
The bounded RAM handle is not a durable once acknowledgment or recoverable
capability. A restart cannot restore it. There is no execution endpoint.

## Actual validation and remaining integration

The committed example receipt binds actual isolated HA AuthManager users,
normal/long-lived/system tokens, middleware, ConfigEntryStore/runtime and the
real OptionsFlow temporary-entry/finally-restore path. Rotation's provider port
is a bounded synthetic failure; no network, real key or provider action occurs.
The identical test fails against the exact pre-hook admitted source and passes
after synchronous retirement. Original setup and runtime failures are preserved
separately. This is not installed, native, provider or product acceptance.

Real managed storage/signer lifecycle, actual installation/principal trust,
separate approved key/enrollment operations, canonical authenticated receiving
and rich read/start/artwork wires, qualified cross-domain clocks and native
push acceptance remain open. Any later effect must first use the existing
original durable SQL19 lifecycle; this preparation cannot replace it or become
`CustodyOperationOwner`. Ordinary automatic device pairing grants none of these
installation-management or provider rights.
