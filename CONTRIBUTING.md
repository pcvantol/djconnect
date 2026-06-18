# Contributing to DJConnect

Thanks for helping improve DJConnect.

This repository contains the MIT-licensed Home Assistant custom integration for DJConnect. Related DJConnect client and firmware repositories are also MIT-licensed unless their own repository files state otherwise.

## What Belongs Here

Good contributions for this repository include:

- Home Assistant integration fixes and features under `custom_components/djconnect/`
- HACS, config-flow, options-flow, repairs, diagnostics and entity improvements
- Documentation, translations, examples and release workflow updates
- Tests under `tests/`
- Brand assets that support the Home Assistant integration

Please do not add firmware source, device secrets, OAuth tokens, WiFi passwords or private release artifacts to this repository.

## Development Setup

Use a normal Python environment. The lightweight test suite stubs Home Assistant where possible, so a full Home Assistant checkout is not required for most changes.

Run tests with:

```bash
python3 -m unittest discover -s tests
```

For targeted work, run the relevant test module, for example:

```bash
python3 -m unittest tests.test_config_flow_helpers tests.test_translations
```

## Contribution Guidelines

- Keep changes focused and scoped to the requested behavior.
- Preserve the architecture split: Home Assistant owns OAuth, backend playback, Assist/TTS/STT orchestration and OTA; clients and firmware should not receive Spotify credentials.
- Keep active voice routes on Home Assistant Assist/TTS. Do not add direct external AI/STT/TTS APIs to active runtime paths.
- Redact secrets in diagnostics and avoid logging full token/password payloads.
- Update Dutch and English translations when changing config-flow, options-flow, repairs, entity or service text.
- Update docs when behavior, user-facing setup, API contracts or release workflow changes.
- Add or update tests for code, contract and UI-string changes.

## Pull Requests

Before opening a PR:

1. Run `python3 -m unittest discover -s tests`.
2. Check `git status` and make sure only intended files are changed.
3. Include a clear summary of the behavior change.
4. Mention any tests you ran and any checks you could not run.

For larger changes, include the reason for the design choice and any compatibility impact for ESP32, iOS, macOS or Raspberry Pi clients.

## Releases

Maintainer releases use:

```bash
./release.sh X.Y.Z
```

Release changes should keep `README.md`, `CHANGELOG.md`, `AGENTS.md`, `HANDOFF.md`, `TODO.md`, `ISSUES.md`, `SYNC_PROMPTS.md`, `PRODUCT_ROADMAP.md`, `TECHNICAL_DESIGN_DECISIONS.md`, `info.md` and relevant `examples/` files aligned when affected.

## Licensing

By contributing to this repository, you agree that your contribution is licensed under the MIT License in `LICENSE`.

Spotify is a trademark of Spotify AB. DJConnect is not affiliated with, endorsed by, or sponsored by Spotify AB.
