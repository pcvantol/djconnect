# DJConnect federated delivery planning v1

This is a pinned planning projection for assignment `DJC-PLATFORM-ROADMAP-DAG-LANES-V1-20261003`. Owning roadmap, backlog, code and qualification records remain authoritative. It grants no product pickup, release, deployment or resource lease.

Portfolio: https://github.com/pcvantol/djconnect/issues/1101. Pinned on 2026-10-03T08:28:23+00:00.

## Delivery state

| Boundary | State |
|---|---|
| `PLANNING_DELIVERY` | `IN_PROGRESS / PROTECTED_DELIVERY_NOT_YET_DONE` |
| `PRODUCT_DELIVERY` | `UNCHANGED_BY_PLANNING` |
| `EXECUTION_READY` | `NO_NEW_PRODUCT_PICKUP_AUTHORIZED` |

The snapshot has 12 repository lanes, 205 pinned sources, 205 records and 82 typed relations. Records are not a feature count. 5 of 27 audit/delivery obligations are closed.

## Current five-item Execution Horizon

This distribution order is retained from the current management/engineering records. Each item remains subject to its own evidence and explicit authorization.

| Order | Planned item | Owning node | Direct condition |
|---:|---|---|---|
| 1 | Public distribution: Apple | `PROJ::EVOLUTION::APPLE-PUBLIC` | PLANNED; explicit release authorization and qualified Internal Release consumers required |
| 2 | Public distribution: Windows | `PROJ::EVOLUTION::WINDOWS-PUBLIC` | PLANNED; qualified Internal Release consumers and explicit authorization required |
| 3 | Public HACS distribution | `PROJ::EVOLUTION::HACS-PUBLIC` | PLANNED; fresh candidate and release authorization required |
| 4 | HACS 3.3.0 release visibility | `HACS-3.3.0-001` | PLANNED investigation of tag/cache/index/update presentation |
| 5 | Firmware OTA publication and staged rollback | `PROJ::EVOLUTION::FW-OTA` | PLANNED; manifest-bound consumer qualification required |

## Product sequence and parallel work

DJ Intelligence Evolution → Reference Experience → Apple Premium Experience → Public Release Readiness → Productization → Product & Community Readiness → Community Public Release. The dotted milestone arrows show product priority. Independent contract, source and test preparation may proceed; an integrated consumer claim waits for its exact predecessor evidence.

The selected VibeCast reference increment still needs the Apple-owner to physical portrait-Pi active-Session receipt. The Cast receiver is a later feasibility step. The original selected E2E verification path is recorded complete in the candidate owning roadmap and backlog; optional additions remain deferred.

## Current admission

Host verification: `./scripts/runner/bootstrap_djconnect_macos_host.sh --verify` exited `0` with `MATCH / READY FOR DJCONNECT DEVELOPMENT` and onboarding `4.5.3`. This does not grant future product pickup. Current local Apple and Windows WIP is outside this planning writer.

## Findings

