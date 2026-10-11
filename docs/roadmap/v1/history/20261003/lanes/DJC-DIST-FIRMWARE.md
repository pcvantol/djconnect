# DJC-DIST-FIRMWARE — pcvantol/djconnect-firmware

This is a pinned planning projection for assignment `DJC-PLATFORM-ROADMAP-DAG-LANES-V1-20261003`. Owning roadmap, backlog, code and qualification records remain authoritative. It grants no product pickup, deployment or resource lease; the narrowly authorized planning publication side effect is recorded in the audit.

**Owns:** Firmwaremanifest en updateartifacts; geen bronimplementatie. Profiles: LilyGO firmware binaries / SHA-256 / metadata.

**Baseline main:** `cb9cc7ba321ca57675223dfac32f5583fbcb3656`. **Owning register:** https://github.com/pcvantol/djconnect-firmware/issues/24. **Portfolio:** https://github.com/pcvantol/djconnect/issues/1101.

**Current assignment/WIP:** CLEAN_LOCAL_MAIN_OBSERVED; active assignment not independently verified. Product pickup: `NOT_ISSUED`. Capacity: `UNKNOWN`.

## Selected and proposed outcome

No new selected product execution is established for this lane by this planning assignment.

Planning continuation: Behoud de gedelegeerde firmwarebron-publicatie, compatibiliteitsmetadata en HA-consumergrens als afzonderlijke bewijsstappen; website-copy is conditioneel op een goedgekeurde asset. Geen publicatie onder deze planning.

## Owning backlog and handoffs

Read the local `REPOSITORY_STATUS.md` and existing TODO/ISSUES or release metadata that this repository actually owns. Local backlog audit: All 37 tracked paths, including all 15 Markdown paths, were inventoried at exact main; owning status/phase projections and sole planning issue retained. GitHub release and source-to-consumer reconciliation remain open beyond the CLOSED documentary source inventory..

- `FW-DIST`: DJC-ESP32 → DJC-DIST-FIRMWARE; Source-generated firmware manifest, exact board asset and SHA-256. Phase `distribution`; exact artifact `UNKNOWN`; acceptance owner `DJC-DIST-FIRMWARE`.
- `DIST-FIRMWARE-WEBSITE-DOWNLOADS`: DJC-DIST-FIRMWARE → DJC-WEBSITE; Conditional consumer of firmware board/channel release asset and manifest links where a target/channel is approved and advertised; otherwise truthful localized absence. Phase `assessment`; exact artifact `Exact release tag/asset and deployed Pages revision UNKNOWN`; acceptance owner `DJC-WEBSITE`.
- `DIST-FIRMWARE-CORE-OTA-CONTRACT`: DJC-DIST-FIRMWARE → DJC-CORE; Board/version/channel firmware manifest consumed by HA OTA offer. Phase `integration_acceptance`; exact artifact `UNKNOWN; exact candidate, manifest or consumer receipt depends on the named subset`; acceptance owner `DJC-CORE`.
- `DIST-FIRMWARE-CORE-OTA-QUAL`: DJC-DIST-FIRMWARE → DJC-CORE; Exact manifest/checksum/channel/rollback evidence for core OTA consumer qualification. Phase `qualification`; exact artifact `UNKNOWN; exact candidate, manifest or consumer receipt depends on the named subset`; acceptance owner `DJC-CORE`.

## DoR, DoD and resource boundary

DoR for a future product pickup: selected owning scope, exact phase-specific producer receipt, authority, free writer slot and measured capacity. UNKNOWN is not FREE. No issue or prompt alone starts a writer.

DoD for a future authorized vertical assignment: contract and user-facing acceptance, applicable five-language UX, tests, independent review, required CI, fixes, protected merge, exact-main readback and owning Finalization; any release/install acceptance requires separate explicit release scope.

Workflow effect audit: Main push runs integrity validation and Action-run cleanup; successful main workflow_run may invoke contents-write reusable release-evidence workflow that can create/append internal-ha-{SHA} prerelease after gates and can write the main Post-Merge Release Evidence commit status. Manual release execution contract accepts dry_run only. No distribution push/merge under this planning assignment.. Shared signer, HA lab and devices are not reserved by this plan. A delegated publication requires both source and receiving distribution writer coordination.

## Copyable continuation prompt

```text
Continue assignment DJC-PLATFORM-ROADMAP-DAG-LANES-V1-20261003 in pcvantol/djconnect-firmware / DJC-DIST-FIRMWARE.
Read https://github.com/pcvantol/djconnect/issues/1101 and https://github.com/pcvantol/djconnect-firmware/issues/24; keep the current WIP/assignment intact: CLEAN_LOCAL_MAIN_OBSERVED; active assignment not independently verified.
Use the existing owning backlog, exact source pins and local bootstrap. Planning outcome: Behoud de gedelegeerde firmwarebron-publicatie, compatibiliteitsmetadata en HA-consumergrens als afzonderlijke bewijsstappen; website-copy is conditioneel op een goedgekeurde asset. Geen publicatie onder deze planning.
Selected owning node IDs (no new pickup): none established for this lane.
Local test-policy audit: Main-only distribution-integrity check validates dry-run metadata and local manifest/binary sidecar hashes; exact-main validation run not retained in the latest run listing; local source audit is not live/installed acceptance.. Workflow effects: Main push runs integrity validation and Action-run cleanup; successful main workflow_run may invoke contents-write reusable release-evidence workflow that can create/append internal-ha-{SHA} prerelease after gates and can write the main Post-Merge Release Evidence commit status. Manual release execution contract accepts dry_run only. No distribution push/merge under this planning assignment..
This is documentary planning only. Do not infer product selection, writer availability, resource capacity or release authority.
For any later selected vertical work, first prove DoR, then include UX, tests, review, fixes, protected merge and finalization in the same assignment.
Coordinate these exact handoff IDs and acceptance owners through the owning registers:
- FW-DIST: DJC-ESP32 -> DJC-DIST-FIRMWARE; Source-generated firmware manifest, exact board asset and SHA-256; phase distribution; acceptance owner DJC-DIST-FIRMWARE; exact artifact UNKNOWN.
- DIST-FIRMWARE-WEBSITE-DOWNLOADS: DJC-DIST-FIRMWARE -> DJC-WEBSITE; Conditional consumer of firmware board/channel release asset and manifest links where a target/channel is approved and advertised; otherwise truthful localized absence; phase assessment; acceptance owner DJC-WEBSITE; exact artifact Exact release tag/asset and deployed Pages revision UNKNOWN.
- DIST-FIRMWARE-CORE-OTA-CONTRACT: DJC-DIST-FIRMWARE -> DJC-CORE; Board/version/channel firmware manifest consumed by HA OTA offer; phase integration_acceptance; acceptance owner DJC-CORE; exact artifact UNKNOWN; exact candidate, manifest or consumer receipt depends on the named subset.
- DIST-FIRMWARE-CORE-OTA-QUAL: DJC-DIST-FIRMWARE -> DJC-CORE; Exact manifest/checksum/channel/rollback evidence for core OTA consumer qualification; phase qualification; acceptance owner DJC-CORE; exact artifact UNKNOWN; exact candidate, manifest or consumer receipt depends on the named subset.
Do not start a release or deployment from this prompt.
Report PLANNING_DELIVERY, PRODUCT_DELIVERY and EXECUTION_READY separately. Stop after this planning delivery.
```
