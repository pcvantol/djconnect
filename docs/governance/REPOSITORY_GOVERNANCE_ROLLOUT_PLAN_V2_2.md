# DJConnect Repository Governance Rollout Plan — Version 2.2

**Status:** executable planning record
**Decision:** `DJCONNECT_REPOSITORY_GOVERNANCE_ROLLOUT_PLANNED`
**Canonical governance:** `pcvantol/djconnect`,
`docs/governance/PLATFORM_ARCHITECT_SYSTEM_INSTRUCTIONS.md`, AI-Native
Engineering Operating System **2.2**

## Basis

Central PR #126 merged as `a7e0c055b0c747e32de6e689a78cd07b407cb3a6`.
Current main therefore has matching Version 2.2 label and decision values.
The predecessor history is archived and its remote branch is absent. The
earlier blocked report remains immutable evidence of the pre-merge stop; this
document is the authoritative post-reconciliation plan.

## Active scope and release profiles

| Repository | Classification | Local release/deployment profile | Primary gap |
| --- | --- | --- | --- |
| `djconnect-app` | Active engineering | Signed macOS/iOS/watchOS artifacts; internal relay/TestFlight/App Store when approved | Partial adoption: stale merged records and incomplete 2.2 adoption contract. |
| `djconnect-windows` | Active engineering | Signed Windows package/installer, GitHub Release, later winget when approved | Missing discovered canonical local governance record set. |
| `djconnect-pi` | Active engineering | Linux package/deployment bundle, service/display validation, GitHub Release | Same governance-record gap. |
| `djconnect-esp32` | Active engineering | Firmware binaries, target metadata/checksums, OTA/GitHub Release | Same governance-record gap. |
| `djconnect-firmware` | Active distribution | Firmware manifest, checksums, release notes/assets | Same governance-record gap; no source-runtime DoD. |
| `djconnect-api` | Active engineering | Cloudflare Worker, D1 migrations, Wrangler deployment evidence | Same governance-record gap. |
| `djconnect-website` | Active engineering | Actual static/web hosting build artifact and route smoke evidence | Same governance-record gap. |
| `djconnect-app-releases` | Active distribution | Apple artifact handoff/provenance metadata | Same governance-record gap; no local signing ownership. |
| `djconnect-pi-releases` | Active distribution | Pi artifact/checksum/release-note provenance | Same governance-record gap. |

`djconnect-verification-platform` and `djconnect-releases` are `NOT_FOUND` on
GitHub; `djconnect-sha-enforcement-reproducer` is `OUT_OF_SCOPE`. They receive
no adoption PR. Docker is only a verification-runtime distribution, never a
default repository release profile.

## Apple verification

`APPLE_GOVERNANCE_ADOPTION_PARTIAL`. Apple references central governance and
has a bootstrap, rolling records, roadmap/prompt indexes and immutable history.
PR #23 is merged but local rolling records still show review pending and a
non-canonical lifecycle label. Its dedicated prompt corrects only those gaps,
adds the 2.2 declaration and defines Apple-native validation, release and
hygiene rules.

## Deterministic queue

| Order | Prompt ID | Repository | Objective | Priority | Depends on |
| --- | --- | --- | --- | --- | --- |
| 1 | `RG-APPLE-001` | `djconnect-app` | Complete focused Apple alignment | P0 | Version 2.2 plan |
| 2 | `RG-WINDOWS-001` | `djconnect-windows` | Establish local adoption | P0 | 1 merged/reconciled |
| 3 | `RG-PI-001` | `djconnect-pi` | Establish local adoption | P0 | 2 merged/reconciled |
| 4 | `RG-ESP32-001` | `djconnect-esp32` | Establish local adoption | P0 | 3 merged/reconciled |
| 5 | `RG-FIRMWARE-001` | `djconnect-firmware` | Establish distribution adoption | P0 | 4 merged/reconciled |
| 6 | `RG-API-001` | `djconnect-api` | Establish Worker/D1 adoption | P0 | 5 merged/reconciled |
| 7 | `RG-WEBSITE-001` | `djconnect-website` | Establish web adoption | P0 | 6 merged/reconciled |
| 8 | `RG-APPLE-DIST-001` | `djconnect-app-releases` | Establish artifact-handoff adoption | P1 | 7 merged/reconciled |
| 9 | `RG-PI-DIST-001` | `djconnect-pi-releases` | Establish Pi-distribution adoption | P1 | 8 merged/reconciled |
| 10 | `RG-AUDIT-001` | `djconnect` | Cross-repository governance audit | P0 | 1–9 merged/reconciled |

The order keeps the requested default intent while placing source ESP32 before
its distribution repository and placing the API after primary device/client
repositories. This reflects source-before-distribution dependency and the API's
optional relay role; it is the only deviation.

## Shared prompt contract

Every prompt below is complete only with this mandatory contract:

