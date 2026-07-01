DJConnect localization guidance:
- Any new user-facing Home Assistant integration string must be added in the same change for all supported languages: `en`, `nl`, `de`, `fr` and `es`.
- Localized Home Assistant strings live in `strings.json`, `translations/en.json`, `translations/nl.json`, `translations/de.json`, `translations/fr.json`, `translations/es.json` and `services.yaml`; runtime text outside HA's localization renderer, such as OAuth result pages and Ask DJ help text, must use centralized per-language helper mappings.
- Prefer centralized string keys, placeholders/format strings and shared error mapping for repeated copy such as pairing, OAuth, stale auth, client type mismatch and unsupported setup messages.
- Preserve technical identifiers, protocol values, JSON keys, service names, entity ids, endpoint paths, `client_type` values, tokens and machine-readable error codes. Do not localize values such as `/api/djconnect/command`, `esp32`, `ios`, `macos`, `watchos`, `raspberry_pi`, `windows`, `djci_`, `not_configured` or `version_mismatch`.
- Preserve the Spotify trademark/non-affiliation disclaimer in every supported language wherever Spotify setup or backend selection is described.
- Keep Ask DJ help examples generic with placeholders such as `[artiest]`/`[artist]`, `[nummer]`/`[song]`, `[playlist]` and `[genre]`; do not use real artist or song names in help examples.
