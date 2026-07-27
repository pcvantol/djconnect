# Platform Dependency Governance Conformance Report

**Status:** implementation complete; successor exact-main evidence pending finalization
**Scope:** GitHub-native Dependabot configuration and existing platform
governance only.

## Canonical contract

All active repositories receive a repository-local weekly grouped Dependabot
configuration for GitHub Actions. Source ecosystems are configured only where
tracked manifests establish their use: pip/Docker (Home Assistant), npm (API
and website), Swift (Apple), pip (Pi) and NuGet (Windows). Release-only and
PlatformIO repositories receive GitHub Actions updates only.

| Repository | Native ecosystems | GitHub Actions | Native exception |
| --- | --- | --- | --- |
| djconnect | pip, Docker | yes | none |
| djconnect-api | npm | yes | none |
| djconnect-app | Swift | yes | none |
| djconnect-app-releases | none | yes | release-only |
| djconnect-esp32 | none | yes | PlatformIO has no existing Dependabot adapter |
| djconnect-firmware | none | yes | release-only |
| djconnect-pi | pip | yes | none |
| djconnect-pi-releases | none | yes | release-only |
| djconnect-website | npm | yes | none |
| djconnect-windows | NuGet | yes | none |

Dependency Graph and Dependabot Security Updates were API-verified enabled in
every repository. Main protection is uniform: Trusted Delivery is the required
check and each repository has one ruleset. Cleanup/evidence governance is
unchanged.

The ten configuration PRs are merged: central PR #564; API #57; Apple #62;
Apple releases #18; ESP32 #37; firmware #17; Pi #61; Pi releases #17; website
#39; and Windows #49. Their merged configuration is revalidated by this
successor finalization because the historical central PR workflow run was
removed by cleanup before its high-risk Owner Authorization could be read back.
This is recorded as evidence-retention follow-up, not treated as qualified
historical PR evidence.

The report does not claim a new Dependency Review or vulnerability analyzer:
those remain bounded by existing repository assurance. TDE remains Deferred.
