# DJ Intelligence production and credits provenance — Core Finalization

- **Directive:** `DJC-CORE-PROVENANCE-CREDITS-CONTEXT-V1-20261004` in
  [owning issue #1101](https://github.com/pcvantol/djconnect/issues/1101#issuecomment-5982642617).
- **Assignment:** `DJC-CORE-CREDITS-PROVENANCE-V1-20261004`.
- **Admission:** Exclusive DJC-CORE writer; exact base
  `1f826ed76b803aed6c612fa4b5636f9c1d7ee543`; clean single Core
  checkout; only independent Dependabot #1096 open; canonical host verification
  exit 0/all MATCH with onboarding 4.5.3. VibeCast `PI_QUAL` stayed
  DJC-APPLE-owned; no shared HA test resource was reserved.
- **Implementation:** [Core PR #1108](https://github.com/pcvantol/djconnect/pull/1108),
  reviewed head `0d58cef9ee4793cb18804ee744382b7ab3f2d88c`, protected
  squash-merged as `800516230584f20b4e42c12fe4e240a651260936` with an
  identical tree. Phase A added `custom_components/djconnect/credit_provenance.py`,
  six focused tests and the
  [source contract](../../product/CREDIT_PROVENANCE_SOURCE_CONTRACT.md).
- **Actual source inventory:** Existing normalized Spotify playback exposes a
  joined track artist value and separate track URI/artist IDs; the separate
  album-query normalizer exposes album artist and release date with album URI.
  Live Track Insight drops source URI, IDs, release date and label and has no
  typed producer, songwriter, composer, engineer or featured-role producer.
  Interpretive `production_notes` and injected scenario fixtures are not
  source-qualified facts. The isolated album query is not bound to the current
  observed Session album.
- **Qualification:** The fixed machine-readable policy requires source
  identity, bounded factual category, confidence, freshness, conflict
  suppression, runtime retention, affirmative use rights, applicable Spotify
  link/mark attribution, and Session/renderer/public safety. All current
  fields fail those final gates; no new fact enters Knowledge, Planner,
  DJMoment, Session Flow or Broadcast. `PRODUCT_ACCEPTANCE=PHASE_A_PASS_PHASE_B_BLOCKED`.
  Artist/Album enrichment, within-Session deduplication and behavior acceptance
  items 6–8/12 were not attempted or claimed because the owner directive
  requires stopping after Phase A when current producers are insufficient.
- **Validation:** Six focused tests pass; local full HA suite ran 1,489 tests
  with 7 existing skips and no remaining failure; CI-scope Ruff, compilation
  and diff checks passed. An initial parallel-loaded full run hit only the
  roadmap snapshot validator's 10-second subprocess timeout; isolated and
  repeated full runs passed with no source or timeout change. Independent
  exact-head review found no P1/P2/P3. Exact-main
  [Validate](https://github.com/pcvantol/djconnect/actions/runs/37223741542),
  [CodeQL](https://github.com/pcvantol/djconnect/actions/runs/37223741363),
  [artifact](https://github.com/pcvantol/djconnect/actions/runs/37223870631)
  and [evidence](https://github.com/pcvantol/djconnect/actions/runs/37223870720)
  succeeded. The main Validate run uploaded Cobertura artifact digest
  `sha256:0cc9d9f4a3cfc5f4863f2297d73bcb2e2f6d513d2c45169e3e59e4018439806f`;
  the redacted qualification JSON binds the merge SHA and reports
  `POST_MERGE_RELEASE_EVIDENCE_QUALIFIED` with all required checks PASS.
- **Publication:** The unchanged main workflow produced the publicly visible
  [SHA-bound internal prerelease](https://github.com/pcvantol/djconnect/releases/tag/internal-ha-800516230584f20b4e42c12fe4e240a651260936)
  with one exact HA integration archive and one qualification JSON. This is
  artifact/evidence publication, not a stable product release, signing or
  deployment. No service, protection or workflow changed.
- **Exact Phase B prerequisite:** An authorized source must emit a named,
  role-typed credit with provider identity and evidence handle bound to the
  observed Session track/album. Its rights must positively permit the intended
  use; Knowledge may receive only normalized eligible context; every intended
  surface must satisfy source attribution without leaking provider internals.
  Only then may the existing Planner/Moment path be tested for Artist and
  Album value, non-repetition, safe fallback and immutable contract regression.
  No external provider is selected in this assignment.
- **Finalization:** This governance-only increment reconciles the four
  rolling records, Product Backlog/Roadmap, source-contract status and this
  immutable Prompt History. The five Planned Execution Horizon items remain
  derived from `PLATFORM_EVOLUTION_BACKLOG.md`. Repository State becomes
  `MERGED_RECONCILED` only after Finalization merges; Workspace State becomes
  `WORKSPACE_READY` only after cleanup. No follow-on Core product family is
  started.
