# VibeCast owner refinements — current-slice extension

Parent: `DJC-CORE-VIBECAST-MULTIMOMENT-TIMELINE-V1-20261006`.
Qualification: `DJC-VIBECAST-MULTIMOMENT-PI-CAPTURE-V1-20261006`.
Base: `40763f7e829802da4bce815702da675f944f3b46`.
Status: implementation candidate, verification and protected delivery pending.

## Admission and history

The owner rejected the sparse physical experience and explicitly requested
implementation of the listed content/UI functions within this slice. This is
one Core increment; completed source #1118 and Finalization #1119 stay closed.
The exact-candidate physical baseline remains PARTIAL: real same-track Genre
and Track cards were captured, but grammar, grounding, motion and normal end
were not fully accepted. Evidence remains private under the ignored Pi run.
The ACK and first material change are registered in #1101.

## Genuine current-track facts

`session_facts.py` normalizes typed `QualifiedSessionFact` evidence. Planner
chooses available independent angles; Knowledge validates source/subject,
freshness, locale and attribution; Moment produces deterministic copy; the
existing Runtime publication appends Flow and Presentation/Broadcast output.
Provider payloads, Profile data and credentials never become cards. No direct
AI service, paragraph splitting, synthetic playback, type carrousel or new
persistent knowledge store is introduced.

| Producer | Exact identity / qualified display fields | Rights and attribution | Missing/ambiguous result |
| --- | --- | --- | --- |
| Current Spotify `/me/player` catalog | Track URI, album URI, album name, release date and precision, ISRC, track artist IDs. Current-edition date only, never inferred original release. | Metadata display, unchanged public title and service link plus official full logo. No model training, AI rewrite or spoken credit use. | Invalid identity/date/precision suppresses album card. |
| MusicBrainz ISRC lookup → recording → artist/work relationships | Exactly one ISRC recording; exact version title and credited artist names; exact MBID lookup. Explicit producer/instrument/vocal roles, one linked work's composer roles; artist life-span start and type. | Core data including relationships is CC0. Resource link and MusicBrainz attribution retained. Tags, annotations, ratings, search indexes and edit history excluded. | Multiple recordings, artist/version mismatch, unknown roles, multiple works or malformed IDs yield no associated facts. |
| MusicBrainz artist URL relation → Wikidata entity | Exactly one linked QID, reciprocal P434 equal to that exact artist MBID. Existing localized short description only. | Structured Wikidata CC0 data, entity link and attribution. No Wikipedia article prose. | Missing reciprocal identity, description or locale yields no description card. |

Rights qualification is limited to these exact public catalog/core-data fields
and deterministic visual cards. It does not alter the older fixed inventory
or mark all Artist/Album/credit sources eligible. The Phase A
[Credits Source Contract](CREDIT_PROVENANCE_SOURCE_CONTRACT.md) remains the
baseline; this is the narrow implemented producer/consumer qualification
extension, requiring tests and renderer evidence before delivery acceptance.

Public source requests use a descriptive User-Agent, one HA-wide serialized
rate limiter (at least1.1s between requests), at most four requests per observed
track, a35s total lookup budget,8s request timeout, bounded512KB response and
429/503/Retry-After/maxlag backoff. No account, paid API or credential is needed.
Only public catalog identifiers are sent. Raw responses are discarded; facts
expire after30min and live only within the active Runtime. Rendered source cards
are deliberately excluded from the existing durable Moment-history projection;
Session lifecycle history remains. No future historical-display qualification
is inferred. Source links are
renderer-safe public attribution, never private provider responses.

### Cadence and cancellation

Up to six available distinct facts per observed track, one at a time, with at
least35s observed playback spacing and a minimum40s readable card lifetime.
Longer text increases dwell up to90s. At least45s remaining is required for a
later card. A repeated source/subject/angle is suppressed across the Session;
separate complete artist description and birth/formation fact may share a
Moment type because their content is independent. No quota is filled with
fabricated or repeated text. A track without qualified facts retains the
previous two-Moment Track Insight boundary; its interpretation is not a credit
source. Initial observed playback may now produce a qualified fact without
waiting for a track change. Empty initial evidence only establishes baseline.

