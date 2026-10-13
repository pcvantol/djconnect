# Session history summary v1

Status: selected Core implementation **In progress**; native Apple adoption **Planned**.
Implementation: `DJC-CORE-SESSION-HISTORY-SUMMARY-V1-20261013`, existing
`HISTORY::CORE::SUMMARY` → `HISTORY::APPLE::SUMMARY`.
[Connected acceptance refinement](SESSION_HISTORY_SUMMARY_ACCEPTANCE_V1.md).
Assignment: `DJC-SESSION-ENTRY-LIFECYCLE-HISTORY-DESIGN-V1-20261012`.
[Full A/B decision](https://github.com/pcvantol/djconnect/issues/1101#issuecomment-6131072407)
and [combined pickup](https://github.com/pcvantol/djconnect/issues/1101#issuecomment-6131363097).
Baseline: Core `e8bb982f148ac7a22b6991ee6f54d10188849ee0`.

## Existing basis and missing contract

[Persistent Session Storage](../../PERSISTENT_SESSION_ARCHITECTURE.md) and
[Session conversation/history](SESSION_CONVERSATION_HISTORY_CONTRACT.md) already
own authorized list/detail/timeline/search/open and restart interruption.
`session_history_projection.public_session` now adds the optional private summary
to identity, lifecycle timestamps/revision and read-only/coverage information.
The implementation records newly accepted entries and semantic publications,
and confirmed symbolic Mood intervals; legacy sessions remain unknown.
Apple source `11ecab47bff28eaf6d7231f63477d893c0e91cb7` has Session history models;
that is not proof of this summary contract or native adoption.

Add an optional, versioned Core list/header projection, not a second archive or
client summary algorithm. Reuse the existing history routes and storage owner;
no new route or general event bus. Version6 adds compact tables through the
existing Session Storage migration chain, with no legacy backfill. Read/list
must not fetch N timelines, provider data, expired content or DNA/model output.
See [entry/lifecycle](SESSION_ENTRY_LIFECYCLE_EXPERIENCE_V1.md) and
[native privacy boundaries](APPLE_SESSION_NATIVE_SURFACES_V1.md).

## Proposed wire contract

The connected producer advertises `session_history_summary: true` and
`contract_versions.session_history_summary: 1`. The optional summary version is
`djconnect-session-history-summary/1`. Source protected delivery and native
consumer acceptance remain separate gates. Old clients ignore optional `summary`; new
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
      "state": "provisional",
      "revision": 12,
      "as_of": "2026-10-12T18:00:00Z"
    },
    "moments_published": {
      "value": null,
      "basis": "semantic_publication_commit",
      "coverage": "unknown",
      "state": "provisional",
      "revision": 12,
      "as_of": "2026-10-12T18:00:00Z"
    },
    "mood": {
      "value": null,
      "basis": "confirmed_symbolic_mood_elapsed_intervals",
      "coverage": "unknown",
      "state": "provisional",
      "revision": 12,
      "as_of": "2026-10-12T18:00:00Z"
    }
  }
}
```

Required per metric: `value`, `basis`, `coverage`, `state`, `revision`, `as_of`.
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

The pre-slice baseline had only live Flow and a rights-qualified archive subset;
full publication counts were therefore unknown. The connected implementation
now provides the missing compact semantic acceptance transaction for the existing
Manager publication entrances (opening/direction, coordinator, fallback track,
qualified fact, shared-producer relation and immediate/pending narrative paths).
This local implementation is not yet protected-delivered or independently fully
qualified; no producer release or native acceptance is implied.

One non-Silence immutable proactive DJMoment has a canonical Session/Moment key
and aggregate in existing Session Storage, independent of a permitted optional
body in the same transaction. Proposals, failed acceptance/generation, reactive
Ask DJ turns, system entries, Silence, presentation variants, language renders,
Broadcast fan-out/replays, snapshots, reconnect and renderer receipts do not
increment. The actual Flow remains ephemeral; the compact commit is not a new
full-content archive or permission to retain source-restricted text/artwork.

Persistence failure creates neither an accepted count nor a committed fact;
a semantic commit followed by Broadcast failure retains the accepted count.
Transport delivery and human reading are separate qualifications. Runtime and
SQLite fault/retry tests plus actual HA end/reopen transport exercise that
ordering. Retention and source/privacy qualification still control visibility.

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

## Documentary delivery receipt

[Source PR #1160](https://github.com/pcvantol/djconnect/pull/1160) protected merged as `fdc79c9d7174b9d67dcf743400fbb76a0c163387`.
[Exact source/artifact qualification](../verification/SESSION_ENTRY_LIFECYCLE_HISTORY_DESIGN_V1_SOURCE_READBACK.md) records documentary checks and independent review; all proposed product implementation remains **Planned**. Separate Finalization reconciliation is still gated.

## Connected implementation qualification (in progress)

The aggregation boundary is a short existing SQLite transaction. It accepts
canonical playback entry + key/count together, or a semantic non-Silence Moment
key/count with an independently permitted optional body. Confirmed Mood is
persisted before live mutation. Runtime working Planner/Knowledge/Moment state
and presence debit are adopted after acceptance; subscriber failures cannot
undo the semantic commit. Explicit history opt-out validates live ownership but
retains no summary, key or body; opt-out does not disable existing live Moments.

Dedup keys are bounded at8192 per Session and256 characters per reference; no
accepted key is evicted to admit another publication. Capacity suppresses new
Moment acceptance and marks omitted observation capture partial once. Four
integer duration counters and one current interval bound Mood storage. Closed
retention/Profile purge erase summaries and keys; source withdrawal removes
derived counts conservatively while retaining keys until late replay is inert.

A fixed bulk summary query augments the existing list read; the measured100-
Session/20-row list uses four SELECTs and zero timeline SELECTs. A real SQLite
8192-key boundary benchmark uses572330 identity bytes in a1622016-byte database
with100 Sessions; this storage benchmark is distinct from elapsed Runtime proof.

Ordinary paired isolated HA proof gives two observed entries, two semantic
Moments (opening Session + qualified Spotify Album), one permitted readable
body, and time-weighted energy after end and storage reopening. Fixtures:
[producer examples](../../examples/client_contracts/session_history_summary_v1/README.md).
Only external provider responses are fixtures; the acceptance/storage/query
chain is real. The local matrix,27 owningtests,1788 regressions (7 existing skips), security
and134 DAG checks pass. Exact independent candidate reviews and protected
source/Finalization delivery remain required before a delivered Core claim. No native/installed/hardware PASS.

## Direct list consumption and value/coverage matrix

A provisional read can advance `as_of` and its open Mood duration with an
unchanged revision. Consumers render that coherent response, without dropping
a newer as-of solely because its revision repeats.

List metric/header revisions are integers; detail metric/header revisions are
the existing opaque strings. Consumers compare exact equality with their own
containing header, never parse an integer from an opaque token, order tokens
lexicographically or merge revisions across routes. Every metric uses the same
header snapshot as_of. A cursor conflict uses existing409 semantics and a fresh
page; it is not a reason to keep old totals under a new header revision.

| Value / coverage | Interpretation / safe presentation |
| --- | --- |
| 0 / complete | Known zero accepted entries or contributions |
| positive / complete | Known accepted total within explicitly stated Stage1 scope |
| nonnegative / partial | Registered subset; label incomplete, never an exact full total |
| null / unknown | Unknown, not zero and not a pending count reconstructed by client |
| null / withdrawn | No longer available under current source/privacy rights |
| Mood / complete | Confirmed elapsed majority or mixed; no listening claim |
| null Mood / unknown | No qualified complete positive elapsed interval |

Suggested five-language accessibility vocabulary for consumer adoption (not a
new native implementation):

| Meaning | en | nl | de | fr | es |
| --- | --- | --- | --- | --- | --- |
| unknown | Unknown | Onbekend | Unbekannt | Inconnu | Desconocido |
| partial | Partially registered | Gedeeltelijk geregistreerd | Teilweise erfasst | Enregistré en partie | Registrado parcialmente |
| withdrawn | No longer available | Niet meer beschikbaar | Nicht mehr verfügbar | Indisponible | Ya no disponible |
| provisional | Provisional | Voorlopig | Vorläufig | Provisoire | Provisional |
| final | Final | Definitief | Abschließend | Définitif | Definitivo |

[Machine-readable local qualification](../../examples/client_contracts/session_history_summary_v1/qualification.json)
and [source-file integrity](../../examples/client_contracts/session_history_summary_v1/source-integrity.json)
freeze the measured software boundary; neither is a published integration-artifact
receipt or native acceptance. The source SHA is bound in the owning register
after the local commit, so the manifest does not contain a circular self-digest.

[Actual owner state fixtures](../../examples/client_contracts/session_history_summary_v1/summary-states.json)
show known0 before externally gated provider generation, partial8191 observations
plus one Moment at the real8192-key bound, source-withdrawn null values and
legacy final unknown. Only provider responses and explicit legacy Store data
are fixtures; registration, transactions, query and owner authorization are real.
