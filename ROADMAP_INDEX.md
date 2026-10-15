# DJConnect Roadmap Index

## PR #1136 Shared VibeCast renderer — dedicated Finalization

### Repository Status

PR [#1136](https://github.com/pcvantol/djconnect/pull/1136) protected merged as
`b211e5e99235e5862b3befb100dd9e64438f6e80` from independently reviewed
`7460ef5e1d4c15888569b857d7c636620ace7e37`; both trees
`7774f7d002d0946eeaefe6bc769f3ee853ee0de5`. Assignment
DJC-CORE-VIBECAST-SHARED-RENDERER-V1-20261009; original base69315f43dd1cce8cca4d70f28eccfbc3daa37c66;
one reused Core writer, branch codex/vibecast-shared-renderer. ACK6079692264 and
first material6079707457 followed fresh canonical hostverify0/MATCH. Initial
admission was held for disk and then stopped Tailscale; no source mutation
occurred while NOT_READY. Apple WIP/lab and installed HA-dev were preserved.

Source1680 unittest scenarios PASS(7 existing skips),172 verification PASS,
Ruff/diff/Bandit medium gate PASS. Independent exact technical/privacy and
bounded software-UX GO,19 testsPASS,139 integration/source hashes matched.
Two draft P2 findings were fixed: late collect after host-stop and incomplete
manifest identity validation. New CodeQL HTML-tag regex finding was corrected
with the standard HTMLParser and regression, without suppression. All final
candidate checks PASS; protected tree readback equal.

Source/main Validate37930455032, coverage, CodeQL37930454085, Golden37930453407,
EP boundary37930453296 and TDE37930453402 PASS. Automatic qualification37930767801
first attempt PASS; canonical integrity and every required check validatePASS.
Package37930767333 initially failed because the concurrent qualification job
created the same release tag (HTTP422 Release.tag_name already exists). Only
that failed package job was retried on unchanged approved SHA; attempt2 PASS.
No workflow/source repair, evidence replacement or unrelated dispatch occurred.
139 safe regular package files are byte-identical to exact source-main. Archive
SHA256a0f96433f6e9d2d0751c1a8a3c4d0ecd00915d32abe81d40d552547a65968b92;
qualificationJSONSHA256d1a10ca354a8fb330fc0a545fc33d96f7e24f2b406b4238f64da528f6fdc6ac6.
Coverage11615878235 digest32c16f57ad33bcb449a82a9ced6ef4be02a19577be3c1fdc0ce8de4971ca2f21
matches durable qualification; not expired. Canonical and isolated source-main
readback equalb211e5e9 with reviewed7774f7d0 tree. Source remains uninstalled.

The separately approved generic static bundle was uploaded once, without
clobber, to the same internal source prerelease. Published asset API digest
matchesdfb800634652de610e6d3861bc0aedfa1e1cdb1a65dc80b3bdd4a2a3326c56d1.
[Immutable static bundle](https://github.com/pcvantol/djconnect/releases/download/internal-ha-b211e5e99235e5862b3befb100dd9e64438f6e80/vibecast-shared-7460ef5e.tar.gz)
contains both self-contained entries and externally pinned manifest; supplying
commit7460ef5e is preserved, not relabeled as the squash SHA. No receiverrepo
push, Pages/Cast/LG deployment or installation followed.


### Management Summary

One migrated rich VibeCast source builds the self-contained HA/Pi entry and
static Cast entry. Local claims and thin CAF handoff differ; Moment identity,
Persona text, source links, ordering/dedupe/expiry and presentation share one
implementation. Static runtime data comes directly from authorized HA HTTPS.
Exact existing HA CORS origins supplement token authority; public start URLs
carry no private data. Version1 handoff/current snapshot capability checks fail
closed. No private Apple conversation/archive/search/Profile projection,
second Planner/Knowledge pipeline, Swift writer or new TTS is introduced.

Eleven actual isolated HA2026.10/TLS/Core-Broadcast browser sequences cover
original baseline and local/static builds in five languages, portrait1200x1920
and landscape1920x1080; ordinary producer credit, shared-producer two sources,
actual later same-track Moment, reconnect/renewal, expiry/Runtime-end and held
real collect after host-stop with no late socket. Before/after PNGs and motion
records are retained. Source and image-provider adapters are synthetic; CAF
message delivery is modeled. Browser trust is confined to the disposable lab
NSS/Node CA; no certificate/auth bypass or live-provider/hardware claim.

Pinned delivery7460ef5e/build1.0.0 manifestSHA256
72239b476e793fe5bb5493d2be5720fcd1f6e64ea83e012c77573732a58c7898,
bundleSHA256dfb800634652de610e6d3861bc0aedfa1e1cdb1a65dc80b3bdd4a2a3326c56d1,
rendererSHA2562f08d8f0a82db1749ef97ff5508dd64016b35f14878abdcd5f3475f27bfec276.
VibeCast#10/6080217273 supersedes the historical24e4 pin; Apple was informed via
its existing register. Receiver import/Pages/AppID/TV qualification stay owned
by the receiving lane. Public/physical promotion is not implied.

[Completion and Finalization](docs/history/prompts/2026-10-09-vibecast-shared-renderer-finalization.md)
closes only this slice after exact Finalization delivery and safe own cleanup.

### Roadmap Position

Generation2/Phase1 remains current. CORE_LOCAL_RENDERER and SHARED_STATIC_BUILD
are software PASS; CONTRACT_COMPATIBILITY is currentv1 software PASS;
DISTRIBUTION_HANDOFF is pinned, not live promoted. GOOGLE_CAST_TV_QUAL and
LG_WEBOS_QUAL are NOT_RUN. Chromium68 syntax/fallback preparation is not actual
legacy-engine or CX hardware qualification. Pi capture/frame-rate remainsPARTIAL.

### Rolling Horizon (Execution Horizon — Next 5 Planned)

1. **Public distribution: Apple — Planned** | Source: `PLATFORM_EVOLUTION_BACKLOG.md`; dependency: qualified Internal Release consumers and explicit authorization. Execution Rationale: next canonical retained public-distribution item after its release gates.
2. **Public HACS distribution — Planned** | Source: `PLATFORM_EVOLUTION_BACKLOG.md`; dependency: fresh candidate and release authorization. Execution Rationale: next retained integration distribution item.
3. **HACS 3.3.0 release visibility (`HACS-3.3.0-001`) — Planned** | Source: `PLATFORM_EVOLUTION_BACKLOG.md`; dependency: release metadata and discovery evidence. Execution Rationale: bounded recorded visibility investigation after HACS qualification.
4. **Firmware OTA publication and staged rollback — Planned** | Source: `PLATFORM_EVOLUTION_BACKLOG.md`; dependency: manifest-bound consumer qualification. Execution Rationale: next recorded firmware distribution item after its consumer gate.
5. **ESPHome firmware platform adoption — Planned** | Source: `PLATFORM_EVOLUTION_BACKLOG.md`; dependency: ADR-0017, pinned community baseline and board qualification. Execution Rationale: next recorded eligible adoption assessment; no implementation selected.


### Blocked Items

Actual receiver import, secure deployed HA reachability, Google AppID/CAF/TV and
LG .ipk/input/suspend/hardware remain separately gated receiving work. Core has
no remaining source review finding. Distinct Finalization publication approval
and exact finalmain/readback are still required before terminal reconciliation.

### Deferred Items

No Pages/receiverpush/tvinstall, HA-dev update, Pi probe, Windows retirement,
new monitor/provider/knowledge family or next source increment is selected.
HA-dev remains explicitly installed69315f43; this source is not installed.

### Repository State

Repository State: `MERGED_RECONCILED` only after this dedicated Finalization's
approved protected merge and exact-main/package readback. Until those conditions
hold, actual state is MERGED_UNRECONCILED and Finalization PendingYES. The final
identity is bound by external receipts, never fabricated in its own document.

### Workspace State

Workspace State: `CLEANUP_PENDING` until verified own source/Finalization branch
cleanup. Source/internal bundle publication and later local sourcebranch cleanup
were specifically approved by direct owner “ga verder”; local Finalizationbranch
cleanup and its distinct publication still require specific approval. Retain
recovery/evidence and other writer WIP. Stop after this one Core delivery.


**Status:** Canonical navigation

Use this index to find the one canonical record for current work.

CMB-04 is complete as the atomic Renderer Experience roadmap assessment;
`docs/product/RENDERER_EXPERIENCE_ROADMAP.md` is its planning projection.
CMB-08 is complete as the Universal Receiver / VibeCast decomposition recorded
in that same roadmap projection.

| Need | Canonical document | Owner |
| --- | --- | --- |
| Generation 2 execution direction: remaining assessment necessity, bounded engineering readiness, blocked and deferred disposition | `docs/governance/GENERATION_2_EXECUTION_REVIEW.md` | Platform governance |
| Long-term engineering intent | `PLATFORM_STRATEGY.md` | Platform strategy |
| Generation 1 historical closure | `ENGINEERING_PLATFORM_GENERATION_1_COMPLETION_REPORT.md` | Platform governance |
| Program boundaries | `ENGINEERING_PROGRAM_MODEL.md` | Engineering governance |
| Generation 2 completed foundations, current execution and historical-transition reconciliation | `GENERATION_2_PROGRAM_RECONCILIATION.md` | Platform governance |
| User-facing product priorities and sequence | `PRODUCT_ROADMAP.md` | DJConnect Product Development |
| Selected current product work and roadmap-held work not yet selected | `PRODUCT_BACKLOG.md` | DJConnect Product Development |
| Future Interactive DJMoments capability family and its assessment-first boundary | `PRODUCT_ROADMAP.md` | DJConnect Product Development |
| Future Session Continuation capability family, privacy-safe external invitation boundary and assessment-first scope | `PRODUCT_ROADMAP.md` | DJConnect Product Development |
| Future Session Lifecycle Completion capability family, activity-aware completion, closing experience and completed-Session transition boundary | `PRODUCT_ROADMAP.md` | DJConnect Product Development |
| Future Apple Watch Moment-First Conversational Companion experience, within Apple Premium Experience | `PRODUCT_ROADMAP.md`, `docs/product/RENDERER_EXPERIENCE_ROADMAP.md` | Product Development / Apple Renderer Host |
| Future Home Assistant installation-to-first-DJ-Session onboarding and configuration experience | `PRODUCT_ROADMAP.md` (`HA-ONBOARDING-001`) | Product Development / Home Assistant Integration |
| Product & Community Readiness phase: presentation, onboarding, deployment and developer-experience readiness before Community Public Release | `PRODUCT_ROADMAP.md` | DJConnect Product Development |
| Engineering-platform improvements | `PLATFORM_EVOLUTION_BACKLOG.md` | Platform Evolution |
| Embedded EP source retirement owner decision and active DJConnect boundary | `docs/governance/LANE_5_EP_SOURCE_RETIREMENT.md`, `docs/development/ENGINEERING_PLATFORM_SOURCE_RETIREMENT.md` | LANE_5 / DJConnect |
| Completed TDE 1.1.1 consumer rollout and its product-planning boundary | `docs/governance/TDE_1_1_1_PLANNING_RECONCILIATION.md` | Platform governance |
| Current Generation 2 assessment qualification status and remaining objective items | `QUALIFICATION_REGISTER.md` | Cross-program governance index |
| Implemented cross-platform capability catalog, projections and convergence decisions | `DJCONNECT_CAPABILITY_MODEL.md` | Platform Foundation |
| Host Role abstraction, capability inheritance and platform role matrix | `HOST_ROLE_ARCHITECTURE.md` | Platform Foundation |
| Raspberry Pi Platform Family and Pi 4-inch/Pi 10-inch Concrete Host architecture | `RASPBERRY_PI_PLATFORM_FOUNDATION.md` | Platform Evolution |
| Canonical reverse-engineered cross-surface experience baseline and Experience Gap Analysis framework | `EXPERIENCE_FOUNDATION.md` | Experience Engineering |
| Assessment-first capability-model planning projection | `CAPABILITY_MODEL_BACKLOG.md` | Platform Evolution |
| Registered Native Surface Integration family, its Apple-first capability assessment and bounded future surface candidates | `docs/product/RENDERER_EXPERIENCE_ROADMAP.md`, `CAPABILITY_MODEL_BACKLOG.md` | Platform Evolution / Apple Renderer Host |
| Repository-grounded current DJ Intelligence, Planner inputs, knowledge sources, DJMoments and planning gaps | `docs/product/DJ_INTELLIGENCE_CAPABILITY_REVIEW.md` | DJConnect Product Development |
| Live Playback Observation, Continue Current Playback Continuity and external capability dependencies | `docs/product/DJ_INTELLIGENCE_MATURITY.md` (canonical maturity, blocked status and planning policy), `docs/product/LIVE_PLAYBACK_OBSERVATION.md`, `docs/product/CONTINUE_CURRENT_PLAYBACK_CONTINUITY.md`, `docs/adr/0016-playback-instance-identity-observation-boundary.md` | DJConnect Product Development |
| DJ Session transport independence, HTTP recovery and transport-neutral Broadcast delivery | `DJ_SESSION_TRANSPORT_ARCHITECTURE.md` | DJConnect Product Development |
| Historical V4 transition to the completed Session Intelligence Runtime milestone | `DJCONNECT_V4_COMPLETION_ROADMAP.md`, `docs/product/DJ_INTELLIGENCE_MATURITY.md` | Historical engineering evidence |
| VibeCast ambient web-renderer product definition and selected reference increment: portrait Pi evidence first, landscape Google Cast Custom Web Receiver follow-on | `docs/product/VIBECAST_REFERENCE_RENDERER_INCREMENT.md`, `docs/product/VIBECAST_ARCHITECTURE.md`, `docs/technical/RENDERER_HOST_CLASSIFICATION.md`, `docs/technical/UNIVERSAL_RECEIVER_ARCHITECTURE.md`, `PRODUCT_ROADMAP.md` | DJConnect Product Development |
| Deferred Audience Experience, ambient reactions and future privacy-bounded Audience Observation | `docs/product/AUDIENCE_EXPERIENCE_ARCHITECTURE.md`, `PRODUCT_ROADMAP.md`, `INNOVATION_BACKLOG.md` | DJConnect Product Development / Innovation Lab |
| Deferred room-scoped eligibility for independent Visual and Audio Renderer Hosts | `docs/technical/ROOM_PRESENTATION_ROUTING_ARCHITECTURE.md`, `PRODUCT_ROADMAP.md` | DJConnect Product Development |
| Audio Renderer Host internal terminology and its Home Assistant Voice Satellite mapping | `docs/technical/AUDIO_RENDERER_HOST_ARCHITECTURE.md`, `PRODUCT_LANGUAGE.md` | DJConnect Product Development |
| Deferred Ambient Light Renderer Host direction and lighting-platform boundary | `docs/technical/AMBIENT_LIGHT_RENDERER_HOST_ARCHITECTURE.md`, `PRODUCT_ROADMAP.md` | DJConnect Product Development |
| Deferred Platform Ambient Experience: platform-neutral wall-panel direction and future Platform Adapter boundary | `docs/technical/PLATFORM_AMBIENT_EXPERIENCE.md` | DJConnect Product Development |
| Current engineering execution supporting DJ Intelligence Evolution: Automated Session Intelligence E2E Verification, its architecture, Golden Scenario catalogue, governance, qualification policy and executable restricted Verification Clock | `docs/verification/SESSION_INTELLIGENCE_E2E_ARCHITECTURE.md`, `docs/verification/SESSION_INTELLIGENCE_GOLDEN_SCENARIOS.md`, `docs/verification/GOLDEN_SCENARIO_GOVERNANCE.md`, `docs/verification/SESSION_INTELLIGENCE_QUALIFICATION_POLICY.md`, `docs/verification/VERIFICATION_CLOCK_ARCHITECTURE.md`, `docs/product/DEVELOPER_EXPERIENCE_ROADMAP.md` | DJConnect Product Development |
| Durable Session lifecycle, historical DJMoment projections and future local persistence sequencing | `PERSISTENT_SESSION_ARCHITECTURE.md` | DJConnect Product Development |
| Rolling approximately twenty-minute Session experience planning, safe future-context degradation and bounded replanning sequence | `ROLLING_SESSION_HORIZON_ARCHITECTURE.md` | DJConnect Product Development |
| Coordinated V4 server-to-iOS completion sequencing, gates and deferred work | `DJCONNECT_V4_COMPLETION_ROADMAP.md` | DJConnect Product Development |
| Future ideas and research | `INNOVATION_LAB.md`, `INNOVATION_BACKLOG.md` | Innovation Lab |
| Innovation promotion rules | `INNOVATION_PROMOTION_POLICY.md` | Innovation Lab |
| Current operational release position | `docs/release/PLATFORM_RELEASE_MANAGEMENT_SUMMARY.md` | Platform Release operations |
| Consolidated state | `MANAGEMENT_SUMMARY.md` | Platform governance |
| Engineering-method operating rules | `ENGINEERING_METHOD.md` | Engineering governance |
| Repository-governance rollout decision | `docs/governance/REPOSITORY_GOVERNANCE_ROLLOUT.md` | Platform governance |
| Repository-governance rollout plan | `docs/governance/REPOSITORY_GOVERNANCE_ROLLOUT_PLAN_V2_2.md` | Completed and archived governance evidence |
| Repository-governance audit | `docs/governance/REPOSITORY_GOVERNANCE_AUDIT_V2_2.md` | Completed and archived governance evidence |
| Execution prompt navigation | `PROMPT_INDEX.md` | Prompt governance |

`PLATFORM_BACKLOG.md` is a Generation 1 archive, not an active source of
priority. Historical project and release records remain evidence, not duplicate
roadmaps.
