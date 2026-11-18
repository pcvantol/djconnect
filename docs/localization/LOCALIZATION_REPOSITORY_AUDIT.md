# DJConnect Localization Repository Audit

Status: Initial audit
Date: 2026-07-10
Canonical standard: `LOCALIZATION_STANDARD.md`

## Scope

This audit records observed localization state across the local DJConnect
checkouts. It does not claim full translation quality or UI completeness unless
native tests and rendered UI evidence exist.

Canonical required locales:

```text
en
nl
de
fr
es
```

## Summary

| Repository | Mechanism | Current locale signal | Status |
| --- | --- | --- | --- |
| `pcvantol/djconnect` | Home Assistant `strings.json` plus `translations/*.json` | `en`, `nl`, `de`, `fr`, `es` present | Partial: catalogs present; CI gate should be explicit |
| `pcvantol/djconnect-app` | Apple `.lproj` catalogs | Source `.lproj` folders for all five locales present | Partial: source catalogs present; rendered UI parity needs evidence |
| `pcvantol/djconnect-windows` | .NET `.resx` | neutral plus `nl`, `de`, `fr`, `es` present | Partial: catalogs present; Catalyst/native Windows smoke evidence needed |
| `pcvantol/djconnect-pi` | Python translation table plus QML key tests | `SUPPORTED_LANGUAGES` tested against translation table | Stronger local validation; rendered Pi screenshots still needed |
| `pcvantol/djconnect-esp32` | C++/web portal embedded i18n table | `en`, `nl`, `de`, `fr`, `es` tested by native script | Partial: portal validation present; constrained display coverage unclear |
| `pcvantol/djconnect-api` | TypeScript messages | No dedicated locale catalogs observed | Gap: user-facing API messages need mapping/audit |
| `pcvantol/djconnect-website` | Website pages and release-note JSON | No dedicated locale routes/catalog observed | Gap: public website localization not implemented or not discoverable |
| `pcvantol/djconnect-firmware` | Release manifest | No user-facing locale catalog observed | Distribution surface; release copy policy needed |
| `pcvantol/djconnect-app-releases` | Release artifacts | No AGENTS/localization files observed | Distribution surface; release copy policy needed |
| `pcvantol/djconnect-pi-releases` | Release artifacts | No AGENTS/localization files observed | Distribution surface; release copy policy needed |

## `pcvantol/djconnect`

- Localization mechanism: Home Assistant integration catalogs:
  `custom_components/djconnect/strings.json` and
  `custom_components/djconnect/translations/*.json`.
- Locales currently present: `en`, `nl`, `de`, `fr`, `es`.
- Completeness status: catalogs exist for all five required locales; key and
  placeholder parity must remain an explicit release gate.
- Hardcoded string risk: medium. Python API handlers, services and repairs can
  still expose user-facing messages outside catalogs if not reviewed.
- Placeholder-validation status: requires explicit CI check if not already
  covered by tests.
- CI status: multiple workflows exist; localization gate should be visible in
  HA validation.
- User-facing surfaces: config flow, options flow, repairs, diagnostics,
  services, entity names, API error display messages and legal notices.
- Required actions: add/confirm localization parity tests for all HA catalogs;
  review API/display errors for machine-code versus localized-message split.
- Blockers: none observed for catalog presence.
- Recommended PR: add a HA localization validation test that fails on missing
  locale, key mismatch, placeholder mismatch and raw key exposure in fixtures.

## `pcvantol/djconnect-app`

- Localization mechanism: Apple `.lproj` catalogs for app targets, widgets and
  shared `DJConnectCore` resources.
- Locales currently present: source folders for `en`, `nl`, `de`, `fr`, `es`
  under app targets and `Sources/DJConnectCore/Resources/Localization`.
- Completeness status: all five locale families are represented; source key
  parity and UI rendering completeness were not proven by this audit.
- Hardcoded string risk: medium to high until SwiftUI views and accessibility
  labels are scanned against localization usage.
