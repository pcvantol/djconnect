# DJC-CORE — pcvantol/djconnect

This is a pinned planning projection for assignment `DJC-PLATFORM-ROADMAP-DAG-LANES-V1-20261003`. Owning roadmap, backlog, code and qualification records remain authoritative. It grants no product pickup, release, deployment or resource lease.

**Owns:** HA-integratie, centrale productautoriteit en server-side DJConnect-domein. Profiles: HA / Runtime / Universal Receiver / HA-hosted VibeCast.

**Baseline main:** `60d5ee2e034323515092cd4100b1683f588e59fc`. **Owning register:** https://github.com/pcvantol/djconnect/issues/1101. **Portfolio:** https://github.com/pcvantol/djconnect/issues/1101.

**Current assignment/WIP:** PLANNING_WRITER_ACTIVE; LANE_5 terminal WORKSPACE_READY; local main clean before branch. Product pickup: `NOT_ISSUED`. Capacity: `UNKNOWN`.

## Selected and proposed outcome

Selected in an owning source, without a new execution assignment: `SLICE::CORE::AMBIENT-RENDERER`.

Planning continuation: Reconcileer E2E-selectie en VibeCast-selectie met de bestaande productbacklog. Rond onder deze planningsassignment de centrale graaf en beschermde documentaire oplevering af; geen nieuw productwerk.

## Owning backlog and handoffs

Read the local `REPOSITORY_STATUS.md` and existing TODO/ISSUES or release metadata that this repository actually owns. Local backlog audit: Relevant local backlog/status entries read; complete audit pending.

- `HA-DJC-APPLE`: DJC-CORE → DJC-APPLE; Profile-aware pairing, capabilities and backend-owned playback/Ask DJ subsets; preserve each host privacy and intentional absences. Phase `integration_acceptance`; exact artifact `UNKNOWN`; acceptance owner `DJC-APPLE`.
- `HA-DJC-ESP32`: DJC-CORE → DJC-ESP32; Profile-aware pairing, capabilities and backend-owned playback/Ask DJ subsets; preserve each host privacy and intentional absences. Phase `integration_acceptance`; exact artifact `UNKNOWN`; acceptance owner `DJC-ESP32`.
- `HA-DJC-PI`: DJC-CORE → DJC-PI; Profile-aware pairing, capabilities and backend-owned playback/Ask DJ subsets; preserve each host privacy and intentional absences. Phase `integration_acceptance`; exact artifact `UNKNOWN`; acceptance owner `DJC-PI`.
- `HA-DJC-WINDOWS`: DJC-CORE → DJC-WINDOWS; Profile-aware pairing, capabilities and backend-owned playback/Ask DJ subsets; preserve each host privacy and intentional absences. Phase `integration_acceptance`; exact artifact `UNKNOWN`; acceptance owner `DJC-WINDOWS`.
- `RELAY`: DJC-API → DJC-CORE; Server-side APNs relay boundary; no client provider credentials. Phase `integration_acceptance`; exact artifact `UNKNOWN`; acceptance owner `DJC-CORE`.
- `HA-CAST`: DJC-CORE → DJC-VIBECAST; Renderer-safe active Session Broadcast and lifecycle. Phase `integration_acceptance`; exact artifact `UNKNOWN`; acceptance owner `DJC-VIBECAST`.

## DoR, DoD and resource boundary

DoR for a future product pickup: selected owning scope, exact phase-specific producer receipt, authority, free writer slot and measured capacity. UNKNOWN is not FREE. No issue or prompt alone starts a writer.

DoD for a future authorized vertical assignment: contract and user-facing acceptance, applicable five-language UX, tests, independent review, required CI, fixes, protected merge, exact-main readback and owning Finalization; any release/install acceptance requires separate explicit release scope.

Workflow effect audit: Branch/PR validation is safe for planning review. Successful main validation starts two publication-capable workflows targeting the same internal-ha-{SHA} prerelease tag; after their own gates either may create that release and each may upload an asset. Docs-only merge does not suppress the triggers. The possible unauthorized release effect blocks protected merge under this assignment; no workflow or service change authorized. Shared signer, HA lab and devices are not reserved by this plan. A delegated publication requires both source and receiving distribution writer coordination.

## Copyable continuation prompt

```text
Continue assignment DJC-PLATFORM-ROADMAP-DAG-LANES-V1-20261003 in pcvantol/djconnect / DJC-CORE.
Read https://github.com/pcvantol/djconnect/issues/1101 and https://github.com/pcvantol/djconnect/issues/1101; keep the current WIP/assignment intact: PLANNING_WRITER_ACTIVE; LANE_5 terminal WORKSPACE_READY; local main clean before branch.
Use the existing owning backlog, exact source pins and local bootstrap. Planning outcome: Reconcileer E2E-selectie en VibeCast-selectie met de bestaande productbacklog. Rond onder deze planningsassignment de centrale graaf en beschermde documentaire oplevering af; geen nieuw productwerk.
Selected owning node IDs (no new pickup): SLICE::CORE::AMBIENT-RENDERER.
Local test-policy audit: NOT_FULLY_AUDITED. Workflow effects: Branch/PR validation is safe for planning review. Successful main validation starts two publication-capable workflows targeting the same internal-ha-{SHA} prerelease tag; after their own gates either may create that release and each may upload an asset. Docs-only merge does not suppress the triggers. The possible unauthorized release effect blocks protected merge under this assignment; no workflow or service change authorized.
This is documentary planning only. Do not infer product selection, writer availability, resource capacity or release authority.
For any later selected vertical work, first prove DoR, then include UX, tests, review, fixes, protected merge and finalization in the same assignment.
Coordinate these exact handoff IDs and acceptance owners through the owning registers:
- HA-DJC-APPLE: DJC-CORE -> DJC-APPLE; Profile-aware pairing, capabilities and backend-owned playback/Ask DJ subsets; preserve each host privacy and intentional absences; phase integration_acceptance; acceptance owner DJC-APPLE; exact artifact UNKNOWN.
- HA-DJC-ESP32: DJC-CORE -> DJC-ESP32; Profile-aware pairing, capabilities and backend-owned playback/Ask DJ subsets; preserve each host privacy and intentional absences; phase integration_acceptance; acceptance owner DJC-ESP32; exact artifact UNKNOWN.
- HA-DJC-PI: DJC-CORE -> DJC-PI; Profile-aware pairing, capabilities and backend-owned playback/Ask DJ subsets; preserve each host privacy and intentional absences; phase integration_acceptance; acceptance owner DJC-PI; exact artifact UNKNOWN.
- HA-DJC-WINDOWS: DJC-CORE -> DJC-WINDOWS; Profile-aware pairing, capabilities and backend-owned playback/Ask DJ subsets; preserve each host privacy and intentional absences; phase integration_acceptance; acceptance owner DJC-WINDOWS; exact artifact UNKNOWN.
- RELAY: DJC-API -> DJC-CORE; Server-side APNs relay boundary; no client provider credentials; phase integration_acceptance; acceptance owner DJC-CORE; exact artifact UNKNOWN.
- HA-CAST: DJC-CORE -> DJC-VIBECAST; Renderer-safe active Session Broadcast and lifecycle; phase integration_acceptance; acceptance owner DJC-VIBECAST; exact artifact UNKNOWN.
Do not start a release or deployment from this prompt.
Report PLANNING_DELIVERY, PRODUCT_DELIVERY and EXECUTION_READY separately. Stop after this planning delivery.
```
