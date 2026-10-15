# Session narration, speech and live Persona v1

Assignment `DJC-SESSION-SPEECH-PERSONA-VOICE-20261015`; owner decision6189231491,
original audit6188230166 and autonomous-next6189912293. Design-first contract;
implementation and all acceptance remain pending. Base70c0a300, after genuinely
closed artwork1172/1173. This does not reopen historical expressive/artwork work.

## Existing owners and bounded change

| Owner | Disposition |
| --- | --- |
| Session Runtime/Planner/Presence | REUSE one active Profile Session, existing opportunity/budget and final commit fences; no second announcement planner. |
| `async_update_persona` | FIX normal paired owner CAS/readback/Broadcast; preserve existing helper and Runtime identity. |
| Moment Engine/expressive realization | FIX remaining type bypasses and metadata; realize Persona before semantic acceptance. |
| Presentation Composer | KEEP immutable approved text/segment order; never invent or rewrite facts. |
| Common Ask DJ service/dialogue | REUSE the one general+Session implementation; ADD post-acceptance speech projection for early and ordinary answers alike. |
| Existing image/native delivery/History | KEEP exact subject, source, retention, owner and revision; speech does not grant archive/image rights. |
| `dj_response`/HA TTS | REUSE temporary audio ownership and supported HA helpers for separately qualified synthesis; no direct provider API or speaker action. |
| Legacy Mood voice style | RETIRE as an override of explicit Session Persona; KEEP compatibility outside Session when no explicit Persona exists. |
| Apple Audio Renderer Host | Own actual voice inventory, local playback/stop/autoplay and native accessibility; no Core Swift write or new consumerwriter. |

## Distinct axes

Session Persona is shared semantic state: `home_dj`, `radio_dj`, `club_dj`,
`festival_dj`. Home is warm/curious, Radio polished/narrative, Club compact and
restrained, Festival playful/energetic without permanent hype. Mood shades that
identity; Presence doses unsolicited contributions; neither selects a voice.
Concrete voice/provider and autoplay belong to the device/audio output. A
female preference does not silently fall back to male or create a new Persona.
An unavailable matching voice is a visible capability outcome.

## Semantic acceptance and live changes

`POST /api/djconnect/v1/session/persona`, contract1, exact normal paired identity,
`session_id`, `selected_persona`, `expected_persona_revision`. Reuse the existing
Mood/Presence owner authorizer and Runtime lock. Wrong owner401/403; absent or
ended Session404; stale revision409 with current Session/Persona/revision.
Same-value updates preserve revision. Result and owner snapshot expose confirmed
Persona/revision; `persona_changed` publishes through existing Broadcast. No
Profile default write, Session restart, track/queue command or budget reset.

All work captures Persona/revision at realization. Revalidate immediately before
the existing semantic commit. A stale result is discarded or re-realized once
from the same already qualified facts under the new revision; it cannot become
a newly published old-Persona answer. Never re-execute an already committed
playback effect to repair style. Published text/history is immutable. Record
realization Persona/Mood/revisions as bounded presentation/owner metadata.

## Playback observations and narration

`playback_observed` remains the canonical factual observation with original
identity/time/Stage1 coverage and its original track count. It remains compact
music context, never a fabricated DJMoment. When the existing Planner admits a
track announcement, the existing Moment Engine realizes that contribution once
in Session Persona, bound to the observed identity. It uses the same Presence
budget/publication boundary; no second listener or status-read generation.
Only a successfully accepted non-Silence DJMoment increments Moment totals.
Attaching speech/audio creates no contribution, track count, opportunity or
history entry. Presence music_only suppresses unsolicited narration including
pending work; compact playback context remains. Explicit owner listening to an
already authorized contribution remains a distinct user action.

## Per-family realization and processor qualification

