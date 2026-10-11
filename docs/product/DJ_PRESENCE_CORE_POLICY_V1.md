# DJ presence Core policy v1 — admission and calibration

Assignment: `DJC-CORE-DJ-PRESENCE-V1-20261011`. Source base:
`9cdee0602b2ff0db99c433f2a3f2eb6d5ba8fe4e`; sole existing Core writer;
branch `codex/dj-presence-v1`. Design: [DJ_PRESENCE_V1](DJ_PRESENCE_V1.md).
Fresh host verification exits 0, onboarding 4.5.3. Documentary predecessor
#1149 is reconciled. No installation or publication permission is implied.

## Baseline and complete production inventory

The unchanged base's existing qualified producer fixture, through Runtime,
Planner, Knowledge, Moment, Flow and Broadcast, publishes Track at 0 s,
Album at 45 s and Artist at 90 s (15 s observations, groove, Radio DJ,
300 s track). This is modeled software evidence, not a provider/live HA claim.
The original trace is retained in the owning private lab before code changes.

| Entry | Existing clock / budget / rejection | Presence boundary |
| --- | --- | --- |
| Track start coordinator and async insight | One accepted media identity; planner 60 s spoken interval; freshness, rights, direction and repetition | Before insight, after insight, final candidate revision fence |
| Legacy fallback Track/Artist/Album/Genre/Recommendation | Same identity plus planner policy; Knowledge async callback | Same shared admission and final revision fence |
| Qualified fact first and later cards | Observed playback; 35/50 s spacing, previous read minus 5 s, six facts/track, 45 s tail, six qualified input facts | Global admission before selection and publication; published ledger only |
| Legacy later current-track context | One spent opportunity; 180 s track, read-dependent gap, 45 s tail, 30 s freshness; async Knowledge | Global admission and candidate revision fence |
| Session direction update | Existing planner direction decision; no knowledge provider | Same contribution ledger, never separate quota |
| Ordinary Transition | Planner approval after substantive Moment | Same contribution ledger, preserves existing approval and validity |
| Discover narrative Transition | Existing evidence/relation approval and deduplication | Same contribution ledger; no new narrative knowledge |
| Silence / explicit conversation / lifecycle | Silence is diagnostic; explicit Ask DJ is owner initiated | No contribution debit; explicit conversation remains available |

## Calibrated numeric policy

Values are stable protocol codes. Default `balanced` is deliberately bounded,
including for older clients. Caps are maxima, never targets. All substantive
proactive families share the rolling budget and current-track cap.

| Value | Dutch anchor | Min interval (s) | Maximum / track | Maximum / rolling 600 s |
| --- | --- | ---: | ---: | ---: |
| `music_only` | Alleen muziek | — | 0 | 0 |
| `occasional` | Af en toe | 180 | 1 | 2 |
| `balanced` | Gebalanceerd | 35 | 3 | 6 |
| `talkative` | Praatgraag | 35 | 4 | 10 |
| `presenter` | Presentator | 35 | 6 | 16 |

The actual global interval is at least the previous contribution's read time
minus 5 s. Existing per-route 35/50 s Mood/Persona spacing, source fitness,
40–90 s read duration, source/attempt limits and tail fit remain hard gates.
High presence never weakens them. Richer modes spend more eligible opportunities,
not more words. All five modes may legitimately publish nothing with poor input.

One Runtime-owned bounded ledger follows monotonic time and stable playback
identity. Settings changes, no-ops, reconnect and seek never clear it. A skipped
observation creates no queue. Published identities and counters survive raising
and lowering within the same Session. End discards the ephemeral ledger.

Every changed presence increments its own revision. Work captures that revision
before any asynchronous boundary; its final commit rejects even off/on ABA.
Music-only prevents new proactive work. Explicit questions, voice and operational
control do not use that gate. Old Moment and presentation bytes are immutable.
Mood, Persona, Session and playback retain their independent fields.

## Bounded qualification plan

Use one own isolated HA SDK process and loopback ports 18213/18214 (confirm free
before binding); preserve Apple 18196/18197 and HA-dev 8123. Synthetic provider
and speech boundaries must be labeled. Real pairing/router/owner/policy/publication
must run unchanged. Browser matrix: local/static × portrait/landscape.
Duration trial: 120 modeled minutes, at most 240 track observations and 2,880
intra-track observations; one process, no external network/provider. Report real
elapsed time, peak tasks/memory, rolling ledger bounds and late publication.
Stop on assertion failure, unexpected external effect or free disk below 5 GB;
maximum one diagnosis/rerun per newly fixed failure, no retry-to-green loop.

Before publication: full regressions, owning file coverage, transport/privacy,
localization, lint/security, DAG/schema/render checks and independent technical
and experience review. Source and Finalization each need fresh exact-SHA grants.
Native Apple, installed and hardware acceptance stay separate; joint product
node remains open until native receipts exist.
