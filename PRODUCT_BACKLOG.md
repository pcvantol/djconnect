# DJConnect Product Backlog

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
| DJ Intelligence Evolution | Source-qualified production and credits context | Phase A contract protected merged and exact-main qualified under `DJC-CORE-CREDITS-PROVENANCE-V1-20261004`; Phase B Artist/Album product behaviour blocked by missing qualified producer, rights and renderer attribution | [Owner directive](https://github.com/pcvantol/djconnect/issues/1101#issuecomment-5982642617); [Core PR #1108](https://github.com/pcvantol/djconnect/pull/1108) merged as `800516230584f20b4e42c12fe4e240a651260936`; `docs/product/CREDIT_PROVENANCE_SOURCE_CONTRACT.md` | Current Spotify Core normalizers expose only track/album artist and isolated album release date, without a live Session-bound typed production credit or verified link/mark projection. Missing, conflicting, unreliable or unattributable facts remain ineligible. `PRODUCT_ACCEPTANCE=PHASE_A_PASS_PHASE_B_BLOCKED`; no new provider, retrieval, Moment copy, client, playback, persistence or product-release behaviour. |
| Reference Experience | VibeCast Reference Renderer increment | Selected first-slice Core/Apple source, decoder, Profile backend binding, observer reload and live playback/locale coherence repairs merged; physical `PI_QUAL` remains open | `PRODUCT_ROADMAP.md`; `docs/product/VIBECAST_REFERENCE_RENDERER_INCREMENT.md`; Core [PR #1104](https://github.com/pcvantol/djconnect/pull/1104), [Profile binding PR #1110](https://github.com/pcvantol/djconnect/pull/1110), [observer reload PR #1114](https://github.com/pcvantol/djconnect/pull/1114) and [coherence/locale PR #1116](https://github.com/pcvantol/djconnect/pull/1116) merged as `a187f7c6f7f91f4d5c25ff685323e528ba97449c`; Apple [PR #89](https://github.com/pcvantol/djconnect-app/pull/89), decoder [PR #91](https://github.com/pcvantol/djconnect-app/pull/91) and decoder Finalization [PR #92](https://github.com/pcvantol/djconnect-app/pull/92); [physical Pi evidence](https://github.com/pcvantol/djconnect/issues/1101#issuecomment-5980907407) | Physical portrait Pi handoff, active snapshot, reconnect, Runtime end and token non-persistence were observed on an earlier candidate. Core now provides supported Spotify Profile binding, reload-safe observation, current-playback-correlated Moments and Assist-derived five-language Session locale. The exact Core candidate still needs HA-dev installation; Apple must pass its locale explicitly; and a correct Dutch same-Session non-terminal `playback`/`dj_moment`/`session_flow_updated` receipt remains unproven. No integrated PASS or next slice is claimed. |

The verification row reconciles the old current-execution heading with the
owning roadmap's completed original scope and leaves optional additions
deferred. The earlier DJ Intelligence row records the completed bounded Core
continuity assignment; the bounded Discover row records one completed
same-artist Genre→Track narrative relation without opening another family.
The owner-selected credits assignment delivered only
its protected, exact-main-qualified source-qualification gate while Phase B
lacks a qualified producer. The
VibeCast row records the merged Core binding, observer reload and live coherence/locale repairs and the earlier physical
subset without qualifying the remaining exact-candidate non-terminal receipt
or starting another writer.

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
