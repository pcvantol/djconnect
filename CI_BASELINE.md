# DJConnect CI baseline

The Home Assistant CI workflow and security rules live in this repository.
Reusable cross-repository CI variants live in `djconnect-music-dj/djconnect-shared-workflows`.
The examples below pin reviewed immutable commits; qualify changes to those pins
for the consuming repository before updating them.

## Home Assistant integration repositories

Use this in the Core HACS/Home Assistant repository, where the called workflow
exists in the same commit:

```yaml
name: Validate

on:
  push:
  pull_request:

permissions:
  contents: read

jobs:
  validate:
    uses: ./.github/workflows/djconnect-ha-integration-ci.yml
    with:
      test-command: python -m unittest discover -s tests
```

This runs:

- an advisory dependency/tool audit that reports available updates without
  failing the workflow by default;
- the repository test command;
- Ruff against `custom_components/djconnect` and `tests`;
- Bandit against `custom_components/djconnect`;
- hassfest;
- the HACS validation action.

## Python client or service repositories

Use this for Python-only clients or services, such as Raspberry Pi tooling:

```yaml
name: Validate

on:
  push:
  pull_request:

permissions:
  contents: read

jobs:
  python:
    uses: djconnect-music-dj/djconnect-shared-workflows/.github/workflows/djconnect-python-5f12.yml@4bd9731a6fe7bb50c932e36635eb3ff5c5372687
    with:
      source-path: src
      test-path: tests
      test-command: python -m unittest discover -s tests
```

## CodeQL

Use CodeQL in each source repository with the language that matches that repo:

```yaml
name: CodeQL

on:
  push:
  pull_request:
  schedule:
    - cron: "24 4 * * 1"

permissions:
  contents: read
  security-events: write

jobs:
  codeql:
    uses: djconnect-music-dj/djconnect-shared-workflows/.github/workflows/djconnect-codeql-191.yml@2a1c6fd2841b08630aee01402850f56840b50f70
    with:
      languages: python
```

Common language values:

- `python` for the Home Assistant integration, Raspberry Pi client, and Python APIs;
- `javascript-typescript` for web or TypeScript services;
- `c-cpp` for ESP firmware source.

## Semgrep

DJConnect custom Semgrep rules live in `.semgrep/djconnect-security.yml`.
Repositories can use the shared workflow without copying the ruleset:

```yaml
name: Semgrep

on:
  pull_request:
  workflow_dispatch:

permissions:
  contents: read
  security-events: write

jobs:
  semgrep:
    uses: djconnect-music-dj/djconnect-shared-workflows/.github/workflows/djconnect-semgrep-191.yml@2a1c6fd2841b08630aee01402850f56840b50f70
    with:
      continue-on-error: true
      config: https://raw.githubusercontent.com/djconnect-music-dj/djconnect/cb2958e0b61b27e1eb67a4a17d0ea3454b631451/.semgrep/djconnect-security.yml
```

The initial rules focus on DJConnect-specific mistakes:

- token, password, and secret values printed or logged;
- `subprocess` calls using `shell=True`;
- Ask DJ image responses that appear to use direct external image URLs instead
  of the DJConnect image proxy.

## Repository profile guidance

Recommended baseline per repository:

- `djconnect`: Home Assistant reusable workflow, CodeQL `python`, Semgrep.
- `djconnect-app`: Swift tests and unsigned Apple builds, release-script dry run,
  and the repository's configured security checks.
- `djconnect-esp32`: PlatformIO build, release-script dry run, CodeQL `c-cpp`,
  Semgrep or secret scan.
- `djconnect-firmware`: manifest JSON validation, SHA256 and asset naming
  checks, secret scan, no source build.
- `djconnect-pi`: Python reusable workflow, CodeQL `python`, Semgrep.
- `djconnect-api`: language-specific tests/lint, CodeQL, Semgrep, API contract
  checks.
- `djconnect-website`: build, lint/typecheck, link checks, Playwright smoke
  tests, CodeQL/Semgrep.
- `djconnect-windows`: Windows runner build/tests, CodeQL for the app language,
  release artifact checks.

Keep strict checks phased. Unit tests, build checks, HACS/hassfest, CodeQL,
Ruff, and medium/high Bandit findings should block once the initial baseline is
clean. Semgrep defaults to advisory while the first GitHub runs are reviewed;
make it blocking only after the shared rules are clean for the repository. MyPy
can also start as advisory if an existing repository needs cleanup before it
becomes required.

## Dependency and tool updates

Every shared Python/Home Assistant CI workflow includes an advisory
`dependency-audit` job. It installs the repository-declared runtime dependencies
where possible, reports outdated Python packages, and prints the newest visible
Ruff and Bandit versions. The job is `continue-on-error` because new upstream
versions are a maintenance signal, not an automatic release blocker.

Release work must still review this output. Apply safe third-party package,
framework and tool updates before publishing, update lockfiles/manifests and
license/dependency documentation in the same change, or record the skipped
upgrade and reason in `HANDOFF.md`.