| Family / evidence | Bubble realization | Speech route and limits |
| --- | --- | --- |
| Current observed playback | Exact title/artist, observation not selection/listening claim; authored short announcement in existing track opportunity | Owner-local reading of already admitted exact presentation; no catalog/private payload to model/cloud TTS. |
| Artist CC0 begin/formation | Existing normalized date/precision, four Persona forms and published-only variation | Exact admitted local speechtext; no biography lookup or new fact. |
| Wikidata localized description | Exact qualified descriptor inside authored framing; never translate an absent language | Same descriptor/framing; qualified local renderer; no surrounding Wikipedia prose or images. |
| Album/edition catalog | Preserve exact album URI/edition/date precision, source link and Spotify mark | Current owner-local reading only; no implied historical/cloud processing right. Missing source/audience permission is explicit unavailable. |
| Recording/work credits | Normalized contributor/role/opera title; distinct Persona sentence structures | Qualified CC0 fields and exact realized text only; supplementary reviews/ratings/annotations not admitted. |
| Shared producer/album continuity | Existing previously published relationship proofs, current exact recording and both attribution links | Same qualified relation, shortest original deadline; never infer another connection or archive authority. |
| Track Insight/trivia | Existing validated source/route, no arbitrary provider prose passthrough; exact subject and qualified anchors | Existing permission must qualify spoken processing independently; no private Spotify/model input workaround. |
| Session direction/Forecast | Existing Planner-authored intent and uncertainty, no guaranteed next track | Exact authored approved segments, no Horizon export; Forecast is not a historical observation. |
| Explicit Ask DJ answer/list/help/error | Same accepted common dialogue result; active Session style when present, otherwise existing explicit/default style | Explicit manual listening projection even when audio_response never; no resend or re-execution for replay. Original source/retention governs. |
| Silence/heartbeat/technical progress | No narration | No speech grant/autoplay. |

CC0 source qualification is field-specific, not a blanket provider permission.
[MusicBrainz core data](https://musicbrainz.org/doc/About/Data_License) is distinct
from supplementary data and documentation; [Wikidata structured data](https://www.wikidata.org/wiki/Wikidata:Licensing)
is distinct from other-namespace text. Their normalized qualified fields can
support deterministic local presentation; this decision does not add a model
route. [Spotify policy](https://developer.spotify.com/policy) remains applicable:
no added voice-control functionality or cloud/model use of catalog/private
payloads under this presentation slice. Source-linked owner-local reading is
separate from generic cloud synthesis and archive processing. Unsupported use
must return explicit processor/source unavailability, not a silent fallback.

## Content and five-language acceptance

Use en/nl/de/fr/es and actual Home/Radio/Club/Festival forms in the factual
sentence, not a fixed greeting, Persona label or hype suffix. Preserve exact
names, roles, edition, date precision and attribution. A known year does not
become a complete date. Do not claim choosing the music, attentive listening,
personal memories, collaboration/influence or an unknown next track. Vary only
within the existing bounded published-only style memory; rejected proposals and
speech preparation do not consume forms.

Before/after matrix: playback,Artist,Album,Track,TrackInsight,trivia,relation and
direction × four Personas × five languages. Include connected multi-track actual
Runtime/Planner/Moment/Flow/Broadcast sequences, not template calls alone.
Explicitly test pending Persona switch, same-value/CAS race, Mood independent
of Persona, Presence Off/in-flight, no regeneration on history/reconnect,
text/audio identity, source/Profile withdrawal and unchanged counters/artwork.

## Delivery and acceptance boundaries

See [speech delivery/replay](SESSION_SPEECH_DELIVERY_V1.md). Core contract and
connected producer, local model/provider-fixture tests, installed integrity,
actual synthesis, native visible/audible and joint acceptance are separate.
Manual capability fields and nonempty WAV alone do not prove audible quality.
An unqualified family remains explicit OPEN; no whole-product PASS via fallback.
Source and separate Finalization retain exact candidate publication gates.
Existing latest-main HA-dev/prod installation authority applies only after
qualified delivery. No native writes, new provider/cost/contract, home-speaker
mutation, second planner/store/dialogue engine, hardware or new product family.
