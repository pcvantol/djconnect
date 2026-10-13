# Session history summary — connected acceptance contract v1

Implementation assignment: `DJC-CORE-SESSION-HISTORY-SUMMARY-V1-20261013`.
Base: `06e04d9996a8909337b6eb78b8568e1e2ddead5f`. This refines
[the summary design](SESSION_HISTORY_SUMMARY_V1.md) before runtime changes.
Only `HISTORY::CORE::SUMMARY` is admitted; Apple adoption remains separately Planned.

## Acceptance inventory

| Input | Existing owner and actual boundary | Connected requirement |
| --- | --- | --- |
| playback observation | Runtime Manager lock → HistoricalProjectionRepository `async_append_entries`, canonical `playback_observed` identity; Stage1 adjacent same-media collapse | Insert entry and compact acceptance key/count in one existing SQLite transaction, before changing live playback projection |
| opening/direction, initial track/coordinator, qualified Artist/Album/Genre/relations and later track context | Manager `_async_persist_moment` then Runtime Flow/Broadcast | One compact semantic acceptance before publication; permitted historical body is optional in the same transaction |
| narrative transition | Synchronous pending-transition path currently bypasses persistence | Convert that narrow manager path to awaited acceptance; preserve existing Planner approval, no second planner |
| Silence, reactive questions, presentation/replay | No proactive semantic contribution | No count or acceptance key; existing explicit question/history contracts unchanged |
| confirmed Mood | Manager `async_update_mood` currently changes only live state | Persist closed/open symbolic interval and revision first; same-value remains no-op |
| create/activate/end/interruption | PersistentSessionRepository transaction, startup reconciler | Initialize new-only summary; finalize at explicit end, mark unknown Mood gap at restart without restoring Runtime |

## Transaction, identity and cancellation

Migration6 creates private compact summary and accepted-key tables in existing
Session Storage. No old session backfill; no Timeline scan or second history engine.
Keys are `(session_id, kind, reference_id)` using existing observation and Moment
identities, with deterministic canonical entry IDs. Acceptance increments the
same history revision as its entry/metric transaction. Full Moment bodies still
require their original CC0/direction archive grant; a neutral Core publication
fact has a separate private-owner aggregation basis and carries no text/art/provider
payload or Performance Memory.

Before the short acceptance boundary, generation/composition/cancellation/stale
context may reject with no write. The final Mood authorization fence runs on
the event loop after storage-lock acquisition, immediately before transaction
admission; revoked token/Profile authority while waiting produces no write.
Proactive acceptance uses the same event-loop admission fence to recheck current
Session/item/opportunity generation, observation freshness, source expiry and
remaining readable playback. A stale candidate before admission consumes no
count, key, opportunity or presence budget. Once its transaction starts, cancellation is drained through
commit/rollback and the locked Runtime acceptance tail completes consistently;
commit wins if accepted. Failure before commit consumes no presence/opportunity
or working-engine state. A committed event remains counted after Flow/Broadcast
failure; its accepted opportunity/dedup and presence debit remain consumed,
while new published-only continuity seeds require successful Flow. One prepared
presentation is ephemeral, consumed immediately and cleared on end; transport delivery is separate. Retrying an accepted identity does not
consume another budget or change counts. End/restart refuse new late acceptance.

## Bounds, rights and withdrawal

At most8192 compact acceptance keys per Session, never evicted while replay is
possible. At capacity a new Moment is not accepted/published; no opportunity is
consumed. A new observation omitted at capacity marks coverage partial and does
not create a canonical accepted history entry, while current playback remains
usable. Existing accepted keys remain idempotent. Summary state has four Mood
duration integers and one open interval, never an interval list. Closed Session
retention expires keys only with its Session; erased/disabled history cannot
accept later events. No opaque keys become a new cross-Session archive.

Core-owned aggregate retention is private owner history (90 days), independent
of full Moment-body rights. Capture only bounded internal backend/account/entry
references and a one-way account-binding fingerprint, never provider payloads or
credentials. Profile purge, source/account withdrawal and relevant expiry
withdraw affected derived totals conservatively rather than infer fresh rights;
no source body is refetched. Counts withdrawn by that boundary stay null.

## Projection and Mood

Reuse optional `djconnect-session-history-summary/1`: `tracks_observed`,
`moments_published`, `mood`, and per metric value/basis/coverage/state/revision/as_of.
Revision may be the existing opaque history revision string in detail; each
metric must equal its containing header revision. `as_of` is one response snapshot.
Complete observation count means complete accepted-entry capture, **not** complete
listening, exact plays or same-track occurrence coverage. Advertise the fixed
Stage1 observation scope; missing observation/capacity/gaps remain partial.

Exact integer microsecond durations (timedelta days/seconds/microseconds,
without floating truncation that can invent a majority) cover known elapsed Session time including pauses.
Strict majority >50% requires complete positive coverage; otherwise mixed (no
majority) or null (gaps/zero). Restart never closes an unobserved open interval as
measured time. Old summary absent/unknown is not zero. Final is independent of
coverage. Queries attach one bulk compact-row read to the existing list/header query and
never write, fetch providers or read timelines per row. Rights checks use bounded
per-response binding reuse; summary stays no-store owner content and never enters
Broadcast/VibeCast/widget/push/diagnostics.

## Required qualification

Actual paired isolated HA → start → accepted observations/all publication paths/
Mood → end → SQLite reopen → owner list/header; independent expected counts,
including opening contributions. Race/failure/cancel/retry, migration/withdrawal,
Profile auth, paging/revision, zero/unknown/partial/final and measured query/storage
bounds are owning tests. Real transport fixtures precede Apple implementation.
Existing presence/Mood/Forecast/ambient/AskDJ/history/Broadcast suites, coverage,
security and two exact independent reviews remain delivery gates. No runtime or
native acceptance is claimed by this pre-implementation contract itself.
