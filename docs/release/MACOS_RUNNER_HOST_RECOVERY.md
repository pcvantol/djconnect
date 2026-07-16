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

Alongside the transcript, an actual recovery creates one owner-only final
Markdown report at `~/Library/Logs/DJConnect/macos-runner-recovery-<UTC>.md`.
It lists every recovery stage, its `PASSED` or `FAILED` result, the final
outcome, and the path of the detailed transcript. Use `--report-file` to choose
another report path or `--no-report-file` only when another authoritative
operational report is being produced. A dry-run prints the intended report path
but creates neither the transcript nor the Markdown report.

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
