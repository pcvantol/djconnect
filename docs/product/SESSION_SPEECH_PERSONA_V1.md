# Session narration, speech and live Persona v1

Assignment `DJC-SESSION-SPEECH-PERSONA-VOICE-20261015`; owner decision6189231491,
original audit6188230166 and autonomous-next6189912293. Design-first contract;
Core source is protected delivered in [PR1177](https://github.com/pcvantol/djconnect/pull/1177)
at `3535c97c3b50e9a126d0f22fcc5ce50d81851499`; native/audible/installed/joint
acceptance remains separate and open. Original admission base70c0a300, after genuinely
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
Concrete voice playback and autoplay belong to the device/audio output.
Owner clarification: gender preference is an optional client setting, gated by
the actual configured server Assist pipeline/provider capabilities. No supported
provider gender metadata means no male/female selector; keep provider default.
Native voice inventory alone cannot enable an unadvertised gender setting. A
female preference does not silently fall back to male or create a new Persona.
An unavailable matching voice is a visible capability outcome.

### Active-session controls (owner clarification, 2026-10-16)

Apple exposes Voice and Persona controls in the active DJ-session, not solely
in Profile setup. Voice/gender preferences are runtime mutable and scoped to
HA installation + authorized user/Profile + session_id + device/install-ID;
Core validates current provider metadata on each explicit prepare. Only actual
supported voices/qualified genders are offered. No shared HA pipeline/default
write; no preference leak to other sessions/devices. See the
[generic provider contract](GENERIC_HA_TTS_V1.md).

Persona uses the existing confirmed Session update route below and synchronizes
as shared Session state across authorized devices. The Profile choice remains
the start default; an active-session change must not silently overwrite it.
Show pending/error/CAS conflict and confirmed readback, preserving published
text, playback, presence budgets and other client draft/scroll state. No new
Persona endpoint, Planner or product implementation is required in Core for
this existing delivered capability; actual native controls remain Apple-owned.

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

### Current-track announcement admission refinement

Inventory: the normal observer already invokes the one Track Started
Planner/Knowledge/Moment lifecycle. Its unmeasured Track Insight fallback can
currently publish a generic analysis-unavailable sentence, spending the common
Presence opportunity without a useful narration. Replace only that fallback
within an approved Track-context opportunity with an authored current-track
announcement. Qualified Artist/Album/credit facts retain selection priority.

Runtime may attach a typed immutable proof from its actual current playing
projection only after the existing observed-item/generation/freshness checks.
Require exact current canonical item identity and exact title/artist agreement
with the provider boundary. Knowledge carries that proof, not a caller flag or
raw provider narrative; the Moment Engine realizes the four Persona forms in
the selected language. Missing/mismatching evidence gives the existing safe
alternative/Silence, not a fabricated announcement. No new listener, opportunity,
Planner, counter or backend action. No status-read publication.

The proof is ephemeral, current-only and bounded to the original observation
freshness deadline (30s), publication display window and Session lifetime.
Native owner/shared visual admission requires the exact published binding and
Spotify source link/mark; it grants no archive. Speech is independently the
qualified owner-local exact reading, never cloud/model processing of catalog
metadata. Historical aggregate acceptance may count the actual Moment once,
while its body remains unavailable for retention. Reconnect, preparation and
later observations cannot renew the old proof or rewrite its content.

### Genre fallback qualification refinement (review finding)

The real Track Insight fallback can enrich artist genres even when no catalog
fact qualifies. A generic Genre card with only `track_insight` as source has no
native/speech grant. Do not widen that grant on a source label. Reuse the
existing qualified-fact path for the already available exact-ID Spotify
playback-status artist/genre evidence: same canonical current recording,
matching title/artist, exactly one identified artist and a bounded genre label
actually present in that observation. Its normalized fact names genre context,
not measured track audio; attribute/link the identified Spotify artist. No new
lookup, source, model input, historical body or independent publication path.

Name-only `artist_profile` search, absent/multiple artist identities, malformed
or stale evidence does not qualify this extension. The production unmeasured
Genre fallback then becomes Silence, with ordinary compact playback context
remaining available. Four-Persona local forms retain the original anchors;
current-only display and owner-local speech keep their existing source expiry,
attribution and session/profile withdrawal checks. This closes a real review
gap; legacy source fixtures are not evidence of a broader processing right.

Genre qualification attaches to the existing Genre intent after Planner
selection, so it does not change that Planner's Silence/Direction priority or
replace the delivered Genre→Track continuity policy. Existing narrative line,
published anchor checks, pending-transition budget and final fences remain the
owners. A later relation needs the original published qualified genre fact and
a fresh existing observation of the actually current different recording; it
cannot renew an old announcement's30s display proof. The new relation has its
own current-only proof/deadline and original two-anchor identity, both Spotify
source links, no archive, and four authored Persona realizations. No queue,
future-media promise, catch-up publication or new relation selection is added.

The existing Spotify artist cache deadline is part of the private qualification
proof. A read, fact realization or relation never renews that deadline. Genre
validity ends at the earlier of the original six-hour cache deadline and the
ordinary thirty-minute fact bound. Missing, malformed or elapsed cache evidence
fails closed, including while generation or speech is in flight. The deadline
stays internal; owner/native delivery receives only its existing safe expiry.

## Per-family realization and processor qualification

| Family / evidence | Bubble realization | Speech route and limits |
| --- | --- | --- |
| Current observed playback | Exact title/artist, observation not selection/listening claim; authored short announcement in existing track opportunity | Owner-local reading of already admitted exact presentation; no catalog/private payload to model/cloud TTS. |
| Artist CC0 begin/formation | Existing normalized date/precision, four Persona forms and published-only variation | Exact admitted speechtext through the selected HA TTS provider or local renderer; no biography lookup or new fact. |
| Wikidata localized description | Exact qualified descriptor inside authored framing; never translate an absent language | Same qualified CC0 descriptor/framing through configured HA TTS or local renderer; no surrounding Wikipedia prose or images. |
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

### Direction realization refinement before runtime changes

The existing Planner-approved Session update remains the sole publication
opportunity. Knowledge's validated Direction context owns its meaning. The
Moment Engine chooses an authored Home/Radio/Club/Festival wording for that
same intent; it adds no track, artist, album, next-media or observed-energy
claim. An unanchored Direction update cannot borrow Forecast's artist/album
placeholders. Use four explicit unanchored forms for exploring, deepening and
maintaining; reuse Forecast's already authored intent forms for building,
cooling, returning and resetting. Keep intent/uncertainty, locale, source,
Presence budget and semantic commit unchanged. Existing Forecast current and
conditional-target facts retain their factual labels; its narrative intent
continues to use its four Persona forms. No speech preparation creates or
rewrites either projection.

Qualified Track Insight continues to use its existing independently authorized
model context and configured HA conversation route. Reuse the common Ask DJ
Persona answer-form instructions for that request's confirmed style instead of
passing only a machine Persona label. This is presentation guidance on the same
already permitted evidence/call, not another generation, fallback provider or
permission to submit catalog display metadata. Keep its existing target/style/
locale cache partition and acceptance guard. A general or Session Ask DJ screen
still reaches the same backend; insight is a selected capability, not a parallel
conversation implementation. Missing source permission keeps the existing
unmeasured detail, without a model call or fabricated musical analysis.

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

## Connected realization refinement

Qualified fact read-fit now considers only authored Persona variants. A shorter
raw provider sentence cannot bypass the Persona invariant; if no approved form
fits the original opportunity, choose an existing alternative or Silence without
consuming style memory. Year/month/day display uses exact qualified precision in
en/nl/de/fr/es; source fields remain unchanged. Album-continuity framing uses the
same current edition realization, including published-only variation, rather than
appending a raw catalog sentence. This is a connected foundation, not completion
of every Track/Insight/trivia/announcement/Forecast family or editorial approval.

The same Persona-only admission now applies to genre read-fit. The original
opportunity duration remains authoritative: an approved shorter alternate may
fit, otherwise Silence, never raw genre prose. Birth/formation sentences use the
grammatical year/month/day phrase; edition sentences name the qualified catalog
edition without implying its first release. A single date is still a single
fact, not evidence of a rich multi-fact narrative or finished Persona acceptance.

## Local connected qualification checkpoint

The implementation joins accepted common dialogue turns, live immutable Moments
and independently retained historical contributions to the same private speech
preparation/byte owner. Current playback announcements share the existing Planner
and Presence ledger; they neither create playback observations nor archive catalog
bodies. A later Genre→Track relation uses its existing pending opportunity and
budget, original published genre proof and a fresh current-track observation.

The captured connected matrix contains six qualified fact families across four
Personas and five languages (120 real Core/SQLite/owner-adapter cases). The
transition matrix distinguishes one complete Runtime sequence with simulated
elapsed time from twenty Moment-engine previews of its actual approval; previews
are not twenty publications. Exact text, original source links, original Persona,
manual-only replay and shared-screen exclusion are asserted. Backend cache-hit
tests prove that repeated reads cannot renew near-expired genre evidence; an
actual pending private synthesis is cancelled at that original deadline.

Description realization preserves the exact localized Wikidata descriptor inside
a natural attributed introduction. Qualified Spotify genre narration refers to
the identified artist’s classification, not measured audio properties of the
recording. Its richer source-specific wording requires the validated display
core; generic metadata cannot acquire a Spotify attribution through presentation.
The source-poor unmeasured fallback remains Silence, including when Knowledge
receives a fact whose deadline elapsed before realization.

These are local qualification results, not source/main delivery or native
listening acceptance. Browser software proofs use actual isolated HA/Broadcast
and the common local/static renderer, with a modeled CAF host adapter. External
provider/STT/Wyoming inventory and waveform boundaries are explicit fixtures;
nonempty WAV bytes do not qualify real audible voice quality. Native visible/
audible adoption, installed acceptance and joint product acceptance remain open.

The [local qualification record](../verification/SESSION_SPEECH_PERSONA_LOCAL_QUALIFICATION_20261015.md)
binds the exact runtime checkpoint, real model-route output, full family/locale
receipts, browser/expiry proof and the separate open delivery/consumer gates.

Provider-qualified runtime gender/voice behavior is specified in
[Provider voice/gender](PROVIDER_VOICE_GENDER_V1.md). Cloud metadata support
does not change Session Persona, shared pipeline defaults or device scope.
