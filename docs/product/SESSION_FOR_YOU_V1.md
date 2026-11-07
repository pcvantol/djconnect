# Session For you v1

Owner scope: Core #1101 comments 6660680798, 6656838175 and 6656995614;
Apple #87 comment 6657013431. The visible Dutch title is **Voor jou**, explicitly
reconfirmed by the owner. This replaces the Verras me launcher, rather than adding
a second recommender or playback engine. The older first-play v1/v2 documents and
HTTP receipts describe historical behavior; this document owns the new behavior.

## Presentation and contract

Only authenticated iOS/iPadOS and macOS Session start/active responses expose
`for_you` schema1. Native clients place one compact card below the Session mode
bar and above artwork/playback. No initial launcher or fourth Ask DJ suggestion.
Watch has neither this card nor automatic preparation. Its ordinary Ask DJ,
playback, pairing and speech routes retain their existing authority.

Feature-detect `session_start_actions` contract2 and
`session_first_play_surprise_mix` contract3. The former envelope is schema2;
its first item is `kind: inline_offer`, with the localized For-you label and
`offer`. Its second item remains playlist navigation, independently available.
Internal first-play identifiers and localized legacy prompts are compatibility
routes to this same implementation; never display a second Verras me card.

The `for_you` object contains schema_version, offer_id, session_id, title,
visible, state, intro, intro_source, options, result_set, conversation_context,
actions_available, expires_in, automatic_playback:false and
queue_effect:replace_on_explicit_selection. An unavailable preparation contains
an honest reason and no options. Supported titles: For you / Voor jou / Für dich /
Pour toi / Para ti. Intro and fallback controls cover en/nl/de/fr/es.

Each of exactly three backed options contains option_id, action_id, genre,
label and visual_recipe. The bounded recipe contains only schema_version1,
revision1, variation_id, original owned genre, current mood, persona,
artistic_direction (layered_dunes, misty_valley or mountain_horizon), and
illustrative_not_audio_analysis:true. It contains no raw DNA/history, catalogue
URIs, action grants, images or Spotify artwork URLs. Pass **only this recipe**
to Apple's local model. Native Foundation Models may turn it into a bounded
SceneSpec for a native landscape renderer; procedural fallback must be honest
when local generation is unavailable. Core does not generate genre images or
claim native AI execution. Cache native results by Session/option/recipe revision;
normal polling must not change imagery. Three directions are deliberately distinct.

## Preparation and lifetime

One accepted genuine Session start may perform three bounded parallel Spotify
catalogue reads and bounded existing HA narration. The preparation has its own
ordinary dialogue frame with no synthetic user text, no chat/history publication,
no speech or playback grant and no preference write. Reconnect/active polling
projects cached data; a late already-observed matching confirmation may persist
its one deduplicated choice, without source/model lookup or playback. Ended idle preparation frames are released without
evicting ordinary or executing conversations from the existing bounded owner.

Use only actually loaded consenting owner Music DNA and current authorized source.
Read at most20 distinct safe genre names, rank by current Mood and earlier
confirmed For-you choices, and avoid repeating the most recent genre when enough
owned alternatives exist. No invented genres, listening facts or acoustic analysis.
Each real genre query returns at most8 records and needs at least2 canonical,
unique, unrestricted, explicitly playable tracks. Identical three mixes are
unavailable. Existing playback, pause or nonempty queue never suppress the card.

The intro uses the existing HA narrator with original Persona/Mood/locale and
bounded genre/confirmed-choice facts; an independent structured review must
approve its short first-person question. Unavailable or rejected narration uses
a localized authored fallback, never a false generated-text claim. No provider
keys, action grants or track URIs enter that narration prompt.

The exact original owner/source/Session/Broadcast/settings/DNA/history grant and
both wall/monotonic60-second deadline fence every awaited continuation and final
dispatch. A cached card survives lease expiry, with disabled actions and an explicit
refresh_request (automatic:false); polling never renews it. That compatibility
request remains manual. The additive server-owned refresh policy below is not a
client request to synthesize or replay an Ask DJ prompt.

