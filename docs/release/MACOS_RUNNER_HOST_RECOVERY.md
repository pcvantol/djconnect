# macOS Runner Host Recovery

Use this procedure after replacing or rebuilding the maintainer MacBook. It
recovers the development-tooling baseline and all DJConnect macOS GitHub
Actions runner registrations without copying a runner directory, a registration
token or other runner state from the old host.

## One-command recovery after cloning the central repository

On the fresh Apple-Silicon Mac, install Codex and clone this repository. Then
run the bootstrap with the explicit, currently qualified Xcode line:

```sh
./scripts/runner/bootstrap_macos_runner_host.sh --xcode-version <qualified-version>
```

Before the bootstrap downloads, installs or authenticates anything, its
mandatory host preflight determines whether the Mac is suitable for DJConnect
development. It requires macOS 14 or newer, a physical Apple-Silicon Mac
(`arm64` with an Apple CPU), at least 8 GB RAM, at least four CPU cores and at
least 80 GB free on the filesystem that will contain `~/Documents/GitHub`.
It records the detected macOS version, Apple CPU model, RAM, core count and
free disk space in the transcript and final report. 16 GB RAM and 120 GB free
space are recommended for Docker, Xcode and Windows-VM workloads. This gate is
deliberately non-skippable.

## Declarative machine desired state

The canonical desired state is
[`macos_runner_host_desired_state.yml`](../../scripts/runner/macos_runner_host_desired_state.yml).
It declares the host qualification thresholds, required Homebrew tooling,
refreshable casks and repository-scoped runner profiles (repository, runner
name and labels). The bootstrap validates this manifest before it changes the
machine, then reconciles the declared state idempotently. The final report
records the manifest path and schema version used as evidence.

The file intentionally uses a bootstrap-safe flat YAML key/value subset. This
lets a fresh Mac parse it with native macOS shell tooling before Homebrew,
Python or a general YAML runtime exists. Use `--desired-state <file>` to test
or apply another compatible desired-state manifest; unsupported schema versions
or missing required keys fail closed.

## Script reference

Run the script from the central `djconnect` checkout. The most useful modes
are:

| Goal | Command | Machine changes |
| --- | --- | --- |
| Compare the current Mac with desired state | `./scripts/runner/bootstrap_macos_runner_host.sh --verify` | None |
| Inspect the full recovery plan | `./scripts/runner/bootstrap_macos_runner_host.sh --xcode-version <qualified-version> --dry-run` | None |
| Recover all declared runner profiles | `./scripts/runner/bootstrap_macos_runner_host.sh --xcode-version <qualified-version>` | Yes, after preflight |
| Recover selected profiles | `./scripts/runner/bootstrap_macos_runner_host.sh --profiles apple,esp32 --xcode-version <qualified-version>` | Yes, after preflight |
| Verify another compatible desired state | `./scripts/runner/bootstrap_macos_runner_host.sh --desired-state /secure/path/host.yml --verify` | None |
| Show the installed bootstrap version | `./scripts/runner/bootstrap_macos_runner_host.sh --version` | None |

The recovery bootstrap is independently versioned from DJConnect releases.
The initial stable version is `1.0.0`; its release history is maintained in
[`BOOTSTRAP_MACOS_RUNNER_HOST_CHANGELOG.md`](../../scripts/runner/BOOTSTRAP_MACOS_RUNNER_HOST_CHANGELOG.md).
Include the `--version` output in support or recovery evidence when the script
itself is relevant to a result.

`--verify` emits a Markdown delta to standard output and exits `0` only when
all required desired-state rows match. It exits `1` when it finds drift. It
does not create a recovery transcript or final report unless those paths are
explicitly requested. Optional entries, such as Parallels Desktop, are shown
as `OPTIONAL` rather than drift when absent.

During a recovery, a failed phase offers `retry`, `skip` or `abort` on an
interactive terminal. `retry` repeats just that phase. `skip` is recorded and
prevents a qualified conclusion; dependent phases fail closed until the skipped
phase is recovered. Use `--no-step-retry` for an unattended fail-closed run.

Use `--force-phases <ids>` to re-run idempotent reconciliation even when a
phase already has its desired state. For example,
`--force-phases runner-apple` validates and reconciles an existing Apple
runner service without deleting or re-registering it. A phase cannot be both
skipped and forced.

