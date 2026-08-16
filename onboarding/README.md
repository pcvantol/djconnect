# DJConnect developer onboarding

This directory is the canonical, versioned onboarding package for a DJConnect
developer workstation. It owns the macOS and Windows onboarding scripts, their
contract tests and package documentation.

## Release alignment

The current onboarding package is released as `4.5.0`, aligned with the current
DJConnect platform release for operator clarity. This is version alignment only:
the package remains independently versioned, does not consume platform release
artifacts, and does not require a matching platform version to run or verify.

## Entry points

- macOS: `./onboarding/dev_onboarding_macos.sh`
- Windows: `pwsh -File .\onboarding\dev_onboarding_windows.ps1`
- macOS machine transfer: `./onboarding/machine_transfer_macos.sh`

## Engineering Inbox (macOS)

Engineering Platform `1.5.0` provides a local iCloud Engineering Inbox through
the configured Remote Submission Provider. Run
`./onboarding/dev_onboarding_macos.sh --steps 31 --yes` to create the private
workspace, install the per-user `com.djconnect.engineering-inbox` watcher and
the private dashboard LaunchAgent, and verify both. Submit UTF-8 `.md` or
`.txt` prompts to `iCloud Drive/DJConnect Engineering/Inbox`; iOS-created
`.txt` files and filename-neutral Markdown are supported. The watcher claims
stable files one at a time, oldest File Date Modified first, and invokes only
this repository's `engineering-execution-host`.

After admission, the Engineering runner is detached from the polling watcher.
The watcher continues to scan the Inbox and updates the dashboard queue during
the active run, while the admission record enforces exactly one execution at a
time. A prompt added during a run is therefore visible in **Inbox-wachtrij**
on the next polling cycle, but remains queued until the active execution is
terminal.

iCloud is transport only. After a prompt is claimed, the executed prompt copy,
status, reports, logs and terminal archive live locally under `.engineering/`:

- `.engineering/inbox/Running`, `Completed` and `Failed` hold the local prompt
  lifecycle archive;
- `.engineering/inbox-processing/` contains the immutable executed input;
- `.engineering/status/` holds the canonical dashboard status;
- `.engineering/reports/` holds Engineering Reports; and
- `.engineering/engineering.db` holds redacted component logs and other
  versioned local Engineering evidence. `.engineering/logs/` is only a private
  fallback for early startup or crash logging when SQLite is unavailable.

The installed Inbox watcher and dashboard record bounded lifecycle `INFO`
events for startup, received shutdown signals and orderly shutdown. A confirmed
dashboard restart records the fixed component requested before the owned
LaunchAgent is kickstarted. Each lifecycle event contains only component
version, short build commit and fixed LaunchAgent identity; it never includes
prompt content, secrets, account data or a browser-supplied command. Inspect
these records through **Engineering Status → Logs**. If SQLite is unavailable
during early startup, use the corresponding owned LaunchAgent output stream as
the fallback diagnostic source, then run the documented `doctor` command.

Each completed Engineering Report also records the execution provenance for
that exact run: Runtime Provider, reported AI Model, reported Reasoning and
Configuration Profiles, and detected Codex CLI Version. Values are shown as
`not reported` when the CLI did not supply them; the runner and Engineering
Status never guess them. In Engineering Status, open the matching
**Promptgeschiedenis** row to view those fields in its read-only execution
detail dialog. The Engineering Report and AI analysis remain separate actions
on that same row, so every view stays bound to its exact Run ID. There is no
separate **Laatst uitgevoerde prompt** card.

The detail dialog is a read-only projection, not a second history store. It
loads one immutable SQLite history row and its bounded companion data for the
selected Run ID, then derives only the compact Evidence Bundle and displayed
target-repository provenance from that run's report. It never modifies a
report or stored history, and it never falls back to evidence from another
prompt. If a matching report is absent or cannot be read, the dialog retains
the history fields and shows no derived evidence.

### Dashboard language verification

Engineering Status supports the canonical five language families `en`, `nl`,
`de`, `fr` and `es`. Its language selector changes both fixed dashboard chrome
and dynamic feedback such as AI-chat labels, copy actions and component-status
messages. When changing any dashboard copy, add the key to all five language
blocks in `tools/engineering/assets/dashboard_locales.mjs`; do not put a
user-facing sentence directly in `dashboard.js`.

Before handing off dashboard copy, run:

```sh
npx playwright test tests/engineering/dashboard.spec.mjs
```

The suite checks catalogue completeness, scans client-created presentation
text for unexpected literals, and renders each supported language in the
browser. Its source-to-interface check also covers template bindings, modal
copy, pull-to-refresh feedback, downloadable chat labels and accessibility
names. It therefore catches a missing translation as well as a label that was
accidentally left in the source language.

