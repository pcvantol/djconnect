# DJConnect Product Backlog

Completed source: `DJC-CORE-SHARED-PRODUCER-CONTINUITY-V1-20261007`,
PR [#1124](https://github.com/pcvantol/djconnect/pull/1124) protected merged as
`c542d8ea9889db3509cab2dd5f19b26dd1a21342` from independently reviewed head
`da309585121d7069c5a56fdd3a0520fc567d2419`; source/merge trees equal
`d8a6d668247ea87d0c6f25d2b58e893b7c9054d9`.
[Shared-producer contract](docs/product/SHARED_PRODUCER_CONTINUITY_CONTRACT.md)
qualifies one Discover/Exploring track relation and the requested glass bubbles.
[Completion and Finalization](docs/history/prompts/2026-10-07-shared-producer-continuity-finalization.md) reconciles protected source, software/browser proof and
internal publication. No install, broader credits Phase B or next slice.

Completed source: `DJC-CORE-CONTEXTUAL-FACT-PLANNING-V1-20261007`,
[contextual fact planning](docs/product/CONTEXTUAL_FACT_PLANNING_CONTRACT.md).
Improves selection and dosing within #1120's existing qualified fact pool;
Runtime/browser software acceptance, exact review and protected checks passed;
PR #1122 merged as `d7a646e0e83a92211875e2f3b45606678e992e76`.
The [dedicated Finalization](docs/history/prompts/2026-10-07-contextual-fact-planning-finalization.md)
reconciles the source; completion follows its merge/cleanup. No new provider, speech, future queue,
persistent learning or change to parked physical PARTIAL findings.

**Status:** Canonical selected-product-work register

## Purpose

This register contains only product work selected from
`PRODUCT_ROADMAP.md`. It does not create a capability, authorize an
assessment or implementation, or replace the roadmap's phase sequencing.
Platform Evolution, Verification, Software Assurance and TDE work remain in
their owning records.

## Current selected work

| Group | Item | Status | Canonical evidence | Boundary |
| --- | --- | --- | --- | --- |
| Verification support | Automated Session Intelligence E2E Verification | Completed for the original selected scope; optional additions deferred | `docs/product/DEVELOPER_EXPERIENCE_ROADMAP.md` | All six original Golden Scenarios and their architecture, bootstrap, driver, capture, validator, Smoke, Regression, advisory CI, browser E2E and process-local overlay are reported complete. Deferred Presentation scenarios, TTS replay and comparison need separate selection; this row starts no new work. |
| DJ Intelligence Evolution | Runtime-bounded Session continuity, Transition spacing and Session Update pacing | Completed — Core source protected merged and exact-main qualified under `DJC-CORE-SESSION-INTELLIGENCE-CONTINUITY-V1-20261004` | [Owner directive](https://github.com/pcvantol/djconnect/issues/1101#issuecomment-5977878118); [Core PR #1106](https://github.com/pcvantol/djconnect/pull/1106) merged as `b2c2264f59777a4a2fd620fd2d2a63c0472e1e73`; `docs/product/DJ_INTELLIGENCE_MATURITY.md` | One existing HA Runtime/Planner/Knowledge/Moment/Flow path; safe current Track Insight, Direction, Mood, Persona and bounded Flow memory. Multi-track observable Session decisions, deliberate Silence and valid transitions passed source/Session-level acceptance. No future-queue truth, Audience Planner input, Lyrics, external knowledge, cross-Session learning or client source. VibeCast Pi acceptance remains separate. |
| DJ Intelligence Evolution | Bounded narrative Discover Genre→Track continuation | Completed — Core source protected merged as `3b93284e00844ced9d6ec1b2e2fd945c9a1ccff3` under `DJC-CORE-DISCOVER-NARRATIVE-TRANSITION-V1-20261004`; exact-main qualification recorded in its Finalization | [Owner directive](https://github.com/pcvantol/djconnect/issues/1101#issuecomment-5983584086); [Core PR #1112](https://github.com/pcvantol/djconnect/pull/1112); `docs/product/DISCOVER_NARRATIVE_TRANSITION_CONTRACT.md`; `docs/product/DJ_INTELLIGENCE_MATURITY.md` | One verified artist-genre relation between existing Genre and Track Moments from consecutive observed Spotify tracks. Opens once per Discover Runtime, deepens once or abandons on the next accepted event, then closes. Existing Transition and Manual/Continue remain; no future track, new provider, client, playback mutation or physical Pi acceptance. |
| DJ Intelligence Evolution | Source-qualified production and credits context | Phase A contract protected merged and exact-main qualified under `DJC-CORE-CREDITS-PROVENANCE-V1-20261004`; Phase B full Artist/Album product behaviour remains blocked by consumer, rights and all-surface attribution gates | [Owner directive](https://github.com/pcvantol/djconnect/issues/1101#issuecomment-5982642617); [Core PR #1108](https://github.com/pcvantol/djconnect/pull/1108) merged as `800516230584f20b4e42c12fe4e240a651260936`; `docs/product/CREDIT_PROVENANCE_SOURCE_CONTRACT.md` | At the #1108 Phase A snapshot, Spotify Core normalizers exposed only track/album artist and isolated album release date; they had no live Session-bound typed production credit or verified link/mark projection. Missing, conflicting, unreliable or unattributable facts remain ineligible. `PRODUCT_ACCEPTANCE=PHASE_A_PASS_PHASE_B_BLOCKED` remains the #1108 decision. Later #1120 separately qualified a narrow attributed MusicBrainz production-credit VibeCast card, without qualifying full Artist and Album credit consumption or a public release. |
| Reference Experience | VibeCast Reference Renderer first increment | Complete — `SIMULATOR_QUAL=PASS`, `PHYSICAL_PI_QUAL=NOT_RERUN_BY_USER_OVERRIDE` | [Owner closure](https://github.com/pcvantol/djconnect/issues/1101#issuecomment-6010273964); `docs/product/VIBECAST_REFERENCE_RENDERER_INCREMENT.md`; Core [PR #1116](https://github.com/pcvantol/djconnect/pull/1116) and Finalization [PR #1117](https://github.com/pcvantol/djconnect/pull/1117); Apple [PR #93](https://github.com/pcvantol/djconnect-app/pull/93) and Finalization [PR #94](https://github.com/pcvantol/djconnect-app/pull/94) | Exact Core/Apple source was qualified through a paired iPhone simulator, HA-dev and a portrait receiver with real Spotify Direct playback, Dutch same-Session non-terminal update, reconnect, Runtime end and ephemeral handoff. The owner replaced the remaining physical Pi run with simulator acceptance; earlier Pi subset evidence is not a new hardware PASS. |
| Reference Experience | VibeCast same-track Moment timeline and portrait cards | Core source merged; separate owner refinement physically qualified with findings | [Owner selection](https://github.com/pcvantol/djconnect/issues/1101#issuecomment-6011916468); [acceptance](https://github.com/pcvantol/djconnect/issues/1101#issuecomment-6012947392); [source PR #1118](https://github.com/pcvantol/djconnect/pull/1118) merged as `f15fb861e223a209341592666dc2092bad4b4a2e`; `docs/product/VIBECAST_MULTIMOMENT_TIMELINE_CONTRACT.md` | One active observed item produced distinct factual Genre and Track Moments through the canonical Planner/Knowledge/Moment/Flow/Broadcast path. The 1200×1920 browser proved bounded readable cards, entry/exit motion, scrolling, reconnect and expiry with deterministic Runtime events. The fixture is synthetic, not live Spotify or a fresh 10-inch Pi run. No new audio, source calls, persistent history or client ownership. [Owner refinement PR #1120](https://github.com/pcvantol/djconnect/pull/1120) added qualified source facts, visuals and opt-in end; a new physical run passed real same-track two-type playback and idle, with capture automation and full-rate motion partial. The baseline first-slice flags stay historical. |

The verification row reconciles the old current-execution heading with the
owning roadmap's completed original scope and leaves optional additions
deferred. The earlier DJ Intelligence row records the completed bounded Core
continuity assignment; the bounded Discover row records one completed
same-artist Genre→Track narrative relation without opening another family.
The owner-selected credits assignment delivered only
its protected, exact-main-qualified source-qualification gate. Later #1120
qualified a narrow MusicBrainz producer card; full Phase B Artist/Album
consumption, rights and attribution remain separately blocked. The
first VibeCast row records the owner's completed simulator acceptance and
keeps the physical Pi outcome explicit. The second row is the newly selected
same-track slice and does not inherit hardware qualification.

## Roadmap-held work not yet selected

The following existing roadmap groups have no active Product Backlog item.
They remain planned or deferred exactly as classified in `PRODUCT_ROADMAP.md`;
they must not be inferred as authorized engineering work.

| Group | Existing roadmap area | Current disposition |
| --- | --- | --- |
| Architecture | Provider-independent Knowledge Source Architecture | Completed architecture refinement; no provider integration selected. |
| Knowledge | Future Knowledge capabilities, including Lyrics Knowledge and production-credit Moment consumption | Deferred or separately qualified only; the selected credits assignment cannot enter Phase B until its producer and attribution prerequisites are proven. |
| Runtime | Playback Observation Stage 2 and Continue Stage 2 | Blocked by Backend-owned Playback Instance Identity. |
| Planner | Broader long-horizon, autonomous narrative and cross-Session Performance Learning directions | Deferred beyond the separately selected Runtime-bounded continuity tranche above. |
| Renderer Experience | Reference Experience, Universal Receiver and platform-native surfaces | Planned, assessment-first where recorded. |
| Productization | Public Release Readiness, Productization and Product & Community Readiness | Planned in their recorded phases. |
| Documentation | Canonical planning and product documentation | Maintenance through bounded documentation increments only. |
| Community | Community Public Release | Planned after its recorded readiness dependencies. |
| Maintenance | Operational quality and release evidence | Owned by Platform Evolution and operational foundations, not this backlog. |
| Future Research | Audience, Personal AI DJ and Cloud evolution | Deferred. |

## TDE boundary

TDE 1.1.1 is an operational engineering-quality foundation, not a Product
Backlog item. Its observe-only `code_size`, `complexity`, `coverage` and
`dependency_health` evidence informs engineering quality without selecting,
blocking or reordering product work.
