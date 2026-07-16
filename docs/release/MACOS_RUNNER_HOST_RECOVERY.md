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
Docker/Home Assistant and voice backend, HACS/integration sync, Apple/ESP32/
Pi/API/website tooling, Python 3.12, Node, .NET/MAUI tooling and the local
validation baseline.
Use `--skip-developer-workstation` only for a deliberately minimal runner-only
host.

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

Use a bounded recovery when a host needs only one capability:

```sh
./scripts/runner/bootstrap_macos_runner_host.sh --profiles apple
```

Use `--dry-run` to inspect the complete recovery plan without changes.

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

## Security boundary

The bootstrap never downloads Apple certificates, private keys, provisioning
profiles, Apple-account sessions or GitHub Environment secrets. It uses only
locally supplied signing material, never logs passwords or token values, and a
fresh Apple runner-qualification workflow must pass before private distribution
resumes.

This boundary keeps a lost or replaced laptop from becoming a secret-export
mechanism while still making host and runner recovery repeatable.