For a real recovery, default outputs are an owner-only transcript
`~/Library/Logs/DJConnect/macos-runner-recovery-<UTC>.log` and a matching
Markdown report. Override their paths with `--log-file` and `--report-file`,
or suppress them with `--no-log-file` and `--no-report-file` when an external
recorder is authoritative.

## Repository mutation governance

This bootstrap reconciles host state and may clone, fetch or fast-forward its
managed checkouts. It must not silently edit tracked source files. If a
desired-state gap can only be resolved by changing tracked repository content,
stop that recovery subtask and open one dedicated engineering increment in the
owning repository. Follow that repository's bootstrap, active engineering
prompt and completion protocol, then create exactly one reviewable Pull Request
for the scoped mutation. Do not mix generated output, credentials, unrelated
changes or multiple repository owners into that Pull Request.

## Reboot continuation

If macOS reports that a reboot is required, recovery stops at the reboot gate
and writes an owner-only (`0600`) resume checkpoint at
`~/Library/Application Support/DJConnect/macos-runner-recovery-resume.env`.
The checkpoint contains only phase completion state and non-secret recovery
context; it never contains passwords, tokens, signing passwords, key material
or interactive authentication data.

Restart macOS, then rerun the same non-secret recovery options with:

```sh
./scripts/runner/bootstrap_macos_runner_host.sh --resume --xcode-version <qualified-version>
```

Supply any signing P12/profile paths again if later phases require them. Resume
re-runs the mandatory host preflight and reboot gate, preserves earlier phases
that completed successfully, and continues with the remaining phases. A
successful resumed recovery removes its checkpoint. Use `--resume-state <file>`
only when an explicitly managed, owner-only checkpoint location is required.

Every subsequent recovery phase starts with a recorded precheck. The precheck
requires each declared upstream dependency to be `PASSED` (a skipped, failed or
blocked dependency stops the dependent phase) and checks its relevant local
condition, such as Homebrew availability, GitHub CLI availability, repository
presence, Docker readiness, the maintenance installer, keychain tooling or
Xcode. The Markdown report includes a separate `Precheck: <phase>` row with
the dependency and condition evidence before that phase can run. Dry-run
records the dependency order and plans runtime condition checks without
claiming that post-installation tools already exist.

The bootstrap asks GitHub CLI to authenticate if needed. The signed-in account
must be able to administer the DJConnect repositories. It then obtains a fresh,
short-lived registration token through the GitHub API for each profile; no
token is entered on the command line, written to a file or retained in a log.
The downloaded Apple-Silicon Actions-runner archive is verified against the
SHA-256 digest GitHub publishes in its release metadata before it is unpacked.

By default, the recovery then invokes the established
`tools/dev_onboarding_macos.sh --all --yes --warm-sudo` flow. This restores the
complete macOS developer workstation: all DJConnect repositories, Codex CLI,
Docker Desktop, the persistent local Home Assistant Docker Compose service
(`homeassistant` on `http://localhost:8123`), Whisper, Piper and Music
Assistant voice/backend services, HACS/integration sync, Apple/ESP32/Pi/API/
website tooling, Python 3.12, Node, .NET/MAUI tooling and the local validation
baseline. Docker Desktop may show its own first-run acceptance screen; once
accepted, the onboarding creates or reconciles the Compose file and starts the
containers. Use `docker compose -f ~/docker/homeassistant/docker-compose.yml
ps` to inspect their state.

The recovery keeps authentication interactive and scoped to the local user:

- GitHub CLI opens the browser-based `gh auth login` flow before repositories
  and runners are accessed.
- Docker Desktop presents any first-run dialogs; the recovery waits for its
  daemon, then invokes Docker Hub's device-login flow with `docker login`.
- `xcodes` asks for Apple Developer authentication when an Xcode download is
  requested, and ngrok can prompt invisibly for its auth token when configured.

No GitHub, Docker, Apple or ngrok credential is accepted as a command-line
argument, added to repository files or printed in recovery logs.
Use `--skip-developer-workstation` only for a deliberately minimal runner-only
host.

To recover the persistent Home Assistant tunnel too, supply the existing
reserved domain and let the bootstrap prompt invisibly for the token:

```sh
./scripts/runner/bootstrap_macos_runner_host.sh \
  --xcode-version <qualified-version> \
  --ngrok-domain <reserved-domain> \
  --prompt-ngrok-auth
```

The token is passed only in memory to the existing onboarding flow, which
creates the runner-user LaunchAgent. It is never a command-line value or
written to a recovery log.

