# DJConnect developer onboarding

This directory is the canonical, versioned onboarding package for a DJConnect
developer workstation. It owns the macOS and Windows onboarding scripts, their
contract tests and package documentation.

## Release alignment

The current onboarding package is released as `3.3.1`, aligned with the current
DJConnect platform release for operator clarity. This is version alignment only:
the package remains independently versioned, does not consume platform release
artifacts, and does not require a matching platform version to run or verify.

## Entry points

- macOS: `./onboarding/dev_onboarding_macos.sh`
- Windows: `pwsh -File .\onboarding\dev_onboarding_windows.ps1`
- macOS machine transfer: `./onboarding/machine_transfer_macos.sh`

The former `tools/dev_onboarding_macos.sh` and
`tools/dev_onboarding_windows.ps1` paths remain minimal compatibility wrappers.
New documentation and automation must use the canonical `onboarding/` paths.

The macOS package reconciles Docker Desktop and the persistent local Home
Assistant Compose environment. The Home Assistant service is available at
`http://localhost:8123` after its container is healthy. The Windows package
uses the macOS-hosted Home Assistant environment rather than Docker Desktop in
the Windows ARM VM.

## Windows Actions runner service identity

The Windows ARM64 Actions runner is a persistent service for native builds and
deployment. It must run as its own passwordless Windows virtual service account
(`NT SERVICE\<runner-service-name>`), not as `NETWORK SERVICE`, Local System,
an administrator or a developer's interactive account. The account receives
Modify rights only to the runner work root and the internal-release install
root; it has no interactive sign-in, no reusable password and no membership in
local administrator groups.

For an existing Windows runner, run this explicit onboarding step from a
normal PowerShell 7 terminal. It requests UAC only for the narrowly scoped
service migration:

```powershell
pwsh -File .\onboarding\dev_onboarding_windows.ps1 -Steps 15
```

For first-time runner setup, use the same repository's
`scripts\runner\bootstrap_windows_arm64_runner.ps1`; it registers the runner,
then immediately replaces the temporary bootstrap identity with its dedicated
virtual account. No service or GitHub token is written to the repository.

A Windows service always runs in session 0. This identity hardening therefore
does not make a MAUI/WinUI GUI smoke interactive. GUI smoke must use a separate
least-privilege interactive relay and remains unavailable while no user is
logged on.

## Secure machine transfer

Use the dedicated macOS tool to transfer explicitly selected DJConnect
developer assets between Macs. It writes its AES-256 encrypted archive outside
the repository, by default under
`~/Library/Application Support/DJConnect/machine-transfer/`, and prints a
generated recovery passphrase once. Store that passphrase separately.

```sh
./onboarding/machine_transfer_macos.sh --export \
  --signing-p12 /secure/Apple-signing.p12 \
  --ssh-key ~/.ssh/id_ed25519 \
  --license-file /secure/license-file

./onboarding/machine_transfer_macos.sh --import --archive <archive>.tar.enc
```

The archive can include the explicit Apple P12, provisioning profiles, the
DJConnect onboarding token environment, explicitly selected SSH keys and
explicit license files. Import verifies a SHA-256 manifest, imports profiles,
offers a hidden P12-password prompt for login-keychain import, and stages
licenses/SSH keys with owner-only permissions. It never exports the whole
Keychain, browser profiles, Docker/GitHub credential stores or Apple/GitHub/
Docker sessions. Reauthenticate those services interactively on the new Mac.

## Home Assistant development lab baseline

`home_assistant_lab/configuration.yaml` and
`home_assistant_lab/compose.yaml` capture the portable baseline of the active
local development lab: Home Assistant, Whisper, Piper and Music Assistant,
the ngrok proxy trust boundary and DJConnect debug logging. The onboarding
seeds these files only when the target `configuration.yaml` or Compose file is
absent; existing local files are preserved. It renders the selected container
names, images, voice settings and local Music Assistant data path into a new
Compose file. External URLs are added later by the ngrok step.

The templates intentionally contain no access tokens, passwords, private keys,
tailnet identity, host-specific absolute paths or Home Assistant runtime state.

## Network checks and firewall recommendations

Run the read-only network assessment to document required outbound DJConnect
development dependencies, active TCP endpoint sessions, listening services,
Docker-published ports and the macOS firewall/PF posture:

```sh
./onboarding/network_checks_macos.sh
```

It writes an owner-only Markdown report outside the repository by default. It
does not capture all system traffic and does not mutate services or firewall
rules; it assesses the known DJConnect dependency endpoints and produces
conditional least-privilege recommendations.

Its mandatory macOS preflight requires macOS 14 or later and verifies that no
patch update is available within the installed macOS major version. It does not
force a major-version upgrade. If a patch is available, install it through
**System Settings → General → Software Update**, restart when requested, and
run preflight again.

At startup the macOS entry point reads its package version and compares it with
the local `onboarding/dist` catalog, including versioned subdirectories. It
warns before execution when a newer package is found. An interactive user must
explicitly confirm continuing with the older package; `--yes` is the explicit
non-interactive confirmation. The Markdown run report records the comparison
path and decision without recording secrets. Use `ONBOARDING_DIST_DIR` to point
an extracted package at a different local catalog, or `--report-file` to choose
the report path.

## Desired-state manifest compatibility

The desired-state manifest is versioned independently from this onboarding
package. Its normative contract is in
[`MANIFEST_COMPATIBILITY.md`](MANIFEST_COMPATIBILITY.md): it declares both its
own `version` and the `minimum_tool_version` required to apply it. A consuming
tool must check compatibility at startup, block apply when it is too old, and
log and report both versions and the compatibility decision. The separate
runner desired-state manifest and its consumer are deliberately not changed by
this onboarding-package documentation update.

## Tests

Run the package contract tests from the repository root:

```sh
python3 -m unittest onboarding.tests.test_onboarding_scripts
```

Build the deterministic, versioned distribution bundle into `onboarding/dist`:

```sh
python3 onboarding/build_package.py --output onboarding/dist
python3 onboarding/build_package.py --output onboarding/dist --check
```

The Linux GitHub Actions workflow runs the cross-platform build unit tests,
verifies that `onboarding/dist` is current, and uploads that directory as its
build artifact.

The root `tests/test_onboarding_package.py` is deliberately only a discovery
bridge for repository-wide `unittest discover`; the canonical tests remain in
this package.

The macOS script is sourceable as a function library: sourcing it loads helpers
without running onboarding. The Windows script supports `-Library` for the
same purpose. Unit tests directly exercise pure step selection, labels,
Compose-path resolution, command quoting and Windows selection behavior.
CLI contract tests retain coverage of dry-run plans, Docker Compose setup,
ngrok redaction, interactive selection and guarded mutating steps.

## Package manifest

`manifest.yml` records the package version, its canonical components and the
compatibility wrappers. Its `package.platform_release_alignment` is descriptive
only; `package.platform_release_dependency: none` is the explicit no-coupling
contract. `CHANGELOG.md` records package releases. Update both together with
any package-surface change.
