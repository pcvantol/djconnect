## Session first-play control copy — five UI language families

The separately versioned first-play action catalogue provides Core-owned
labels/prompts for en/nl/de/fr/es and deterministic control replies. Clients use
the exact Core locale entry; no static unqualified executable CTA is introduced.
Genre IDs, result/action IDs, error codes and wire keys remain untranslated.
This source-route coverage does not publish additional Help catalogue leaves or
widen the existing EN/NL-only textual qualification boundary. Existing Help
catalogue/hash, UI language data, date precision and rendering remain intact.
See [Session first-play v1](docs/product/SESSION_FIRST_PLAY_SURPRISE_MIX_V1.md).

## 2026-11-02 — Localized album-edition date presentation

Ask DJ release-date sentences use the effective app/request language, normalized
to the existing five canonical families. Full numeric dates display as follows:

| Language | Example for ISO `2024-12-20` | Month-only `2024-12` |
| --- | --- | --- |
| nl | 20-12-2024 | 12-2024 |
| en | 12/20/2024 | 12/2024 |
| de | 20.12.2024 | 12.2024 |
| fr | 20/12/2024 | 12/2024 |
| es | 20/12/2024 | 12/2024 |

A year-only source remains `2024`. Never invent a missing day or month. Validate
source date and precision before presentation; retain the original ISO value and
precision in structured observations. Format only the date slot, not dates that
happen to occur in artist or work titles. This uses the app language rather than
the host operating-system locale and adds no provider or model lookup.

## Scoped textual Help qualification — 26 October2026

Peter explicitly limited the current textual Help qualification/release to
English and Dutch. This bounded exception concerns the Help catalogue and its
40 original content cases (20 per language), not the platform-wide language
families or existing client translations. German, French and Spanish templates
and historical results remain retained and unreleased in this scope. Until real
content/editorial acceptance and protected publication, the existing catalogue
remains revision1/qualifiedfalse/70pending. No language is advertised as qualified
merely by retaining its template. See
[the current source boundary](docs/verification/HELP_EN_NL_TYPED_ARTIST_20261026.md).

--- Earlier full policy retained below ---

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

## Engineering Platform presentation ownership

The standalone Engineering Platform owns its Operations Console, locale
catalogue and browser verification. DJConnect keeps the five-language contract
for its own product surfaces. Historical dashboard checks and source paths in
earlier qualification records remain provenance, not current DJConnect test
commands.