1. In its named repository run `git switch main` and `git pull --ff-only`; verify branch, HEAD, upstream, zero divergence and a clean tree. Stop on any failure.
2. Use GitHub and Git evidence to verify the predecessor PR, containment in main, immutable history and remote-branch cleanup; classify and reconcile `MERGED_UNRECONCILED` rolling records before substantive work.
3. Read local bootstrap/status/summary/roadmap/backlog/prompt index, then check whether the requested records already exist. Preserve valid work; do not copy central governance.
4. Add a concise adoption declaration referencing this central document and Version 2.2, named exceptions (or `none`), the reference-not-copy rule, local ownership, local Definition of Done, native validation profile, actual release/deployment profile and fail-closed hygiene.
5. Add or align `BOOTSTRAP.md`, `ENGINEERING_STATUS.md`, `REPOSITORY_STATUS.md`, `MANAGEMENT_SUMMARY.md`, `ROADMAP_INDEX.md`, `PROMPT_INDEX.md` and `docs/history/prompts/` only where reality shows they are absent or incomplete. Bootstrap must give reading order and clean-session continuation; rolling records must be factual and self-describing.
6. Model `LOCAL_IN_PROGRESS`, `REVIEWABLE_FROZEN`, `MERGED_UNRECONCILED` and `MERGED_RECONCILED`; require post-merge reconciliation without rewriting immutable history.
7. Validate references, the local profile, `git diff --check` and the repository's native documentation/configuration checks. Update rolling records and create one immutable history record. Open exactly one reviewable, mergeable PR, do not merge, and report decision, branch, SHA, PR, validation, limitations, deferred work and exactly one next prompt.

## Repository prompt specifications

| Prompt | Mission and scoped local profile | Expected decision and completion criteria |
| --- | --- | --- |
| `RG-APPLE-001` | Reconcile merged PR #23 records, declare Version 2.2, remove only stale duplicate bootstrap interpretation, and document Xcode/XCTest, signing/entitlement and macOS/iOS/watchOS release profile. | `APPLE_GOVERNANCE_ADOPTION_VERIFIED` or `..._PARTIAL`; one Apple docs-only PR; no client implementation change. |
| `RG-WINDOWS-001` | Add the local record set and .NET/Windows-native build, test, package/signing validation and GitHub Release profile. | `WINDOWS_GOVERNANCE_ADOPTION_ESTABLISHED` or `..._BLOCKED`; one docs-only PR. |
| `RG-PI-001` | Add the local record set and Python/service/display/startup validation plus Linux package/deployment profile. | `PI_GOVERNANCE_ADOPTION_ESTABLISHED` or `..._BLOCKED`; one docs-only PR. |
| `RG-ESP32-001` | Add the local record set and PlatformIO/native/board/OTA validation plus firmware-binary/checksum profile. | `ESP32_GOVERNANCE_ADOPTION_ESTABLISHED` or `..._BLOCKED`; one docs-only PR. |
| `RG-FIRMWARE-001` | Add distribution records, manifest/checksum/asset-name/release-note validation and explicitly exclude source-code/runtime claims. | `FIRMWARE_DISTRIBUTION_GOVERNANCE_ESTABLISHED` or `..._BLOCKED`; one docs-only PR. |
| `RG-API-001` | Add Worker/D1 records, npm/Vitest/lint/Wrangler and migration/route evidence profile; do not create Docker obligations. | `API_GOVERNANCE_ADOPTION_ESTABLISHED` or `..._BLOCKED`; one docs-only PR. |
| `RG-WEBSITE-001` | Add web records, package build/lint/typecheck/link/route-smoke profile and actual hosting evidence. | `WEBSITE_GOVERNANCE_ADOPTION_ESTABLISHED` or `..._BLOCKED`; one docs-only PR. |
| `RG-APPLE-DIST-001` | Add artifact-handoff records, provenance/metadata validation and the explicit boundary excluding Apple signing and source ownership. | `APPLE_DISTRIBUTION_GOVERNANCE_ESTABLISHED` or `..._BLOCKED`; one docs-only PR. |
| `RG-PI-DIST-001` | Add Pi artifact-distribution records, manifest/checksum/release-note validation and the explicit source boundary. | `PI_DISTRIBUTION_GOVERNANCE_ESTABLISHED` or `..._BLOCKED`; one docs-only PR. |
| `RG-AUDIT-001` | From synchronized central main, inspect all nine merged adoption PRs and current default branches. Verify matching Version 2.2 references, immutable history, lifecycle/reconciliation, local DoD, native release profile, documented dependencies and clean-session navigation. | `DJCONNECT_REPOSITORY_GOVERNANCE_AUDIT_PASSED` or `..._BLOCKED`; one central audit PR with no sibling modifications. |

## Final audit criteria

The audit passes only when every active repository references Version 2.2 from
the central source, has no copied central corpus, has current rolling records
and immutable history, applies the four lifecycle states and reconciliation,
uses a product-appropriate DoD and native release profile, documents
cross-repository dependencies, and can be continued without conversation
history. It must also confirm no repository treats Docker as a universal target.
