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
| DJ Intelligence Evolution | Runtime-bounded Session continuity, Transition spacing and Session Update pacing | Selected; Core implementation in progress under `DJC-CORE-SESSION-INTELLIGENCE-CONTINUITY-V1-20261004` | [Owner directive](https://github.com/pcvantol/djconnect/issues/1101#issuecomment-5977878118); [executor pickup](https://github.com/pcvantol/djconnect/issues/1101#issuecomment-5980597774); `docs/product/DJ_INTELLIGENCE_MATURITY.md` | One existing HA Runtime/Planner/Knowledge/Moment/Flow path; safe current Track Insight, Direction, Mood, Persona and bounded Flow memory. Multi-track observable Session decisions, deliberate Silence and valid transitions are acceptance. No future-queue truth, Audience Planner input, Lyrics, external knowledge, cross-Session learning or client source. |
| Reference Experience | VibeCast Reference Renderer increment | Selected first-slice Core/Apple source merged; integrated acceptance still open | `PRODUCT_ROADMAP.md`; `docs/product/VIBECAST_REFERENCE_RENDERER_INCREMENT.md`; Core [PR #1104](https://github.com/pcvantol/djconnect/pull/1104); Apple [PR #89](https://github.com/pcvantol/djconnect-app/pull/89) | The ambient renderer and owner handoff source are merged with exact-main CI/evidence. Installed candidate, paired Apple-owner handoff to the physical portrait Pi, active Session, reconnect, Runtime-end and token non-persistence still require exact joint evidence before the reference increment is qualified. Cast feasibility follows that Pi evidence. |

The verification row reconciles the old current-execution heading with the
owning roadmap's completed original scope and leaves optional additions
deferred. The DJ Intelligence row records only the newly selected bounded Core
assignment. The VibeCast row repeats its existing selection and does not
qualify a physical host or start another writer.

## Roadmap-held work not yet selected

The following existing roadmap groups have no active Product Backlog item.
They remain planned or deferred exactly as classified in `PRODUCT_ROADMAP.md`;
they must not be inferred as authorized engineering work.

| Group | Existing roadmap area | Current disposition |
| --- | --- | --- |
| Architecture | Provider-independent Knowledge Source Architecture | Completed architecture refinement; no provider integration selected. |
| Knowledge | Future Knowledge capabilities, including Lyrics Knowledge | Deferred or separately qualified only. |
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
