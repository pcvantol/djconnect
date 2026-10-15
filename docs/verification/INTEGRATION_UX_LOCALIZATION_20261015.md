# Integration UX localization correction — 2026-10-15

Owner request: inspect the integration UX and fill missing translations, while
preserving the existing Core transport writer and WIP. This is a presentation
correction, not a new product capability or an installation approval.

## Findings and correction

- All five catalogues already contain the profile-management form labels and
  translated profile/privacy/action selectors from the reported screenshot.
  This source fact does not establish which build the installed frontend loads.
- Added the missing `missing_spotify_client_id` Repair title and explanation to
  the canonical English source and en/nl/de/fr/es.
- Added Home Assistant `services` translations for all 50 declared actions and
  their 186 fields: action names/descriptions and field names/help. The YAML
  schemas, selectors, actions, permission boundaries and defaults stay intact.
- A synchronous keyed `flow_labels.py` catalogue supplies all five languages to
  setup/Bluetooth/options choices, default/no-speaker/no-address placeholders,
  stable/beta channel labels and token-management choices. Region families are
  normalized; unsupported/missing language falls back to English. No network,
  storage or product actions occur during resolution. User-assigned device,
  profile and entity names are preserved.
- Corrected English service examples that offered Windows as a current client;
  legacy Windows protocol recognition remains unchanged.
- Corrected playback-command help in every language: `play:false` is not a
  general dry run and cannot suppress an explicit `play` command. The separate
  text-command test parameter retains its own meaning. No playback code changed.

## Qualification

Separate local commits: `7997934d284b5ec47f8260d5059d42bcc5b5cafc`,
`8b33d72d687db1cd266765c4aad662398207e1b7`,
`221a6fbd48ab6870a351268c858abda4c80c5c3a`.

The targeted translation/config-flow/announcement suite passes 156 tests and
159 subtests. New gates enumerate every service and field, discover literal
Repair keys from source, enforce retired-client wording, distinguish playback
help from text-command testing, and exercise real form builders for all five
languages and regional/English fallback. Ruff and diff whitespace checks pass.
The full subsequent regression suite passes 1,913 tests, with seven existing
skips. Tests use the repository's lightweight HA stubs where applicable; they
are not installed frontend evidence.

Two independent read-only reviewers approve the exact cumulative translation
range `03bcabf2..221a6fbd`. The editorial review initially blocked the Windows
examples and unsafe dry-run claim; both were fixed and re-reviewed. Technical
review confirms unchanged protocol, authorization, secret selectors and storage.
These approvals cover localization, not the other pending transport changes.

## Acceptance boundary

Source-level catalogue completeness and form wiring are qualified. Actual
Home Assistant frontend layout, cache refresh and localized rendering on HA-dev
or HA-prod remain NOT_RUN. Nothing was installed, restarted or deployed. Final
publication/main reconciliation belongs to the current protected delivery;
these local commits alone do not establish published or installed availability.