### Confirmed Mood refresh and locale (6 November 2026)

The explicit existing session/start mood field is a Session-only welcome choice:
a valid supplied mood wins for that newly created Session without changing any
Profile default or defaults_revision. Missing mood inherits canonical defaults.
The initial runtime, opening context, first offer and returned selected_mood must
all agree. The server performs no corrective write after responding; clients
must not persist welcome previews or silently mutate Profile defaults.

Owner-selected repair scope is English/Dutch. Genuine preparation must use the
original accepted Session locale, even when the Profile/Assist default is English.
Visible genre labels are localized presentation; the owned canonical genre,
Spotify search query, frozen track mix and opaque action IDs remain unchanged.
Unknown genre names remain original taxonomy, never fabricated translations.
An explicitly supplied current app locale on an authenticated active read may
localize labels and the authored intro fallback without provider I/O, renewal or
changing Session state. A generated intro is used only for its accepted locale.

One successfully committed, non-replayed Settings3 Mood revision may schedule one new
server-owned offer for that same Session. It clears stale genre choices, never
starts/transfers music, never writes taste/history, and never retries uncertain
work. Reads, reconnect, same-revision writes and expiry alone spend no calls.
The original Session/owner/source/pairing/settings/DNA/history guards and original
bounded preparation deadline apply after every await and at publication. Late
results cannot overwrite a newer Mood revision, a dismissed client or another
Session. A failed attempt remains unavailable for that revision; polling cannot
restart it. An in-flight or uncertain explicit playback action blocks automatic
replacement rather than creating a second effect opportunity.

Additive for_you.refresh_policy schema1 describes execution:server,
trigger:confirmed_mood_revision, mood_revision, state (pending/available/unavailable),
automatic_playback:false and retry_automatically:false. It is freshness/status,
not an action grant. Native clients adopt the current server offer from the
normal active response; they never generate a refresh from a GET or replay an
uncertain selection. refresh_request.automatic stays false for compatibility.

A selection response and active projection may include for_you.continuation with
the originally accepted first_play state, result_set, playback_actions,
conversation_context and action_outcome. Continuation expires_in is recomputed
from the original wall/monotonic deadline, never renewed; mood_revision binds
its accepted Session context. Active reads accept language=nl/en in GET query
or the ordinary djconnect/read payload.language, plus existing language headers. Only an actually admitted output result
set may supply speaker buttons. An awaiting_output state must expose that exact
continuation, not the old genre IDs. Uncertain/attempted playback stays visibly
uncertain with retry_automatically:false; it cannot be silently retried or upgraded
to confirmed. Exact original explicit choices continue through the existing
normal command adapter and readback.


## Selection and dismissal

Send one normal `POST /api/djconnect/v1/ask_dj/message` with unique
client_message_id, audio_response:never, the supplied conversation_context and
choice_action:{result_set_id,action_id,operation:select}. Use opaque server
choices; never execute catalogue IDs or client-built media lists.

With one fresh active unrestricted authorized output, that genre click starts
its exact frozen mix via the existing durable dialogue reservation and normal
command adapter. Without one, the response contains one ordinary output result
set to show as an Ask DJ speaker bubble in Session Flow. Select that speaker
using the same conversation_context and returned opaque IDs. Transfer uses
play:false, confirms that output, then completes the **same selected mix**.
There is no second genre step or extra Play Now. A speaker selection without the
preceding genre request is not a standalone play grant. Explicit negation or
informational questions remain nonexecuting. Queue replacement is intentional
only at the chosen mix's dispatch; no Spotify cross-endpoint atomicity is claimed.

