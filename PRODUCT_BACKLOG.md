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
| DJ Intelligence Evolution | Source-qualified production and credits context | Selected `DJC-CORE-CREDITS-PROVENANCE-V1-20261004` — Phase A contract implemented; Phase B Artist/Album product behaviour gated by missing qualified producer and renderer attribution | [Owner directive](https://github.com/pcvantol/djconnect/issues/1101#issuecomment-5982642617); `docs/product/CREDIT_PROVENANCE_SOURCE_CONTRACT.md` | Current Spotify Core normalizers expose only track/album artist and isolated album release date, without a live Session-bound typed production credit or verified link/mark projection. Missing, conflicting, unreliable or unattributable facts remain ineligible. No new provider, retrieval, Moment copy, client, playback, persistence or release behaviour is authorized. |
| Reference Experience | VibeCast Reference Renderer increment | Selected first-slice Core/Apple source merged; physical `PI_QUAL` remains open | `PRODUCT_ROADMAP.md`; `docs/product/VIBECAST_REFERENCE_RENDERER_INCREMENT.md`; Core [PR #1104](https://github.com/pcvantol/djconnect/pull/1104); Apple [PR #89](https://github.com/pcvantol/djconnect-app/pull/89) and decoder [PR #91](https://github.com/pcvantol/djconnect-app/pull/91); [physical Pi evidence](https://github.com/pcvantol/djconnect/issues/1101#issuecomment-5980907407) | Physical portrait Pi handoff, active snapshot, reconnect, Runtime end and token non-persistence were observed. The distinct non-terminal `playback`/`dj_moment`/`session_flow_updated` receipt remains unproven on HA-dev `later_manual`; Apple owns its decoder Finalization and remaining `PI_QUAL`. No integrated PASS or next slice is claimed. |

The verification row reconciles the old current-execution heading with the
owning roadmap's completed original scope and leaves optional additions
deferred. The earlier DJ Intelligence row records the completed bounded Core
continuity assignment; the new owner-selected credits assignment delivers only
its source-qualification gate while Phase B lacks a qualified producer. The
VibeCast row records the observed physical subset without qualifying the
remaining non-terminal receipt or starting another writer.

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
