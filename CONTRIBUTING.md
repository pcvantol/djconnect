# Contributing to DJConnect

Thanks for helping improve DJConnect.

This repository contains the MIT-licensed Home Assistant custom integration for DJConnect. Related DJConnect client and firmware repositories are also MIT-licensed unless their own repository files state otherwise.

Please follow the community standards in `CODE_OF_CONDUCT.md` when
participating in DJConnect project spaces.

Please report suspected security vulnerabilities privately through
`SECURITY.md`, not in public GitHub issues.

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

See `DEVELOPMENT_ENVIRONMENT.md` for the local Docker Home Assistant setup,
install/restart commands and manual UI validation checklist.

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
- After a completed capability, use canonical Workspace Cleanup; squash merges
  require its recorded patch-equivalence verification.
- Preserve the architecture split: Home Assistant owns OAuth, backend playback, Assist/TTS/STT orchestration and OTA; clients and firmware should not receive Spotify credentials.
- Keep active voice routes on Home Assistant Assist/TTS. Do not add direct external AI/STT/TTS APIs to active runtime paths.
- Redact secrets in diagnostics and avoid logging full token/password payloads.
- Update every supported localization when changing config-flow, options-flow, repairs, entity, service or other user-facing text.
- Update docs and examples when behavior, user-facing setup, API contracts or
  release workflow changes. For Ask DJ endpoint changes, also update
  `README.md`, `HANDOFF.md`, `SYNC_PROMPTS.md`, `VOICE_INTENT_DATA.md` and
  `examples/djconnect.postman_collection.json` when the request/response shape
  changes.
- Add or update tests for code, contract and UI-string changes.

## Localization Policy

DJConnect supports these Home Assistant UI languages in this repository: `en`,
`nl`, `de`, `fr` and `es`.

Localized Home Assistant strings live in:

- `custom_components/djconnect/strings.json`: base integration strings and the
  canonical key structure for config flows, options flows, entities, issues and
  repairs.
- `custom_components/djconnect/translations/en.json`,
  `custom_components/djconnect/translations/nl.json`,
  `custom_components/djconnect/translations/de.json`,
  `custom_components/djconnect/translations/fr.json` and
  `custom_components/djconnect/translations/es.json`: translated copies of the
  same key structure.
- `custom_components/djconnect/services.yaml`: Home Assistant service/action
  names, descriptions, fields and examples.
- Runtime text that is returned outside Home Assistant's localization renderer,
  such as OAuth callback pages and Ask DJ help text, must use centralized helper
  mappings with the same five language codes.

All new user-facing strings must be added for `en`, `nl`, `de`, `fr` and `es`
in the same change. Prefer centralized string keys, placeholders/format strings
and shared error mappings over repeating near-identical prose in code. Run
`python3 -m unittest tests.test_translations` or `pytest tests/test_translations.py`
after touching localization files; missing keys in any supported translation
file must fail tests and CI.

Do not localize machine-readable values. Keep protocol values, JSON keys,
endpoint paths, `client_type` values, tokens, entity ids, service ids and
machine-readable error codes stable and literal. Examples include
`/api/djconnect/v1/command`, `client_type`, `esp32`, `ios`, `macos`, `watchos`,
`raspberry_pi`, `windows`, `djci_`, `sensor.djconnect_*`,
`djconnect.ask_dj`, `not_configured` and `version_mismatch`.

Generic help, onboarding and examples must not use real artist, song, album or
playlist names. Use placeholders such as `[artist]`, `[song]`, `[artiest]`,
`[nummer]`, `[playlist]` and `[genre]`.

The Spotify trademark/non-affiliation disclaimer must remain present in every
supported language wherever DJConnect describes Spotify-backed setup or backend
selection. Preserve the legal meaning: Spotify is a trademark of Spotify AB, and
DJConnect is not affiliated with, endorsed by, or sponsored by Spotify AB.

## AI-Assisted Development

DJConnect is developed and maintained with AI-assisted and agentic engineering
workflows, including Codex. AI assistance may be used for code changes,
documentation, tests, release preparation and cross-repo consistency checks.

All accepted changes remain maintainer-reviewed. Contributors are responsible
for ensuring their changes are correct, testable, license-compatible and free of
secrets or private data. Do not include tokens, passwords, private URLs,
personal data or proprietary third-party material in prompts, issues, logs,
screenshots or test fixtures.

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

Release changes should keep `README.md`, `CHANGELOG.md`, `AGENTS.md`, `HANDOFF.md`, `TODO.md`, `ISSUES.md`, `SYNC_PROMPTS.md`, `PRODUCT_ROADMAP.md`, `TECHNICAL_DESIGN_DECISIONS.md`, `CHAT_BOOTSTRAP.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`, `info.md` and relevant `examples/` files aligned when affected.

As a review/QA step for every release or client-contract change, check each
DJConnect repo against the `DJ Announcement Output Sync` section in
`SYNC_PROMPTS.md`. Confirm announcement output modes, optional HA speaker
handling, nested `announcement.audio_url`, push-safe hints and product/docs
wording still match the contract for that repo.

## Licensing

By contributing to this repository, you agree that your contribution is licensed under the MIT License in `LICENSE`.

Spotify is a trademark of Spotify AB. DJConnect is not affiliated with, endorsed by, or sponsored by Spotify AB.
