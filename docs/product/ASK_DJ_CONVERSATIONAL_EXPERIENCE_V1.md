# One Ask DJ conversation v1

Assignment `DJC-CORE-ASKDJ-CONTEXTUAL-DIALOGUE-V1-20261013`; selected [owner
decision](https://github.com/pcvantol/djconnect/issues/1101#issuecomment-6145537044).
Admission base `c955ec80407f4ab0237bc4e9381761d3c9274617`, sole Core writer,
branch `codex/askdj-contextual-dialogue-v1`. Status: design fixed before runtime
implementation; product qualification and exact publication remain pending.
The [producer contract](ASK_DJ_CONTEXTUAL_DIALOGUE_CONTRACT_V1.md) owns wire,
rights, bounds and acceptance. No native implementation is admitted here.

## Product invariant

General Ask DJ and the Session composer are two inputs to **one actual Ask DJ
application service**. Their only implementation difference is optional,
authorized Session/Moment context and the resulting optional Flow reference.
They share interpretation, agent, knowledge/music tools, style resolution,
short conversation, choice identity, response and history acceptance. No screen
flag selects business behavior; no lasting legacy/Session stacks behind a facade.
Text and the existing STT completion adapter normalize to that same service.

A user can ask without playback, with a paused Session or with an unavailable
music backend. General available knowledge does not depend on a live player.
The DJ answers the question; a literal quote is returned only when requested.
An explicitly new subject takes precedence over an old selection. A single
clear referent is used; multiple plausible entities get one useful clarification.
Composer, performer, producer and general biography remain distinct claims.

## Existing capability disposition

| Family / current owner | Disposition | Connected outcome |
| --- | --- | --- |
| `async_handle_ask_dj`, informational/action/hybrid helpers | KEEP / REUSE | One existing interpretation/tool implementation; rich cards, art, links and actions preserved. |
| General message, contextual message, HTTP/WebSocket, STT completion | FIX | Thin normalizers enter the same Profile-bound application and acceptance path. |
| Selected-entry informational early return | RETIRE | Removed as general response; explicit quote remains faithful and local. |
| `async_session_exchange` orchestration | FIX / REUSE | Optional source/Session resolver and common acceptance; no second chat policy. |
| `AskDJHistoryManager`, revision/clear/retention and Session references | KEEP / FIX | Same owner and Store; qualified short prompt projection, no blanket archive import. |
| Current `session_turn` blanket prompt exclusion | FIX | Source- and scope-qualified turns only; unsupported older bodies remain excluded. |
| Music DNA pending confirmations / recent-action text heuristics | FIX / RETIRE | Functional choice state belongs to bounded conversation state, not durable profiling or opt-in. |
| Lookup, artist/album/track/playlist, recommendations, output selection | KEEP / REUSE | Real results and their types/links/art retained; no fabricated URI or replacement FAQ. |
| Explicit control, Play tap, spoken/text choice, follow-up | KEEP / FIX | Existing tools plus shared authority, action identity and outcome readback. |
| Legacy numeric Mood / `dj_style` / TTS voice | KEEP / CLARIFY | Compatibility inputs remain separately named; no undocumented Persona mapping. |
| Ambient status-read producer | KEEP RETIRED | No unsolicited response/history/last-Ask-DJ generation returns. |

## State, actions and outcomes

| State / action | User-visible result and boundary |
| --- | --- |
| Standalone, no music; general question | Available agent knowledge, selected standalone style/default; no hidden Session or provider action. |
| Active/paused Session; selected credit | Relevant person/role explanation using qualified context; pause and presence-Off do not block an explicit question. |
| Selected historical entry | Current private conversation answers; the closed archive remains read-only. |
| Published live-only Moment | Bounded owner reference if separately qualified; selecting it does not force archiving. |
| New explicit artist/album topic while chip remains | New topic wins; do not identify the new artist as the old credited contributor. |
| Pronoun or “that album” | Use the current permitted subject; if ambiguous, ask one targeted question. |
| Volume/skip/pause between questions | Fast existing control; preserve relevant subject and a still-valid result set. |
| Temporary “more acoustic / less gloomy” | Refine the musical request; no implicit durable preference, Mood setting, queue replacement or Session start. |
| Named catalogue question → “which ones?” | Actual titles and artist subtitles in the live reply; original card order/IDs/expiry, no model/search/playback on the follow-up. Missing/expired list gets a useful five-language recovery instruction. |
| Real lookup results → “the second” | Bind to the exact shown set and item, never a newly sorted or model-invented list. |
| Result preview, selection, navigation | No playback, microphone, model or TTS side effect merely from viewing. |
| Explicit valid Play / clear control | Authorized existing effect, concise response based on actual outcome. |
| External timeout after dispatch | Uncertain/request-sent; same identity is not executed again automatically. |
| Agent/backend/STT failure | Honest localized error/fallback; general agent availability and music backend availability are separate. |
| Clear/revocation/Profile or install change | Invalidate relevant short context, choices and pending work; no old agent memory resurrection. |
| Session end/replacement during Session-dependent work | Discard late private answer/old Flow commit; general Ask DJ remains available for a new valid turn. |
| Private/nonpersistent conversation | Useful ephemeral continuity without body archive or Music DNA profiling; explicit replay-safety boundary remains qualified. |

One owner conversation does not merge Profiles or import arbitrary historical
sessions. Changing screen alone does not start a conversation, clear a draft,
reset a subject or duplicate a turn. New public questions do not depend on
playback item changes; only a question actually using that item captures its
identity as a completion guard. An action can legitimately change playback
without turning a valid independent subject into stale data.

## Style and evidence

Confirmed Session Persona/Mood govern Session-context turns. Outside a Session,
the existing Profile response style and Mood state, explicit supported request
selection and documented Home/default fallback apply. Profile voice style and
legacy `dj_style` are not the four-persona catalogue. One resolver supplies the
same typed style to agent and concise control responses. Persona changes wording,
rhythm and warmth; Mood changes atmosphere, never facts, identity or authority.
Reactive wording does not consume proactive Runtime style memory or budgets.

Keep exact source-supported credit separate from additional general agent
knowledge. A credit link supports the credit, not an unverified biography. A
model cannot claim it fetched a page or discovered a result when no tool did.
New answers do not edit old immutable Moments. Private questions, choices,
history and replies are absent from shared VibeCast, push and widgets.

## Consumer and qualification milestones

1. Pin this design and contract before runtime edits; reproduce the quote/filter
   baseline and record the KEEP/REUSE/FIX/RETIRE inventory.
2. Implement one connected Core service and adapters; retain current rich tools
   and wire compatibility, qualify short context/rights/action and lifecycle.
3. Early exact contract/real transport fixtures to existing Apple #87 writer;
   no Swift writes, consumer start or WIP extension. Existing clients retain
   rich responses; adoption of additive context/choice diagnostics is separate.
4. Shared capability matrix with/without Session context, ordinary pairing,
   text/STT, all five languages and four Personas; real configured-agent
   conversational quality separately from fixture routing/security evidence.
5. Exact technical/privacy and conversation/UX review, fixes, owning coverage,
   regressions, protected source delivery/readback and separate Finalization.

The mixed sequence is credit → identity → pronoun/role → different artist →
volume → temporary refinement → real results → second choice → explicit effect
and readback → content follow-up. Run standalone, active and paused variants.
Assess relevance, entity/role correctness, style, nuance, non-echo and continuity;
constant response fixtures or “text present” do not qualify model quality.
Bounded longer dialogue and race/failure/private/retry tests qualify resource
limits. Native/installed/hardware and joint acceptance remain separately open.
Only this one Core slice is selected; no lifecycle, proactive editorial, Watch,
new provider/model/account/cost route, deployment or following slice.

## Directed Track Insight addition

An eligible useful Track contribution can offer explicit
[Track Insight drilldown](MOMENT_TRACK_INSIGHT_DRILLDOWN_V1.md). Receiving it never
navigates. The same detail and target resolution serve a requested drilldown in
either composer. Earlier subject mode stays fixed during playback changes;
Apple navigation/back/draft/scroll acceptance remains separately owned.


## Connected delivery and consumer boundary

General Ask DJ and Session composer use the same Profile thread and the same
text/voice/command service. A selected composer remains the composer through an
ordinary volume action; an explicit new artist takes precedence. Qualified real
results support refinement, selecting a shown version and explicit playback without
extracting permission from model prose. Known pre-send failures and uncertain
outcomes have different retry behavior. A temporary acoustic preference changes
neither the stored Mood nor the queue by itself.

The [Track Insight drilldown](MOMENT_TRACK_INSIGHT_DRILLDOWN_V1.md) belongs to this
same selected Core increment. A useful existing published Track-Moment can offer
one explicit navigation button. It keeps the exact recording after A→B and uses
the existing full detail/cache, with honest unavailable/retry states. The same
subject route is available to either Ask DJ screen; VibeCast without detail support
shows the contribution and no unusable button. No Swift or receiver implementation
is started by this Core handoff. Native and joint acceptance remain separate.

Local implementation/qualification is not protected source delivery. Exact source
and Finalization permissions remain distinct. The owner additionally requested HA-dev
and HA-prod integration updates after readiness; installation/readback follows the
qualified exact artifact and does not establish native or hardware acceptance.


## Live-regression acceptance refinement

Core6154181590/6154227030/6154393277 extend the same assignment before the
corresponding runtime fixes. The producer contract's connected refinement
separates information from explicit effect authority and preserves rich live
queue/speaker/media actions without archiving expired execution grants.
The quarter-hour question uses existing Forecast direction and a qualified
queue read, never invents empty or future playback. Confirmed command state,
current card selection and eventual new proactive Moment remain different
observations. Both composers retain one pipeline and exact result identities.
The real paired baseline on ba84d2ac reproduces one unintended play request
from 'wat was vorige nummer'; this is source proof, not installed root cause.
Both independent reviewers approved the directed contract refinement; new
source, real conversation and native/installed acceptance remain pending.


## Artist/genre album and playlist options — 18October2026 correction

The existing artist/genre options route publishes one short localized intro and
one playable collection in `playback_actions`. Titles, subtitle/curator, proxied
artwork, media kind and the existing exact action/result-set identity belong to
those cards. `items` is empty for this route: it must not duplicate the playable
collection as informational rows. The intro does not enumerate all card titles.
The existing `result_set.items` remains selection metadata, not another visible
collection. Other informational/recent-history routes retain their own contracts.

The same accepted intro is the literal speech source through the existing
reference/prepare/private-audio path, including Settings3's confirmed voice.
Preparing speech never re-runs catalogue lookup or a playback request. Original
source expiry, source/owner/settings fences, text-only and provider-error notices
remain unchanged. This is no richer archive right or native/audible acceptance.
[Qualification and the still-open original iPhone speech failure](../verification/ASK_DJ_PLAYABLE_OPTIONS_20261018.md).
