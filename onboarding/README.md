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
compatibility wrappers. `CHANGELOG.md` records package releases. Update both
together with any package-surface change.