- **DRIFT-E2E (CANDIDATE_CANONICAL_STATUS_RECONCILED):** Candidate Product Roadmap, Product Backlog and owning E2E Roadmap now say the six original Golden Scenarios and enabling verification path are complete. Optional Presentation scenarios, TTS replay and comparison remain deferred and require separate selection. No Smoke/CI rebuild or new gate is selected. Sources: `PRODUCT_BACKLOG`, `E2E_ROADMAP`, `GOLDEN_CI`.
- **DRIFT-VIBECAST (CANDIDATE_BACKLOG_RECONCILED; PI_ACCEPTANCE_OPEN):** Candidate PRODUCT_BACKLOG now lists the existing selected VibeCast reference increment. Ambient renderer basis exists; exact Apple-owner to physical portrait-Pi active-Session, reconnect, end cleanup and privacy acceptance remain open. Standalone Cast receiver is a later assessment. Sources: `PRODUCT_ROADMAP`, `PRODUCT_BACKLOG`, `VIBECAST_INCREMENT`, `README::DJC-VIBECAST`.
- **DRIFT-DIST (OPEN):** app-releases Apple-only internal-handoff README conflicts with Windows consumer distribution claims. No silent route redesign. Sources: `README::DJC-WINDOWS`, `README::DJC-DIST-APPLE`.
- **DRIFT-PI (OPEN):** Pi source intentional no voice/local input versus distribution copy; profile bundles versus older component qualification identity. Sources: `README::DJC-PI`, `README::DJC-DIST-PI`, `QUALIFICATION`.
- **DEDUP-CMB (RECORDED_NOT_CANONICALLY_CHANGED):** CMB12 repeated active projection is one CMB07 question; retain six unique follow-up qualifications; CMB09 no open follow-up. Sources: `QUALIFICATION`, `CMB`.
- **SHARING-BOUNDED (RECORDED_NOT_REQUALIFIED):** CMB11 includes completed Track Insight→Apple Native Sharing only; not generic sharing implementation. Sources: `CMB`, `E2E_ROADMAP`.
- **HISTORY (OPEN):** Historical old release checklists, iCloud migration and TD-GITHUB detail must not recreate active work. Sources: `PRODUCT_ROADMAP`, `EVOLUTION`, `ROADMAP_INDEX`.
- **RETIREMENT-DELTA (CLOSED_BY_OWNING_TERMINAL_EVIDENCE):** Issue #1098 closed with terminal WORKSPACE_READY and MERGED_RECONCILED; this planning assignment does not reopen it. Sources: `EVOLUTION`, `RETIREMENT_DELTA`.
- **PUBLIC-COPY (OPEN):** Website README retains 3.2-era versions and older presentation claims; compare current producer contracts/artifacts before public changes. Sources: `README::DJC-WEBSITE`.
- **INTELLIGENCE-GAPS (ASSESSMENT_ONLY):** Dated review names missing inputs/knowledge/lyrics/timing and audience projection drift, not new product selection. Sources: `INTELLIGENCE_REVIEW`.
- **HORIZON-5 (READ_FROM_CURRENT_RECORDS):** The five planned distribution items are captured verbatim by topic and order; each still requires its own evidence and authorization. Sources: `EVOLUTION`, `MANAGEMENT_SUMMARY`, `ENGINEERING_STATUS`.
- **CURRENT-WIP (OBSERVED_LOCAL_ONLY):** Apple and Windows checkouts contain unrelated WIP. This planning writer does not mutate their source worktrees or infer free capacity. Sources: `STATUS::DJC-APPLE`, `STATUS::DJC-WINDOWS`.
- **CORE-MAIN-ARTIFACT (PROTECTED_MERGE_BLOCKED_BY_NO_RELEASE_SCOPE):** Successful core main validation unconditionally creates two GitHub prerelease objects: the internal HA artifact and durable qualification evidence. The current assignment prohibits releases and service/workflow changes. Branch/PR checks are safe from these main-only triggers; protected merge requires a separately authorized safe route or owner resolution. Sources: `CORE-INTERNAL-ARTIFACT`, `POST_MERGE`.
- **LOCAL-BACKLOG-DISPOSITION (MAPPED_NOT_SELECTED):** Open local API, Apple, ESP32, Pi, Windows and website concerns remain with their owning backlogs; completed local records were not reissued as product work. Sources: `ISSUES::DJC-API`, `ISSUES::DJC-APPLE`, `TODO::DJC-ESP32`, `ISSUES::DJC-PI`, `ISSUES::DJC-WINDOWS`, `ISSUES::DJC-WEBSITE`.
- **NORMATIVE-SOURCE-LINK-GAPS (LINK_FRONTIER_TRIAGED; BROADER_SOURCE_AUDIT_OPEN):** Independent reviews exposed missing linked Runtime/Presentation and verification authorities. Twenty-six directly relevant linked sources plus nine core repository/status files were added and pinned to existing nodes beyond the previous 170; six of the nine core files were fully read, while HANDOFF, CHANGELOG and TECHNICAL_DESIGN_DECISIONS historical/detail ranges remain partial. The reproducible pinned-blob Markdown-link scan now finds 32 remaining existing relative .md targets; each has an explicit navigation, historical, non-selection or audit-open disposition. Broader repository source audit remains open, and link existence alone creates no dependency or product selection. Sources: `FOUNDATION_INDEX`, `SESSION_RUNTIME_CONTRACTS`, `DJ_PRESENTATION_ARCH`, `AGENTS::DJC-CORE`, `README::DJC-CORE`, `MANIFEST::DJC-CORE`, `CONST::DJC-CORE`, `HANDOFF::DJC-CORE`, `CHANGELOG::DJC-CORE`, `ISSUES::DJC-CORE`, `TECH_DESIGN::DJC-CORE`, `SECURITY::DJC-CORE`.
- **LOCALIZATION-DELIVERY-ORDER (FUTURE_ARCHITECTURE_ONLY):** Narrative Architecture orders future governance/typed outcome, native renderer resources, DJMoment history and Narrative Realization, Ask DJ/voice resolution, then Lyrics-safe renderer adoption and five-language qualification. Apple, Windows and Pi own native rendering; other distribution surfaces follow the five-language validation standard. No catalog, API or renderer work is selected here. Sources: `LOCALIZATION_NARRATIVE`, `LOCALIZATION_VALIDATION_SPEC`.
- **CORE-VERSION-LINE-RECONCILIATION (RELEASED_3_3_1__SOURCE_CANDIDATE_4_0_0_RC1__LEGACY_SYNC_3_2_X):** At the pinned core head, AGENTS and HANDOFF Current State call 3.3.1 the current released integration; manifest.json and const.py identify the checked-out source as 4.0.0-rc.1, and the Changelog top describes a coordinated 4.0 release-candidate train. SYNC_PROMPTS Current Protocol Line, HANDOFF later historical Release Notes, and TECHNICAL_DESIGN_DECISIONS current-implementation scope still say 3.2.x/v3.2.50. Treat those 3.2 current-wording passages as stale coordination/design text, not a release or compatibility decision. Public release/field state is not inferred from source version strings; owning release verification and a separate authorized documentation correction remain open. Sources: `AGENTS::DJC-CORE`, `HANDOFF::DJC-CORE`, `MANIFEST::DJC-CORE`, `CONST::DJC-CORE`, `CHANGELOG::DJC-CORE`, `SYNC_PROMPTS`, `TECH_DESIGN::DJC-CORE`.

## Files and checks

[SOURCES.md](SOURCES.md) is the source-to-node completeness matrix. [CATALOGUE.md](CATALOGUE.md) preserves existing IDs and dispositions. [DEPENDENCIES.md](DEPENDENCIES.md), [HANDOFFS.md](HANDOFFS.md) and [LANES.md](LANES.md) are generated from the same JSON. [OPEN_WORK.md](OPEN_WORK.md) lists exact unclosed obligations.

```sh
python3 validate_snapshot.py djconnect-platform-v1.json --check-rendered
python3 -m unittest -v test_snapshot
python3 validate_snapshot.py djconnect-platform-v1.json --require-complete
```

The offline validator checks internal consistency, not whether a remote source or receipt is true. Freshness is a separate read-only head check. A complete-delivery result requires closed source, review, protected merge and Finalization evidence.