By default it prepares these repository-scoped macOS ARM64 runners:

| Profile | Repository | Runner name | Additional labels |
| --- | --- | --- | --- |
| `apple` | `pcvantol/djconnect-app` | `djconnect-apple-macos` | `internal-release`, `qualification`, `apple` |
| `private-network` | `pcvantol/djconnect` | `djconnect-private-network-relay` | `internal-release`, `private-network-deployment` |
| `esp32` | `pcvantol/djconnect-esp32` | `djconnect-esp32-firmware` | `internal-release`, `qualification`, `firmware`, `esp32`, `private-network-deployment` |
| `pi` | `pcvantol/djconnect-pi` | `djconnect-pi-readiness` | `internal-release`, `private-network-deployment` |

All profiles run as launchd services under the current runner user. The
bootstrap also installs and executes the daily macOS tooling-maintenance
LaunchAgent from `djconnect-app`.

## Administrator rights and persistent tasks

The recovery is run as the normal logged-in maintainer account, never as
root. It verifies that account is a local macOS administrator and prompts once
for sudo; a short-lived keepalive maintains that authorization only while the
bootstrap is running. No passwordless sudo rule or persistent sudoers entry is
created.

The bootstrap installs and then verifies these persistent tasks:

- every selected GitHub Actions runner as a system service through its checked
  runner svc.sh script;
- the runner-user com.djconnect.ci-tooling-maintenance LaunchAgent, including
  one immediate maintenance execution;
- when --ngrok-domain is supplied, the runner-user
  dev.djconnect.homeassistant.ngrok LaunchAgent.

It stops if a selected runner is not registered, a runner service is not
running, or a required user LaunchAgent is not loaded. The runner services need
sudo; the two user LaunchAgents deliberately do not.

## Completion: tooling currency, reboot gate and initial verification

Before reporting recovery complete, the bootstrap refreshes every
Homebrew-managed tool used by the recovered workstation: Git, GitHub CLI, jq,
Node, Python 3.12, XcodeGen, SwiftLint, xcbeautify, create-dmg, mas, xcodes and
PlatformIO. It refreshes installed Docker, .NET SDK and Parallels casks, and
updates the Codex CLI when it is in scope. Local repository dependencies,
Python environments, .NET workloads and PlatformIO packages are restored by
the complete developer onboarding.

Xcode is the intentional exception: the bootstrap uses only the explicitly
supplied qualified Xcode line and runs its first-launch setup. It does not
silently switch to a newer Xcode line, because that requires Apple runner
qualification.

The bootstrap queries macOS Software Update for a pending restart/reboot
requirement. If one is reported, recovery stops without rebooting the machine;
restart macOS and rerun the bootstrap so qualification evidence belongs to the
post-reboot host.

Finally, the bootstrap runs the developer-environment validation steps, checks
Docker/Home Assistant, all selected system runner services and user
LaunchAgents, and waits for every selected runner to report online to GitHub.
Only then does it report the recovery as passed.

Use a bounded recovery when a host needs only one capability:

```sh
./scripts/runner/bootstrap_macos_runner_host.sh --profiles apple
```

Use `--dry-run` to inspect the complete recovery plan without changes:

```sh
./scripts/runner/bootstrap_macos_runner_host.sh \
  --xcode-version <qualified-version> \
  --ngrok-domain <reserved-domain> \
  --prompt-ngrok-auth \
  --configure-apple-internal-release \
  --install-parallels \
  --dry-run
```

Dry-run never downloads or installs tooling, authenticates a service, prompts
for a secret, changes a keychain, registers a runner, creates a GitHub secret
or variable, changes launchd, starts Docker, updates macOS or writes local
configuration. It includes the subordinate developer-onboarding and final
verification commands with their own `--dry-run` flag so the printed plan
covers the complete recovery chain.

Interactive terminal output uses cyan section markers, green success markers,
yellow warnings, red errors and magenta dry-run commands. Set `NO_COLOR=1`
or pass `--no-color` for plain logs and CI capture.

For an actual recovery, the bootstrap creates one owner-only transcript at
`~/Library/Logs/DJConnect/macos-runner-recovery-<UTC>.log`, or at the path
given through `--log-file`. Its subordinate onboarding writes through that
same transcript and does not create a second onboarding log. Use
`--no-log-file` only when an external terminal/session recorder is already
the authoritative capture.