Do not create or rely on `iCloud Drive/DJConnect Engineering/Reports` or an
iCloud `status.json`. Existing legacy iCloud archives can be moved safely with
`python3 -m tools.engineering.inbox_watcher migrate-icloud-archives` after
checking the local copies. Use `python3 -m tools.engineering.inbox_watcher
doctor` or `./tools/engineering/dj-engineering-dashboard doctor` for corrective
actions. Use each component's `uninstall` command to remove only its own
LaunchAgent. Repository and GitHub evidence remain authoritative.

The Inbox is deliberately strict: if a prompt ends `BLOCKED` or `FAILED`,
later prompts remain unclaimed with dashboardstatus `WAITING_FOR_PREDECESSOR`.
Submit the repaired prompt with `Retry-Of:
<blocking-run-id>` on its own line to release the sequence after that retry
completes. The dashboard identifies the blocking prompt and recovery action.

Engineering prompts require Engineering Platform `>= 1.5.0`. An older platform
is incompatible: upgrade it before starting a prompt; do not bypass bootstrap
compatibility validation.

## Authoring a prompt without Forge

Engineering Platform accepts producer-neutral prompts. In the Operations
Console, use **Download Prompt Template** to obtain the canonical English
Markdown starter template for a new or existing project. A human or any GPT can
complete it, then submit it through a supported mechanism. The canonical
[Prompt Authoring Contract](../docs/engineering/EP_PROMPT_AUTHORING_CONTRACT.md)
explains the authoring rules, the distinction from the Producer Submission and
Execution Host contracts, execution-mode guidance, versioning and the no-runtime-
enforcement boundary. The downloaded artifact is the canonical
[starter template](../docs/engineering/EP_PROMPT_TEMPLATE.md), not a
dashboard-maintained copy.

## Raspberry Pi Pico 2 W development (macOS)

Pico 2 W is a first-class profile of this canonical onboarding package. It is a
developer-experience capability only: it does not introduce Pico product
runtime behavior, a new Home Assistant contract, or a second firmware
architecture.

The current `djconnect-pico` checkout contains no implementation or build
contract that selects the C/C++ Pico SDK. The canonical onboarding default is
therefore **MicroPython**, not two competing complete toolchains. Re-evaluate
that choice only when the Pico repository itself adopts and documents a C/C++
SDK contract.

From a clone of `djconnect`, run the normal onboarding entry point:

```sh
./onboarding/dev_onboarding_macos.sh --steps 13,29,30 --yes
```

Step 13 discovers/clones `djconnect-pico`; step 29 installs the Pico host
tools and immediately re-runs step 30, the read-only Pico readiness report.
For a later read-only check use:

```sh
./onboarding/dev_onboarding_macos.sh --steps 30
```

The report uses `PASS`, `WARNING` and `FAIL` rows and exits non-zero only for
missing required host tooling. A disconnected board is a `WARNING`, so a new
developer can prepare a workstation before connecting hardware.

### Required tools

| Tool | Installation owner | Readiness requirement |
| --- | --- | --- |
| Homebrew, Python 3.12+, Git | canonical macOS onboarding | Required |
| VS Code + `code` launcher | developer / VS Code | Required |
| MicroPico, Python and Pylance VS Code extensions | Pico onboarding step | Required |
| `picotool` | Homebrew | Required |
| `mpremote`, `micropython-stubber`, Ruff | isolated Pico tool environment | Required |
| MicroPython `RPI_PICO2_W` stable UF2 | manual device flashing | Required before first device run |

The Pico step installs Python host tools in
`~/Library/Application Support/DJConnect/pico-tools` by default, rather than
globally. Use `--pico-tool-venv <directory>` or `PICO_TOOL_VENV` to select a
different isolated environment. Onboarding calls those tools by full path and
does not edit a shell startup file or silently change `PATH`.

Black is not a required developer command: the existing canonical Python
checks use Ruff, while no repository evidence selects Black as a formatting
contract. It can be present as a transitive dependency of `micropython-stubber`.
Thonny is optional for people who prefer its beginner-focused REPL workflow;
the recommended IDE is VS Code with MicroPico.

### Tool-version matrix

| Component | Supported policy | Reported by readiness |
| --- | --- | --- |
| macOS | 14 or later; Apple Silicon is the primary host | Host version and architecture |
| Python | 3.12 or later | Python version |
| MicroPython firmware | Current stable `RPI_PICO2_W` release; do not use a preview for baseline work | Board-reported implementation when connected |
| `picotool` | Homebrew stable formula | `picotool --version` |
| `mpremote` | `>=1.26,<2` | `mpremote --version` |
| `micropython-stubber` | `>=1.24,<2` | `stubber --version` |
| Ruff | `0.16.0` (the existing canonical CI version) | `ruff --version` |

### Flash, connect, upload and debug

1. Download the stable `RPI_PICO2_W` UF2 from the official MicroPython download
   page. Hold **BOOTSEL** while connecting the Pico 2 W through a data-capable
   USB cable; copy the UF2 onto the `RPI-RP2` volume. The board restarts after
   the copy completes.
2. Connect normally. Run step 30; it checks macOS USB visibility, `/dev/cu.usb*`
   serial access and asks the connected board for its MicroPython version.
