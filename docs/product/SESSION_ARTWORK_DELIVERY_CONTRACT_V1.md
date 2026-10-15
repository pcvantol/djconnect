# Session artwork delivery contract v1

Canonical companion to [Session Moment artwork](SESSION_MOMENT_ARTWORK_V1.md).
Contract-first proposal for the connected implementation; not an implemented
capability assertion until qualified. Existing native/Broadcast/history schemas
remain v1 with additive optional fields and a separately advertised capability.

## Representation

An optional `session_media` projection has `schema_version:1`, stable target
`session_id`, `moment_id` or `entry_id`, monotonically changing content-derived
`revision`, and `artwork`. The latter contains:

- `state`: `ready`, `loading`, `missing`, `expired`, `withdrawn`, `unavailable`;
  closed machine `reason`, never human prose used as a protocol discriminator.
- `subject`: provider `spotify`, type `track|album|artist`, exact provider URI;
  optional proven `album_uri` for a track, never title-based identity.
- `role`: `cover|contextual_artist|playback_thumbnail`; role is not proof of
  current or future playback. `resolution_basis`: `observed|resolved_now`.
- `source_url`, `attribution` (provider, mark, exact linked subject), `usage_basis`;
  `captured_at`, original `expires_at`, `media_revision` and optional relative
  managed `url` only while admitted. Never forward provider credentials.
- independent `current_display_allowed`, `active_flow_display_allowed`,
  `historical_display_allowed`; `cache_policy:no-store`, `crop_allowed:false`.
  An archive image grant grants no current Moment display or playback claim.

A ready image always has complete provenance and an actual validated byte
resource. A prepared body with missing publication/authority is not ready.
Clients clear URL and decoded pixels on expiry/revision/withdrawal. Unknown
optional schema degrades to existing text-only card. Five-language alt text is
presentation copy, distinct from stable subject/provider/protocol identifiers.

## Authority and routes

Owner preparation uses an explicit versioned `POST /api/djconnect/v1/session/media/prepare`
with normal device pairing/Profile resolution and `contract_version:1`, exact
`session_id`, bounded `targets` (at most8, each `moment_id` or `entry_id`). No
caller-supplied subject, source URL, account, CDN URL or archive permission.
Source proof is selected from the authorized published Runtime/retained record.
Wrong Profile is denied, hidden/deleted/expired entries unavailable. Recheck
normal owner/source authority after every external await and at byte delivery.

Pure owner snapshots/history may project existing prepared media or a typed
unavailable state, never fetch/prepare/renew. Explicit preparation may perform
provider work and returns per-target states. Errors remain normal400/401/403/404/
409/503 application outcomes; one source failure must not remove valid text.
Byte delivery uses a short unguessable managed capability bound to original
owner, source/account/revision, target, subject and applicable audience. No
unrestricted URL fetch, shared-screen exposure or HA-admin credential fallback.
No separate client image lookup, second WebSocket action family or new eventbus.

## Bounds and storage

At most8 requested targets,2 simultaneous preparations,64 prepared target slots,
32MiB aggregate decoded-source byte budget,2MiB per image,4096px per side and
16million pixels; reject mismatched MIME/magic/invalid decode and animation.
Timeout8s per external operation, bounded complete preparation deadline20s;
negative backoff60s, original asset TTL at most300s and grant at most300s. Cache
hits and reconnect never slide either deadline. Identical in-flight target work
is shared; target replacement invalidates late results. Capacity rejects safely
rather than silently retaining unlimited assets. No headers/cookies/credentials
forwarded to CDN; exact HTTPS `i.scdn.co/image/<hex>` only, redirects denied.

Persistent history stores only optional versioned minimal exact subject and
original source binding, if the entry's independent retention basis allows it.
No binaries, full providerpayloads, CDNasset/grant/URL, new user history or
Performance Memory. Old records are not bulk rewritten; reliable exact track
source URLs already stored may support explicit resolution. No arbitrary
name-only or absent-identity backfill. Retention/deletion/withdrawal governs
references and all derived RAM grants; no schema migration is needed for optional
fields in existing versioned JSON bodies. Reads retain old-store compatibility.

## Required invariants and examples

A track has URI `spotify:track:<22charID>` and fetches only that exact item; its
returned album ID/URI must agree. An album fact's source album URI must agree
with fetched edition. Artist cross-reference is explicit and unique; no image
of another contributor or borrowed current artist. An old row's exact source
URL may establish track identity, but a title alone never does.

Publication and summary are immutable. Image preparation cannot publish a
Moment, alter history ordering/revision as a semantic event, consume Presence,
start playback, replace Session or invoke a model. Media revisions are separate.
Terminal/new Profile invalidates current grants; new historical grant requires a
fresh original source/retention check. Failure and late completions preserve
these invariants. Fixtures and final producerpin will be handed to existing
Apple#87 without initiating or expanding its WIP. Native visible adoption and
joint acceptance remain OPEN until Apple supplies actual proof.
