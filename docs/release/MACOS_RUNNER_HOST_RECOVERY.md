# macOS Runner Host Recovery

Use this procedure after replacing or rebuilding the maintainer MacBook. It
recovers the development-tooling baseline and all DJConnect macOS GitHub
Actions runner registrations without copying a runner directory, a registration
token, signing material or other machine state from the old host.

## One-command recovery after cloning the central repository

On the fresh Apple-Silicon Mac, install the current qualified full Xcode line,
complete its first-run license prompt, install Codex, and clone this repository.
Then run:

```sh
./scripts/runner/bootstrap_macos_runner_host.sh
```

The bootstrap asks GitHub CLI to authenticate if needed. The signed-in account
must be able to administer the DJConnect repositories. It then obtains a fresh,
short-lived registration token through the GitHub API for each profile; no
token is entered on the command line, written to a file or retained in a log.
The downloaded Apple-Silicon Actions-runner archive is verified against the
SHA-256 digest GitHub publishes in its release metadata before it is unpacked.

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

## Intentional manual boundary

The bootstrap never restores Apple certificates, private keys, provisioning
profiles, Apple-account sessions or GitHub Environment secrets. Signing
material must be restored locally to the runner user's login keychain, then a
fresh Apple runner-qualification workflow must pass before private
distribution resumes.

This boundary keeps a lost or replaced laptop from becoming a secret-export
mechanism while still making host and runner recovery repeatable.
