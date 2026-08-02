# DJConnect Developer Onboarding Changelog

## 4.4.0 — 2026-08-02

- Document report-bound Engineering Platform runtime provenance: Runtime
  Provider, reported AI Model, reported Reasoning and Configuration Profiles,
  and detected Codex CLI Version.
- Clarify that unavailable runtime metadata is shown as `not reported` and
  cannot be inferred from the current dashboard configuration or another run.
- Require the matching `4.4.0` canonical onboarding package during macOS host
  bootstrap verification and recovery.

## 4.3.0 — 2026-08-01

- Add the private Engineering Status Tailnet relay recovery guidance, including
  the scoped ESET firewall rule required for iPhone dashboard access.
- Preserve the immutable `4.2.0` distribution artifact; this release carries
  all onboarding-content changes introduced after that version.

## 4.2.0 — 2026-08-01

- Align the canonical onboarding package, developer-machine readiness contract
  and bootstrap requirement with the Engineering Platform 1.5 operational
  hardening update.
- Document the local-only Engineering Platform evidence model, including the
  iCloud Inbox transport boundary, local reports and component logging.
- Require the Engineering Platform watcher, dashboard, loopback health check,
  local status/report storage and iCloud Inbox transport to be healthy during
  development-host readiness verification.
- Make host-bootstrap repair diagnose and restart only the canonical local
  Engineering Platform services when those readiness checks report drift.

## 4.1.0 — 2026-07-30

- Add the macOS-first Raspberry Pi Pico 2 W MicroPython profile to canonical
  onboarding: isolated `mpremote`, `micropython-stubber` and Ruff tooling;
  Homebrew `picotool`; and required VS Code MicroPico/Python/Pylance extensions.
- Add a deterministic read-only Pico readiness report with PASS/WARNING/FAIL
  checks for host tools, versions, PATH, USB visibility, serial access and a
  connected board's MicroPython implementation.
- Add Pico to the shared macOS desired-state formula and runner-profile model.

## 4.0.0 — 2026-07-28

- Add explicit, opt-in cleanup of ignored local build output and a read-only
  per-repository storage report to macOS developer readiness.
- Install the ignored verification-artifact retention task for 10:00 daily.

## 3.3.1 — 2026-07-17

- Fix the Windows virtual-service-account migration: configure its `obj=`
  identity without a `password=` argument, which Service Control Manager
  rejects for virtual accounts; document direct elevated recovery/verification
  when the UAC wrapper reports a failure.
- Make the scheduled macOS maintenance task the single tooling-currency owner:
  it upgrades every installed Homebrew formula and cask, including ngrok,
  while retaining Tailscale's verified signed-app auto-update path.
- Add the explicit Windows onboarding step that elevates only the migration of
  an existing GitHub Actions runner to its dedicated passwordless virtual
  service identity.
- Make the Windows runner bootstrap use a per-service `NT SERVICE` account,
  scoped filesystem ACLs and removal of the temporary `NETWORK SERVICE` grant.
- Document that service-account hardening does not create an interactive GUI
  session; MAUI/WinUI smoke remains a separate interactive-relay concern.

## 3.3.0 — 2026-07-16

- Add a macOS-only, explicit machine-transfer export/import utility for
  encrypted transfer of selected DJConnect developer assets.
- Exclude Keychain, browser and CLI credential stores; require interactive
  service reauthentication on the replacement machine.
- Add a read-only macOS network and firewall assessment for known outbound
  dependencies, active TCP endpoints, local listeners and Docker-published
  ports.
- Add portable Home Assistant development-lab configuration and Compose
  baselines, rendered only for missing local files without overwriting existing
  runtime configuration.

- Align the package release version with DJConnect Platform Release 3.3.0 for
  operator clarity.
- Record that the alignment is descriptive only: no platform runtime,
  artifact, desired-state or compatibility dependency is introduced.

## 1.1.4 — 2026-07-16

- Add executable package-contract coverage for independent desired-state
  manifest versioning and fail-closed compatibility outcomes.

## 1.1.3 — 2026-07-16

- Document independent desired-state manifest versioning and the required
  `minimum_tool_version` apply-compatibility contract.

## 1.1.2 — 2026-07-16

- Compare the running macOS onboarding package with the local versioned
  distribution catalog before execution.
- Require explicit confirmation before continuing with an older package and
  record the decision in the Markdown onboarding report.

## 1.1.1 — 2026-07-16

- Require the macOS preflight to verify that no patch update is available for
  the installed macOS major version.
- Fail preflight when the Software Update scan cannot establish that security
  patch currency, while leaving major macOS upgrades optional.

## 1.1.0 — 2026-07-16

- Package the macOS and Windows developer-onboarding scripts with deterministic
  distributable artifacts and Linux CI verification.
