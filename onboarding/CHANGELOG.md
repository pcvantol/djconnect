# DJConnect Developer Onboarding Changelog

## 1.1.1 — 2026-07-16

- Require the macOS preflight to verify that no patch update is available for
  the installed macOS major version.
- Fail preflight when the Software Update scan cannot establish that security
  patch currency, while leaving major macOS upgrades optional.

## 1.1.0 — 2026-07-16

- Package the macOS and Windows developer-onboarding scripts with deterministic
  distributable artifacts and Linux CI verification.
