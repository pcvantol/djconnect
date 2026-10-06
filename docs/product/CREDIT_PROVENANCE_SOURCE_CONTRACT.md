# Production and Credits Source Contract — Phase A


## Owner-authorized current-slice extension

The [VibeCast owner refinements contract](VIBECAST_OWNER_REFINEMENTS_CONTRACT.md)
records the new bounded qualified-fact producer/display path, responsive UI,
read-only next-queue item and separate opt-in receiver end authority. Its
implementation/acceptance is pending; the completed baseline below stays
historical and its evidence is not upgraded by the new code. Older source
qualification flags and generic Broadcast permissions remain unchanged.

**Owner:** DJC-CORE / DJ Intelligence Evolution
**Directive:** `DJC-CORE-PROVENANCE-CREDITS-CONTEXT-V1-20261004`
**Status:** Phase A contract protected merged and exact-main qualified in [Core PR #1108](https://github.com/pcvantol/djconnect/pull/1108); Phase B NO-GO
**Boundary:** existing sources only; no new Artist/Album Moment behavior

## Decision and existing architecture

This is the first concrete, machine-readable qualification policy under the
provider-independent [Knowledge Source Architecture](KNOWLEDGE_SOURCE_ARCHITECTURE.md).
The fixed field inventory and fail-closed evaluator are in
`custom_components/djconnect/credit_provenance.py`. They are deliberately not
wired to Runtime, Planner, Knowledge Engine or DJMoment Engine. A policy record
is not a producer and does not make a fact eligible for Session output.

The current Core source gives **no qualified production or additional credit
fact for the live Artist/Album Moment path**. Therefore Phase A can be delivered
and tested, but Phase B is `NO-GO` until a separately proven producer and safe
attribution path exist. Existing metadata-based Moments keep their current
behavior; this contract adds no new factual claim to them.

## Exact current source inventory

The table identifies only fields emitted by current Core normalizers. Each
machine-readable field record also states reliability, freshness, conflict,
rights, attribution, retention, privacy, Session readiness and renderer safety.
All three records have `usage_rights_qualified=false`: a URL to provider
terms is a reference, not permission for new AI DJ output.
They also have `public_safe=false`; public use needs separate qualification.

| Provider / Core producer | Field and identity handle | Supported category and reliability | Freshness / conflict | Attribution and public safety | Session and retention boundary |
| --- | --- | --- | --- | --- | --- |
| Spotify Web API via `spotify_backend._normalize_playback` | `playback.artist`, with `playback.uri` and separate `artist_ids` | `track_performer`: Spotify calls its track artists performers, but the normalizer collapses names and loses per-name role/ID association. Provider catalog metadata only. | Current playback observation; suppress conflicting values, require a bounded fresh observation. | Spotify metadata needs a service link and mark; neither is carried through Track Insight to a verified Moment renderer. `renderer_safe=false`. | `uri` and IDs are dropped by Track Insight; `session_ready=false`. Runtime-only candidate, no persistent credit cache. |
| Spotify Web API via `spotify_backend._normalize_album_item`, used by album search and artist albums | `albums[].artist`, identity `albums[].uri` | `album_artist`: album artist attribution only, not a producer/featured/engineering role. Provider catalog metadata only. | Query-time observation; conflicts suppress all. | Spotify link and mark required; no Session attribution projection. `renderer_safe=false`. | Search/artist-album result is not bound to the currently observed Session track. `session_ready=false`; runtime-only candidate. |
| Same normalized album item | `albums[].release_date`, identity `albums[].uri` | `album_release_date`: release metadata, not a production credit. The normalizer does not preserve source date precision. | Query-time observation; reject malformed/expired/conflicting dates. | Spotify link and mark required; no Session attribution projection. `renderer_safe=false`. | Not bound to the observed Session track or live Track Insight. `session_ready=false`; runtime-only candidate. |

Source API semantics and attribution requirements come from Spotify's official
[Get Playback State](https://developer.spotify.com/documentation/web-api/reference/get-information-about-the-users-current-playback),
[Get Track](https://developer.spotify.com/documentation/web-api/reference/get-track),
[Get Album](https://developer.spotify.com/documentation/web-api/reference/get-an-album)
and [Developer Policy](https://developer.spotify.com/policy). These references
identify provider fields and terms; they do not grant this assignment rights to
skip attribution or add a provider call. Attribution alone does not establish
that a future spoken or model-mediated use is permitted under the current
provider terms; that use needs its own explicit qualification.

### Not a qualified credit source

- Raw Spotify playback contains a simplified album release date, but the
  current playback normalizer drops that date and the album URI. The full
  Spotify album object may contain a label, but the current Session path does
  not fetch it and `_normalize_album_item` does not emit it. Neither is a live
  credit producer here.
- Music Assistant and HA media-player status expose current title, artist,
  album and an arbitrary media content ID. They do not supply a verified credit
  role, catalog evidence handle or a qualified attribution path.
- Track Insight's `analysis.production_notes`, instrumentation and summary are
  generated or fallback interpretive text. They are **not** evidence of a named
  producer, songwriter, composer, engineer or recording-history claim. Its
  `track` contract projects title, artist, album and genres, but drops Spotify
  URI, artist IDs, release date and label.
- The `producer`, `composer`, `recording_context` and `release_year` values in
  Session tests and developer scenarios are injected fixtures. The current
  Track Insight producer does not emit them. Their presence in a Planner hint
  allowlist is not proof of a live factual source.
- No current normalized Core producer supplies songwriter, composer, mixer,
  mastering engineer, producer, label or a verified featured-artist role to
  live Session Intelligence. These categories are absent from the implemented
  machine-readable allowlist.

## Qualification rules

`qualify_current_moment_credit` accepts only the fixed current field IDs. A
normalized candidate cannot set its own policy. A usable fact requires:

1. exact provider and source-field match, valid provider item identity and
   bounded category value;
2. finite confidence at or above the contract threshold and an aware, fresh
   observation timestamp;
3. the stated provider rights reference, affirmative use-rights qualification,
   runtime-only retention and exact resource link plus visible provider mark
   for required attribution;
4. no disagreement among candidates for the same subject/field; and
5. an independently qualified Session producer **and** renderer-safe scope.

Missing, stale, low-confidence, conflicting, malformed or unattributable input
returns a typed negative decision. Its audit serialization contains only
eligibility, reason and category; no fact value, credential, provider payload,
URI, source identity or private Profile information. All current fields fail
the final producer/attribution gate. No public renderer projection is created.
Candidate observations are transient normalized data; this contract authorizes
no raw-response cache, persistent source memory, cross-Session learning, AI
training, new account or provider retrieval.

## Exact prerequisite for Phase B

Before Artist or Album Moments can use new production/credits context, a
producer/consumer handoff must prove all of the following:

1. A current authorized provider actually emits a named, typed credit role
   (or a bounded release fact), with provider item identity and evidence handle.
   Names inferred from generic Track Insight text or a search-string match fail.
2. The adapter preserves role, value, subject identity, observation time, date
   precision where relevant, source link, confidence/reliability basis,
   conflicts, rights/terms and retention limits. It binds that exact item to
   the observed current Session track/album before Knowledge consumes it.
3. The Knowledge Engine receives only normalized eligible fields internally;
   raw provider responses, bearer/OAuth tokens and internal IDs do not enter
   DJMoments, Session Flow or Broadcast. Runtime-scoped continuity can then
   avoid repeated credit angles without persistence.
4. The intended use is positively qualified against current source rights and
   terms, including any model-mediated or spoken use. Every intended
   presentation channel can satisfy attribution, including the required
   link/mark when Spotify metadata is used. If a voice or renderer surface
   cannot do so safely, that fact is ineligible on that surface. No client,
   Broadcast-schema or renderer change is silently assumed here.
5. Unit, negative, Session-behavior and existing Golden/E2E/contract evidence
   prove actual Artist **and** Album credit use, safe Silence/fallback and no
   repeated credit angle before Phase B can claim product acceptance.

The current producer and attribution paths do not satisfy these prerequisites.
This assignment therefore stops after Phase A rather than selecting an external
music/editorial database, adding Spotify album calls, inventing a production
credit or treating general LLM text as source-qualified.
