# Automatic paired native-surface registration v1: passive source contract

The [machine-readable contract](AUTOMATIC_PAIRED_SURFACE_REGISTRATION_V1.json)
freezes the jointly reviewed passive Core/API/Apple interface. It replaces the
unimplemented single-role discovery proposal with two exact role paths.
It does not implement HTTP routes, create an acknowledged pairing epoch,
install a coordinator, authorize native SDK work or activate push.

Normal HA pairing should automatically start server-owned reconciliation.
No additional owner, Profile-role or push-approval screen is required. Device
transport A does not require a Session or Profile. A later, narrower B child
requires the real authoritative device-bound Profile/source/Session/settings.
Each role has its own original A parent under the same actual pairing epoch.

## Exact discovery and child lookup

Only these two role discovery paths are selected:

- `GET /api/djconnect/v1/surface_registration/widget_transport/state`
- `GET /api/djconnect/v1/surface_registration/status_activity_transport/state`

The contract also defines role-owned child indexes, exact original child-state
and original CURRENT B-receipt lookup. Every GET is pure and no-store. No GET
creates an epoch, child, challenge, token, job, native instruction or new lease.
Read only already-loaded real ConfigEntry data/options and direct runtime auth
fields. Do not read `runtime.config`: that property can resolve a Profile/backend.
Do not learn a device alias, warm state or call an `ensure_*` helper. Compare the
original entry/runtime/device/client-type/token/install/purpose snapshot again
immediately before serialization. Ordinary HA admin/user credentials and old
background/purpose/management credentials are not device authority.

The existing Apple `client_id == device_id` alias is explicit in this new family;
it does not recover a full native installation UUID. `installation_id` means the
already-loaded HA install identity, never a newly generated or Apple private ID.
Physical iPad is `ipados`, with ordinary paired client type `ios`. Enumeration
of Watch or Activity roles does not qualify their actual native availability.

Responses, field order, ownership and type rules are complete in the JSON.
`AUTHORITY_CURRENT` is nonsecret data, never a native capability. Never feed it
into legacy `nativePushOwner` arming. Unknown coordinates close rather than being
filled with fake UUIDs. Each original parent/child and operation remains distinct.
Expired, retired and unknown outcomes cannot silently start fresh work.

Complete state and original B-receipt HTTP responses are at most 16,384 UTF8
bytes, including wrapper and base64. Only the two explicit role-child index
routes have a 65,536-byte override, with a required finite child-count policy.
Overflow or missing policy is unavailable; do not truncate authority. Nested
receipt bodies remain at most 8,192 bytes and signature envelopes 12,288 bytes.

## Original status projection

Retain the existing status-only profile identity and its exact original native
shapes. Activity ContentState has eight fields. Widget response has five fields
and its available observation has six. Presentation `phase` is `active|ended`;
playback is separately `playing|paused|stopped|unknown`, with explicit null only
for ended playback. Do not equate an active Session with playing music.

The selected display remains status and its original last-observed timestamp,
without title, artwork, progress or currentness guarantee. Transport child/proof
metadata belongs in a separate envelope, never extra Activity ContentState keys.
Do not convert integer target generations into native presentation UUIDs, borrow
a legacy Activity token or fabricate independent tokens for shared widgets.
The status-only codec is currently Tools-only; shipping renderer/configuration
and actual native/provider receipt acceptance remain separate open work.

## Original authority and execution boundaries

Core owns real pairing capture, purpose-record ACK, immutable epoch, mutation
retirement and actual scoped child creation. Its purpose-store ACK does not prove
HA config-file durability, two-store atomicity or rollback immunity. Synchronous
retirement precedes device/token changes and unload awaits, including identity
learning during an ordinary authenticated request. Duplicate pair/status/voice
persistence does not renew a grant. Pair-only and B-scope preimages are distinct;
private credential fingerprints and raw Profile/Session values never leave Core.

Three finite original lifetime bounds and separate finite count/rate policies
remain required injected inputs, with no guessed live defaults. Known-terminal
expiry renewal is disabled until an accepted policy exists. Explicitly synthetic
policies and dependencies can qualify source behavior without granting live use.

API owns the coherent coordinator/native SQLite source package; Worker/D1 does
not become a second authoritative journal. Actual signer custody, principal,
clock, VFS/restore, TLS/provider, native transcript/key-mode/role and durable
native reservation facts are not supplied by this contract. Missing facts keep
positive execution unavailable. No new installation, paid call, native effect
or provider deployment follows from this source-only contract publication.
