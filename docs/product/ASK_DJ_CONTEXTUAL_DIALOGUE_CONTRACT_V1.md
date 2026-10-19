# Shared Ask DJ contextual dialogue contract v1

Assignment `DJC-CORE-ASKDJ-CONTEXTUAL-DIALOGUE-V1-20261013`; companion
[experience](ASK_DJ_CONVERSATIONAL_EXPERIENCE_V1.md). This directed refinement
is committed before production changes. Existing source-main
`c955ec80407f4ab0237bc4e9381761d3c9274617` was the admission base.
[Protected source readback](../verification/ASK_DJ_CONTEXTUAL_DIALOGUE_V1_SOURCE_READBACK.md)
separately records source #1166, exact archive/formal proof and open consumer/install boundaries.

## Single application boundary and compatibility

Existing `/ask_dj/message`, WebSocket message and text/STT adapters invoke one
Profile-authorized conversation service, one existing Ask DJ interpretation/tool
core, one context/style/choice owner and one response/history acceptance unit.
`conversation_context` is optional enrichment, never an alternate pipeline.
The old Session wrapper is reduced to qualified context/reference helpers.
Developer/raw calls normalize to the same interpretation service with their
explicit existing persistence/auth contract; they do not fork conversation logic.

Existing identity, `client_message_id`, `text`, locale, numeric `mood`, legacy
`dj_style`, `audio_response`, cards, art, sources, `playback_actions`, confirmation,
revision/clear and STT transcript fields remain compatible. Missing old context
is an empty context, not a legacy engine. Contextual requests still require a
valid client message identity; old id-less transport receives a generated turn
identity and cannot claim idempotent retry without retaining that identity.

```json
{
  "client_message_id": "client-turn-1",
  "text": "Who is that?",
  "language": "en",
  "conversation_context": {
    "session_id": "current-session-or-null",
    "selected_entry": {"session_id": "selected-session", "entry_id": "entry-id"},
    "thread_id": "optional-current-owner-thread",
    "result_set_id": "optional-shown-set"
  }
}
```

The existing selected-entry shape remains accepted. Additive live reference is
typed `{session_id, moment_id}` under `selected_moment`; it is mutually exclusive
with `selected_entry`, owner-only, published-only and deadline/rights checked.
It grants neither an archive write nor a shared/private model permission.
Response retains existing fields and adds a versioned `conversation` projection:
turn/thread identities, confirmed effective context, input type, source basis,
optional canonical Flow entry IDs and exact result-set/action IDs/status. No
screen-origin or client-supplied owner is authority. Capability/contract version
advertise this common boundary; absent optional fields work with older clients.

Both screens use the same default owner thread, or the same explicitly retained
thread ID. A different explicit thread does not silently import another thread.
Existing HA-user history stays historical data; no unconditional import into
Profile conversations. Default and explicit Profile history/clear adapters map
to the shared paired-owner namespace. Explicit legacy administrative history
compatibility remains an authorization-bound read/clear projection, not an
alternate writer, promptstack or dialogue-memory policy.

## Context owner, limits and lifecycle

Extend the existing Ask DJ history owner with bounded operational conversation
state. No second eventbus, durable chat store or persistent profiling. Per-owner
thread: one model-safe window of12messages/12KiB and one local operational
window of12messages/12KiB. Local catalog captions never enter model input.
There are4typed subjects, at most20compact source dependencies, one result set
of12items/16KiB (the scoped album-track exception is defined below), one pending confirmation/8KiB and a20-minute idle expiry. At most
4 threads per owner and 32 retained owner states; admission at capacity fails
closed rather than stealing live in-flight state. External agent memory is not
trusted: each call starts fresh with the explicit qualified window; returned
`conversation_id` is not reused after clear/expiry/owner or Session changes.

One active semantic/model turn per thread. Identical in-flight IDs join the same
bounded result; every joining transport revalidates its own owner and the
original Session, playback, source expiry, history and generation before delivery.
Dispatch membership fences may be consumed by a successful turn; response
admission instead binds to the accepted replacement offer and retained evidence.
This remains RAM-only within the existing reservation, without a completed raw
response cache. Different open questions receive busy/retry semantics. Explicit
fast controls may execute without a broad model lock and do not erase topic or
choices. Only short reserve/state/history/reference commits use owner/Runtime
locks. Model/provider waits hold neither storage nor broad Runtime lock.

Scope binds server Profile/install, privacy, clear generation, relevant source
rights and optional Session generation. A question depending on playback also
binds its actual item; independent trivia does not. Revalidate before model
input, effect and private response/history/Flow acceptance. End/replacement
invalidates Session-derived context and pending outputs; general Ask DJ survives.
Explicit selected old entries remain read-only; new turns never append there.
Clear removes conversation content/choices and invalidates in-flight windows.
Relevant source withdrawal removes derived model snippets and response visibility.

## Typed model/data-rights boundary

### Semantic interpretation of contextual reads

The named-artist catalog repair also admits a closed `artist_tracks` read. A
named reference carries only a bounded public `artist` string plus the existing
read/reference/exclude_current fields; contextual current/selected references
carry no name. The configured HA agent interprets free wording and typos, never
proposes recording facts, provider IDs or playback. Core resolves the proposed
name through the existing artist-profile read and then the existing track-search
read. Only actual recordings credited to that canonical artist ID qualify.
This is a bounded Spotify catalog sample, not a chart ranking or a claim that
all hits were found. An explicit more/other request omits the freshly observed
current recording. Missing/unsupported/provider-failed reads return functional
music guidance, never a false history-storage explanation or guessed titles.
Existing frozen result/action IDs own a later explicit Play action; listing has
no playback/output mutation. Catalog fields remain local display data under
their existing retention and model-processing boundary.