- Placeholder-validation status: not confirmed from the cross-repo scan.
- CI status: CI and release workflows exist; localization parity should be a
  named check.
- User-facing surfaces: iOS, macOS, watchOS, widgets, onboarding, pairing, Ask
  DJ, Music DNA, private-session and profile UI, accessibility labels, store
  metadata and screenshots.
- Required actions: run native Apple catalog validation; scan Swift/SwiftUI for
  hardcoded user-facing strings; add snapshot/smoke coverage in all five
  locales.
- Blockers: no writable access from this HA-repo task; implement in app repo.
- Recommended PR: add a localization test target that validates `.lproj` key
  parity and placeholders for iOS, macOS and watchOS resources.

## `pcvantol/djconnect-windows`

- Localization mechanism: .NET resource files under
  `src/DJConnect.Windows/Resources`.
- Locales currently present: `Strings.resx` plus `Strings.nl.resx`,
  `Strings.de.resx`, `Strings.fr.resx`, `Strings.es.resx`.
- Completeness status: all five locale families are represented if neutral
  resources are treated as English; key parity was not proven in this audit.
- Hardcoded string risk: medium until XAML/C# UI is scanned.
- Placeholder-validation status: not confirmed.
- CI status: CI, CodeQL and Semgrep workflows exist; localization gate should
  be named.
- User-facing surfaces: native Windows UI, Catalyst/debug build if used for
  development, pairing, Ask DJ, Music DNA, profile/privacy UI, errors and
  installer/update copy.
- Required actions: validate `.resx` key parity and placeholders; smoke-test
  macOS Catalyst/debug and native Windows ARM64 under Windows 11 on ARM.
- Blockers: native Windows ARM64 execution requires a Windows 11 on ARM
  environment.
- Recommended PR: add `.resx` parity tests and capture representative UI
  screenshots for all five locales.

## `pcvantol/djconnect-pi`

- Localization mechanism: Python `djconnect_pi.i18n` translation table with QML
  and web portal key usage.
- Locales currently present: `SUPPORTED_LANGUAGES` is tested against
  translation keys; tests normalize regional variants to canonical languages.
- Completeness status: local tests enforce same keys and placeholder matching
  against English.
- Hardcoded string risk: medium. QML and Python tests cover known key calls, but
  broader UI string scanning and rendered overflow checks are still needed.
- Placeholder-validation status: covered in `tests/test_i18n.py`.
- CI status: validation workflow exists.
- User-facing surfaces: Pi touchscreen/QML UI, local web portal, pairing,
  settings, diagnostics, update UI and install notes.
- Required actions: add SSH-driven smoke tests for locale switching,
  persistence, missing-key detection and screenshot overflow.
- Blockers: hardware or remote Pi access needed for rendered validation.
- Recommended PR: extend Pi verification harness to switch all five locales and
  capture sanitized screenshots.

## `pcvantol/djconnect-esp32`

- Localization mechanism: C++/web portal embedded table in `src/WebPortal.cpp`
  plus native validation in `test/native/test_webportal_i18n.py`.
- Locales currently present: test requires `en`, `nl`, `de`, `fr`, `es`.
- Completeness status: portal table validates language option order, unknown
  keys and required overrides; `de`, `fr` and `es` may intentionally merge over
  English defaults for compactness.
- Hardcoded string risk: medium to high for firmware screens, serial-visible
  user messages and constrained display text outside the web portal.
- Placeholder-validation status: not observed for all firmware strings.
- CI status: CI and release workflows exist.
- User-facing surfaces: local web portal, device display, setup/pairing,
  settings, OTA/update status and recovery messages.
- Required actions: inventory firmware display strings; add build-time catalog
  validation for all user-facing firmware/web portal strings; add constrained
  display overflow checks where practical.
- Blockers: hardware/display verification needs ESP32 device or simulator.
- Recommended PR: expand native i18n validation beyond portal keys and add
  serial/web portal screenshot evidence to verification.