The transcript excludes interactive GitHub/Docker authentication output and
secret prompts so temporary device codes, account prompts and credentials are
not retained. The daily maintenance LaunchAgent retains its separately required
non-secret status evidence; that is operational evidence, not a second recovery
transcript.

As defence in depth, every non-interactive output line is redacted before it
reaches the transcript. The filter removes authorization bearer values,
token/secret/password/credential/private-key key-value values, matching JSON
fields, inline CLI secret values, embedded HTTP credentials and recognizable
GitHub token strings. Recovery never enables shell tracing. The transcript and
final Markdown report are created with owner-only (`0600`) permissions.

Alongside the transcript, an actual recovery creates one owner-only final
Markdown report at `~/Library/Logs/DJConnect/macos-runner-recovery-<UTC>.md`.
It lists every recovery stage, its `PASSED` or `FAILED` result, the final
outcome, and the path of the detailed transcript. Use `--report-file` to choose
another report path or `--no-report-file` only when another authoritative
operational report is being produced. A dry-run prints the intended report path
but creates neither the transcript nor the Markdown report.

The report ends with a **Verification-run verdict** and **Conclusion**. It
states `HOST QUALIFIED FOR THE REQUESTED DJCONNECT RECOVERY SCOPE` only when
the initial post-recovery verification run has passed and no phase was skipped.
A passed verification run with skips is explicitly `NOT FULLY QUALIFIED`; a
failed or absent verification run is `NOT QUALIFIED`. Thus the conclusion is
based on the verification evidence, not merely on the shell process exit code.

If an actual recovery phase fails, the operator is offered `retry` or `abort`
or `skip` on the controlling terminal. `retry` repeats only that same failed
phase; it does not rerun already successful phases or continue into later
phases first. `skip` is an explicit operator decision and is never reported as
a qualified pass. The report records every failed attempt, retry and skip.
Select `--no-step-retry` for an unattended fail-closed run. If no interactive
terminal is available, recovery also fails closed rather than attempting an
unsafe automatic retry or skip.

To intentionally omit known phases before execution, use `--skip-phases` with
one or more comma-separated IDs, for example:

```sh
./scripts/runner/bootstrap_macos_runner_host.sh \
  --xcode-version <qualified-version> \
  --skip-phases parallels,apple-signing
```

Valid IDs are `sudo`, `tooling`, `xcode`, `parallels`, `github-auth`,
`repositories`, `developer-workstation`, `docker-auth`,
`runner-apple`, `runner-private-network`, `runner-esp32`, `runner-pi`,
`maintenance`, `tooling-refresh`, `reboot-check`, `services`,
`apple-signing`, `apple-readiness`, `apple-github-audit` and
`initial-verification`. `macos-preflight` is mandatory and cannot be skipped.
Unknown IDs fail before recovery continues. Any skip results in **COMPLETED
WITH SKIPPED PHASES**, not **PASSED**; separately rerun and qualify the
skipped phases before treating the host as release-capable.

Use `--force-phases` when a phase must be deliberately run again although its
desired state is already present. For example, this reconciles the existing
Apple runner service without removing or registering the runner again:

```sh
./scripts/runner/bootstrap_macos_runner_host.sh \
  --xcode-version <qualified-version> \
  --force-phases runner-apple
```

Forced phases remain subject to the same prechecks and dependencies. They are
idempotent: force means validate/reconcile, never destructive recreation.
A phase cannot be both skipped and forced.

## Optional Parallels Desktop recovery

If this Mac hosts the Windows ARM64 build or deployment VM, include
`--install-parallels`. The bootstrap checks for the Parallels Desktop app and
`prlctl`, then installs Parallels with Homebrew only when it is absent:

```sh
./scripts/runner/bootstrap_macos_runner_host.sh \
  --xcode-version <qualified-version> \
  --install-parallels
```

The first Parallels launch still requires license activation. Windows ARM VM
creation/recovery and registration of its Windows self-hosted runner are a
separate explicit operation. Parallels downloads the supported Windows 11 ARM
image through **Get Windows 11 from Microsoft**; Microsoft EULA acceptance and
Windows first-run account setup cannot be bypassed by repository automation.

After the Windows 11 ARM desktop is available, clone `pcvantol/djconnect` in
the VM, open an elevated PowerShell 7 session and run:

```powershell
.\scripts\runner\bootstrap_windows_arm64_runner.ps1
```

