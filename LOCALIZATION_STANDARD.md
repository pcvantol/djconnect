# DJConnect Localization Standard

Status: Accepted
Owner: `pcvantol/djconnect`
Source language: English

## Purpose

This document defines the authoritative DJConnect localization contract for all
user-facing product surfaces across the platform.

It is not a requirement to translate arbitrary developer documentation. It is a
platform standard for product UX, public distribution surfaces and end-user
copy.

## Canonical Language Set

The platform-supported locale set is exactly:

```text
en
nl
de
fr
es
```

These language families mean:

- English: `en`
- Dutch: `nl`
- German: `de`
- French: `fr`
- Spanish: `es`

Use regional variants only where platform tooling requires them, for example
`en-US`, `en-GB`, `nl-NL`, `de-DE`, `fr-FR` or `es-ES`. Normalize regional
variants to the five canonical language families for cross-repository parity.

Do not silently add a sixth supported product language in one repository. A new
supported language requires an explicit platform-level decision and coordinated
rollout.

## Scope

The five-language requirement applies to user-facing:

- navigation;
- buttons;
- forms;
- onboarding;
- settings;
- profile UX;
- errors shown to users;
- pairing;
- privacy descriptions;
- empty states;
- status messages;
- update and install UI;
- firmware or web portal UI;
- website content;
- release and install instructions intended for end users;
- store metadata;
- accessibility labels where localized;
- screenshots or demo data containing user-facing text.

It does not require translating:

- source identifiers;
- API paths;
- JSON keys;
- service names;
- machine-readable error codes;
- protocol values;
- log tokens;
- class or function names;
- developer-only diagnostics;
- repository documentation unless explicitly public or user-facing.

## Source Language And Keys

English is the canonical source language for localization keys.

Translations must map from stable keys, not arbitrary source strings.

Require:

- stable localization keys;
- no user-facing strings embedded in business logic;
- placeholders remain consistent across all locales;
- pluralization uses platform-native mechanisms;
- locale fallbacks are explicit;
- missing translations fail validation where practical;
- removed keys are cleaned consistently;
- keys describe meaning, not English wording.

## Fallback Policy

Locale selection should use the preferred locale from platform or user settings.

Fallback behavior:

- normalize regional variants to the canonical language family;
- fall back to English when a supported translation is unavailable;
- never display a raw localization key in production UI;
- never fall back to a random different non-English language;
- log missing keys safely in debug builds where useful.

## Machine Versus User-Facing Errors

Machine-readable codes remain English and stable, for example:

```text
profile_required
device_not_mapped
backend_not_configured
```

The displayed message is localized into one of the five supported languages.
Never translate machine-readable API codes, protocol values or JSON keys.

## Terminology Consistency

Translations must preserve canonical product concepts:

- DJConnect Profile
- Music DNA
- Ask DJ
- Insights
- VibeCast
- Discover
- Music Backend
- Music Account
- Household Profile
- Shared Room Profile
- Guest Profile
- Voice Endpoint
- Private Session
- Community
- Personal

Brand and feature names `DJConnect`, `Music DNA`, `Ask DJ` and `VibeCast`
remain invariant unless a later accepted product-language decision changes
that rule. Surrounding consumer copy should still be natural in each locale.

Do not translate brand names inconsistently across repositories.

## Quality Requirements

Translations must be:

- natural rather than literal;
- concise enough for small screens;
- consistent between apps and website;
- privacy-safe;
- accessible;
- suitable for buttons, errors and spoken output where applicable.

## Repository Responsibilities

Each repository owns:

- its localization implementation;
- key completeness;
- UI layout validation;
- native accessibility and localization integration.

The HA repository owns:

- canonical locale set;
- canonical terminology;
- shared validation requirements;
- cross-repository parity policy.

`LOCALIZATION_NARRATIVE_ARCHITECTURE.md` owns the V4 language-resolution,
immutable DJMoment narrative and renderer/voice realization boundaries.

## Adding Or Changing A String

Required workflow:

1. Add or change the canonical key.
2. Update all five locales in the same PR.
3. Validate placeholders.
4. Run localization tests.
5. Inspect affected UI.
6. Update screenshots, store text or public release copy when relevant.

No PR should intentionally ship a new user-facing key in only one language
unless it is explicitly experimental and hidden from release builds.

## Engineering Status Dashboard Verification

The private Engineering Status dashboard uses
`tools/engineering/assets/dashboard_locales.mjs` as its single client-copy
catalogue. Its browser code must resolve visible labels, status messages,
accessibility names and dynamic UI feedback through that catalogue; only
non-verbal control glyphs and intentionally empty values may be literal in the
client.

Dashboard changes require both of these checks:

1. catalogue completeness: every key is present and non-empty in `en`, `nl`,
   `de`, `fr` and `es`;
2. browser verification: each supported locale is selected in Playwright and
   the rendered template bindings plus dynamically-created UI copy are matched
   against the catalogue.

The dashboard browser suite also guards client-side presentation assignments so
a newly added literal user-facing string fails the test instead of silently
shipping in the developer's language. Run the focused verification with:

```sh
npx playwright test tests/engineering/dashboard.spec.mjs
```
