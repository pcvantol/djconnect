# DJC-DIST-APPLE — pcvantol/djconnect-app-releases

This is a pinned planning projection for assignment `DJC-PLATFORM-ROADMAP-DAG-LANES-V1-20261003`. Owning roadmap, backlog, code and qualification records remain authoritative. It grants no product pickup, release, deployment or resource lease.

**Owns:** Artifact-handoff; Apple-only README versus Windows/Mac Catalyst consumerclaim is onopgelost. Profiles: Apple unsigned handoff; Windows/Mac Catalyst scope requires reconciliation.

**Baseline main:** `02fa92f74b56fbc4223ee152d6f612559b84779d`. **Owning register:** https://github.com/pcvantol/djconnect-app-releases/issues/25. **Portfolio:** https://github.com/pcvantol/djconnect/issues/1101.

**Current assignment/WIP:** CLEAN_LOCAL_MAIN_OBSERVED; active assignment not independently verified. Product pickup: `NOT_ISSUED`. Capacity: `UNKNOWN`.

## Selected and proposed outcome

No new selected product execution is established for this lane by this planning assignment.

Planning continuation: Bepaal de daadwerkelijke huidige artifact- en publicatiegrens uit workflows/receipts. Behoud één lane voor deze repo; maak geen tweede Windows-distributiewriter.

## Owning backlog and handoffs

Read the local `REPOSITORY_STATUS.md` and existing TODO/ISSUES or release metadata that this repository actually owns. Local backlog audit: All 25 tracked paths, including all 15 Markdown paths, were inventoried at exact main; owning status/phase projections and sole planning issue retained. GitHub release and source-to-consumer reconciliation remain open..

- `APPLE-DIST`: DJC-APPLE → DJC-DIST-APPLE; iOS/macOS unsigned bundles, hashes and tags. Phase `distribution`; exact artifact `NOT_PUBLISHED_BY_THIS_ASSIGNMENT`; acceptance owner `DJC-DIST-APPLE`.
- `WIN-DIST`: DJC-WINDOWS → DJC-DIST-APPLE; Windows x64/arm64 and conditional Mac Catalyst artifacts. Phase `distribution`; exact artifact `NOT_PUBLISHED_BY_THIS_ASSIGNMENT`; acceptance owner `DJC-DIST-APPLE`.
- `DIST-APPLE-WEBSITE-DOWNLOADS`: DJC-DIST-APPLE → DJC-WEBSITE; Conditional consumer of apple and windows target-matched public release asset links where a target/channel is approved and advertised; otherwise truthful localized absence. Phase `assessment`; exact artifact `Exact release tag/asset and deployed Pages revision UNKNOWN`; acceptance owner `DJC-WEBSITE`.

## DoR, DoD and resource boundary

DoR for a future product pickup: selected owning scope, exact phase-specific producer receipt, authority, free writer slot and measured capacity. UNKNOWN is not FREE. No issue or prompt alone starts a writer.

DoD for a future authorized vertical assignment: contract and user-facing acceptance, applicable five-language UX, tests, independent review, required CI, fixes, protected merge, exact-main readback and owning Finalization; any release/install acceptance requires separate explicit release scope.

Workflow effect audit: Main push runs integrity validation and Action-run cleanup; successful main workflow_run may invoke contents-write reusable release-evidence workflow that can create/append internal-ha-{SHA} prerelease after gates and can write the main Post-Merge Release Evidence commit status. Manual release execution contract accepts dry_run only. No distribution push/merge under this planning assignment.. Shared signer, HA lab and devices are not reserved by this plan. A delegated publication requires both source and receiving distribution writer coordination.

## Copyable continuation prompt

```text
Continue assignment DJC-PLATFORM-ROADMAP-DAG-LANES-V1-20261003 in pcvantol/djconnect-app-releases / DJC-DIST-APPLE.
Read https://github.com/pcvantol/djconnect/issues/1101 and https://github.com/pcvantol/djconnect-app-releases/issues/25; keep the current WIP/assignment intact: CLEAN_LOCAL_MAIN_OBSERVED; active assignment not independently verified.
Use the existing owning backlog, exact source pins and local bootstrap. Planning outcome: Bepaal de daadwerkelijke huidige artifact- en publicatiegrens uit workflows/receipts. Behoud één lane voor deze repo; maak geen tweede Windows-distributiewriter.
Selected owning node IDs (no new pickup): none established for this lane.
Local test-policy audit: Main-only distribution-integrity check validates dry-run metadata; exact-main validation run not retained in the latest run listing; local source audit is not live/installed acceptance.. Workflow effects: Main push runs integrity validation and Action-run cleanup; successful main workflow_run may invoke contents-write reusable release-evidence workflow that can create/append internal-ha-{SHA} prerelease after gates and can write the main Post-Merge Release Evidence commit status. Manual release execution contract accepts dry_run only. No distribution push/merge under this planning assignment..
This is documentary planning only. Do not infer product selection, writer availability, resource capacity or release authority.
For any later selected vertical work, first prove DoR, then include UX, tests, review, fixes, protected merge and finalization in the same assignment.
Coordinate these exact handoff IDs and acceptance owners through the owning registers:
- APPLE-DIST: DJC-APPLE -> DJC-DIST-APPLE; iOS/macOS unsigned bundles, hashes and tags; phase distribution; acceptance owner DJC-DIST-APPLE; exact artifact NOT_PUBLISHED_BY_THIS_ASSIGNMENT.
- WIN-DIST: DJC-WINDOWS -> DJC-DIST-APPLE; Windows x64/arm64 and conditional Mac Catalyst artifacts; phase distribution; acceptance owner DJC-DIST-APPLE; exact artifact NOT_PUBLISHED_BY_THIS_ASSIGNMENT.
- DIST-APPLE-WEBSITE-DOWNLOADS: DJC-DIST-APPLE -> DJC-WEBSITE; Conditional consumer of apple and windows target-matched public release asset links where a target/channel is approved and advertised; otherwise truthful localized absence; phase assessment; acceptance owner DJC-WEBSITE; exact artifact Exact release tag/asset and deployed Pages revision UNKNOWN.
Do not start a release or deployment from this prompt.
Report PLANNING_DELIVERY, PRODUCT_DELIVERY and EXECUTION_READY separately. Stop after this planning delivery.
```
