# Platform Dependency Governance Conformance Assessment

**Status:** Assessment complete  
**Decision:** `NO_GO_PLATFORM_DEPENDENCY_GOVERNANCE_DIVERGENCE`  
**Scope:** Existing repository, GitHub and platform evidence only. No
configuration, workflow, CI, branch-protection or product change.

## Reconciliation

The active Platform Release inventory contains `djconnect`, `djconnect-api`,
`djconnect-app`, `djconnect-app-releases`, `djconnect-esp32`,
`djconnect-firmware`, `djconnect-pi`, `djconnect-pi-releases`,
`djconnect-website` and `djconnect-windows`. Each was synchronized on clean
`main == origin/main` before inspection.

## GitHub-native inventory

GitHub Dependency Graph is enabled in all ten repositories (the repository
vulnerability-alert endpoint returned its enabled `204` state). Dependabot
Security Updates are enabled in the GitHub repository settings for all ten.
The authenticated API token did not have Dependabot-alert-list access; alert
counts are therefore not inferred.

No active repository contains `.github/dependabot.yml`. Consequently there is
no repository-owned evidence of version-update ecosystems, GitHub Actions
updates, cadence, grouping, lockfile policy or automerge policy.

| Repository class | Used-evidence examples | Repository-local version-update policy |
| --- | --- | --- |
| Home Assistant / Python | `djconnect` development requirements and verification container requirements | Absent |
| npm | API and website `package.json` / lockfile | Absent |
| SwiftPM | Apple `Package.swift` | Absent |
| PlatformIO | ESP32 `platformio.ini` | Absent |
| NuGet | Windows project files | Absent |
| Distribution | Apple, firmware and Pi release repositories | Absent; no source dependency ecosystem evidenced |

## Existing quality chain

Software Assurance and Trusted Delivery are platform-wide qualified controls.
The current central HACS route includes dependency audit as one bounded input.
The source repositories retain ecosystem-specific build/test evidence where
their projects require it. This is not an equivalent platform-wide dependency
assurance contract: Dependency Review, ecosystem-native vulnerability audit,
development/transitive dependency treatment, lockfile enforcement and
required-status-check evidence are not uniformly present in repository source.

`PLATFORM_EVOLUTION_BACKLOG.md` records Technical Debt Engine Dependency Health
as **Deferred** pending a released standalone CLI, stable schema, trusted
distribution and Software Assurance compatibility. TDE is therefore not an
active platform control. When integrated, its recorded role is observational
per-repository health evidence; it cannot replace Dependabot, Dependency
Review or ecosystem-native vulnerability scanning.

## Contract and settings boundary

Dependency Graph, Dependabot Alerts and Dependabot Security Updates are
GitHub-platform settings. Repository-owned evidence is required separately for
version-update configuration and CI quality-chain behavior. Branch-protection
and required-check configurations remain outside this assessment's scope; the
existing Trusted Delivery readiness record already identifies their historical
platform inconsistency and this assessment makes no settings claim beyond the
observed repository/workflow evidence.

## Result and remaining qualification items

The platform does not currently demonstrate one uniform public-distribution
dependency-governance contract. The following objective gaps remain:

1. all ten repositories lack repository-local Dependabot version-update policy;
2. ecosystem coverage, cadence, grouping, lockfile and GitHub Actions update
   policy are consequently unproven;
3. Dependency Review and ecosystem-native vulnerability-assurance coverage are
   not uniformly evidenced; and
4. TDE Dependency Health is deferred, so it cannot supply the intended
   platform-wide assessment layer.

There is insufficient current evidence to establish a canonical Platform
Dependency Governance Policy. This assessment proposes no implementation.
