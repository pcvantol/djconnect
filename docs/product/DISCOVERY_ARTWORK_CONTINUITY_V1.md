# Discovery artwork continuity v1 — bounded Core correction

Assignment `DJC-CORE-DISCOVERY-ARTWORK-CONTINUITY-V1-20261012`,
[selection6117357579](https://github.com/pcvantol/djconnect/issues/1101#issuecomment-6117357579).
Actual base `90fa0463bb40c705c41d4025dc53aee4de514c79`, same Core writer,
branch `codex/discovery-artwork-continuity-v1`. Presence1150/1151 remains closed.
Phase: local implementation and qualification; unpublished, not protected delivery.
Source and separate Finalization publication need their own exact-SHA grants.

## Reproduced boundary

The own isolated HA router ordinarily pairs a configured synthetic client,
authorizes opt-in/profile requests and invokes the actual Spotify backend,
normalizers, Music DNA manager, HA Store save/load and Discovery feed. Only
external provider network responses are bounded loopback fixtures. No Core
handler, compaction, storage or feed function is mocked. The same provider
track/album and artist each have an image after normalization, lose it at
compaction/Store, and produce eligible feed cards without artwork. The captured
[baseline](../../examples/client_contracts/discovery_artwork_v1/baseline.json)
records both positives and missing outputs. This is not live Spotify, native
Apple or installed HA acceptance.

## Optional bounded reference

The correction carries an optional `artwork` reference on exact identity-backed
provider items. It identifies Spotify, the exact subject URI, album/media URI
where supplied by the provider, one permitted CDN asset ID, original capture
and expiry. A track uses its own recording URI and its actual album edition;
an artist uses its own artist URI. An existing album item uses that album URI.
No lookup or name-based identity/artwork matching is introduced. Name-only
aggregated artist counts stay honest placeholders. Conflicting IDs/URIs, unknown
provider, missing album relation or asset, invalid clock and expiry omit artwork.

Only exact HTTPS `i.scdn.co/image/<hex asset>` provider references are accepted
for this producer path, with no credentials, non-default port, query, fragment,
encoded path, private/literal IP or alternate host. No signed URL, raw provider
object, image array or binary is persisted. URL structure is an access constraint,
not proof of entity identity: the normalized provider item establishes the binding.
The opaque asset identifier is preserved only in a temporary opt-in snapshot.
Reference TTL is at most the existing six-hour provider/profile cache lifetime;
second compaction/load never extends capture or expiry. Expired artwork is omitted.

Generic `_compact_track` callers do not automatically acquire image retention.
Listening-profile and exact server-proven accepted recommendation copies opt into the bounded reference
explicitly; historical snapshots, imports and exports do not acquire portable
artwork grants. Imports strip artwork regardless of supplied provider/expiry;
normal authorized provider refresh restores old stores with missing references.
No clear, re-pair, bulk-backfill or new provider/account/scope is required.

Temporary metadata/cover-art caching and deletion of old data follow
[Spotify terms, sectionIV.3](https://developer.spotify.com/terms) and
[compliance guidance](https://developer.spotify.com/compliance-tips).
Six hours is this existing Core cache bound, not a provider-guaranteed URL lifetime.
Spotify attribution and an exact source/media link accompany valid image output;
DJConnect retains MIT licensing and Spotify non-affiliation notices.

## Exact optional schema

The current private Store reference is `artwork` with `version:1`,
`provider:"spotify"`, `subject_uri`, `media_uri`, lowercase hex `asset_id`
(40–64 characters), numeric `captured_at`/`expires_at`, and `owner` containing
non-secret canonical `profile_id`, `backend_id`, `account_id`, `revision`.
No device/HA/provider credential or opaque delivery grant is serialized.
Expiry is at most capture + **21,600 seconds** and never extended by compaction.
Track IDs and album IDs must agree with the provider's exact URIs.

Public feed items retain existing `id`, `kind`, `uri`, reason and quality fields.
Valid artwork adds `image_url`, `image_expires_at` (UNIX UTC seconds, optionally
fractional) and `image_attribution` (`provider`, exact `media_uri`, `source_url`).
Absent/unsafe/expired data omits all three; no borrowed asset or source lookup.
`_artwork` is private transient feed-cache metadata and is removed before output.
Delivery expiry is `min(reference.expires_at, issue_time + 900 seconds)`.
At most **512** transient grants exist; expired/revoked grants are reclaimed,
and oldest grants may be evicted at capacity. No grant survives Store reload.

Image GET is headerless by capability possession, compatible with existing
Apple `AsyncImage`. Supplied identity/bearer headers must authorize the issuing
paired device. Response: `200` image; `404` missing/expired/revoked authority;
`401` explicitly wrong credentials; `502` upstream, redirect or content failure.
Timeout is **12 seconds**, streamed body at most **2 MiB**, MIME/magic limited to
PNG/JPEG/WebP. Successful responses use `Cache-Control: private, no-store` and
`X-Content-Type-Options: nosniff`. Feed TTL **86,400 seconds** is not image TTL.
No incoming bearer/cookie/provider authorization is forwarded to the CDN.
Music DNA profile withdrawal during refresh returns `409` with
`success:false,error:"music_dna_context_changed"`; no stale pre-fetch profile.

## Existing delivery and cache

Existing Discovery `image_url` remains optional and points to the existing HA
image-proxy route. A scoped opaque read capability, minted only after authorized
feed access, is bounded by reference expiry and a short delivery lease. Its
owner entry/pairing, exact resolved Profile/account/backend and Music DNA clear/
opt-in generation are checked before and after network fetch. A supplied wrong
device/bearer is rejected. Lifecycle withdrawal yields unavailable artwork without
serving old image bytes in a new server response or carrying state to another Profile. No new endpoint or broad
HA credential replaces ordinary device authentication. Legacy shared-renderer and
Ask DJ image transport remains compatible; Discovery data never enters VibeCast.

CDN requests contain no incoming device/HA/provider authorization or cookies.
Only permitted targets are fetched, redirects are refused for this scoped path,
timeouts/content types/byte sizes are bounded, and unavailable content remains a
placeholder. No binary image is stored in Music DNA or the persistent archive.
Artwork expiry/update participates in feed context invalidation, not only track
names. Cached feed reads renew valid delivery capabilities within original asset
expiry; they cannot renew removed data. No N+1 provider enrichment or refresh loop.

The existing `has_artwork` quality factor is exactly +2 for a valid available
reference; this correction restores that existing input. Eligibility, provenance,
negative feedback, deduplication, quantity and ranking algorithm are preserved.
Viewing feed/image changes no playback, queue, Session, Mood, Persona, presence,
Play Now or like history.

## Qualification and effects

Own bounded real HA lab, ordinary pairing, actual provider normalization/Store/
feed/cache and image route/decode; external provider/CDN fixtures are separately
labeled. Cover track/album/artist, missing/unsafe/conflicting/expired references,
same-name entities, save/load/second compaction, old-store refresh, fetch/save/load
failure, clear/opt-out/account/Profile changes, late responses, imports/exports,
redirects, wrong/withdrawn credentials and two isolated Profiles. Preserve owning
presence/Mood/Ask DJ/history/search/retirement/VibeCast regressions and report
per-file coverage/security. Independent technical/privacy and consumer/experience
reviews bind the final candidate, after fixes and refreshed evidence.

Early exact producer/feed/TTL/error/refresh handoff goes to Apple87 after reading
its current status. No Swift writes, second Apple writer or silent99 expansion.
Native, installed, live-provider and hardware acceptance remain separate. Existing
main workflows publish SHA-bound internal HA artifacts/formal evidence; no install,
restart, Pages/signing/hardware/service/workflow/runner/new cost route is selected.
Stop after this one Core correction and its separately gated Finalization.


## Existing Apple consumer boundary

Read-only exact Apple main `c045473a8a0eda05b0ad4824284ca50a46baf9d2`,
register87 receipt6117731869 closes99/100. Relative HA `image_url` and headerless
loads are compatible. Native currently does not decode separate attribution or
expiry fields: bronchips are not an exact clickable Spotify source link, and
server revocation cannot erase previously decoded pixels. Card/open-detail
expiry, cache clearing, opt-out/Profile/account transitions and visible attribution
need Apple-owned acceptance. This Core correction does not reopen99 or write Swift.
Native, installed, live Spotify and hardware remain **NOT_RUN**.


## Bounded explicit positives and qualification relationship

An existing accepted album item may reuse a current listening-profile track's
reference only when its album URI equals that reference's exact media URI.
Original capture/expiry and owner remain unchanged. Incoming client artwork is
ignored; missing/wrong/expired proof stays a placeholder. Current favorite
projections and name-only artist counts are not enriched by name. Historical
snapshots and exported/imported profiles do not retain artwork references.
Private-session read and persistence permissions are independently fenced;
private provider cache entries cannot become normal persistent enrichment.

This is an indirect Golden Scenario relationship: it restores a private
Discovery image projection, without changing eligibility, Runtime/Planner/
Moment/Flow/Broadcast or shared VibeCast. Existing presence/Mood/conversation/
history/search/retirement/renderer and verification-framework regressions remain
required; transport/browser proof is isolated from native/installed/hardware.
