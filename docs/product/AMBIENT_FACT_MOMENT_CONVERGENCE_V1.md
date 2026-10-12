# Ambient fact → Session Moment convergence v1

Assignment: `DJC-CORE-AMBIENT-FACT-MOMENT-CONVERGENCE-V1-20261012`.
Owner selection: [Core register](https://github.com/pcvantol/djconnect/issues/1101#issuecomment-6125691006).
Admission base: `de0e1fccbfdb0f8ffc5a58c77c209919f4cf00de`.
Status: local implementation and software qualification; unpublished, reviews and protected delivery pending.

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

| Old content family / claim | Existing eligible Session basis and form | Missing bounded connection | Disposition / remaining gap  Concrete example and evidence level |
| --- | --- | --- | --- | --- |
| Artist formation/birth date and group/person type | Exact MusicBrainz artist linked from a uniquely matched recording; typed life-span/type → Artist Moment | None in the current qualified producer | Reuse existing dated Artist fact, subject/type semantics and attribution; an arbitrary model biography is ineligible.  Baseline model claim “Northline werd in 1994 opgericht” has no qualified evidence ([paired fixture](../../examples/client_contracts/ambient_fact_convergence_v1/paired-status-before-after.json)). Existing resolver positive: MusicBrainz `Test artist`, type `Person`, birth `1960-01-02` ([resolver test](../../tests/test_session_facts.py#L82)); formation/birth four-Persona/five-language forms use [Runtime unit matrix](../../tests/test_expressive_context_variation.py#L109). These are resolver/Runtime unit proofs, not a new actual-HA artist qualification. |
| Short artist identity/context description | Exact reciprocal MusicBrainz MBID ↔ Wikidata QID and existing localized CC0 description → Artist Moment | None | Reuse unchanged descriptor with source. Missing language or reciprocal identity gives no fact. This is not license to rewrite a Wikipedia biography.  Wikidata `Q1`, reciprocal artist MBID `00000000-0000-0000-0000-000000000002`, `Description nl` ([positive resolver](../../tests/test_session_facts.py#L82)); [Runtime expression matrix](../../tests/test_expressive_context_variation.py#L109). Synthetic resolver/Runtime unit proof; no inference from the baseline Wikipedia summary. |
| Album release date | Exact current Spotify track/album URI and release precision → Album Moment | None | Reuse current-edition display fact. Original-release, reissue and remaster narratives need separate evidence; title matches do not qualify them.  `Exact edition`, album URI ending in22 `Z` characters, date `2001-03-04`, observed tracks1/2: [twenty actual paired-HA chains](../../examples/client_contracts/ambient_fact_convergence_v1/canonical-session-reuse.json). Date-precision/original-release rejection: [owning test](../../tests/test_session_facts.py#L41). |
| Recording producer, instrumental or vocal contributors | Unique ISRC recording, exact version title/artist match and explicit MusicBrainz roles → Track Moment | None | Reuse typed credits and full attribution. Do not infer a producer from fame, sound or artist membership.  MusicBrainz recording `00000000-0000-0000-0000-000000000001` explicitly credits `Test producer` ([positive resolver](../../tests/test_session_facts.py#L82)); [independent angles through Flow/Broadcast](../../tests/test_session_facts.py#L173). Resolver/Runtime unit proof; does not establish an arbitrary band member as producer. |
| Composition attribution | One qualified linked work and typed MusicBrainz composer relationships → Track Moment | None | Reuse existing work fact; unknown/multiple work identity stays ineligible.  Qualified linked work `00000000-0000-0000-0000-000000000003` explicitly names `Test composer` ([positive resolver](../../tests/test_session_facts.py#L82)). Synthetic resolver proof; no composer inferred from baseline prose. |
| Sound, genre and listening context | Existing Track Insight / qualified existing Genre interpretation → Track/Genre Moments selected by the existing Planner | None for interpretation | Preserve interpretation as interpretation. Generated prose is not a new historical, cultural or technical fact source.  `A spacious ambient texture.` and genre `ambient`: [actual paired Track Insight response](../../examples/client_contracts/ambient_fact_convergence_v1/paired-status-before-after.json), with an explicit external conversation-response fixture. Genre realization: [existing Runtime expression matrix](../../tests/test_expressive_context_variation.py#L109), unit proof. Neither supplies biographical/chart proof. |
| Connections to an earlier contribution | Existing separately delivered Genre→Track, shared-producer and published Album→current Track contracts | None within those exact bounded relations | Reuse only their published evidence and identity rules; no generic anecdotes or new relation family.  Observed tracks1/2 from `Exact edition`: [actual paired Album→Track fixtures](../../examples/client_contracts/ambient_fact_convergence_v1/canonical-session-reuse.json). Shared-producer source/identity reuse: [five-language Runtime unit test](../../tests/test_shared_producer_continuity.py#L86); Genre→Track: [observed relation unit test](../../tests/test_discover_narrative_transition.py#L209). Proof levels remain distinct. |
| Singles, chart success, awards, cultural importance, historical impact, recording anecdotes | No per-claim qualified producer demonstrated by the baseline or current inventory | No adapter can manufacture missing proof | Explicit unsupported content gap. Do not claim rich anecdote parity from a release year or generated Track Insight. No new lookup/provider/model route in this slice.  No qualified chart/award/impact/anecdote example demonstrated. The baseline’s unsupported `Northline` formation claim remains a concrete negative example; a synthetic model response or current-edition date cannot fill this gap. No positive content-parity claim. |
| Artist image accompanying old fact | Legacy name-based Wikipedia lookup supplies an image, not text proof or documented image rights | No safe migration from its unqualified token | Retire legacy generation/image lookup together. Existing independently qualified current artwork/Forecast artist imagery keep their own rights, provenance and expiry contracts.  Baseline Wikipedia fixture title `Northline`, description `Fixture artist summary; not claim proof`, image `https://fixture.invalid/artist.png` ([paired baseline](../../examples/client_contracts/ambient_fact_convergence_v1/paired-status-before-after.json)); actual old lookup boundary exercised, but image/summary response is synthetic and confers no rights or text-proof qualification. |

Concrete examples above distinguish actual HA transport proof, resolver/Runtime
unit proof and unsupported model claims. The matrix does not claim that each
family received a new actual-HA provider qualification in this slice.

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

## Local implementation and measured qualification

The sole status import/call is removed and the exclusively legacy generation,
name-based Wikipedia lookup and proxy registration module is deleted. Its shared
pipeline, media, history and Music DNA helpers remain. Historical classifications
and system-card retention are unchanged. No Session content producer, renderer,
capability or protocol is modified.

The [paired before/after fixtures](../../examples/client_contracts/ambient_fact_convergence_v1/paired-status-before-after.json)
prove zero new ambient generation, Wiki lookup, history or last-Ask-DJ writes,
including delayed/cancelled/timeout reads and a real history-Store failure. Two
ordinary paired peers and missing/wrong bearer cases exercise actual handlers.
The separate [Session reuse fixtures](../../examples/client_contracts/ambient_fact_convergence_v1/canonical-session-reuse.json)
cover twenty four-Persona/five-language HA chains, native current-only projection,
Off/in-flight/ABA/track/end races and forty observations over 60.185 real seconds.
Its 200s spacing is deliberately modeled; wall spacing is 1.5s and expiry uses real
monotonic deadlines. Memory remains bounded and no catch-up is created.

[Browser evidence](../../examples/client_contracts/ambient_fact_convergence_v1/browser-compatibility.json)
contains four actual HA→local/static renderer sequences in portrait/landscape:
identical immutable text, current track, source/Spotify links, readable card,
transition, reconnect, real 36.6–36.7s expiry wait and end. CAF is modeled only.
The existing twenty chains exercise Album/current Track reuse; they do not
turn a release date into rich anecdote parity. Broader already qualified
Artist/Genre/expression contracts remain covered by full source regressions.

Full regression: 1761 tests, 7 existing skips. Owning branch-instrumented suite:
83 tests, 75% aggregate module coverage (history 70%, DNA/backend 75%); residual
existing broad helper/error branches are not presented as complete coverage.
The changed runtime adds no branch. Explicit text/voice/history/search with
presence Off passes 27 real HA requests. DAG/schema/generation passes 131 tests
and 23 views with preserved history. Current hostverify exits 0 MATCH.

Early [Apple #87 handoff](https://github.com/pcvantol/djconnect-app/issues/87#issuecomment-6130451688)
pins local runtime code 1527b2ae1a6ae3a2cb07f30f157b26f0df1cda62. Read-only
Apple source audit confirms the historical origin-specific fact label and
existing Moment ID/content/source-attribution decoding fields. The existing
writer message tool was unavailable; no native acknowledgment/acceptance is
inferred from that source audit or register handoff. Native, installed, live
provider and hardware are NOT_RUN; joint acceptance OPEN. Exact source review,
publication, artifact readback and separate Finalization remain their own gates.
