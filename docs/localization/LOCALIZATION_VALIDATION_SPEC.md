# DJConnect Localization Validation Specification

Status: Accepted platform specification
Owner: `pcvantol/djconnect`

## Purpose

This document defines a platform-neutral localization validation model. Each
repository should use its native localization tooling, but the observable
result must satisfy the same contract.

Required canonical locales:

```text
en
nl
de
fr
es
```

## Required Checks

Validators should check:

1. all five locale catalogs exist where applicable;
2. all catalogs contain the same required keys;
3. no unknown or stale keys exist unless intentionally supported;
4. placeholder names and counts match;
5. formatting specifiers match;
6. plural forms are valid for the platform;
7. no raw localization key appears in rendered smoke tests;
8. English fallback works;
9. canonical product terms remain consistent;
10. files are valid UTF-8;
11. locale catalogs parse successfully;
12. user-facing machine errors are mapped to localized messages.

## Catalog Model

A repository may use Apple `.strings`, .NET `.resx`, Python dictionaries, C++
embedded tables, JSON catalogs, route-based website content or another native
mechanism.

For validation, normalize each catalog to:

```json
{
  "locale": "en",
  "source": "path-or-native-bundle",
  "keys": {
    "stable.key": {
      "value": "Rendered text with {placeholder}",
      "placeholders": ["placeholder"],
      "format_specifiers": [],
      "plural": false
    }
  }
}
```

Regional variants such as `en-GB` or `nl-NL` should be reported with both the
native locale and the normalized canonical language.

## Machine-Readable Output

Per-repo validators should emit CI-readable results. JSON output should follow
this shape when practical:

```json
{
  "schema": "djconnect.localization.validation.v1",
  "repository": "pcvantol/djconnect",
  "status": "pass",
  "locales": ["en", "nl", "de", "fr", "es"],
  "checks": [
    {
      "id": "catalogs_exist",
      "status": "pass",
      "message": "All required catalogs are present."
    }
  ],
  "issues": []
}
```

JUnit output is also acceptable for CI systems that already collect test
reports. Use stable testcase names such as:

- `localization.catalogs_exist`
- `localization.key_parity`
- `localization.placeholders`
- `localization.english_fallback`
- `localization.rendered_smoke`

## Severity

Use:

- `fail` for missing required locale catalogs, missing required keys,
  placeholder mismatches, parse failures, invalid UTF-8 or production UI that
  can display raw keys;
- `warning` for detected hardcoded strings, stale keys, missing screenshot
  coverage or public copy that has not yet been made multilingual;
- `info` for repository-specific exceptions that are documented and accepted.

## Recommended Repository Validators

- HA integration: validate `strings.json` and `translations/*.json` key parity,
  placeholders and Home Assistant config-flow/error mappings.
- Apple: validate `.lproj` catalogs with native Apple tools and snapshot/smoke
  tests for iOS, macOS and watchOS.
- Windows: validate `.resx` catalogs and smoke-test both macOS Catalyst
  development/debug and native Windows ARM64 rendering where applicable.
- Raspberry Pi: validate Python translation catalogs, QML key usage, locale
  persistence and screenshot overflow checks.
- ESP32: validate embedded firmware/web-portal translation tables and
  constrained-display overflow where practical.
- API: validate user-facing API messages and map machine codes to localized
  display text where the API owns user-visible copy.
- Website: validate locale routes or locale switching, metadata, navigation,
  privacy/support pages, links, sitemap and hreflang where implemented.
- Release repositories: validate public release/install copy and avoid
  translating raw checksums or machine metadata.

Do not force every repository to use the same localization library.
