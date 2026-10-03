# DJC-WEBSITE — pcvantol/djconnect-website

This is a pinned planning projection for assignment `DJC-PLATFORM-ROADMAP-DAG-LANES-V1-20261003`. Owning roadmap, backlog, code and qualification records remain authoritative. It grants no product pickup, release, deployment or resource lease.

**Owns:** Website, publieke documentatie, onboardingpresentatie en release-noteprojecties. Profiles: Static Cloudflare Pages.

**Baseline main:** `6eef6aa267f18239b88f8edae6201dc62494e4eb`. **Owning register:** https://github.com/pcvantol/djconnect-website/issues/59. **Portfolio:** https://github.com/pcvantol/djconnect/issues/1101.

**Current assignment/WIP:** CLEAN_LOCAL_MAIN_OBSERVED; active assignment not independently verified. Product pickup: `NOT_ISSUED`. Capacity: `UNKNOWN`.

## Selected and proposed outcome

No new selected product execution is established for this lane by this planning assignment.

Planning continuation: Reconcileer de publieke Spotify OAuth-callbacktekst: core gebruikt /api/djconnect/v1/spotify/callback, terwijl gepinde websitecopy en tien gerichte HTML-regellezingen /v1 missen; corrigeer MacCatalyst-titel/platform, iOS-distributiekanaal en verouderde automatische-deploybeschrijving onder de owning writer. Verifieer producer/consumer- en live-sitebewijs; geen website push of deploy onder deze planning

## Owning backlog and handoffs

Read the local `REPOSITORY_STATUS.md` and existing TODO/ISSUES or release metadata that this repository actually owns. Local backlog audit: Owning backlog, four phase/status projections and all non-release-note Markdown are pinned. All 348 remaining Markdown paths are classified by exact path/blob as pre-3.3.0 release copy; those contents were not fully read. Static HTML source, runtime and live-site consumers remain separate audit frontiers.

- `WIN-SITE`: DJC-WINDOWS → DJC-WEBSITE; Windows and Mac Catalyst release notes. Phase `distribution`; exact artifact `NOT_PUBLISHED_BY_THIS_ASSIGNMENT`; acceptance owner `DJC-WEBSITE`.
- `APPLE-SITE`: DJC-APPLE → DJC-WEBSITE; Versioned and latest Apple release notes from the same Apple publication workflow. Phase `distribution`; exact artifact `NOT_PUBLISHED_BY_THIS_ASSIGNMENT`; acceptance owner `DJC-WEBSITE`.
- `API-WEBSITE-OPERATOR`: DJC-API → DJC-WEBSITE; Operator-only registration summaries and install-token revocation through Pages server-side proxy. Phase `integration_acceptance`; exact artifact `Authenticated JSON endpoint contract at pinned source revisions; exact deployed artifact binding UNKNOWN`; acceptance owner `DJC-WEBSITE`.
- `DIST-APPLE-WEBSITE-DOWNLOADS`: DJC-DIST-APPLE → DJC-WEBSITE; Conditional consumer of apple and windows target-matched public release asset links where a target/channel is approved and advertised; otherwise truthful localized absence. Phase `assessment`; exact artifact `Exact release tag/asset and deployed Pages revision UNKNOWN`; acceptance owner `DJC-WEBSITE`.
- `DIST-FIRMWARE-WEBSITE-DOWNLOADS`: DJC-DIST-FIRMWARE → DJC-WEBSITE; Conditional consumer of firmware board/channel release asset and manifest links where a target/channel is approved and advertised; otherwise truthful localized absence. Phase `assessment`; exact artifact `Exact release tag/asset and deployed Pages revision UNKNOWN`; acceptance owner `DJC-WEBSITE`.
- `DIST-PI-WEBSITE-DOWNLOADS`: DJC-DIST-PI → DJC-WEBSITE; Conditional consumer of pi bundle and stable install redirect links where a target/channel is approved and advertised; otherwise truthful localized absence. Phase `assessment`; exact artifact `Exact release tag/asset and deployed Pages revision UNKNOWN`; acceptance owner `DJC-WEBSITE`.

## DoR, DoD and resource boundary

DoR for a future product pickup: selected owning scope, exact phase-specific producer receipt, authority, free writer slot and measured capacity. UNKNOWN is not FREE. No issue or prompt alone starts a writer.

DoD for a future authorized vertical assignment: contract and user-facing acceptance, applicable five-language UX, tests, independent review, required CI, fixes, protected merge, exact-main readback and owning Finalization; any release/install acceptance requires separate explicit release scope.

