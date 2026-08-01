# macOS Development Host Bootstrap changelog

This changelog covers only
`scripts/runner/bootstrap_djconnect_macos_host.sh`. It uses
[Semantic Versioning](https://semver.org/) and records user-visible behaviour,
compatibility and security changes to the development-host bootstrap independently of
the DJConnect product release.

## [2.0.14] - 2026-08-01

- Require the immutable canonical developer-onboarding package `4.3.0` before
  recovery invokes it.

## [2.0.13] - 2026-08-01

- Make unattended repair analyze Engineering Platform readiness, archive only
  known legacy dashboard LaunchAgents locally, restart canonical watcher and
  dashboard services, then verify their health again.

## [2.0.12] - 2026-08-01

- Add fail-closed Engineering Platform readiness verification for the canonical
  watcher and dashboard services, loopback health endpoint, platform version,
  local status/report storage and iCloud Inbox transport.

## [2.0.11] - 2026-08-01

- Fail closed before recovery invokes developer onboarding unless the canonical
  `djconnect/onboarding/manifest.yml` declares package version `4.2.0`.

## [2.0.10] - 2026-07-30

- Fail closed before recovery invokes developer onboarding unless the canonical
  `djconnect/onboarding/manifest.yml` declares package version `4.1.0`.

## [2.0.8] - 2026-07-28

- Report ignored local build-output storage for each checked-out DJConnect
  repository and verify the daily ignored verification-artifact retention task.
- Handle an empty optional-cask list under strict shell mode.

## [2.0.6] - 2026-07-17

- Make scheduled maintenance the single Homebrew tooling-currency owner:
  refresh every installed formula and cask, including ngrok.
- Keep Tailscale on its signed-app auto-update channel and enable that setting
  idempotently from macOS onboarding.

## [2.0.5] - 2026-07-16

- An unattended repair no longer synchronizes the active host-bootstrap source
  checkout to `main` while it is executing. This preserves the loaded
  desired-state manifest and package modules through final verification.

## [2.0.4] - 2026-07-16

- Recognize a valid `/Applications/Parallels Desktop.app` bundle as the
  required Parallels Desktop installation, regardless of whether it was
  installed directly or through Homebrew. Verification and unattended repair
  no longer confuse the package-manager receipt with the application itself.

## [2.0.3] - 2026-07-16

- Treat a functional user-local PlatformIO Core installation at
  `~/.platformio/penv/bin/pio` as conformant firmware tooling during
  desired-state verification. Homebrew remains a supported installation path
  but is no longer incorrectly required when PlatformIO is installed by the
  VS Code extension or PlatformIO's own Python environment.

## [2.0.2] - 2026-07-16

- Add Tailscale installation and qualified private-network configuration to
  the macOS developer-onboarding and desired-state verification flow.
- Verify only installation, authenticated runtime state and non-secret network
  preferences; tailnet identity, node addresses and all authentication keys
  remain machine-local and are never emitted.

## [2.0.1] - 2026-07-16

- Add the qualified persistent ngrok Home Assistant tunnel to the macOS
  desired-state manifest and verify its owner-only configuration permissions,
  non-empty locally held authtoken, LaunchAgent and loopback tunnel binding.
- Keep the authtoken outside Git and redact its value from all verification
  output.

## [2.0.0] - 2026-07-16

- Rename the public CLI, package, desired-state manifest and documentation to
  describe the full macOS development-host bootstrap scope rather than only
  runner recovery.
- Retain the tool's independent semantic-version track; this breaking public
  CLI rename advances that tool to version `2.0.0`.

## [1.3.0] - 2026-07-16

- Version the declarative macOS desired-state manifest as `3.3.0`, aligned to
  the active DJConnect platform release major/minor line, and enforce its
  declared minimum compatible bootstrap version for recovery execution;
  verification reports incompatibility without mutating the host.
- Record the desired-state version, bootstrap version and compatibility verdict
  in verification output and recovery reports.
- Make Parallels Desktop a required desired-state cask rather than an optional
  platform component.
- Declare the Windows ARM64 runner as an external Windows profile and verify it
  through GitHub as online with its required labels. The macOS bootstrap never
  attempts to install or register that Windows runner.

## [1.2.0] - 2026-07-16

- Use the canonical `onboarding/` package for macOS developer-workstation,
  internal Home Assistant test-environment and post-recovery verification work.

## [1.1.0] - 2026-07-16

- Refactor the development-host bootstrap into a package of bounded Bash modules behind
  the then-stable thin CLI entry point.
- Add a canonical package manifest with semantic versions for the full package
  and each module, validated before recovery actions begin.
- Bind the stable entry point and every package module to SHA-256 values and a
  deterministic aggregate package checksum, verified before recovery actions.
- Add a dedicated desired-state phase for the internal Home Assistant Docker
  test environment, including container-running and local-URL verification.
- Add configurable `--log-level` output filtering with `debug`, `verbose`,
  `info`, `warning` and `error` levels.
- Mark headless, parallel-safe runner-registration and read-only Apple audit
  phases; expose the metadata through `--list-phases` and recovery reports.
- Execute those marked phases in CPU-bounded batches; default to half of the
  detected CPU cores and retain per-phase transcript/report evidence.
- Require an interactive or explicit recorded confirmation when RAM meets the
  hard minimum but is below the recommended recovery capacity.
- Add `--repair`: one unattended desired-state repair pass with baseline and
  post-repair verification plus explicit remaining manual requirements.
- Refuse recovery output and resume checkpoint paths inside the Git working
  tree, with `.gitignore` patterns as a second line of defence.
- Group execution and evidence into stable installation sections, with visual
  console boundaries and a report summary of completed and attention-needed
  areas.
- Add indicative console and report progress percentages for recovery phases
  and the unattended repair lifecycle.
- Add a least-privilege audit for local write exposure, runner ownership,
  sudo breadth and selected GitHub runner-administration access.
- Audit local Apple certificate and provisioning-profile expiry, while
  explicitly reporting opaque client-token expiry as unverified without
  reading token values.
- After a reboot gate, install a one-shot user LaunchAgent that opens Terminal
  and starts the protected, non-secret recovery continuation after the next
  graphical login.

## [1.0.0] - 2026-07-16

Initial stable release of the declarative macOS development-host bootstrap.

- Declares and verifies the Apple-Silicon development-host desired
  state.
- Reconciles developer tooling, runner profiles, maintenance, optional
  Parallels and locally supplied Apple signing material.
- Supports dry-run, verify, retry, intentional skip, idempotent force and
  reboot-resume modes.
- Produces redacted transcript and Markdown evidence reports without exposing
  credentials or registration tokens.
- Adds `--version` for deterministic automation and support evidence.
