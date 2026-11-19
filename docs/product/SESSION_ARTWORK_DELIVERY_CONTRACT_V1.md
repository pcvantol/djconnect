# Session artwork delivery contract v1

Canonical companion to [Session Moment artwork](SESSION_MOMENT_ARTWORK_V1.md).
Contract-first proposal for the connected implementation; not an implemented
capability assertion until qualified. Existing native/Broadcast/history schemas
remain v1 with additive optional fields and a separately advertised capability.

## Representation

An optional `session_media` projection has `schema_version:1`, stable target
`session_id`, `moment_id` or `entry_id`, opaque content-derived equality-token
`revision` (unordered; never a numeric freshness sequence), and `artwork`. The latter contains:

- `state`: `ready`, `loading`, `missing`, `expired`, `withdrawn`, `unavailable`;
  closed machine `reason`, never human prose used as a protocol discriminator.
- `subject`: provider `spotify`, type `track|album|artist`, exact provider URI;
  optional proven `album_uri` for a track, never title-based identity.
- `role`: `cover|contextual_artist|playback_thumbnail`; role is not proof of
  current or future playback. `resolution_basis`: `resolved_now` for freshly fetched pixels, independently
  of whether the Session is still open or ended; future reuse of genuinely
  captured observational pixels would require its own `observed` evidence.
- `edition_basis`: `original_bound` for an exact original album subject or a
  track matched to its retained original album URI; `provider_resolved_now` for
  an old exact track without retained album identity; `not_applicable` for artist
  imagery. An artist image has no album edition.
- `source_url`, `attribution` (provider, mark, exact linked subject), `usage_basis`;
  `captured_at`, original `expires_at`, `media_revision` and optional relative
  managed `url` only while admitted. Never forward provider credentials.
- independent `current_display_allowed`, `active_flow_display_allowed`,
  `historical_display_allowed`; `cache_policy:no-store`, `crop_allowed:false`.
  An archive image grant grants no current Moment display or playback claim.

A ready image always has complete provenance and an actual validated byte
resource. A prepared body with missing publication/authority is not ready.
Clients compare revisions for equality, never sort hashes; preserve the existing
ordered transport/lifecycle boundary and discard late responses for superseded
requests or withdrawn targets. Clients clear URL and decoded pixels on
expiry/revision/withdrawal. Unknown
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
Existing Profile storage commits immediately collect revoked resident resources
and latch pending preparations invalid. A temporary withdrawal followed by
reassignment cannot revive earlier bytes or an in-flight preparation; a new
explicitly authorized preparation must qualify independently.

Batch preparation has a final synchronous delivery fence after all preparation
and authorization awaits. It revalidates every returned resource and its actual
current/flow/history scope without another await; an early ready target cannot
keep a stale current grant while another target is pending. This fence preserves
the original resource, media revision and expiry rather than resolving again.

Existing historical storage transactions notify the same RAM image owner before
and after Profile purge, entry removal, source withdrawal and retention cleanup.
Scoped barriers prevent matching entry grants during the destructive await;
pending work is invalidated on both boundaries, including failed transactions.
At most eight scopes of at most250 entry IDs are retained; overflow fails closed
for entry grants until outstanding scopes finish. Provider withdrawal matches
the original provider entry; retention uses the actual historical Session header
creation time or the entry's original retained-until deadline. Other Profiles
and independent live Moment grants are preserved. No event journal, persistent
image store, schema migration or second owner is introduced.

Pure owner snapshots/history may project existing prepared media or a typed
unavailable state, never fetch/prepare/renew. Explicit preparation may perform
provider work and returns per-target states. Errors remain normal400/401/403/404/
409/503 application outcomes; one source failure must not remove valid text.
Byte delivery uses a short unguessable managed capability bound to original
owner, source/account/revision, target, subject and applicable audience. The image route requires the same normal paired-device authorization and Profile
identity as other owner reads; the asset ID alone grants no access. No
unrestricted URL fetch, shared-screen exposure or HA-admin credential fallback.
No separate client image lookup, second WebSocket action family or new eventbus.

## Bounds and storage

At most8 requested targets,2 simultaneous preparations,64 prepared target slots,
32MiB aggregate compressed resident-byte budget,2MiB per image,4096px per side and
16million pixels; reject mismatched MIME/magic/invalid decode and animation.
Timeout8s per external operation, bounded complete preparation deadline20s;
negative backoff60s, original asset TTL at most300s and grant at most300s. Cache
hits and reconnect never slide either deadline. Identical in-flight target work
is shared; target replacement invalidates late results. Capacity rejects safely
rather than silently retaining unlimited assets. Decode workers are limited to two; their temporary pixel RAM is measured
separately from the compressed resident-byte budget. Resource-expiry callbacks
in the existing HA loop dispose pixels without provider work; Session end and
last-entry unload explicitly clear their scoped resources. No headers/cookies/credentials
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


## Independent passive cover qualification

[Passive Session projection v1](PASSIVE_SESSION_PROJECTION_V1.md) adds a separate
explicit paired-owner surface grant. This private owner contract remains
`no-store`; its image URL, prepared resource or historical permission is never
an OS/App Group/Activity grant. The passive read independently qualifies only
exact covers/metadata, original source/capture and display deadlines, all links/
marks and cache/locked-display consent. Artist photographs remain unqualified
for passive OS retention; do not copy Forecast/Discovery/private art grants.

The same RAM media owner retains original `captured_monotonic` alongside its
existing immutable deadline. Passive cover validity requires both original
monotonic capture+120seconds and original UTC/source/presentation limits; a
backwards wallclock, fresh same-track observation or new consent cannot renew
old pixels. Legacy RAM assets without that proof are unavailable to passive
reads. No additional pixel store, downloader, source/provider or history cache.
Existing observation/explicit owner preparation does the work; passive read and
image GET never prepare, fetch or renew. Native rich/background/Watch adoption
and physical acceptance remain separately owned/open.


## Retained Flow parity refinement — owner instruction17October

Read-only historical Sessions retain the same semantic richness as active Flow.
An admitted DJMoment with an exact original artist/album/recording identity and
captured source/account binding retains that compact media reference alongside
its accepted body. This applies to qualified CC0 contributions and temporary
owner-metadata narration alike. No CDN URL, artwork bytes or provider payload is
archived. The existing explicit entry-target media preparation resolves that
original subject again, with current provider permission and temporary no-store
pixels. It does not substitute current playback, search a historical name, change
history revisions or restore Runtime. Native UI remains consumer-owned.

A genre fact with one exact source artist resolves artist art; an exact album
edition/callback resolves that album. A typed revisit Recommendation targets its
earlier recommended recording, never the currently playing recording's cover.
Unqualified or identity-poor historical entries stay explicitly unavailable.
Old rows lacking an original subject/account binding receive no guessed backfill.
Source withdrawal, reassignment, Profile privacy, Session deletion/retention and
expiry invalidate pending and prepared image grants before bytes can be read.

## Owner-requested artist photography extension — 19 October

The delivered version1 Spotify contract remains unchanged. Explicit version2
preparation adds subject-bound artist/band photography and licensed Commons
fallback with full photographer/rights attribution, within the existing media
owners. See [Session artist photo v2](SESSION_ARTIST_PHOTO_V2.md). Producer and
consumer/native qualification are separate and still OPEN.
