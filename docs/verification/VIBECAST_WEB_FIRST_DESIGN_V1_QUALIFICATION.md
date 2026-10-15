# VibeCast web-first design — documentary qualification v1

Assignment: `DJC-VIBECAST-WEB-FIRST-GUEST-EXPERIENCE-DESIGN-V1-20261015`.
Authority: [issue #1174](https://github.com/pcvantol/djconnect/issues/1174).
Admission: [public receipt](https://github.com/pcvantol/djconnect/issues/1174#issuecomment-6196869453).
Date: 2026-10-15. Decision: **GO for docs-only reviewable delivery**;
product implementation **Planned**, native/physical/joint acceptance **OPEN**.
Source PR/exact reviewed head are recorded in GitHub at freeze; no main merge is
claimed by this premerge record. Separate Finalization remains mandatory.

## Admission and source boundary

Clean isolated branch `codex/vibecast-web-first-guest-design-v1` is based on
verified main `70c0a3009910db8763e65949d0a10eade7d006dc`. First material commit
`25652ec9` contains the actual three designs, canonical addenda and live DAG.
Canonical macOS host verification exited 0/MATCH, desired-state manifest 3.3.0,
onboarding package 4.5.3. Existing Core writer explicitly confirmed serialized
docs-before-Speech integration; no unmerged runtime/maintenance12 is imported.
Its active Speech/Persona work, Apple #87 and receiver #10 work remain intact.
Future Speech integration must preserve this extension on freshly qualified main.

## Durable outputs and architectural delta

- [Whole experience](../product/VIBECAST_WEB_FIRST_EXPERIENCE_V1.md): issue sections 1–10 traceability, web-first/legacy disposition, two-step onboarding, shared readonly view, five-reaction design, guest chat, exact requests, lifecycle, open questions and future acceptance matrix.
- [Trust/authority](../product/VIBECAST_ONBOARDING_GUEST_AUTHORITY_V1.md): minimal encrypted rendezvous proposal, per-browser secrets, role matrix, REST/WSS/media/effect fences, expiry, threat model, source checks and unqualified security gates.
- [Apple guest mode](../product/APPLE_VIBECAST_GUEST_MODE_V1.md): distinct scanner intents, permission/discovery/QR fallback, home isolation, local leave, callbacks, crash and safe return.
- Canonical VibeCast/Audience/Universal Receiver/build/refinement references, product index, ADR navigation, canonical map, roadmap/backlog and SYNC_PROMPTS point to the same forward contract.
- Live JSON adds 21 WEB:: subsets and 44 typed dependencies under existing VibeCast/Audience/Guest parents; all 23 human views/diagrams are generated. Only DOCS is Completed/DESIGN_AUTHORED, explicitly distinct from protected publication; all 20 product slices are Planned/NOT_ISSUED. Earlier delivered receipts/statuses and frozen snapshots remain byte-semantically unchanged.

No frozen platform owner or engine is replaced. Cast-first/native-TV entry
prerequisites are superseded for forward design; optional adapters and prior
source/physical evidence remain historically scoped. Existing installed opt-in
end-only grants are not changed; new web-first TV targets are readonly. The
central service is only a proposed temporary bootstrap owner boundary, not a
new Session backend or approved deployment.

## Executed validation

| Check | Actual result / limit |
| --- | --- |
| Existing DAG structure/schema/acyclicity plus generated views | PASS; validator reports PASS_INCLUDED_SNAPSHOT_ONLY, complete_delivery=false |
| `python3 -m unittest -q test_snapshot test_maintenance_delta` in roadmap v1 | 150 tests PASS; includes 12 new negative mutations against false delivery/dispatch, hidden choices, overwritten predecessor, ownership/dependencies/cycle/hash |
| Full existing integration test suite | 1,949 tests PASS, 7 existing skips; source tree unchanged |
| Offline AI-development projection | PASS with pinned source ec070e399ff4dbd92e760370002995fe4f4d52d6/profile djconnect/extension DJCONNECT_DEVELOPMENT_EXTENSION |
| Software Assurance governance CLI | PASS, canonical policy 1.0.0 |
| Ruff on changed docsgate Python | PASS |
| Changed Markdown local links | 285 checked, zero missing before this record; final freeze reruns all changed links |
| Predecessor semantic comparison | All existing nodes/edges/receipts/statuses and nonmaintenance JSON unchanged; document bindings intentionally refreshed |
| Scope and diff hygiene | `git diff --check` PASS; production integration, SDK, firmware, scripts, workflows, runners, onboarding and generic tools unchanged |
| Independent product/UX review | GO, all ten issue topics and future acceptance coverage checked |
| Independent technical/privacy review | Initial gate failure fixed with explicit documentary test branch; rereview GO, 150/150 tests and generated views PASS; no remaining concrete finding |

The docsgate changes are strictly needed to admit and verify this new additive
planning extension. They retain the existing schema11 predecessor validator,
strip only the versioned WEB extension, bind old node/edge digests and validate
all new owners/prerequisites, full-graph acyclicity and document hashes. No old
test assertion is disabled; the explicit DOCS assertion preserves all product
Planned checks. No production/test runner/workflow gate is relaxed.

## Remaining gates and handoff

Short URL/domain/path, unspecified web-first exception, exact five emoji,
crypto/service/old-browser choice, shared-media rights, Apple rendering strategy
and budgets/share policy remain OPEN. No runtime, installation, deployment,
domain registration, source-rights approval or model/provider/cost commitment.
No fallback-only product PASS. Golden Scenarios are related only indirectly:
existing server-owned Session/Flow/Broadcast semantics are preserved; future
WF-01 through WF-12 require real primary-path source/consumer/native/physical
qualification, not this documentary test run.

Before source merge: exact independent review, all required checks, exact
HIGH_RISK Owner Authorization for canonical-map changes and the bounded source/
internal-artifact publication gate. Before reconciliation: separate governance
Finalization with exact predecessor/PR/main/check evidence, updated rolling
records and immutable history; then own-checkout cleanup. Main workflows may
publish the existing internal HA artifact/formal evidence on a successful main
validation even though its runtime bytes are unchanged. No Pages, DNS, HA install
or production deployment is part of that effect.

Core #1101, Apple #87 and receiver #10 receive exact documentary source and
Finalization pins only after their actual gates. This is not runtime dispatch.
Next step is this same assignment's protected delivery/Finalization, not a new
product capability. Release ordering and selected Speech/consumer work remain.
