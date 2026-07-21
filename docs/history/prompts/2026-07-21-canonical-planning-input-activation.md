# Prompt History: Canonical Planning Input and Candidate Projection Activation

**Prompt ID:** Session Intelligence Runtime Integration, Cell 3
**Engineering program:** DJConnect Product Development
**Branch:** `codex/activate-canonical-planning-input`
**Pull Request:** [#346](https://github.com/pcvantol/djconnect/pull/346)
**Merge Commit:** `eddf1034272a5665e02881906f7df7722b5fbc4c`
**Decision:** `MERGED_UNRECONCILED` pending dedicated Finalization
**Execution date:** 2026-07-21
**Created:** 2026-07-21
**Updated:** 2026-07-21

## Outcome

Every ordinary Track Started event now enters the existing Planning Runtime
Coordinator, including when no Upcoming Playback Projection is available. The
Planner creates one bounded, runtime-scoped current-track candidate from the
already observable Track Insight selection. The candidate enters the existing
Planning Window, Planned Intent, readiness, approval, Knowledge and immutable
DJMoment lifecycle. It is not future playback and does not fabricate a queue
occurrence.

The existing legacy Track Started route remains only a deterministic safe
fallback. Planned intent consumption is deferred until after the existing
Session Flow and Broadcast publication succeeds, preventing consumed planning
state without its corresponding published result.

## Validation

- `python -m unittest discover -s tests` — 1310 passed, 7 skipped
- `ruff check custom_components tests` — passed
- `git diff --check` — passed
- `./scripts/runner/bootstrap_djconnect_macos_host.sh --verify` — MATCH
- `python -m unittest tests.test_playback_observation.PlaybackObservationTest.test_rolling_records_reconcile_current_merged_implementation` — passed

Focused coverage verifies no-projection coordinator entry, Artist/Album/Genre/
Recommendation current-track candidates, Prepared Knowledge reachability and
fallback, non-fabrication of future coverage, observation-entry regression,
single execution and consumption only after publication.

## Known limitations

The capability does not add future playback observation, provider queue reads,
new intent-selection heuristics, persistent planning state, transport or
renderer behavior. Existing current-track-safe Track Insight remains the only
input when an Upcoming Playback Projection is absent.

## Deferred work

Playback Observation Stage 2, provider queue qualification, occurrence-correct
identity, replanning influences, Narrative Sequencing, Audience Intelligence,
Lyrics and new knowledge providers remain separately deferred.

## Recommended next prompt

After this dedicated Finalization and Workspace Cleanup restore
`MERGED_RECONCILED` and `WORKSPACE_READY`, select one fresh capability only
from current repository evidence. Do not begin implementation from this merged
but unreconciled state.