## `pcvantol/djconnect-api`

- Localization mechanism: no dedicated locale catalogs observed; TypeScript
  `src/messages.ts` likely centralizes API messages.
- Locales currently present: none observed.
- Completeness status: gap for user-facing central API errors/messages where
  applicable.
- Hardcoded string risk: high for responses that clients might render directly.
- Placeholder-validation status: not present.
- CI status: CI, CodeQL and Semgrep workflows exist.
- User-facing surfaces: install-token/bootstrap errors, relay/admin
  diagnostics that may be shown by clients, future entitlement/profile-cloud
  messages.
- Required actions: classify machine-readable API codes versus display
  messages; add locale mapping for display messages if the API owns user-facing
  copy; otherwise document that clients localize API codes.
- Blockers: product decision needed per endpoint about whether the API or
  client owns display copy.
- Recommended PR: add a small message catalog or typed error-code map with all
  five localized display messages for user-visible API errors.

## `pcvantol/djconnect-website`

- Localization mechanism: no dedicated locale routes, catalogs or AGENTS file
  observed in the scan.
- Locales currently present: no canonical five-locale website structure
  observed.
- Completeness status: gap for public website content.
- Hardcoded string risk: high because website pages appear to be authored as
  direct copy.
- Placeholder-validation status: not present.
- CI status: deploy and validate workflows exist.
- User-facing surfaces: homepage, docs, onboarding, privacy/support pages,
  release notes, download/install guidance, metadata, screenshots and SEO.
- Required actions: add AGENTS guidance; choose route-based or catalog-based
  localization; implement five-locale navigation, metadata and key public
  pages; add link and hreflang validation if route-based.
- Blockers: website localization design is needed before implementation.
- Recommended PR: introduce locale routing or a locale catalog and make the
  homepage, privacy/support and install flows available in all five languages.

## `pcvantol/djconnect-firmware`

- Localization mechanism: release manifest only observed.
- Locales currently present: none; raw firmware manifest metadata is not
  expected to be translated.
- Completeness status: distribution copy policy gap.
- Hardcoded string risk: low for machine metadata, medium if release notes or
  install instructions are added.
- Placeholder-validation status: not applicable for manifest-only metadata.
- CI status: no workflows observed in this checkout.
- User-facing surfaces: public firmware release notes, install/download
  instructions and repository README if present.
- Required actions: add AGENTS localization guidance; keep manifests machine
  readable; ensure public release/install copy follows the canonical standard.
- Blockers: none for policy; release copy may live in GitHub releases rather
  than files.
- Recommended PR: add AGENTS guidance and a release-copy checklist.

## `pcvantol/djconnect-app-releases`

- Localization mechanism: none observed in local files.
- Locales currently present: none observed.
- Completeness status: distribution copy policy gap.
- Hardcoded string risk: medium for release notes, installer text and public
  download guidance.
- Placeholder-validation status: not applicable until catalogs or templates
  exist.
- CI status: no workflows observed.
- User-facing surfaces: app release notes, public install guidance, store/TestFlight
  adjacent copy and screenshots where stored.
- Required actions: add AGENTS localization guidance and release-note policy.
- Blockers: release copy may be stored only in GitHub release metadata.
- Recommended PR: add release-note templates that require all five languages
  for end-user copy.

## `pcvantol/djconnect-pi-releases`

- Localization mechanism: none observed in local files.
- Locales currently present: none observed.
- Completeness status: distribution copy policy gap.
- Hardcoded string risk: medium for release notes and install guidance.
- Placeholder-validation status: not applicable until catalogs or templates
  exist.
- CI status: no workflows observed.
- User-facing surfaces: Pi release notes, install/download guidance and public
  support copy.
- Required actions: add AGENTS localization guidance and release-note policy.
- Blockers: release copy may be stored only in GitHub release metadata.
- Recommended PR: add release-note templates that require all five languages
  for end-user copy.
