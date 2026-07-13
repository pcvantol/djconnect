# Self-Hosted Runner Architecture

Status: `MIGRATION_IN_PROGRESS`
Scope: DJConnect Platform Release Engineering Generation 1

## Decision

Codex is the Platform Release control plane. It may plan, discover, dispatch,
wait, collect redacted evidence and decide. It must not compile platform
binaries, build Apple or Windows applications, build firmware, or publish
artifacts. Those actions execute only in GitHub Actions on a qualified
self-hosted runner selected by explicit labels.

GitHub-hosted runners remain permitted for repository governance, static
analysis and non-platform-specific policy checks. They are not an execution
surface for an `INTERNAL_RELEASE` build, package, signing or deployment job.

The DJConnect repositories are public. Platform jobs selected for a
self-hosted runner must therefore run only for trusted internal events: a push
to a protected branch or an explicit maintainer `workflow_dispatch`. They must
not run for a fork pull request. Fork validation remains on GitHub-hosted
runners or is not scheduled when it requires an internal platform build.

## Canonical runner roles

| Runner role | Required labels | Purpose | Isolation boundary |
| --- | --- | --- |
| Apple | `self-hosted`, `internal-release`, `qualification`, `macos`, `apple`, `ios`, `watchos` | iOS, macOS and watchOS build, test, archive and developer-device deployment | Dedicated macOS workspace; Xcode toolchain and Apple signing access only on this host. |
| Windows | `self-hosted`, `internal-release`, `qualification`, `windows`, `windows11`, `parallels` | Windows build, package and internal VM deployment | Dedicated Windows 11 VM workspace; Windows SDK and signing material stay in the VM. |
| Firmware | `self-hosted`, `internal-release`, `qualification`, `firmware`, `esp32` | PlatformIO firmware build, checksum and internal OTA artifact preparation | Dedicated runner workspace with approved PlatformIO/toolchain; no production publication credential. |
| Pi | `self-hosted`, `internal-release`, `qualification`, `linux`, `raspberry-pi` | Pi package build and Pi-target upgrade validation | Native Pi/Linux workspace; target actions are explicit workflow steps. |
| Home Assistant | `self-hosted`, `internal-release`, `qualification`, `linux`, `home-assistant` | Home Assistant integration package and internal deployment validation | Dedicated Linux workspace/container; no interactive Codex build path. |
| Deployment | `self-hosted`, `internal-release`, `qualification`, `linux`, `production` | API and website deployment after all release gates pass | Separate deployment workspace with only required Cloudflare credentials. |

`self-hosted` is supplied by GitHub. `internal-release` prevents ordinary CI
from accidentally selecting a release runner. `qualification` denotes a runner
with a current qualification record. Platform labels select the required
toolchain. `production` is limited to the deployment role; `staging` is
intentionally not assigned until a distinct staging channel exists.

## Operational controls

- Every platform workflow uses an array-valued `runs-on` selector containing
  `self-hosted`, `internal-release`, `qualification` and its role label.
- A job records runner name, labels, runner version, checkout SHA, toolchain
  versions, artifact hashes and test/coverage references as an artifact.
- Runners use one repository checkout per job, remove untracked work after a
  job, and never reuse signing or deployment material in uploaded artifacts.
- Runner registration is repository scoped until a documented organization
  scope exists. A runner may access only the repositories whose workflows it
  serves.
- Runner upgrades, label changes and credential rotation invalidate its
  qualification until a new report is recorded.
- A migrated platform job contains an event/actor guard that excludes fork
  pull requests before selecting a self-hosted runner.

## Current state

All required repository-scoped runners are registered and online as of
2026-07-13. Apple and firmware passed isolated workflow qualification. The
remaining role qualifications and full workflow migration are still required;
see `RUNNER_QUALIFICATION_REPORT.md`. A runner may not be selected by an
internal release until that report records a passing qualification for its
role.
