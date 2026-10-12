# Published Album → current Track continuity v1

Assignment: DJC-CORE-NARRATIVE-ALBUM-CONTINUITY-V1-20261012.
Admission: same Core writer, base 0f37b53cc56f89109a1adcbcf39dd454ba52c72d,
branch codex/narrative-album-continuity-v1, [ACK6121336412](https://github.com/pcvantol/djconnect/issues/1101#issuecomment-6121336412).
Status: local implementation and Core software qualification complete; exact
source publication/protected delivery and separate Finalization pending.
Artwork1152/1153 is closed, MERGED_RECONCILED and WORKSPACE_READY.

## Existing evidence and publication boundary

Current Spotify playback supplies exact track URI, album URI/name and edition
release date/precision. SessionFactsResolver already produces a field-qualified
album_release with immutable DisplayFactCore, original monotonic observation
and Spotify album resource link. Names, Insight prose, provider responses,
search results, proposed Moments and failed publications cannot open a line.
The actual Album Moment must have entered Planner Flow and Broadcast.

The existing Runtime/Planner/Knowledge/Moment pipeline remains authoritative.
This is a closed derived Track fact, not another provider field, planner,
Moment type, transport, history store or narrative engine. Both Discover
strategy AND Exploring direction are required. No Genre→Track or shared-producer
semantics are changed. Only a bounded relational part of Stage4 is selected.

## Closed admission and selection policy (before runtime changes)

| Condition | Required proof / consequence |
| --- | --- |
| Prior A | Actually published eligible Album/album_release; original qualified DisplayFactCore validates exact five-language copy; observed current track A at publication |
| Current B | Fresh accepted playing observation and freshly qualified current album_release; exact Spotify track URI, different from A |
| Edition identity | Exact album resource URL/22-character album URI agrees across A/B; album name/date/precision cores equal; never title/artist-name matching |
| Rights | Existing Spotify metadata visual display only, album URL and visible Spotify mark; no model rewrite, voice/TTS, source training or historical recall |
| Freshness | Both original source observations remain within 1800s; earliest deadline wins; reconnect/read/publication never renew it |
| Memory | At most three latest distinct observed tracks and their published Album proofs; six successful unordered track-pair/edition relations per Runtime; saturated memory closes new relations rather than evicting dedup proof |
| Selection | Most recent eligible published precursor; conflicting current proofs fail closed; existing Planner ranks closed eligible relation as one Track angle, after read-fit/capability gates |
| Repeat | An unordered A/B/edition tuple and a previously connected current B never produce another relation; state commits only after actual successful Flow/Broadcast publication |
| Close | Source expiry, leaving the three-track window, music_only, leaving Discover/Exploring or Session end closes pending evidence; consumed relation guards survive settings/reconnect until end |
| Failure | Failed persistence/publication consumes neither opportunity nor relationship; late/stale/off/ABA candidates fail normal revision/current-item checks; no catch-up cards |
| Fallback | Missing/conflicting/expired identities or copy fall back to existing independently eligible facts/Insight or Silence; no fabricated connection |

Existing shared presence ledger, six-fact-per-track ceiling, observed playback
spacing, readable40–90s and remaining read-time+5s gates apply. No separate quota:

| Presence | Minimum spacing | Per-track cap | Rolling600s cap |
| --- | ---: | ---: | ---: |
| music_only | no proactive output | 0 | 0 |
| occasional | 180s | 1 | 2 |
| balanced | 35s | 3 | 6 |
| talkative | 35s | 4 | 10 |
| presenter | 35s | 6 | 16 |

Mood changes atmosphere and existing bounded ranking/read-time only. Persona
changes current authored expression only. Previous immutable cards are never
rewritten. Neither controls presence or resets publication budgets.

## Authored display contract

Four existing Personas and en/nl/de/fr/es get deterministic reviewed forms.
The connection says that the current track belongs to the exact edition whose
release date the DJ previously presented. It repeats the unchanged qualified
Spotify edition fact, without claiming sound/influence, DJ track selection,
attentive listening or knowledge of the next track. Prior track names are not
revived as historical Spotify metadata. Current track comes from current
playback; the immutable relation uses album/date anchors and original source.
Unsupported locale, malformed core or unfit copy is ineligible.

Native delivery v1 and Cast1.1 envelopes retain existing fields, no actions.
Derived fact binds current B; earliest A/B source deadline remains. Spotify
cards remain current-display only, never ActiveFlow/history/search recall.
The ordinary renderer provides Spotify mark and resource link. No raw source
IDs, private Profile/AskDJ/archive data or provider payload enters Broadcast.

## Required evidence and delivery

Actual Runtime→Planner→Knowledge→Moment→Flow/Broadcast before/after, ordinary
paired isolated HA routes and external-provider-only fixtures. Same edition,
different editions/remasters, same title, same track, missing/conflicting IDs,
unpublished/failed/expired predecessor, Session replacement, retries, saturation,
Off/in-flight/ABA/reconnect, Mood/Persona, track replacement and end are required.
Qualify local/static shared renderer portrait/landscape, current B, immutable
facts, source attribution, readable transitions, reconnect, expiry and end.
Independent technical/privacy and editorial/experience reviews are mandatory.
Apple87/VibeCast10 receive exact fixtures and producer pin, with native/installed/
hardware acceptance separately OPEN/NOT_RUN until independently proven.

Real roadmap/backlog/maturity and versioned maintained DAG updates accompany
source delivery. Frozen planning history stays unchanged. Source publication
and separate documentary Finalization each retain their own exact candidate
gate; no installation/deployment/Pages/signing/service/workflow/hardware effects.


## Actual ordinary-route qualification boundary

Paired HTTP Session-start/end uses a valid Spotify Profile/account binding and
normal device bearer authentication, without HA user test credentials.
Existing direct Festival startup chooses Building Energy; that negative route
remains ineligible and cannot seed a future line. The Festival/Exploring matrix
uses ordinary Home startup followed by the existing server-owned Core Persona
update, with no mocked direction or new consumer command. This is Core software
coverage; it does not claim an authenticated native Persona-update surface.
Source-poor sessions retain existing Track Insight/Silence behavior.

[Core software acceptance](../verification/NARRATIVE_ALBUM_CONTINUITY_V1_ACCEPTANCE.md)
records measured results and distinct native/installed/hardware boundaries.
