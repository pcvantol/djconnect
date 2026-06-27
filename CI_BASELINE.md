# DJConnect CI baseline

This repository is the source of truth for shared DJConnect CI workflows and
security rules. Other DJConnect repositories can call the reusable workflows in
`.github/workflows/` from this repository instead of duplicating the same
validation logic.

## Home Assistant integration repositories

Use this for the HACS/Home Assistant integration repository:

```yaml
name: Validate

on:
  push:
  pull_request:

permissions:
  contents: read

jobs:
  validate:
    uses: pcvantol/djconnect/.github/workflows/djconnect-ha-integration-ci.yml@main
    with:
      test-command: python -m unittest discover -s tests
```

This runs:

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
    uses: pcvantol/djconnect/.github/workflows/djconnect-python-ci.yml@main
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

jobs:
  codeql:
    uses: pcvantol/djconnect/.github/workflows/djconnect-codeql-ci.yml@main
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

jobs:
  semgrep:
    uses: pcvantol/djconnect/.github/workflows/djconnect-semgrep-ci.yml@main
    with:
      continue-on-error: true
```

The initial rules focus on DJConnect-specific mistakes:

- token, password, and secret values printed or logged;
- `subprocess` calls using `shell=True`;
- Ask DJ image responses that appear to use direct external image URLs instead
  of the DJConnect image proxy.

## Repository profile guidance

Recommended baseline per repository:

- `djconnect`: Home Assistant reusable workflow, CodeQL `python`, Semgrep.
- `djconnect-app`: PlatformIO build, release-script dry run, CodeQL `c-cpp`,
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