The Windows bootstrap authenticates GitHub CLI interactively if required,
downloads the current `win-arm64` Actions runner and checks it against GitHub's
release SHA-256, registers `djconnect-windows11-parallels-arm64` as a
`NETWORK SERVICE` Windows service, prepares service-readable runner/install
paths, installs Git, Python 3.12 and Node LTS, restores the checked-out Windows
MAUI workload and installs the daily PowerShell 7/.NET 10/workload maintenance
task.
No registration token is supplied on the command line or retained on disk.

## Xcode and non-interactive signing recovery

`--xcode-version` installs and selects the requested qualified Xcode line with
the `xcodes` CLI. It can require interactive Apple Developer authentication and
MFA, but it downloads, installs, selects the developer directory, accepts the
license and runs the first-launch setup automatically. Do not substitute an
unqualified “latest” version for the explicit qualified version.

To restore release-capable signing, copy the P12 and provisioning profiles from
your secure local backup to the new Mac, then run:

```sh
./scripts/runner/bootstrap_macos_runner_host.sh \
  --xcode-version <qualified-version> \
  --signing-p12 /secure/path/DJConnect-signing.p12 \
  --provisioning-profiles-dir /secure/path/profiles \
  --configure-keychain-access
```

The P12 and login-keychain passwords are prompted invisibly. The script imports
the identity into the current user's login keychain and grants the standard
Apple build tools (`codesign`, `xcodebuild` and `productbuild`) unattended
private-key access through the key partition list. It then lists available
code-signing identities without revealing secret material.

For the current internal Apple release scope, run the Apple-registration and
readiness check after restoring those local materials:

```sh
./scripts/runner/bootstrap_macos_runner_host.sh \
  --xcode-version <qualified-version> \
  --signing-p12 /secure/path/DJConnect-signing.p12 \
  --provisioning-profiles-dir /secure/path/profiles \
  --configure-keychain-access \
  --configure-apple-internal-release
```

This opens Xcode so the operator can interactively register/sign in with the
DJConnect Apple Developer account and refresh managed profiles. It then
fail-closes unless Xcode accepts provisioning updates, the selected local
`Apple Development` identity matches the project Team ID, and unexpired
development profiles cover the iOS app, Watch app, complication and widget
bundle IDs. On success it updates only the new MacBook hardware UUID and the
non-secret signing-identity name in the `apple-secure-distribution` GitHub
Environment. The actual certificate, private key and profiles remain local.

This is intentionally **not** App Store/TestFlight distribution provisioning:
the approved 3.3 internal-release flow uses local Developer provisioning only.
App Store Connect, TestFlight and public distribution require a separate,
explicitly approved process.

## GitHub configuration values after a Mac replacement

The recovery runs a name-only audit of secrets and variables in
`pcvantol/djconnect-app` / Environment `apple-secure-distribution`. GitHub
does not disclose secret values, so the audit never attempts to read or print
them. Update each item as follows:

| GitHub Environment item | New Mac action |
| --- | --- |
| `DJCONNECT_APPLE_MACBOOK_HARDWARE_UUID` | Required. It identifies the old host, so it must change. `--configure-apple-internal-release` derives the new hardware UUID and updates it automatically after readiness validation. |
| `DJCONNECT_APPLE_DEVELOPMENT_SIGNING_IDENTITY` | Required. Reconcile it if the identity name shown by the restored/new keychain differs. The same configure option updates it automatically. |
| `DJCONNECT_APPLE_IPHONE_UDID` | Do not change for a Mac-only replacement. Update it only if the iPhone itself was replaced, in the `apple-secure-distribution` Environment. |
| `DJCONNECT_APPLE_WATCH_UDID` | Do not change for a Mac-only replacement. Update it only if the paired Watch itself was replaced, in the same Environment. |

There are no Mac-local paths held in GitHub secrets or variables for the Apple
relay. Runner roots, keychain paths, provisioning-profile directories, Docker
paths and launchd plist locations are deliberately discovered and configured
locally. They must not be copied into GitHub configuration.

## Security boundary

The bootstrap never downloads Apple certificates, private keys, provisioning
profiles, Apple-account sessions or GitHub Environment secrets. It uses only
locally supplied signing material, never logs passwords or token values, and a
fresh Apple runner-qualification workflow must pass before private distribution
resumes.

This boundary keeps a lost or replaced laptop from becoming a secret-export
mechanism while still making host and runner recovery repeatable.