The17October Armin report separately exposes Apple's generic error label. An
unavailable-history label is not evidence that the failing operation was a
history request. Root-cause attribution requires an actual transport/acceptance
receipt; this producer repair does not retrospectively claim that evidence.

Literal recognition is a fast path, not the supported vocabulary. An otherwise
unresolved contextual question may use one call to the same qualified HA agent
to interpret typos and free wording in any supported language. Its closed read
plan selects artist/recording identification, edition date, album tracks, queue,
Forecast, previous recording or an alternative album. Core resolves identities
through the existing read owners; the model receives only the current question,
locale and context-availability booleans, never catalog text, URI, history,
Profile data or HA state. A selected contribution is retained while this meaning
is unresolved. Explicit independent named topics still detach from that chip.

When a qualified public subject was only inherited, the first existing
research-generation call may instead return this same closed readplan. It
receives only the already-permitted qualified public evidence plus the minimal
availability flags. Actual factual prose still requires its independent second
assessment; no third call or unassessed factual answer is introduced. Missing
public evidence cannot block a genuinely local contextual read.

The plan has no playback, command, output, settings or arbitrary argument slot.
It cannot grant an effect, infer a public artist name, answer from model memory,
or initiate a second research chain. Invalid/ambiguous output asks for
clarification without a repair call. Existing private/injection/gibberish
exclusions precede interpretation. One interpretation plus local read stays
within the existing two-call budget. Existing factual research keeps its own
generation/assessment budget and source qualification.

Capture Session/item state before interpretation and revalidate it before the
chosen current-context read, response delivery and Listen. Selected references
keep their owner/source/expiry guards and cannot silently fall back to current
playback. Golden qualification must include genuine held-out paraphrases and
typos in all five languages using the real HA model path, separately from
deterministic plan validation and read-owner tests. A mocked plan is no evidence
that a language model understands new wording.

Core builds a single bounded data projection: current user question, approved
recent turns, qualified subject/credit facts, actual anonymous tool outcome/count,
style, and optional supported Session context. Maximum serialized Core input
24 KiB including its instructions; UTF-8 bytes provide a conservative token
upper bound, with actual provider usage reported where available. At most two
agent calls and two bounded music lookups per turn; simple controls use zero
agent calls. Per-call deadline is bounded; no retry repeats an external effect.
Configured agent's own system/tool context is a separate reported boundary.

| Data | Client view / retention | Model processing in this reactive request |
| --- | --- | --- |
| Current user question / explicit artist name | Existing authorized private conversation | Necessary user input, bounded; no instruction/tool authority from quoted data. |
| Qualified MusicBrainz core or Wikidata CC0 normalized credit/entities | Existing independently qualified source/retention | Targeted factual projection/excerpt with attribution, after source/owner revalidation; not raw payload or supplementary text. |
| Internal validated Session direction / confirmed Persona/Mood | Existing contextual view | Minimum typed style/context; no Horizon, planner slots or Runtime serialization. |
| Spotify catalog/playback/results, artwork, raw provider bodies | Existing eligible local cards/tools and retention | Excluded, including copied catalog reply text; anonymous result IDs/counts are Core operational data, not a content export. |
| Saved listening history / unqualified historical body | Existing local owner queries only | No model scan or archive text export; local bounded query answers remain. |
| Recent agent prose | Existing private retained turn if permitted | Only marked model-safe prose, same thread and still-valid transitive dependencies. |
| Music DNA / user preferences | Existing opt-in owner | No blanket model export; functional topic/choice memory needs no DNA opt-in. |
| Tokens, account IDs, prompts, raw audio, HA states, private image grants | Internal approved owner only | Never in this projection; source/tool text is data, never a system/tool grant. |

