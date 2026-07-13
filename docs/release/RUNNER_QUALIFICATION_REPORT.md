# Self-Hosted Runner Qualification Report

Date: 2026-07-13
Decision: `RUNNER_INFRASTRUCTURE_PARTIALLY_QUALIFIED`

## Evidence collected

The repository-scoped GitHub Actions runner endpoints were queried after
registration. Each required runner is online and repository-scoped; no
organization-scoped runner is used. Apple and firmware also passed an isolated
GitHub Actions qualification workflow that checked out the exact branch SHA
and uploaded a redacted evidence artifact.

| Role | Repository | Runner | Online labels | Service / isolation |
| --- | --- | --- | --- | --- |
| Apple | `djconnect-app` | `djconnect-apple-macos` | `self-hosted`, `macOS`, `ARM64`, `internal-release`, `qualification`, `apple`, `ios`, `watchos` | macOS LaunchAgent; dedicated runner workspace |
| Firmware | `djconnect-esp32` | `djconnect-esp32-firmware` | `self-hosted`, `macOS`, `ARM64`, `internal-release`, `qualification`, `firmware`, `esp32` | macOS LaunchAgent; dedicated runner workspace |
| Windows | `djconnect-windows` | `djconnect-windows11-parallels` | `self-hosted`, `Windows`, `X64`, `internal-release`, `qualification`, `windows11`, `parallels` | Windows service with delayed automatic startup |
| Pi | `djconnect-pi` | `djconnect-pi-native` | `self-hosted`, `Linux`, `ARM64`, `internal-release`, `qualification`, `raspberry-pi` | native Pi user service; persistence across reboot remains to be formalized |
| Home Assistant | `djconnect` | `djconnect-home-assistant-linux` | `self-hosted`, `Linux`, `ARM64`, `internal-release`, `qualification`, `home-assistant` | isolated non-root Docker container with named runner volume |
| API deployment | `djconnect-api` | `djconnect-api-deployment` | `self-hosted`, `Linux`, `ARM64`, `internal-release`, `qualification`, `production`, `deployment` | isolated non-root Docker container with named runner volume |
| Website deployment | `djconnect-website` | `djconnect-website-deployment` | `self-hosted`, `Linux`, `ARM64`, `internal-release`, `qualification`, `production`, `deployment` | isolated non-root Docker container with named runner volume |

## Qualification matrix

| Required role | Online | Trusted scope | Labels | Toolchain | Workspace / cleanup | Evidence upload | Result |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Apple | Yes | Repository-scoped | Yes | Xcode 26.6; Swift 6.3.3 | Dedicated workspace; LaunchAgent | Passed | Qualified for runner dispatch |
| Windows | Yes | Repository-scoped | Yes | Basic probe only | Windows service | Pending | Not yet qualified |
| Firmware | Yes | Repository-scoped | Yes | PlatformIO executable; Python 3.11.7 | Dedicated workspace; LaunchAgent | Passed | Qualified for runner dispatch |
| Pi | Yes | Repository-scoped | Yes | Python 3.13.5; Git 2.47.3; runner 2.335.1 | Native Pi user service | Pending | Not yet qualified |
| Home Assistant | Yes | Repository-scoped | Yes | Container base inspected | Isolated non-root container | Pending | Not yet qualified |
| Deployment | Yes | Repository-scoped | Yes | Container base inspected | Isolated non-root containers | Pending | Not yet qualified |

## Passed evidence

- Apple: [run 29242259264](https://github.com/pcvantol/djconnect-app/actions/runs/29242259264)
  ran on `djconnect-apple-macos`, completed successfully and uploaded
  `runner-evidence-apple`. The artifact records exact SHA
  `28b303d44b5889be89dd85cbac70bd1112ab9637`, macOS/ARM64, Xcode 26.6 and
  Swift 6.3.3.
- Firmware: [run 29242426970](https://github.com/pcvantol/djconnect-esp32/actions/runs/29242426970)
  ran on `djconnect-esp32-firmware`, completed successfully and uploaded
  `runner-evidence-firmware`. The artifact records exact SHA
  `3cfde557060b46f2f0817b4938585e6e3e937e42`, macOS/ARM64, the PlatformIO
  executable and Python 3.11.7.

## Blocking qualification findings

1. The migrated ordinary Apple and firmware CI workflows both terminated before
   any job was planned: [Apple run 29242200425](https://github.com/pcvantol/djconnect-app/actions/runs/29242200425)
   and [firmware run 29242200461](https://github.com/pcvantol/djconnect-esp32/actions/runs/29242200461)
   returned `startup_failure` with no jobs or logs. Existing CI runs show the
   same no-job failure pattern. The isolated probes prove this is not a runner
   registration, label-selection or artifact-upload failure. It must be
   resolved without bypassing Software Assurance governance.
2. Windows, Pi, Home Assistant, API and website still require their own
   workflow evidence, including cleanup and artifact-upload checks. Pi runner
   persistence must be formalized before it can qualify as an operational
   restart-safe runner.

## Required qualification evidence

Each runner must produce a redacted evidence artifact containing its identity,
GitHub labels, runner version, operating-system and toolchain versions,
workspace-cleanup result, cache policy, artifact-upload probe and the exact
workflow SHA. For build roles it must also prove the platform compiler/SDK and
one representative build. Deployment runners additionally prove restricted
credential access without exposing credential values.

The partial result is not a waiver: `INTERNAL_RELEASE` remains blocked until
every required role passes, all migrated workflows can plan and complete, and
their evidence is present for the candidate SHA.