Dismiss via the same authenticated message endpoint, with the supplied
conversation_context and choice_action:{operation:dismiss,
result_set_id:offer_id,action_id:""}. No text/client_message_id is needed for this
negative-only action. It hides only this paired client's original Session card,
creates no chat/taste vote and invalidates its not-yet-dispatched continuation.
It never rolls back a sent playback effect or dismisses another client's card.

Only confirmation of the chosen mix's first track on the original selected
output closes the whole card for the rest of that Session. Ordinary playback,
a transport ACK or another track is insufficient. Unknown outcomes remain
visible pending, with no duplicate/automatic dispatch. A late matching
observation may confirm once; old callbacks never mutate a replacement Session.
Pause/stop/reconnect/app reopen do not reopen a confirmed card. A genuine new
Session gets a new offer. Confirmed choices alone are deduplicated and retained
compactly in the same owner Music DNA (at most20); clear removes them and opt-out
prevents use/write. Internal operation IDs never enter generic model memory.

## Qualification boundary

Golden relationship: directly exercises Session-start/playback and Ask DJ
source/effect authority. The isolated paired HTTP harness
`scripts/verification/verify_session_for_you_http.py` uses real HA routing,
SQLite and Store with declared synthetic Spotify/model responses, no network,
no live credentials and no paid provider. Unit tests cover original lifetime,
unknown/late acknowledgement, cancellation, client dismissal and recipe isolation.
These are source/runtime-transport proofs, not installed HA-dev, real Spotify,
Apple rendering, local-model, physical-device or APNs acceptance. Normal protected
Source review/CI, separate Finalization and installed/native release gates remain.

### Original output confirmation after speaker selection

For the admitted genre-to-speaker continuation, the normal output adapter may
confirm the exact selected output through its fresh post-transfer player readback
(`action_outcome.state=dispatched`, `readback_confirmed=true`, and the exact
`selected_output_id`). This private adapter receipt must also agree with the
returned playback device ID. A separately lagging devices inventory cannot revoke
that already confirmed transfer. This is output confirmation only: an old paused
track is not proof that the selected mix started. The same frozen mix still requires
its own exact output/first-track/playing readback to close the card.

Without that exact output confirmation, the existing guarded fresh inventory
check remains mandatory. A transfer acknowledgement alone, a wrong output ID or
an uncertain response does not grant playback. Neither path repeats a transfer,
retries a start or renews the original Session/context/choice lease. External
provider responses remain distinct from native/audible acceptance.

### Original late playback output witness (7 November 2026)

The existing late first-track/playing/output confirmation uses the original
accepted provider observation, never a UI status or arbitrary ordinary playback.
The private OriginalSample source/time witness must retain the exact target ID
from that same backend return before any enrichment or owner/Session await.
Its current original source/settings/command fences must still validate before
it can confirm the pending mix. A witness has no field inferred from the output
name, mutable runtime cache, historical row or a later response. Unknown/empty/
wrong output, track or state, stale source, another Session and untyped stand-ins
never confirm. This is private data on the existing source witness: no public
wire, native capability, provider dispatch, new permission or lease extension.
It does not recreate the original uncertain request or authorize its replay.

### Existing committed DNA basis during unrelated metadata persistence

An already prepared offer compares its exact original committed genre snapshot;
polling does not acquire a replacement basis. A pending unrelated metadata save
may not replace that read basis with a missing-DNA result. Comparing the original
loaded source is permitted only while the same manager/data/memories/owner row/
genre containers, selected genres, generation, safety epoch and original privacy
fences still match. A new snapshot remains unavailable during persistence.

Changed/cleared/disabled genres, owner or manager replacement, unobserved
container A-B-A, failed/cancelled writes and withdrawn admissions still retire
the original. No recovery revives an old snapshot after failed persistence.
Read/cached projection never extends the original60-second dual-clock choice,
creates another offer, warms data, grants playback or retries an attempted or
uncertain operation. Other clients need the same loaded Profile memory owner;
a missing/different manager cannot borrow the original cached admission.
