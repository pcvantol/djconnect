# DJConnect Developer Onboarding Changelog

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
