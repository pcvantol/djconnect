# Platform Runner Tooling Currency Standard

Status: `IMPLEMENTATION_READY`

This standard keeps the toolchain on every GitHub Actions execution host
current without making an unattended package upgrade an unreviewed release
architecture change.

## Scope and ownership

| Runner class | Currency owner | Required approach |
| --- | --- | --- |
| GitHub-hosted `*-latest` | GitHub | Workflows select the current hosted image; each job starts on a freshly provisioned image. |
| Self-hosted Windows | DJConnect runner owner | Daily native Windows maintenance, run as `SYSTEM`. |
| Self-hosted macOS | DJConnect runner owner | Daily native macOS maintenance, run as the runner user. |
| Self-hosted Linux | DJConnect runner owner | A documented native package-maintenance task before the runner is eligible for a new workflow. |

The GitHub Actions runner application retains its normal automatic-update
channel on every self-hosted host. Registering a runner with
`--disableupdate`, or otherwise pinning its listener version, is prohibited
unless a time-bounded exception and compensating maintenance procedure are
recorded in the owning repository.

## Latest platform tooling

“Latest” means the latest package-manager release that is compatible with the
runner's approved platform line. It does not mean silently changing a native
SDK whose release qualification, signing or simulator semantics have changed.

- Windows keeps machine-level PowerShell 7, .NET 10 SDK and installed .NET
  workloads current. The job itself must not reinstall the SDK or MAUI
  workloads for each run.
- macOS keeps Homebrew-managed CI tooling current: GitHub CLI, XcodeGen,
  SwiftLint, xcbeautify, create-dmg, mas and Node. The task records Xcode,
  Swift, Git and Python versions.
- Xcode is updated to the latest *qualified* Xcode release. A new Xcode,
  Xcode beta/stable switch or simulator-runtime change requires an Apple
  runner qualification before it becomes the approved platform line; it is
  therefore detected and evidenced by unattended maintenance, not silently
  installed during a release-capable job.
- GitHub-hosted Linux, macOS and Windows jobs use current hosted-image labels
  (`ubuntu-latest`, `macos-latest` or `windows-latest`) unless a workflow has
  an explicit compatibility reason to select another GitHub-hosted image.

This standard governs runner tooling only. It does not change release
manifests, target authorization, artifact binding or smoke architecture.

## Required self-hosted maintenance evidence

Every self-hosted runner host must retain a local, non-secret maintenance log
and a last-success status. The status must identify the maintenance timestamp
and the installed platform-tool versions, but never include credentials,
environment secrets or artifact contents.

### Windows ARM64 runner

The Windows runner uses the elevated installer in
`pcvantol/djconnect-windows`:

```powershell
Set-Location <djconnect-windows-clone>
.\scripts\runner\Install-DJConnectPowerShell7Maintenance.ps1 -RunNow
```

It creates the daily `\DJConnect\Update-RunnerTooling` task and writes its
result to `C:\ProgramData\DJConnect\runner-maintenance\`. The task owns
PowerShell 7, .NET 10 and installed .NET workload updates.

### macOS runners and private-network relays

Install the maintenance LaunchAgent once on *each macOS host*, rather than
once for each runner registration, using the Apple source repository:

```sh
cd <djconnect-app-clone>
./scripts/runner/install_macos_ci_tooling_maintenance.sh --run-now
```

It runs at login and daily as the runner user. This covers Apple build,
Apple-distribution and private-network relay registrations hosted by the same
machine. The log is kept under `~/Library/Logs/DJConnect/`.

For a replacement MacBook, use `MACOS_DEVELOPMENT_HOST_BOOTSTRAP.md`. Its
development-host bootstrap uses authenticated GitHub CLI to obtain short-lived registration
tokens on demand and restores the approved runner profiles without preserving
old runner directories or credentials.

### Linux runners

Current platform source builds use GitHub-hosted Linux. A registered
self-hosted Linux runner is not eligible for a new build, deployment or smoke
workflow until its owner has documented a native scheduled package-maintenance
task, its non-secret evidence path and its supported distribution. This
prevents an idle registration from becoming an accidental unmaintained
execution surface.

## Operational checks

Before routing a new native platform workflow to a self-hosted runner, verify:

1. the runner is online with the intended labels and automatic runner updates
   enabled;
2. the relevant daily maintenance task is installed and has a recent success;
3. the required native toolchain version is recorded in the run evidence; and
4. any Xcode-line change has completed Apple runner qualification first.

Failures in runner maintenance are execution-environment blockers. They must
be repaired or explicitly rolled back before a release-capable job is
dispatched; workflows must not compensate by installing a user-local SDK,
falling back to WSL, or borrowing a different platform's toolchain.
