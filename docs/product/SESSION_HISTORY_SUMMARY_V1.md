# Session history summary v1

Status: documentary design; product implementation **Planned**.
Assignment: `DJC-SESSION-ENTRY-LIFECYCLE-HISTORY-DESIGN-V1-20261012`.
[Full A/B decision](https://github.com/pcvantol/djconnect/issues/1101#issuecomment-6131072407)
and [combined pickup](https://github.com/pcvantol/djconnect/issues/1101#issuecomment-6131363097).
Baseline: Core `e8bb982f148ac7a22b6991ee6f54d10188849ee0`.

## Existing basis and missing contract

[Persistent Session Storage](../../PERSISTENT_SESSION_ARCHITECTURE.md) and
[Session conversation/history](SESSION_CONVERSATION_HISTORY_CONTRACT.md) already
own authorized list/detail/timeline/search/open and restart interruption.
`session_history_projection.public_session` currently projects identity,
lifecycle timestamps/revision and read-only/coverage information. It does **not**
provide complete track totals, published-Moment totals or time-weighted Mood.
Apple source `11ecab47bff28eaf6d7231f63477d893c0e91cb7` has Session history models;
that is not proof of this summary contract or native adoption.

Add an optional, versioned Core list/header projection, not a second archive or
client summary algorithm. Reuse the existing history routes and storage owner;
no new route, storage migration or data collector is implemented here. Read/list
must not fetch N timelines, provider data, expired content or DNA/model output.
See [entry/lifecycle](SESSION_ENTRY_LIFECYCLE_EXPERIENCE_V1.md) and
[native privacy boundaries](APPLE_SESSION_NATIVE_SURFACES_V1.md).

## Proposed wire contract

These exact field names and enum values are the design candidate, **not an
advertised runtime capability**. Capability/version negotiation is a separate
producer implementation gate. Old clients ignore optional `summary`; new
clients accept its absence without inventing zeroes or backfilling old stores.

```json
{
  "summary": {
    "schema_version": "djconnect-session-history-summary/1",
    "session_revision": 12,
    "as_of": "2026-10-12T18:00:00Z",
    "state": "provisional",
    "tracks_observed": {
      "value": 3,
      "basis": "accepted_playback_observed_entries",
      "coverage": "partial",
      "revision": 12,
      "as_of": "2026-10-12T18:00:00Z"
    },
    "moments_published": {
      "value": null,
      "basis": "semantic_publication_commit",
      "coverage": "unknown",
      "revision": 12,
      "as_of": "2026-10-12T18:00:00Z"
    },
    "mood": {
      "value": null,
      "basis": "confirmed_symbolic_mood_elapsed_intervals",
      "coverage": "unknown",
      "revision": 12,
      "as_of": "2026-10-12T18:00:00Z"
    }
  }
}
```

Required per metric: `value`, `basis`, `coverage`, `revision`, `as_of`.
`state` is `provisional` for a live interval or `final` once its permitted
aggregation has closed. Final does **not** mean complete coverage. Each metric
uses `coverage: complete | partial | unknown | withdrawn`; unavailable or
withdrawn value is null, never zero. Metric revision/as-of must match the
snapshot that produced the list/header. Do not mix totals from different
revisions. Counts are nonnegative integers when known; Mood is
`chill | groove | energy | party | mixed | null`. A known complete empty count
can legitimately be zero; empty duration has no predominant Mood.

For an incomplete archived text subset expose the distinct optional metric
`moments_retained` with `basis: retained_readable_entries` and its own coverage.
It is not an alias for `moments_published`. Legacy initial Mood can be shown as
an explicitly labelled Start Mood from existing authorized metadata; never
populate predominant `mood` from that single initial value.

## Track count semantics

Count accepted, deduplicated canonical `playback_observed` entries in this
Session. The user label is **observed/registered tracks**, not songs fully
listened to. Duplicate transport deliveries, snapshots, reads and reconnect do
not increment. A queue item, progress tick, title/URI heuristic or native render
is not a new observation. Follow [delivered observation limits](LIVE_PLAYBACK_OBSERVATION.md)
and [Continue Stage 2 qualification](CONTINUE_CURRENT_PLAYBACK_CONTINUITY.md).

Three quantities stay distinct: accepted observation entries; unique media
identities; qualified occurrence/plays. This design's metric is the first.
Repeated observations of an identity may count as separate accepted entries
only when their canonical entry identity is genuinely distinct. Do not claim
repeat-play or full-listen completeness from Stage 1. Missing observation
coverage stays partial/unknown; never derive totals from history pagination.

## Moment count and semantic publication boundary

Count one non-Silence immutable proactive DJMoment at its accepted **semantic
publication commit** into the existing durable Session decision/Flow authority.
The future metric update must share that idempotent commit, keyed by canonical
Session/Moment identity. A proposal, provider response, failed persistence,
reactive Ask DJ user/assistant turn, historical system entry or pending task
cannot increment. A presentation variant, language render, Broadcast fan-out,
resend, snapshot, reconnect and renderer receipt cannot increment again.

The existing order is semantic decision → durable idempotent commit → live
publication. If persistence fails there is no count or published history. If
durable commit succeeds but Broadcast later fails, retain the accepted
semantic publication count; delivery reachability is separate and replay cannot
increment it. The label does not assert a human read, native render or hardware
receipt. An implementation must verify and bind the actual publication owner,
not add a helper counter before that commit.

Retained readable text may be only a rights-qualified subset. Compact totals
can survive text expiry only with an independently permitted aggregation basis;
archiving fewer bodies does not prove the full published total. If only retained
entries are proven, show `moments_retained` as a partial retained count and leave
`moments_published` unknown. No retention or derived-data rights are widened by
this design.

## Predominant Mood

Use confirmed symbolic Mood intervals over known **elapsed Session time,
including pauses**, not inferred listening time. Bound each interval by accepted
Mood changes and the active as-of/end timestamp. Measure nonnegative elapsed
duration on the authoritative lifecycle clock. Clock reversal, gaps, uncertain
restart intervals or missing history must produce incomplete/unknown coverage.
Do not average numeric enum values or convert Watch's legacy numeric setting.

For complete nonzero coverage, a Mood with strictly more than 50% of known
elapsed duration is predominant. No strict majority, including a tie, is
`mixed`. If the whole elapsed Session span is not known, `value` stays null;
known partial durations must not be presented as a full predominant result.
Same-timestamp changes contribute zero duration. Initial Mood with confirmed
continuous coverage is an interval; an old unqualified initial value is only
Start Mood. No reconstruction from current Mood, track genre, DNA or old text.

Examples: chill 6 min + groove 4 min → chill; 5 + 5 → mixed;
chill 4 + groove 3 + energy 3 → mixed; chill 6 known minutes + unknown gap →
unknown. A 4-minute pause in groove contributes four elapsed groove minutes,
with no claim of listening during that pause.

Persist only bounded typed aggregation evidence in the **existing Session
Storage**, outside Runtime style memory: per-catalog Mood durations, open
confirmed interval boundary, covered elapsed duration, coverage state, revision
and accepted event identity cursor/dedup evidence. No unbounded interval list,
provider payload, artwork, prompts or raw historical text. The implementation
must qualify the existing Store's canonical idempotency guarantees and bounded
dedup/migration strategy; do not drop dedup keys while their events can replay.

## Atomicity, lifecycle and privacy

| Event / failure | Required aggregate behavior |
| --- | --- |
| Accepted observation/publication/Mood change | Update matching projection in the existing atomic/idempotent Store transaction |
| Persistence failure | Neither fact nor aggregate becomes committed; do not broadcast a fictitious total |
| Crash after commit / retry | Same canonical event contributes once; readback sees the committed revision |
| Active read | Provisional open interval closed only to as-of; read itself never writes an observation or Mood change |
| Explicit end | Finalize permitted known intervals/aggregates at accepted end; no late writes from closed Runtime |
| Restart interruption | Final state with actual coverage gaps; no fabricated duration through interruption |
| Old store / unknown version | Summary absent or unknown; no compulsory backfill or N+1 fetch |
| Account/source withdrawal or expired basis | Withdraw/recompute affected derived totals where required, not only source text |
| Profile delete / reassignment / retention | Apply existing owner authorization, deletion and retention atomically to aggregates too |
| List/detail race | Return the same revision, or retry/reconcile; never claim inconsistent rows as one snapshot |

Summary is private owner history under normal paired device/Profile authority
and the existing `no-store` display boundary. It cannot be copied to VibeCast,
APNs, Widget/App Group, Lock Screen, Spotlight index or exported diagnostics by
virtue of being short. Aggregation is still derived personal data. A neutral
retained statistic needs its own rights qualification; otherwise withdraw or
recompute it. Profile reassignment cannot grant a new actor old history.
No query enables Music DNA, revives ended Runtime or refetches expired bodies.

## Planned subsets and acceptance

1. Qualify producer semantic event identities, rights, duration coverage and
   existing Store transaction/migration/dedup boundaries.
2. Implement optional same-revision list/detail aggregation and capability;
   preserve old consumers and missing/unknown values.
3. Independently admit native history row/header rendering, accessible labels
   and five-language terminology; no local counting or N+1 timeline loads.
4. Joint qualification with real routes, concurrent writes/reads, end/restart,
   trim/delete/revocation, duplication/replay and interrupted partial coverage.

Owning tests must distinguish empty from unknown; unique identity from accepted
entries/occurrences; committed publication from render/retained text; all four
Mood values, strict majority/tie/three-way mixed/zero/partial/pause cases; list
versus detail revisions; crash/retry and legacy-store migration; wrong Profile,
privacy withdrawal and expiry. Native surface navigation need not wait for
this richer summary; surface display of private aggregates remains separately
unqualified. No broader Lifecycle, narrative maturity or native/hardware
completion is inferred from these designs.
