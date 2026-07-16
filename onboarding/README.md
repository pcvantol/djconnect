# DJConnect developer onboarding

This directory is the canonical, versioned onboarding package for a DJConnect
developer workstation. It owns the macOS and Windows onboarding scripts, their
contract tests and package documentation.

## Entry points

- macOS: `./onboarding/dev_onboarding_macos.sh`
- Windows: `pwsh -File .\onboarding\dev_onboarding_windows.ps1`

The former `tools/dev_onboarding_macos.sh` and
`tools/dev_onboarding_windows.ps1` paths remain minimal compatibility wrappers.
New documentation and automation must use the canonical `onboarding/` paths.

The macOS package reconciles Docker Desktop and the persistent local Home
Assistant Compose environment. The Home Assistant service is available at
`http://localhost:8123` after its container is healthy. The Windows package
uses the macOS-hosted Home Assistant environment rather than Docker Desktop in
the Windows ARM VM.

## Tests

Run the package contract tests from the repository root:

```sh
python3 -m unittest onboarding.tests.test_onboarding_scripts
```

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
compatibility wrappers. Update it together with any relocation or package
surface change.