3. From `djconnect-pico`, use the isolated tool path for the initial workflow:

   ```sh
   PICO_TOOLS="$HOME/Library/Application Support/DJConnect/pico-tools/bin"
   "$PICO_TOOLS/mpremote" connect auto fs cp main.py :main.py
   "$PICO_TOOLS/mpremote" connect auto reset
   "$PICO_TOOLS/mpremote" connect auto repl
   ```

   Replace `main.py` with the repository-defined entry point when that source
   repository becomes populated. MicroPico provides the equivalent upload,
   serial monitor and REPL actions inside VS Code.
4. For a board that does not appear, first retry with another known data cable
   and direct Mac USB port. Re-enter BOOTSEL mode and confirm that `RPI-RP2`
   mounts before reflashing. If flashing works but no serial device appears,
   rerun step 30 and confirm the installed MicroPython firmware is the stable
   `RPI_PICO2_W` build—not an RP2040/Pico W image.

`picotool` is present for RP2040/RP2350 inspection and recovery work, but does
not replace the MicroPython UF2 flash workflow. Linux and Windows are not
implemented by this increment; the explicit tool choices are portable enough
to assess later without diverging from this canonical macOS experience.

The former `tools/dev_onboarding_macos.sh` and
`tools/dev_onboarding_windows.ps1` paths remain minimal compatibility wrappers.
New documentation and automation must use the canonical `onboarding/` paths.

## Local build output and verification retention (macOS)

The macOS onboarding package keeps local, reproducible build output separate
from Git-tracked source. To reclaim disk space, run the explicit cleanup:

```sh
./onboarding/dev_onboarding_macos.sh --clean-build-output --yes
```

It removes only existing directories that Git confirms are ignored, from the
known local build-output set: Xcode derived-data directories, `.build`, `.pio`,
`DerivedData`, `build`, `bin`, `obj`, `dist` and `release`. It never removes
tracked source, and it preserves a directory when it is not Git-ignored.
`node_modules`, developer configuration and arbitrary untracked files are not
cleanup targets.

Verification artifacts use a separate, conservative retention rule. Install
the user LaunchAgent once to remove only Git-ignored files beneath
`artifacts/verification` after they are older than 14 days:

```sh
./onboarding/dev_onboarding_macos.sh --install-verification-cleanup --yes
```

The task runs daily at 10:00 and also runs once when installed. Its output is
written to `logs/verification-artifact-cleanup.log`. To run the same task
manually, use:

```sh
./scripts/maintenance/cleanup_verification_artifacts.sh --execute
```

Developer readiness remains read-only. Run:

```sh
./scripts/runner/bootstrap_djconnect_macos_host.sh --verify
```

It reports `storage.<repository>.ignored_build_output` for each checked-out
repository, verifies the 14-day retention result, confirms that the LaunchAgent
is loaded, and requires the canonical `djconnect/onboarding/manifest.yml`
package version to be `4.5.0`. It does not delete files or change the host.

The same verification is fail-closed for Engineering Platform readiness. It
requires the declared platform version, the canonical Inbox watcher and
dashboard LaunchAgents running, a healthy loopback dashboard endpoint, writable
local status/report storage and a writable iCloud Inbox transport folder.
If any of these rows reports drift, rerun onboarding step 31 to install and
validate the canonical watcher and dashboard services before accepting Inbox
work. The unattended host-bootstrap `--repair` follows the same path: it saves
the diagnostic result, retires only the two known legacy dashboard LaunchAgents
to local `.engineering` storage, restarts the canonical services, then verifies
them again. It never executes or removes Inbox prompts.

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

If the UAC child process reports a non-zero exit code, open PowerShell 7 **as
Administrator** and run the same bounded migration directly. This preserves
the detailed native `sc.exe`/ACL error in the visible terminal instead of only
reporting the wrapper exit code:

```powershell
Set-Location C:\DJConnect\source\djconnect
pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\runner\bootstrap_windows_arm64_runner.ps1 -MigrateExistingService
```

After a successful migration, verify the account and service state:

```powershell
$service = Get-Service 'actions.runner.*'
Get-CimInstance Win32_Service -Filter "Name='$($service.Name)'" |
  Select-Object Name, StartName, State
```

`StartName` must be `NT SERVICE\<runner-service-name>` and `State` must be
`Running`. Do not change the service to a developer or administrator account,
or create a broad elevated allowlist, as a workaround.

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

For private Engineering Status access from an iPhone through Tailscale, ESET
Cyber Security needs one inbound allow rule for the repository-owned relay:
`<checkout>/.engineering/bin/engineering-dashboard-relay`, TCP port `8765`,
scoped to `100.64.0.0/10` or the trusted Tailscale zone. Keep the firewall
enabled; do not allow LAN, wildcard or public access. The Mac itself uses
`http://127.0.0.1:8765/`; other authorized Tailnet devices use the Mac's
Tailscale IPv4 address on port `8765`.

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