This is a narrow new reactive processing qualification. It leaves proactive
Moment realization/speech, archive permissions and unknown-source no-model
rules unchanged. MusicBrainz distinguishes [CC0 core and supplementary
data](https://musicbrainz.org/doc/About/Data_License); Wikidata [structured
data](https://www.wikidata.org/wiki/Wikidata:Copyright) is separately CC0.
The [Spotify policy](https://developer.spotify.com/policy) excludes Spotify
Content ingestion into models; display/retention does not substitute for that
permission. No general legal/provider-policy override is granted here.

General agent knowledge is not a fetched source, credit proof, URI or playback
readback. Attribution labels distinguish selected credit context from additional
knowledge. Explicit quoting returns faithful allowed text locally. Unknown
rights produce local alternatives/clarification; never a fabricated biography
or a blanket fallback echo for otherwise qualified public context.

For general explanations of musical influence or approach, prefer established
musical characteristics. Precise origin stories, accident anecdotes and causal
biographical incident details require supplied source-qualified evidence; omit
them when that evidence is absent. A general-knowledge label does not verify
such an incident. This is an expression boundary, not a new fact provider or
an automatic factuality validator.

## One style resolver

Active or paused Session context uses confirmed `dj_persona` and symbolic
`selected_mood` plus their Session authority. Outside it: explicit supported
four-persona selection, otherwise documented Home default, existing Profile
`response_style`, Profile `MoodState` and legacy request numeric Mood according
to the existing `mood_zone_for_value` ranges. Mood state/selection source is
reported; no symbolic-to-numeric invented conversion. Profile `voice_style`,
legacy `dj_style` and TTS profile remain separate voice/compatibility fields,
not Persona identity. Resolution never starts a Session or writes preferences.
Temporary refinement does not change Mood or persistent taste.

## Choice, action and semantic acceptance

Result-set IDs bind owner/thread, exact shown order and typed original provider
items, source/backend/output authority and ten-minute or earlier source expiry.
Each action has an immutable ID; a model may select a known index/ID but cannot
mint a provider URI or effect grant. New results replace the current set;
ordinary controls preserve it. Expired/changed sets fail rather than re-search
and silently select a different second result. Play tap and textual/STT choice
reuse the same existing action execution and revalidation. Preview never plays.

Reserve client identity and request digest before work. Same identity/different
text/context conflicts; completed retry reuses existing accepted exchange.
Before an external effect, register a compact opaque replay-safety receipt in
the existing history owner, separately from conversation body retention; no
full prompt/URI/provider payload. Private/nonpersistent content remains absent.
At the existing bounded tombstone capacity, fail closed instead of evicting a
receipt while an old effect can still repeat. A dispatched uncertain request
cannot auto-execute again after cancellation/storage failure/retry or reload.
Expose requested/dispatched/confirmed/failed/uncertain distinctions. “Playing”
requires applicable readback, not successful model prose or merely a request.

Existing Store body acceptance and optional active-Session reference transaction
remain the semantic turn commit. Short commit cancellation finishes acceptance
or rollback before releasing locks. On reference failure, remove the newly
unaccepted Store exchange; retain necessary effect replay safety. No opportunity
or proactive count is consumed. Reactive `conversation_user`/`conversation_dj`
references do not increment `moments_published`; presence-Off permits questions.
No private output is broadcast to VibeCast, push, notifications or widgets.

## Verification and delivery gates

Actual base baseline: selected informational request returns original quote
before the agent; retained Session exchange has two messages but zero prompt
messages. Preserve this receipt. Demonstrate one call graph/acceptance policy
and a shared scenario matrix with/without context; older APIs/STT normalize
without a rollback switch selecting a second implementation. Previous-version
deployment can ignore additive fields; source/hash pins distinguish behavior.

Real isolated ordinary pairing → common service → existing tools/agent → true
outcome → history commit → next turn. Providers may be explicit fixtures for
failure/transport; actual configured-agent answers separately qualify product
quality in full mixed sequences, five languages and four Personas. Missing
agent access/budget is an explicit unfulfilled qualification, never fixture-PASS.
Measure Core context bytes/token upper bound, calls, latency and state limits.
Review ambiguity/quotes/topic and track change, stale choices, owner isolation,
injection, clear/end/revocation in-flight, cancellation, duplicate/retry/uncertain
effect, private mode and long dialogue. Run owning/security/coverage and existing
Ask DJ/text/voice/history/search/presence/Mood/Forecast/ambient/summary regressions.
Early exact producer fixtures go only to existing Apple #87; native adoption
and installed/hardware/joint acceptance remain open. Exact source publication,
protected merge/artifact readback and separate Finalization retain their gates.

## Owner addition: proactive Track Insight navigation

Qualified detail now takes its evidence from the original normalized fact, never
from an already creative Moment narration. Generated summary/full_text/optional
listening interpretations require bounded structure and independent content,
language and style assessment through the same guarded HA Conversation owner,
maximum two calls. Revalidate the original source/owner and configured pipeline
around both calls and before cache/response acceptance. Failed assessment keeps
only the qualified factual context; rejected raw prose is not cached or exposed.
Credits are useful context, not measured genre/energy/instrumentation. The
recording-analysis source gap remains explicit until real evidence qualifies it.

The owner-approved [Moment → Track Insight drilldown](MOMENT_TRACK_INSIGHT_DRILLDOWN_V1.md)
is part of this same assignment. Its directed contract precedes its runtime
changes. One target resolver and existing TrackInsightService serve explicit
Ask DJ in both composers and qualified inert Moment actions. Exact recording,
navigation-only admission, original rights/deadlines and consumer opt-in are
mandatory; a selected earlier subject cannot become current playback silently.
Core delivery and native adoption retain distinct acceptance statuses.


## Connected implementation refinement

### Qualified reads, controls and output selection

The current queue route is a read, not an append capability. Preserve reported
order and repeated recording occurrences; do not infer an upcoming item's album
or playlist from the currently playing context. Invalid identities yield partial
coverage, never a fabricated playable card. Empty, unavailable and partial are
different results. A queue or Forecast read has no preliminary status lookup,
generation, model call or playback effect.

The old similar-tracks helper incorrectly used `play_uris` while claiming to
enqueue. Retire that effect and claim: an unsupported append request may return
qualified suggestions with explicit Play actions, but cannot start or replace
playback. This correction does not introduce a queue writer or queue planner.
An explicit request to play similar tracks keeps the existing typed Play route.

Fast controls use the typed existing command, not reparsing through music search.
Use its actual post-command playback readback. A volume confirmation requires
the observed target value; an output confirmation requires the observed exact
output identity. Forward the existing observer/Broadcast projection receipt.
Never treat the pre-command snapshot as confirmation or generate an extra
announcement/model call for a skip.
Fast controls do not prefetch an unrelated queue. They preserve the current
conversation choice set; an explicit queue question provides its own qualified,
expiring result set through the shared queue-read projection.
Existing `track_mix` cards remain one bounded choice with at most50 canonical
track URIs. Explicit Play binds the entire original ordered URI array; neither
client metadata nor a later search may substitute the mix. The same choice owner,
expiry, effect receipt and existing playback processor apply. A typed legacy tap
still needs a live producer offer; arbitrary or archived client URIs are not a
replacement for that offer. Malformed payloads and stale backend revisions retain
their existing400 errors before choice lookup; expiry remains409.

Output selection is inert. Activate transfers to the selected, currently
available unrestricted output with `play: false`; it cannot reuse a previous
Play proposal. Explicit Play on a compound result additionally binds the exact
recording/context and output. Spotify Play carries that output's `device_id`
at the actual request boundary, including retries; transfer completion alone is
not proof of request ordering. Recheck a fresh output inventory before dispatch.
When a Play request has no active output, it offers a new frozen output choice
instead of silently transferring to a default speaker. The new offer preserves
the original media/request and receives its own choice identity; an old media
selection must not suppress admission of that offer.
Negation, stale/restricted/cached-only outputs, expiry and revoked owner/source
authority fail closed. Text/voice and existing typed taps share these validators.

All application text, post-STT voice, raw HTTP compatibility and Ask DJ command
adapters enter `ask_dj.service.async_exchange`; optional Session context only
enriches this service. Read-only legacy administrative history remains an explicit
`conversation_scope: legacy` projection. New writes use the paired Profile scope;
there is no legacy archive import into functional or model memory.

The configured HA agent must advertise no control capability and no broad Assist,
response retention, web/code tool or HA-state-template context. Qualification is
checked before and after each fresh HA chat session. A scoped call never retries
through a different default agent. Existing broad HA agents are a configuration
qualification gap, not implicit permission to expose home tools. Production keeps
HA Conversation; existing OpenAI API access is used only inside the owned lab.

Opaque effect receipts are reserved immediately before the existing Spotify or
Music Assistant mutating dispatch, after token/owner/source awaits. A token failure
before dispatch is retryable through the same functional conversation; a possible
send followed by timeout, cancellation or failed acceptance is uncertain and is
never automatically repeated. There is a final synchronous owner/source/revision
fence after the last acceptance await, inside the rollback boundary. Result-set
identity, order, action, Session and original deadline are also checked there and
at the actual adapter, including retries. A biography is not playback authority.

Live accepted response bubbles preserve eligible images/audio/cards/actions in
`assistant_message` and `messages`; `media_delivery_basis: current_response_only`
marks this delivery. The Store keeps its separately qualified archival subset.
Replayed archived exchanges do not fetch or resurrect expired transient assets.
No private turn or confirmation produces an automatic push notification.

[Moment Track Insight](MOMENT_TRACK_INSIGHT_DRILLDOWN_V1.md) adds only a closed
navigation offer to an eligible published Track contribution, then uses the same
owner-resolved TrackInsightService from either Ask DJ screen or explicit detail.
It is a user-selected read, distinct from an ordinary current-playback request.
Source #1162/Finalization #1163 and earlier product deliveries remain closed.

## Acceptance refinements: archive rights, owner clear and bounded choices

The existing ten-track recommendations remain selectable within a maximum of12
qualified actions/16KiB; model-led lookup still retrieves at most8 rows per call.
The limit bounds one immutable set rather than silently forgetting visible later
track cards. A batch queue action retains its existing explicit action route;
model text and ordinary selection never grant queue replacement.

Clear revalidates current pairing, loaded integration and device-bound Profile
inside the existing serialized Store mutation, before and after persistence. A
failed save or withdrawn owner rolls back the prior Store/RAM state and does not
invalidate the conversation. Storage refusal is typed503
`history_storage_unavailable`; cancellation settles the existing writer first.
History read, state, export and clear share the default Profile namespace. Only
explicit `conversation_scope: legacy` with authenticated HA-user authority can
read/clear the preserved former archive; malformed scope cannot select it.

A successful RAM-only/raw turn marks that subject's short window non-archiveable.
Switching to the ordinary message route does not grant retention for its dependent
follow-up. An explicit independent new subject resets that bounded operational
context and can qualify new persistence. Private-mode and live-only source grants
retain their stricter scope/expiry fences. No second memory owner is introduced.

Discussing analysis returns text plus bounded `analysis_basis` and qualified
credit attribution, without screen-navigation fields. Explicit five-language
detail requests can open the existing detail; negation keeps the discussion in
chat. Unknown measured audio remains unknown. Catalog captions use local templates
and five languages; they are not model-processing permission. Controls report
successful dispatch, and 'playing' is reserved for qualified playback readback.
Malformed structured model output fails502 without a card, action or archival
commit. A safe typed lookup with a missing caption receives a local search caption;
the existing catalog tool still owns the actual results.

Voice binds the paired Profile before audio input/STT. Synchronous fences after
body-read, STT and service acceptance prevent an owner change from disclosing
the old transcript, generated text, assets or error details. Failed STT creates
no accepted turn. App errors and success responses remain no-store.

A lookup/refinement model response supplies only a typed read-only query; Core
owns the resulting localized caption and actual cards. Invalid structured lookup
output or a wrong operation may receive one format-only retry through the same qualified HA agent,
within the existing two-call bound and repeated owner/source checks. Invalid
output is not returned to the model as context. A second invalid response fails
502 without lookup, effect or archival acceptance. A factual question cannot be replaced
by a model-proposed search/choice object; its retry requires ordinary answer prose.
There is no automatic replay
of music commands and no different default agent.

The same reactive prompt realizes four recognizable forms: Home uses calm
plainspoken context; Radio uses two short fact/meaning sentences; Club uses one
compact precise sentence; Festival uses two or three warm sentences with varied
rhythm and concrete musical detail. There is no obligatory metaphor or closing
scene/invitation. Persona names do not authorize
festival/event claims or fictive performance context. User language remains
exactly en/nl/de/fr/es; identity/credit/role facts remain unchanged and uncertain
gender uses neutral naming. Actual generated examples receive independent
editorial review; these forms never consume proactive style memory or budgets.


## Connected live-regression refinement (before corresponding runtime fixes)

Decision input: Core6154181590,6154227030,6154393277; Apple6154194577,
6154234425,6154408539. Same assignment, sole writer and base c955ec80;
no new Planner, provider, consumer writer or transport project.

### Baseline and qualification boundary

The exact user question is **wat was vorige nummer**. On local checkpoint
ba84d2aca0ebaac29295540b7b04e3d2d43d0055 the shared classifier selects
previous, then the existing skip handler passes the whole question to the
music text parser. In the isolated real paired HA/Store/SQLite chain, an
explicit external artist-search fixture returning unrelated qualified media
leads to one PUT /me/player/play, zero model calls. This proves the source
failure path; it does not establish the installed producer or native cause.
Older104HTTP/69model qualification does not cover these later findings.

### Current user authority, separate from request ownership

An authenticated request is not permission for every music effect. One
immutable current-turn grant records its provenance, allowed effect families
and exact target binding. Questions, quotes, mere selection, navigation,
negation, hypothetical explanations, model proposals and old commands confer
no effect authority. Polite but unambiguous execution requests remain commands.
The common classifier resolves this speech act before broad action keywords.

A typed control stays typed all the way to the existing command use-case:
previous can dispatch previous only, never reinterpret its text as artist play.
Current valid result-play, a validated pending yes or an existing trusted typed
command may add only their expressly confirmed family/target. Receiving an
answer/action list does nothing. Select alone is inert. Retry without proof of
pre-dispatch failure cannot authorize a second uncertain effect.

The existing use-case owns normalization and target resolution. It verifies
this grant, captured Profile/backend/account/output authority and target before
command dispatch. The actual Spotify mutating request / MA service boundary
rechecks the same immutable command context after token/provider awaits, before
receipt and transport. Model-to-tool mutation is denied even if a model tries.
A transport outside a qualified command context is denied during a dialogue.
Compound speaker+play requires explicit authority for both targets; choosing an
output alone preserves existing playing/paused state and cannot add play.
No second action engine or general event bus is introduced.

HA Conversation qualification must prove no household tools, retention or state
context. CONTROL=False alone is insufficient. The supported provider's public
configuration has no Assist API/tools and a static system prompt; dynamic
Jinja context is unqualified, including states property access. Require present explicit scope/prompt metadata rather than silently using defaults.
The owned lab uses the current public HA OpenAI config version2:7 and selects
its exact subentry/entity via the public entity registry, not a legacy parent
alias; older v1 migration can create an additional default agent. Check before
and after each fresh conversation; never switch to an unrestricted default.
No agent/service/configuration changes are authorized by this design.

### Private backend reads and quarter-hour intent

wat komt er komend kwartier aan resolves the existing circa15-minute Session
Forecast direction, plus a necessary bounded queue read from the same existing
owner/backend/account resolver. It never requests private Horizon slots, creates
future-media claims or sends raw catalog/Forecast/artwork data to the model.
Existing Core forecast realization supplies the Persona/Mood narrative; local
five-language catalog captions and cards supply genuinely observed queue anchors.
Intent and observed queue order are separate claims; shuffle/autoplay and finite
queue do not prove every upcoming track. Without a Session, report the queue
but do not invent a DJ plan. PresenceOff permits this explicit private answer.

Queue observation records schema/version, state, captured scope, as_of, bounded
coverage and reason. States distinguish not_requested, present, known_empty,
unsupported, unavailable, stale, partial and withdrawn. None, absent queue,
fetch failure or foreign authority never becomes known_empty. Invalid/unrenderable
items mean partial, not empty. Preserve exact case-sensitive media IDs, repeated
queue occurrences, source order and the provider's separate now-playing field.
Use the same existing queue-use-case and normalization as the standalone route;
no cache/provider fetch on unrelated questions. Queue/speaker error responses
contain useful localized explanations, not an empty heading or canned invitation.

Previous-track information uses accepted qualified owner observations / existing
history projection, not a previous command, client cache or guessed playback.
Stage1 observation limits and missing history remain explicit; no exact same-track
replay claim, playback reconstruction or seek occurs.

### One rich current response, bounded result authority

Keep actual items and playback/output actions on top-level and live assistant
message, attached to the same immutable turn/result-set/item identities. The
full text archive and transient action grant are different rights. Never persist
catalog/artwork/action bodies without qualified retention. Current response-only
values are not reconstructed from old retained text after reconnect. A valid
RAM result may be revalidated against owner, backend/account/output, Session,
source and original deadline through the existing shared route. Lost/expired/
withdrawn authority leaves historical text inert with a typed reason.

General and Session responses use the same result/action contract; opt-in Session
Flow references do not become a second conversation store or decoder. Exact
artistX/query/result/art/action remain X while playbackY becomesZ. Selection and
PlayNow use the identical frozen item, not array index after reorder or a new
fuzzy title lookup. Speakers retain Activate/Active state and exact output-ID;
no inventory/read/presentation causes transfer or playback. Native shared result
rendering/adoption is Apple-owned and remains separately open.

### Direct control outcome and timing

Distinguish immediate native pending, dispatched provider request and observed
state. Use a necessary targeted existing read/observation after a qualified
explicit effect, without an extra poller or fabricated state. Apply confirmed
playback/output through existing Runtime/Broadcast acceptance immediately;
no LLM/TTS/artwork/history reload/card-dwell dependency. Source/owner/Session
fences survive all awaits. New proactive Moments still obey normal publication,
presence and pacing; pause/volume requires no new Moment. A→B does not rewrite
immutableA or showA as currentB. Trace monotone durations per host; correlate
turn/result/command IDs, and report dispatch/state/Moment timing separately.
Native reducer/render timing cannot be claimed from Core HTTP measurements.

### Connected acceptance additions

Before/after actual paired chain measures real effect dispatches: exact previous
question, informational/quoted/negative/hypothetical control text and malicious
agent attempt must yield zero; explicit previous/next/pause/volume/exact-result
play/output yields only the intended effect. Test result deadline/owner/Session/
backend/account/default/output changes during adapter waits, duplicate/retry/
cancellation and pending staleYes. Keep playbuttons; don't solve safety by
removing all actions. Test current-response and nested-message media equality,
archival subset, reconnect/revalidation and source withdrawal.

Same filled queue and current scope produce useful items/actions in AskDJ and
the standalone queue. Include duplicate title/different artist/version, missing
art, repeated track, case-sensitive ID, partial/empty/error/stale/foreign scope,
quarter-hour forecast ready/limited/expired/missing and noSession. Reads do not
mutate playback/queue/Session/Mood/presence or model context. Real five-language
four-Persona multi-turn transcripts demonstrate direct relevant answers without
ritual greeting/footer, correct roles, subject and actionable real results.

Exact technical/privacy and conversation/UX reviews follow the final candidate;
public/source/installed/native/hardware/joint states remain separate. Apple#87
receives pinned real transport fixtures and explicit adoption/timing boundary.


## Independent-review refinements

The registered HA `djconnect.ask_dj` raw service normalizes through the same
owner-authorized message adapter and exchange as HTTP, with `persist_history`
false. It retains optional request identity for replay safety, and cannot reach
a separate agent or effect path. The message service keeps its existing
persistence policy. Service transport does not weaken agent qualification.

When explicit Play binds output B, confirmation requires the observed exact
media/context identity, playing state **and output B**. Same media on another
output or missing output identity remains dispatched, without an automatic retry.

Qualified CC0 credit attribution preserves bounded provider, HTTPS source URL,
license and `qualified_credit_only` scope in live sources and source links.
Additional model knowledge is separate from the credit evidence; archive rights
remain governed by the existing per-turn source acceptance, not the live fields.
A selected catalog result can identify its one displayed artist locally, without
transmitting its fields to the model. Multiple credits require clarification;
unqualified additional explanation cannot be invented or fetched under a new
source permission. Ordinary genre phrases are localized; generated answers must
respect the selected Persona sentence form and omit unsupported named techniques.

A successful generated answer may retain the user's explicitly named subject in
one existing bounded subject slot (`user_named_subject`, `user_explicit_name`).
This is reference resolution from user input, not catalog import, verified credit
or biography. Accepted topic change replaces it; controls preserve it; existing
clear/expiry/privacy/source fences still apply. Possessive follow-ups refer to the
discussed subject in third person. The narrator's Persona cannot become that
person or supply their musical facts.

The common answer parser checks a closed set of ordinary English genre phrases
in non-English prose. Original quoted
work titles are exempt; this is not a general language detector or fact checker.
An invalid format can use the existing single read-only format repair, within
the same two-agent-call maximum and all source/owner fences. The invalid output
is not replayed as model context, rewritten, archived or accepted. Repeated
invalidity returns the existing typed model-response error. Lookup JSON and
local catalog captions retain their existing separate format contracts.

Independent review refinement: Persona form remains a generation and actual
content-review contract. A heuristic sentence counter must not reject valid
music answers containing initials or ordinary abbreviations; no such counter
is part of runtime acceptance. Festival requests three connected sentences
within the established two-to-three sentence range. The existing bounded
repair is retained for demonstrable genre-language format violations. Closed
phrase checks also cover untranslated ordinary occupation/sound descriptions,
double German genitives against actually supplied two-part subject names and
the observed malformed Dutch sound descriptions. Names and quoted work titles
remain exempt; this is not a general grammar, biography or factuality validator.
Localized wording examples introduce no new subject facts or source rights. This
neither adds a general language engine nor guarantees every future model's
style; exact generated samples require independent review.


## HA-native service authority preservation

The existing registered `djconnect.ask_dj` service also operates on a
`conversation_agent`-only integration, whose server identity is
`djconnect-conversation-agent` and which has no app device token. Its internal
adapter uses the service closure's loaded ConfigEntry/runtime and the canonical
server-owned binding for that identity. Payload routing hints cannot choose a
different device or Profile. Missing/unloaded/replaced entry, withdrawn or
reassigned Profile/source and privacy denial fail closed at the same exchange
await/acceptance fences. No fallback Profile or forged app token is introduced.

Both raw and message service normalization reach the same `async_exchange` and
interpretation/agent/tools/acceptance; raw retains `persist_history=false`.
The private runtime authority is a Python caller argument of the registered HA
service, never a request/header flag. HTTP/voice/websocket device ingress still
rejects `conversation_agent` and requires normal supported-device auth. The
agent-only service's existing configured binding is its authority; ordinary
paired app acceptance is separately proven and never replaced with HA-user
credentials. Qualify actual registered service, duplicate/control, unsuitable
agent and entry/owner withdrawal on the no-device-token configuration.

## Pinned local qualification and consumer fixtures

[Core qualification](../verification/ASK_DJ_CONTEXTUAL_DIALOGUE_V1_ACCEPTANCE.md)
and [observed transport projections](../verification/fixtures/ASK_DJ_CONTEXTUAL_DIALOGUE_V1.json)
bind to runtimec21dc337. Product/conversation review is GO only for the actual
HA/OpenAI `gpt-6-luna` lab configuration. Historical `gpt-4.1-2025-04-14` GO and
the current `gpt-4o-mini`
conversation-quality NO GO remains recorded. No Core model default or mandatory
provider is added. Source publication, native/installed/joint qualification and
environment updates remain distinct milestones.

## Current-artist identification corrective contract (2026-10-14)

Simple deictic identification (`welke artiest is dit`, `Welke artiest is dit?`,
`wie hoor ik nu`, `wie is dit`, and qualified five-language equivalents) is one
informational `current_artist_information` intent in the existing text/STT
interpretation. It cannot authorize a pending proposal, catalog result or previous
music retry. A newly admitted identification clears an older music retry even if
its subsequent read is rejected. Richer independent artist questions retain the
same existing separately qualified knowledge/generation path.

A valid explicit selected contribution wins over unrelated current playback.
Stored playback identity/metadata comes from the authorized historical projection;
a selected live CC0 contribution can identify a uniquely qualified artist subject,
never infer that a composer/producer is its performer. Missing selected evidence
does not borrow the current artist. Source attribution and applicable original
source links remain present. No external model receives Spotify metadata.

Otherwise the existing bound backend status use-case supplies fresh metadata;
there is no `last_playback` fallback. Missing identity, cached/stale/withdrawn or
expired evidence gives an honest localized unavailable answer. Two bounded reads
(maximum five seconds each) must agree on identity/title/artist. When an active
Runtime supplied a playback item at admission, the provider identity must match
that captured item and the same Runtime/item must remain valid at acceptance,
even when the caller omitted optional Session context. Track/Runtime changes
reject with `playback_context_changed` or `session_context_changed` (HTTP409),
without silently answering for another item or granting an effect retry.

The metadata response is text-only, with empty `playback_actions`, no lookup,
model call or automatic playback/queue/output/Mood/Session change. Its mutable
current or restricted metadata is marked private/current-only through the
existing shared acceptance owner, not granted durable archival/model retention.
Ordinary device auth, Profile/source withdrawal, in-flight joins, selected-source
rights and turn/client-message correlation remain mandatory. Production/native
acceptance is separate from isolated HA/provider-fixture qualification.

Selected frozen catalog-result referents retain their existing priority over
implicit current-playback identification; explicit qualified entry/Moment context
retains its own priority. An admitted new artist-information turn clears an older
music retry before selected-source validation can reject it. Neither rejection
nor retry grants permission to execute the earlier music request.


## Selected accepted-reference speech adapter

The [Session speech delivery/replay contract](SESSION_SPEECH_DELIVERY_V1.md)
extends this same common application service for both screens. Interpretation
and helpers no longer synthesize or activate a speaker before semantic
acceptance. Explicit `speech_contract_version:1` (WAV uses
`X-DJConnect-Speech-Contract-Version: 1`) selects private accepted-reference
preparation. Manual Listen remains available after never; replay uses the exact
accepted text and original style, without re-executing the question or music
action. Old private audio requests receive a concrete client-protocol upgrade
outcome rather than a silent downgrade to the legacy bearer-free ESP URL.
Retained DJ answers use the existing owner entry/history dependency query;
unknown old style/locale is not backfilled. This adds neither a second Session
implementation nor extra conversation/summary/publication events. Native
postacceptance audio-adapter adoption and actual listening remain open.

## Corrective increment: named catalogue results (2026-10-17)

User-reported defect: a catalogue question returned only the result count;
“which ones?” then reached the prose agent with the same anonymous count. The
agent must not invent titles or acquire catalogue processing rights to repair it.

Named availability questions (“what do you have by …” and the five-language
counterparts) enter the existing typed, read-only lookup operation. Core renders
the actual accepted titles and artist subtitles into the current reply and live
`assistant_message.text`, in precisely the existing card order. Empty lookups
retain the truthful zero-result caption. Labels are display data, not new facts.

A direct result-list follow-up uses the current owner's existing frozen set:
normally maximum12items/16KiB (or the scoped album-track offer below), identical result/action IDs, selected action and original
deadline. It performs no model call, lookup, selection or playback effect and
cannot renew the offer. It returns `items` and the existing `result_set`, with
empty `playback_actions`; explicit selection/Play remains the established route.
A supplied mismatching set is409; expired/cleared/absent/other-thread lists give
a localized unavailable response. Session-dependent sets revalidate the actual
Session even when the follow-up omits its old context chip. Owner/source/clear
and response delivery guards remain authoritative.

The initial durable exchange keeps its original safe count/query caption.
Catalogue labels are supplied only in the current transport reply; a local list
follow-up is nonpersistent. Neither becomes a model-safe prose turn, a durable
catalogue archive or a new cloud-TTS processing grant. No public VibeCast/push
projection, Store migration, source capability or client implementation change.

[Corrective qualification](../verification/ASK_DJ_RESULT_TITLES_CORRECTION_V1.md)
distinguishes real isolated HA acceptance from external provider/model fixtures
and from native/installed acceptance.

## Public music research refinement, 17 October 2026

[Public music research v1](ASK_DJ_PUBLIC_MUSIC_RESEARCH_V1.md) replaces reliance on
general model recollection for an explicit researchable music question with
actual bounded Wikipedia retrieval and optional public web sources. Both screens
use this same owner exchange. Partial-name questions retain a uniquely matching
qualified selected subject; unrelated explicit questions do not inherit it.
General model knowledge is never a substitute for a failed attempted lookup.
Source qualification/answer assessment share the existing two-call budget;
source metadata is retained with the accepted answer, raw webpages/excerpts are
not. Existing direct controls, help and observation answers gain no web calls.
Local implementation/qualification remains distinct from main, native or install.

## Bounded local date refinement

A strict inclusive year-range follow-up may refine the current owner/thread's
already admitted album result set without model input or another provider read.
Use the provider's structured release_date, never parse rendered subtitles or
old history as evidence. The response explicitly covers the shown catalog
editions only, reports missing dates, keeps the original expiry and creates a
new selection set. A known-empty refinement replaces the old offer; old taps
cannot revive it. Session/source/Profile/clear fences remain unchanged. A
historical caption without a current qualified offer grants no subject or dates.


### Current Track Insight qualification refinement

An explicit current Track Insight request may reuse exact current CC0 recording
credits/work-composer facts already held by the existing Session Knowledge owner,
even when the Planner published an Artist contribution instead. A publication is
not required to make a fresh qualified public fact usable by this explicit read.
No new fetch, catalog/model processing grant, historical reconstruction or fake
Moment/navigation reference is created. Bind exact current media identity,
owner/history grant, opportunity generation, source expiry and confirmed settings
before the same two-call analysis/assessment owner; recheck before cache/response.
A missing or conflicting exact recording proof stays unmeasured. Credit context
and labelled interpretation are useful data, but not acoustic measurements.


Private catalog offer retries retain only a bounded operational response receipt
inside the existing DialogueFrame (maximum4responses/64KiB, no durable body).
Body eviction leaves an opaque digest/expiry receipt; maximum256receipts then
refuses new non-control admissions rather than repeating an old request.
Message-ID/digest and original admission/deadline remain authoritative. Reusing
a request cannot mint a new offer or silently refresh expired choices. Clear
and rights-generation changes discard replay bodies. This limited transport
retry support does not close rich catalog-conversation archival retention.


## Album-track answer: one playable album header, then individual recordings

Producer source draft; full catalogue/publication and native adoption gates remain
open. This refines `album_tracks_information` through the existing ordinary
paired Ask DJ and frozen choice owner. It adds no automatic playback authority,
new announcement path or client-side context reconstruction.

The initial response has one short `text`/`dj_text` caption naming the album,
without an enumerated track list. `items`, `playback_actions` and
`result_set.items` are aliases of the same ordered rows, not three lists to
render. The first row is the exact album, `kind:album`, with its title, catalog
artist, proxied `image_url`, localized `button_label` (NL: `Speel album`) and
album `uri`/`context_uri`. Following rows are the requested individual tracks,
with title/artist, disc/track order, the same exact-edition proxied artwork,
localized Play label and their own frozen IDs. An absent cover remains absent;
never reuse another answer's artwork or invent an image.

Additive `result_set.presentation` describes the grouping, using existing frozen
action IDs rather than copied actions:

```json
{
  "kind": "album_tracks",
  "caption": "Deze nummers staan op het gekozen album:",
  "primary_action_id": "the-album-action-id",
  "track_action_ids": ["first-track-action-id", "second-track-action-id"]
}
```

The UI renders the album header first, then a visible gap, then the track rows.
Render this result once and retain separate music-play and speech-replay
controls/accessibility labels. `presentation` grants no effect authority.
Buttons submit the existing `choice_action` with the original `result_set_id`,
`action_id` and `operation:play`. The album action dispatches its entire album
`context_uri`; a track action dispatches only its exact recording URI. Reading
or merely selecting an offer does not start, resume or queue music. The
informational initial question remains zero-model and zero-effect.

Generic offers retain12items/16KiB. Only this Core-produced album page admits
one album plus up to50tracks/48KiB before frozen IDs. It shares the existing
single per-thread result-set slot; bounded RAM-only read-replay budget is192KiB
for this scoped offer, at most4retained bodies, rather than64KiB. Larger bodies
fail closed; no silent12row truncation. The original catalog page remains at
most50tracks with no per-track fetch or search, and partial coverage is explicit.
`album_track_observation.returned_count` counts tracks only, excluding the header.
`current_track_omitted` retains its original meaning. Known-empty other-track
results can still offer the album itself. The original600second choice lease remains unchanged. The60second observation
freshness guards album resolution and initial delivery; once admitted, the frozen
URI does not become the next currently playing album. Repeated list reads retain
IDs, layout and the original choice expiry. History/owner/source/clear/Session fences remain authoritative.
No durable catalog/history permission is added by these presentation fields.

The Apple source decoder currently reads only the result schema/set ID/expiry;
it has not adopted `presentation`. Native grouping, accessible spacing, artwork
loading and action behavior need Apple-owned qualification. The source fixture
`examples/client_contracts/askdj_album_track_choices_v1.json` is an actual isolated
HA HTTP response with synthetic Spotify input and expired lab IDs; it is not a
published producer pin, installed response or native screenshot.
