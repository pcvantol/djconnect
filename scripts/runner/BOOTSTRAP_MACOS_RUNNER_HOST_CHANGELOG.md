# macOS Runner Host Recovery Bootstrap changelog

This changelog covers only
`scripts/runner/bootstrap_macos_runner_host.sh`. It uses
[Semantic Versioning](https://semver.org/) and records user-visible behaviour,
compatibility and security changes to the recovery bootstrap independently of
the DJConnect product release.

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

- Refactor the recovery bootstrap into a package of bounded Bash modules behind
  the unchanged thin `bootstrap_macos_runner_host.sh` CLI entry point.
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

Initial stable release of the declarative macOS recovery bootstrap.

- Declares and verifies the Apple-Silicon development and runner-host desired
  state.
- Reconciles developer tooling, runner profiles, maintenance, optional
  Parallels and locally supplied Apple signing material.
- Supports dry-run, verify, retry, intentional skip, idempotent force and
  reboot-resume modes.
- Produces redacted transcript and Markdown evidence reports without exposing
  credentials or registration tokens.
- Adds `--version` for deterministic automation and support evidence.