Fresh actual Spotify observations drive eligibility, never display clock ticks.
Existing seek, pause/resume settling, source/item change, generation, stale
observation, stop/end/unload controls remain. Late source results must still
match the current Session/item. Queue data does not become Planner future-track
knowledge or a playback command.

## Up next

The observer reads the same authorized Spotify account's `/me/player/queue`
with a30s ephemeral cache. Only `queue[0]` is eligible after exact
`currently_playing.uri` correlation to the current observation. Episode,
unknown, failed, stale-item or empty results are hidden. Only public title,
artist and proxied artwork plus hashed current-item binding enter Broadcast.
The renderer hides Up next after end, track mismatch or missing data. It does
not fetch Spotify, reorder or mutate playback.

## End from an approved screen

HA options default `vibecast_session_end_allowed=false`. Explicit owner opt-in
plus the ordinary authenticated handoff approval may issue a separate
high-entropy end-only grant for that exact Profile/Session. Collection uses the
existing browser claim secret and no-store/no-referrer route. The grant stays
in browser memory, never URL/storage/snapshot/logs; legacy Broadcast-only
connections retain their existing read-only authority.

`POST /api/djconnect/v1/session/broadcast/control/end` accepts only that grant
and exact Session. It is single-use, expires after one hour, is revoked at end
and owner-entry unload/reload (including non-Spotify Sessions) and carries no other command/owner access. The end endpoint also checks that the approving entry is still loaded with its opt-in enabled. The X
appears only when a grant was delivered. Backend confirmation or terminal
Broadcast moves the screen to idle. Failure remains visible; local success is
not simulated. New handoff is required after authority expires/revokes.

## Rendering and languages

Bold local HH:mm clock replaces the header brand; album follows artist; mood
and repeated footer metadata are removed. Portrait artwork increases from400
to600px at1200×1920, preserving the complete original image. Background gradients
use sampled artwork colors, not a cropped/blurred displayed image. Progress and
time grow. Actual cards fade out/in in finite animations; no fake timed Moments.
Whole cards use playful safe bubble regions above/below portrait artwork and
beside landscape artwork. Reduced motion disables movement and automatic scroll.
Long copy stays bounded and readable; title, artwork, source and footer must not
overlap. Up next uses actual queue metadata only. User-facing controls/copy
support `en`, `nl`, `de`, `fr`, `es`; missing source-language text is suppressed.

## Lifecycle repair

Persistent crash-leftover reconciliation runs once per HA process under the
singleton bootstrap lock, before entry business services. Subsequent entry
setup or last-entry options reload must preserve live Runtime lifecycle.
Real HA restart still marks OPENING/ACTIVE crash leftovers INTERRUPTED;
historical INTERRUPTED remains terminal. End removes observation/opportunities
only after persistence succeeds. No Store edit or permissive terminal rewrite.

## Delivery gates

Meaningful source/identity/date/rights/cadence/cancellation, end authority,
queue and multi-entry/restart tests; portrait1200×1920 and landscape1920×1200
browser visual acceptance and motion; independent review; protected source PR;
exact-effect internal publication/HA-dev installation permission before those
actions; bounded fresh physical acceptance if installation is authorized;
separate mandatory Finalization. No production deployment or public release.
Static PNGs alone never prove motion. All raw physical evidence stays private.

## Primary references

- [Spotify playback schema](https://developer.spotify.com/documentation/web-api/reference/get-information-about-the-users-current-playback)
- [Spotify queue](https://developer.spotify.com/documentation/web-api/reference/get-queue)
- [Spotify policy](https://developer.spotify.com/policy) and [design/attribution](https://developer.spotify.com/documentation/design)
- [MusicBrainz API](https://musicbrainz.org/doc/MusicBrainz_API), [rate limiting](https://musicbrainz.org/doc/MusicBrainz_API/Rate_Limiting) and [core/supplementary data licenses](https://musicbrainz.org/doc/MusicBrainz_Database)
- [Wikidata data and API guidance](https://www.wikidata.org/wiki/Help:Linked_Data_Interface)
