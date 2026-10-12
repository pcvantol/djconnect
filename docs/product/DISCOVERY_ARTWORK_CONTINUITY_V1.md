# Discovery artwork continuity v1 — bounded Core correction

Assignment `DJC-CORE-DISCOVERY-ARTWORK-CONTINUITY-V1-20261012`,
[selection6117357579](https://github.com/pcvantol/djconnect/issues/1101#issuecomment-6117357579).
Actual base `90fa0463bb40c705c41d4025dc53aee4de514c79`, same Core writer,
branch `codex/discovery-artwork-continuity-v1`. Presence1150/1151 remains closed.
Phase: pre-runtime contract and reproduced baseline, not delivered software.
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
Listening-profile/current qualified copies opt into the bounded reference
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

## Existing delivery and cache

Existing Discovery `image_url` remains optional and points to the existing HA
image-proxy route. A scoped opaque read capability, minted only after authorized
feed access, is bounded by reference expiry and a short delivery lease. Its
owner entry/pairing, exact resolved Profile/account/backend and Music DNA clear/
opt-in generation are checked before and after network fetch. A supplied wrong
device/bearer is rejected. Lifecycle withdrawal yields unavailable artwork without
serving old pixels or carrying state to another Profile. No new endpoint or broad
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
