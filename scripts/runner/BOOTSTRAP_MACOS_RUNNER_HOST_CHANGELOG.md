# macOS Runner Host Recovery Bootstrap changelog

This changelog covers only
`scripts/runner/bootstrap_macos_runner_host.sh`. It uses
[Semantic Versioning](https://semver.org/) and records user-visible behaviour,
compatibility and security changes to the recovery bootstrap independently of
the DJConnect product release.

## [Unreleased]

- Add configurable `--log-level` output filtering with `debug`, `verbose`,
  `info`, `warning` and `error` levels.

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
