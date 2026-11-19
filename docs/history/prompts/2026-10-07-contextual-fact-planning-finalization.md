# Contextual qualified-fact planning v1 — Completion and Finalization

- **Assignment:** `DJC-CORE-CONTEXTUAL-FACT-PLANNING-V1-20261007`.
- **Decision:** `GO_FOR_PROTECTED_FINALIZATION`; source software acceptance
  passed. `MERGED_RECONCILED` follows this separate governance-only merge;
  `WORKSPACE_READY` follows safe local cleanup. No next capability selected.
- **Base / sole writer:** `4c30399294b56aff89b962a53b37ea91a2d1762f`,
  `codex/contextual-fact-planning-v1`. Fresh `macmini-m6` desired-state verification
  MATCH/exit 0, onboarding 4.5.3; clean main, one checkout, no competing active
  Core writer or assignment pickup. SSH/HTTPS fetch and `git pull --ff-only`
  succeeded; local/origin/protected-API main matched the base.
- **Executor ACK:** [#1101 / 6039361642](https://github.com/pcvantol/djconnect/issues/1101#issuecomment-6039361642).
  **First material source:** [6039436220](https://github.com/pcvantol/djconnect/issues/1101#issuecomment-6039436220).
- **Source PR / commit / tree:** PR [#1122](https://github.com/pcvantol/djconnect/pull/1122)
  protected squash-merged reviewed head `78a43136baba11eb44b42eaa154859143864b652`
  as `d7a646e0e83a92211875e2f3b45606678e992e76` on 2026-10-07 14:35:44 UTC.
  Source and merge trees equal `a60277ced1b5621700c47f80340489825b17994a`.
  Local main/origin/main and protected API exact-main readback matched.
- **Finalization branch:** `codex/contextual-fact-planning-finalization`, based
  on source merge `d7a646e0e83a92211875e2f3b45606678e992e76`. This commit
  cannot embed its own SHA; the separate attached Finalization PR's frozen
  head identifies it. Its exact review/check/merge receipt is recorded in #1101.
- **Created documents:** policy/acceptance contract in the source PR and this
  immutable Completion / Prompt History record in Finalization. Software
  screenshots, snapshots and red logs remain local ignored evidence.
- **Updated documents:** Repository Status, Engineering Status, Management
  Summary, Prompt Index, Product Backlog, Product Roadmap, DJ Intelligence
  Maturity and the selected policy contract. No generic governance amendment.

## Product outcome and frozen policy

The [policy](../../product/CONTEXTUAL_FACT_PLANNING_CONTRACT.md) was fixed before
source implementation. Four real Runtime scenarios failed before mutation:
producer-order dependence, context-insensitive cadence, long-candidate blocking
and eligibility defects (wrong rights accepted / unknown intent raised).

Eligibility now binds existing field/provider/intent/rights/attribution,
current identity, freshness, locale and capability before ranking. A candidate
must fit its unchanged 40–90s read duration plus five seconds in observed
remaining time. Existing current-item specificity, Strategy/Direction and
recent actually delivered Flow type inform ranking. Mood/Persona add at most
ten preference points or fifteen seconds of spacing; they do not rewrite
copy, change truth, rights or read duration. Stable complete tie-breaks remove
retrieval order. Fact use is committed with existing Flow/Broadcast delivery.

Same pool, exact original base versus candidate Runtime ingress:

| Scenario | Exact base | Candidate |
| --- | --- | --- |
| Manual | Album→Track→Artist | Track→Album→Artist |
| Reversed producer pool | Artist→Track→Album | Track→Album→Artist |
| Discover | Album→Track→Artist | Artist→Album→Track |
| Calm second card | 45s | 50s |
| Long first candidate, 50s remaining | No card | Short qualified Album |
| No candidate fits, 44s remaining | No card | No card, no consumed fact |

Another four-angle Runtime scenario proves the recent-type causal effect:
Track→Album→Track→Artist with memory demotion, versus Track→Track without it.
Rejected candidates leave memory/use empty. Direction-only Exploring changes
Manual's Track choice to Artist, and five language copies remain exact.
Pause, seek, source/item switch, stale/late replies, duplicate observations,
unload/end, Track Insight fallback and Discover Genre→Track regressions retain
their existing checks. Runtime-only memory and source limits remain intact.

## Validation and independent review

- Local source and exact-main full suites: **1,562 tests, 7 skips, PASS**.
  An initial unrelated roadmap subprocess timeout passed focused/full reruns.
- Golden-related Session Intelligence suites: **18 tests, PASS**. The existing
  six Golden scenarios are protected by their unchanged source suite; this
  bounded fact choice changes neither scenario ownership nor capture format.
- Ruff on production/tests/new capture script and `git diff --check`: PASS.
- Independent exact read-only source review: **GO, no remaining P1/P2/P3**.
  Reviewer ran 136 tests, checked candidate production hashes and visually
  inspected portrait/landscape frames. The initial P2 recent-type evidence gap
  was fixed before freeze with the causal four-angle scenario.
- Software browser packet:
  `artifacts/verification/contextual-fact-planning/`: exact-base/current real
  Core Runtime snapshots/receipts, reason codes and 20 VibeCast PNGs at
  1200×1920 and 1920×1200. The unchanged consumer rendered Manual, Discover,
  calm and short-fit sequences with exact source links/no-store. Existing
  four-fact owner-refinement browser regression also PASS. Producer responses
  and time are mocked; no live-provider or hardware evidence is inferred.
- Source protected Trusted Delivery qualification and all non-skipped PR
  checks passed. Exact-main [Validate](https://github.com/pcvantol/djconnect/actions/runs/37638027123),
  [CodeQL](https://github.com/pcvantol/djconnect/actions/runs/37638025742),
  [artifact](https://github.com/pcvantol/djconnect/actions/runs/37638393158) and
  [redacted evidence](https://github.com/pcvantol/djconnect/actions/runs/37638393766)
  passed. The evidence workflow's first NOT_QUALIFIED attempt produced no
  durable publication; attempt 2 succeeded with the same immutable source and
  policy after readback of preserved PR checks and exact-main coverage.

## Publication, privacy and qualification boundaries

The owner explicitly answered **akkoord** for source PR #1122's automatic
internal SHA-prerelease. The verified
[internal artifact](https://github.com/pcvantol/djconnect/releases/tag/internal-ha-d7a646e0e83a92211875e2f3b45606678e992e76)
has archive SHA-256
`e92cc2d28b2b35582ea7b3300c9dd3d99a939b35f9ce7cb43a6e60db84e00243`.
Archive paths/types are safe and its 127 files are byte-equal to exact merged
source. Qualification JSON SHA-256:
`d4acf35722023a2f6417301fc551d658a439f83149dcb8a6f2bd9f8953e0dc23`.
Coverage artifact digest:
`6e06831d016803051f46db64c1a2935429ea88cea92a895f91c5299e8a7a4b6b`.
This Finalization merge causes an additional internal SHA-prerelease; confirm
specific authority against its reviewed candidate before that protected merge.
No source or Finalization artifact is installed on HA-dev or production.

`SOFTWARE_CONTEXTUAL_FACT_PLANNING_QUAL=PASS`;
`LIVE_PROVIDER_QUAL=NOT_RUN_FOR_THIS_SLICE`;
`PHYSICAL_PI_QUAL=NOT_RUN_FOR_THIS_SLICE`.
Earlier `PER_MOMENT_SCREENSHOT_CAPTURE=PARTIAL` and
`TRANSITION_MOTION_EVIDENCE=PARTIAL` remain parked and unchanged.
Full Artist/Album credits Phase B, new providers, generative rewriting, TTS,
new Moment types, future queue, cross-Session learning and UI/queue polish are
outside scope. No additional provider calls/accounts/credentials or costs.

## Finalization and stop boundary

Finalization is documentation-only, requiring independent exact review,
governance consistency, protected checks/merge, exact-main readback and safe
cleanup. Source implementation remains frozen. The five Planned distribution
items were read afresh from `PLATFORM_EVOLUTION_BACKLOG.md`: Apple, Windows,
public HACS, HACS 3.3.0 release visibility and firmware OTA rollback. Their
separate authorization/qualification gates remain; none is dispatched.

Outstanding slice delivery at this record's freeze: protected Finalization,
its specifically authorized automatic publication/readback and workspace
cleanup. Recommended next prompt: none under this assignment. Stop after one
fully reconciled intelligence slice; do not reopen #1118–#1121.
