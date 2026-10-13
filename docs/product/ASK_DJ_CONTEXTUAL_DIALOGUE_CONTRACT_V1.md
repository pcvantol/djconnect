# Shared Ask DJ contextual dialogue contract v1

Assignment `DJC-CORE-ASKDJ-CONTEXTUAL-DIALOGUE-V1-20261013`; companion
[experience](ASK_DJ_CONVERSATIONAL_EXPERIENCE_V1.md). This directed refinement
is committed before production changes. Existing source-main
`c955ec80407f4ab0237bc4e9381761d3c9274617`; no implementation/PASS claim yet.

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
thread: at most 12 recent messages/12 KiB, 4 typed subjects, one current result
set of at most 8 items, one pending confirmation, 20-minute idle expiry. At most
4 threads per owner and 32 retained owner states; admission at capacity fails
closed rather than stealing live in-flight state. External agent memory is not
trusted: each call starts fresh with the explicit qualified window; returned
`conversation_id` is not reused after clear/expiry/owner or Session changes.

One active semantic/model turn per thread. Identical in-flight IDs join the same
bounded result; different open questions receive busy/retry semantics. Explicit
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