Workflow effect audit: Successful Validate on website main can start automatic Actions artifact build plus a separate post-merge evidence workflow capable, after its gates, of GitHub prerelease asset/status writes. Cloudflare deploy and post-deployment smoke are workflow_dispatch-only. No website push or dispatch occurred. Shared signer, HA lab and devices are not reserved by this plan. A delegated publication requires both source and receiving distribution writer coordination.

## Copyable continuation prompt

```text
Continue assignment DJC-PLATFORM-ROADMAP-DAG-LANES-V1-20261003 in pcvantol/djconnect-website / DJC-WEBSITE.
Read https://github.com/pcvantol/djconnect/issues/1101 and https://github.com/pcvantol/djconnect-website/issues/59; keep the current WIP/assignment intact: CLEAN_LOCAL_MAIN_OBSERVED; active assignment not independently verified.
Use the existing owning backlog, exact source pins and local bootstrap. Planning outcome: Reconcileer de publieke Spotify OAuth-callbacktekst: core gebruikt /api/djconnect/v1/spotify/callback, terwijl gepinde websitecopy en tien gerichte HTML-regellezingen /v1 missen; corrigeer MacCatalyst-titel/platform, iOS-distributiekanaal en verouderde automatische-deploybeschrijving onder de owning writer. Verifieer producer/consumer- en live-sitebewijs; geen website push of deploy onder deze planning
Selected owning node IDs (no new pickup): none established for this lane.
Local test-policy audit: Pinned TESTS.md is fully read but contains older auto-deploy assumptions. Current website validation, artifact, evidence and dispatch-only deployment workflows are separately pinned; no live-site or installed consumer receipt is qualified. Workflow effects: Successful Validate on website main can start automatic Actions artifact build plus a separate post-merge evidence workflow capable, after its gates, of GitHub prerelease asset/status writes. Cloudflare deploy and post-deployment smoke are workflow_dispatch-only. No website push or dispatch occurred.
This is documentary planning only. Do not infer product selection, writer availability, resource capacity or release authority.
For any later selected vertical work, first prove DoR, then include UX, tests, review, fixes, protected merge and finalization in the same assignment.
Coordinate these exact handoff IDs and acceptance owners through the owning registers:
- WIN-SITE: DJC-WINDOWS -> DJC-WEBSITE; Windows and Mac Catalyst release notes; phase distribution; acceptance owner DJC-WEBSITE; exact artifact NOT_PUBLISHED_BY_THIS_ASSIGNMENT.
- APPLE-SITE: DJC-APPLE -> DJC-WEBSITE; Versioned and latest Apple release notes from the same Apple publication workflow; phase distribution; acceptance owner DJC-WEBSITE; exact artifact NOT_PUBLISHED_BY_THIS_ASSIGNMENT.
- API-WEBSITE-OPERATOR: DJC-API -> DJC-WEBSITE; Operator-only registration summaries and install-token revocation through Pages server-side proxy; phase integration_acceptance; acceptance owner DJC-WEBSITE; exact artifact Authenticated JSON endpoint contract at pinned source revisions; exact deployed artifact binding UNKNOWN.
- DIST-APPLE-WEBSITE-DOWNLOADS: DJC-DIST-APPLE -> DJC-WEBSITE; Conditional consumer of apple and windows target-matched public release asset links where a target/channel is approved and advertised; otherwise truthful localized absence; phase assessment; acceptance owner DJC-WEBSITE; exact artifact Exact release tag/asset and deployed Pages revision UNKNOWN.
- DIST-FIRMWARE-WEBSITE-DOWNLOADS: DJC-DIST-FIRMWARE -> DJC-WEBSITE; Conditional consumer of firmware board/channel release asset and manifest links where a target/channel is approved and advertised; otherwise truthful localized absence; phase assessment; acceptance owner DJC-WEBSITE; exact artifact Exact release tag/asset and deployed Pages revision UNKNOWN.
- DIST-PI-WEBSITE-DOWNLOADS: DJC-DIST-PI -> DJC-WEBSITE; Conditional consumer of pi bundle and stable install redirect links where a target/channel is approved and advertised; otherwise truthful localized absence; phase assessment; acceptance owner DJC-WEBSITE; exact artifact Exact release tag/asset and deployed Pages revision UNKNOWN.
Do not start a release or deployment from this prompt.
Report PLANNING_DELIVERY, PRODUCT_DELIVERY and EXECUTION_READY separately. Stop after this planning delivery.
```
