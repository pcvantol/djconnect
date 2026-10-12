# Ambient fact → Session Moment convergence v1

Assignment: `DJC-CORE-AMBIENT-FACT-MOMENT-CONVERGENCE-V1-20261012`.
Owner selection: [Core register](https://github.com/pcvantol/djconnect/issues/1101#issuecomment-6125691006).
Admission base: `de0e1fccbfdb0f8ffc5a58c77c209919f4cf00de`.
Status: pre-runtime disposition; implementation and qualification pending.

## Reproduced baseline

An isolated HA 2026.10 instance used the ordinary configured-slot → HTTP pairing
handler → minted device bearer → `/api/djconnect/v1/status` chain, the real
Spotify normalizer and real Ask DJ/Music DNA HA Stores. Only external Spotify,
HA conversation-provider and Wikipedia responses were explicit synthetic
fixtures. No HA user credential, installed instance or live provider was used.

With no active Session, the first status read generated one unsolicited fact,
looked up one Wikipedia summary/image and appended one assistant system card
to each of two existing generic HA-user histories. The existing Profile
namespace received none. A repeated artist/album name suppressed a second
generation; an album-name change generated another. With Music DNA disabled,
`last_ask_dj` stayed absent; after explicit opt-in, the next passive status read
stored `ambient_music_fact` as the last Ask DJ interaction with no user question.
Reopening the actual history Store retained those writes. These observations
establish the isolated producer behavior, not the installed Apple provenance.

The same paired HTTP client exercised the existing generative Track Insight
route. Its model response produced summary/full-text interpretation and genre,
with deterministic listening/arrangement fallbacks. It supplied no typed
source identity, rights, expiry or fact qualification. That useful interpretive
surface cannot prove an asserted formation year, credit or chart achievement.

## Per-claim disposition

The migration reuses already maintained Session content. It does not convert
unverified old prose or a Wikipedia image result into qualified knowledge.

| Old content family / claim | Existing eligible Session basis and form | Missing bounded connection | Disposition / remaining gap |
| --- | --- | --- | --- |
| Artist formation/birth date and group/person type | Exact MusicBrainz artist linked from a uniquely matched recording; typed life-span/type → Artist Moment | None in the current qualified producer | Reuse existing dated Artist fact, subject/type semantics and attribution; an arbitrary model biography is ineligible. |
| Short artist identity/context description | Exact reciprocal MusicBrainz MBID ↔ Wikidata QID and existing localized CC0 description → Artist Moment | None | Reuse unchanged descriptor with source. Missing language or reciprocal identity gives no fact. This is not license to rewrite a Wikipedia biography. |
| Album release date | Exact current Spotify track/album URI and release precision → Album Moment | None | Reuse current-edition display fact. Original-release, reissue and remaster narratives need separate evidence; title matches do not qualify them. |
| Recording producer, instrumental or vocal contributors | Unique ISRC recording, exact version title/artist match and explicit MusicBrainz roles → Track Moment | None | Reuse typed credits and full attribution. Do not infer a producer from fame, sound or artist membership. |
| Composition attribution | One qualified linked work and typed MusicBrainz composer relationships → Track Moment | None | Reuse existing work fact; unknown/multiple work identity stays ineligible. |
| Sound, genre and listening context | Existing Track Insight / qualified existing Genre interpretation → Track/Genre Moments selected by the existing Planner | None for interpretation | Preserve interpretation as interpretation. Generated prose is not a new historical, cultural or technical fact source. |
| Connections to an earlier contribution | Existing separately delivered Genre→Track, shared-producer and published Album→current Track contracts | None within those exact bounded relations | Reuse only their published evidence and identity rules; no generic anecdotes or new relation family. |
| Singles, chart success, awards, cultural importance, historical impact, recording anecdotes | No per-claim qualified producer demonstrated by the baseline or current inventory | No adapter can manufacture missing proof | Explicit unsupported content gap. Do not claim rich anecdote parity from a release year or generated Track Insight. No new lookup/provider/model route in this slice. |
| Artist image accompanying old fact | Legacy name-based Wikipedia lookup supplies an image, not text proof or documented image rights | No safe migration from its unqualified token | Retire legacy generation/image lookup together. Existing independently qualified current artwork/Forecast artist imagery keep their own rights, provenance and expiry contracts. |

Smallest justified implementation: retire the independent ambient producer;
reuse the qualified Session chain unchanged. The inventory demonstrates no
missing factual adapter within the permitted sources. Richer unsupported
anecdotes remain a declared gap, not a new implementation workstream.

## Publication and privacy boundary

Ordinary playback-status reads retain playback, favorites, metadata and
consented listening observations. They must invoke no spontaneous conversation
generation, ambient Wikipedia lookup, assistant-history append or
`async_update_last_ask_dj`. No active Session means no proactive Session fact.
Explicit Ask DJ text/voice remains available with presence Off and without a
Session; its authorized history, confirmations and shared media helpers remain.

All unsolicited content uses the existing Runtime → Planner → Knowledge →
immutable Moment → Flow/Broadcast path. The Planner retains eligibility,
priority and shared presence budgets; Knowledge retains exact subject/source,
rights, locale and expiry checks. Mood, Persona and presence stay independent.
Only successful publication commits deduplication/style/continuity memory.
No timer, catch-up queue, extra budget, model call, provider or Moment type is
added. Existing four-Persona/five-language qualified expression is reused.

Presence Off, stale track/authority, revoked account/Profile/device, expired
source, end and unload must reject new and in-flight Session publications.
Changing Off→on, reconnecting or repeating status does not reset budgets or
resurrect pending legacy cards. Candidate status callbacks must not hold an
ambient publication continuation. Qualification must distinguish these actual
candidate races from old installed Python coroutines: source retirement alone
cannot retroactively cancel a coroutine running older installed bytes. No
installation or restart is authorized or claimed here.

Existing historical `ambient_music_fact` / `spotify_playback_context` cards
remain readable with their original origin, classification and retention.
They are neither imported into Sessions nor promoted to qualified evidence.
Other assistant-only and operational system records remain supported; no
blanket system-card filter or Store migration is allowed.

## Consumers and verification

Apple's existing writer owns native adoption and its separate admission.
Suitable new content appears in active Session current/Flow through existing
Moment projection, not general Ask DJ or automatically Forecast. Authorized
Broadcast hosts receive the same immutable ID/text and public attribution.
Private questions, archives, account credentials and raw source payloads remain
outside shared VibeCast. No Swift or receiver writes are part of this slice.

Before delivery, require actual paired HA before/after status/Store proof;
explicit-question and historical-read compatibility; two peers and wrong
authority checks; timeout/cancel/Store failure and lifecycle races; real
Runtime/Planner/Knowledge/Moment/Flow/Broadcast reuse with four Personas and
five languages; local/static shared renderer portrait/landscape, source links,
reconnect, expiry and Session end; regressions/owning coverage and independent
technical/privacy plus editorial/experience reviews. Only external boundaries
may be fixtures. Canonical roadmap/backlog and versioned live JSON-DAG must be
maintained and generated, with frozen snapshots preserved.

Report independently: `SOURCE_AUDIT`, `CONTENT_COVERAGE`,
`LEGACY_PRODUCER_RETIRED`, `CANONICAL_MOMENT_REUSE`, `APPLE_QUAL`,
`VIBECAST_COMPAT`, `CANONICAL_FILES_MERGED`, `JOINT_ACCEPTANCE`.
Source and separate Finalization require their own exact reviewed-candidate
publication authorization, normal checks/protected merge and exact-main/artifact
readback. Native, installed and hardware acceptance cannot follow from browser
or isolated software proof. Full narrative Stage 4 remains partial.
