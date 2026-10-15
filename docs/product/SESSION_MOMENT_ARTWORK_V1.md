# Session Moment artwork v1

Assignment `DJC-CORE-SESSION-MOMENT-ARTWORK-V1-20261014`, selection
[6175336907](https://github.com/pcvantol/djconnect/issues/1101#issuecomment-6175336907),
refinement [6176704119](https://github.com/pcvantol/djconnect/issues/1101#issuecomment-6176704119).
Design-first implementation increment; qualification and delivery remain pending.
Actual admission base `f0a7ff4bb878247db9ab25c4a22320f17d806cd6`, same Core writer,
branch `codex/session-moment-artwork-v1`. Hybrid1170/1171 stays closed.

## Experience and ownership

A published contribution owns its image subject. A track contribution uses its
exact recording/album edition; an album contribution uses that edition; an
artist contribution uses that artist, including when another recording is now
playing. A playback observation is a compact row, never a new DJMoment.
Missing art leaves text/actions usable without a large empty rectangle.

Core owns subject, provenance, authorization, media revisions and bytes. Apple
owns one shared decoder/loader/card implementation for Mac/iPhone/iPad under
`DJC-APPLE-SESSION-MOMENT-ARTWORK-V1-20261014`. No Swift or receiver writes here.
[The delivery contract](SESSION_ARTWORK_DELIVERY_CONTRACT_V1.md) is canonical for
fields, routes, clocks and limits. Existing Moment text, semantic identity,
chronology, summary counters, Mood, Persona, Presence and Planner remain owners.
No model, new scheduler, second image/history store or Music DNA opt-in.

## KEEP / REUSE / FIX / RETIRE

| Existing owner | Disposition and delta |
| --- | --- |
| Spotify observation/normalizers | REUSE exact catalog IDs/album relation; preserve minimal subject proof before hashing item identity. |
| `session_facts` | KEEP content qualification; FIX artist image identity with explicit provider cross-reference, never rendered name inference. |
| Runtime/Moment/Flow/Broadcast | KEEP immutable contributions and budgets; ADD a separate owner media projection/revision after publication. |
| `forecast_imagery` / `discovery_artwork` | REUSE exact CDN validation, original expiry and authority fences; their existing grants stay scoped to Forecast/Discovery. |
| Shared image proxy | REUSE managed HA delivery infrastructure; no portable unscoped proxy token as a Session/archive grant. |
| Persistent Session/history/query | KEEP authoritative records and pure paging/search/open; ADD only qualified compact subject/source references, no bytes/delivery URLs. |
| Legacy Moment `artwork.url` | KEEP backwards compatibility; RETIRE treating the current playback image as a contribution's independent subject proof. |
| Apple rendering | Existing consumer-owned adoption; Core supplies optional versioned projection and fixtures, older clients stay text-only. |

## Source and older-entry decision matrix

| Subject and evidence | Current / active flow | Historical resolution |
| --- | --- | --- |
| Exact Spotify track URI and provider-returned album edition | Qualified cover, link/mark required | Explicit bounded refresh under original valid source/account; new pixels are current enrichment. |
| Exact Spotify album URI | That edition's cover | Same rules; never choose a remaster by title. |
| Artist fact with exact Spotify artist cross-reference from the qualified MusicBrainz URL relation or reciprocal Wikidata identity | `/artists/{id}` photo, contextual role, source link/mark | Only if that compact subject reference and original source binding were retained under the entry's independent archive permission. |
| Old Spotify playback row with exact original Spotify track source URL and retained source binding | Not a current playback assertion | May resolve exact track and its returned edition; mark `resolved_now`, never `captured_then`. |
| Old Moment without exact retained subject / absent source/account | Text remains governed by existing history owner | `unavailable: insufficient_identity` / `source_withdrawn`; no name lookup or current-image substitution. |
| Music Assistant or other unqualified image source | Typed unavailable | No speculative adapter or broad web scraping. |

Spotify display is temporary application rendering with exact source links and
visible Spotify attribution, not image ownership or an unrestricted archival
license. Only compact identity/source references survive where existing entry
retention permits; image bytes and CDN URLs do not. Sources: [Developer
Terms](https://developer.spotify.com/terms), [Compliance
Tips](https://developer.spotify.com/compliance-tips). Public metadata licenses
such as CC0 never grant rights in a picture. No Commons/Wikipedia image is
admitted merely because an entity has a P18 field. This slice first reuses the
existing Spotify source; additional adapters require their own explicit image
qualification, not a generic URL fallback.

## Lifecycle, races and UX

1. Normal playback/source acceptance captures exact identity; publication does
   not wait on art. Only actually published non-Silence contributions are eligible.
2. Existing observation work or explicit owner preparation resolves a bounded
   target. A late result rechecks Profile, source/account, Session/entry and
   subject. A changed current track cannot relabel the original contribution.
3. A separate media revision updates the same contribution/entry; no new Moment,
   position, text rewrite, Presence charge or history summary increment.
4. Session end removes live-only grants. Historical preparation independently
   validates retained entry, current original source authority and archive rights.
5. Expiry, withdrawal, deletion, Profile/reassignment or source changes invalidate
   URLs and client-decoded pixels. Reconnect/read cannot extend an old grant.
6. Cancellation, timeout/429 and failed decode become bounded fallback/backoff.
   Retrying a read never starts provider work. No bulk startup backfill.

Apple keeps the same row/card identity and scroll/draft/selection. Cover/photo
alt text and unavailable states use en/nl/de/fr/es presentation. Respect image
aspect ratio, avoid unsupported crops/overlays, keep source link/mark visible,
and support VoiceOver, larger text and keyboard. Text and controls remain usable
while loading or when image permission is withdrawn. Shared VibeCast stays
text-compatible and receives no private history/image grants under this slice.

## Qualification and gates

Required positive real isolated HA cases: exact cover, contextual artist A while
B plays including late completion, and explicit successful older-entry refresh.
Negative: remaster/ambiguous/missing identity, wrong Profile/account, withdrawn
source, expiry, Session end, cancellation/429/unsafe/oversized/decode failure.
Ordinary pairing, actual Runtime/publication/Store/query/image route; fixtures
only at external provider/CDN boundaries, never injection of a ready public URL.
Measure text latency separately from art, provider requests, memory/bytes and
negative/in-flight dedup. Reads/paging/search/reconnect must have zero provider
requests and no music/history mutation. Preserve existing transport, presence,
Mood, Forecast, Ask DJ, Track Insight and history suites. Independently review
technical/privacy and product/visual contract on exact candidate after fixes.

Core software, Apple native, installed and joint/hardware evidence are separate.
No all-fallback or JSON-only product PASS. Any required unqualified source subset
stays explicitly OPEN. Source and separate Finalization retain exact publication
gates; latest direct owner installation instruction applies after qualification,
not to an unreviewed local candidate. No next productslice within this assignment.
