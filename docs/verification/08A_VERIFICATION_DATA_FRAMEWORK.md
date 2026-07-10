# Verification Program V1 Phase 8A - Verification Data Framework

Status: Implemented
Date: 2026-07-10
Scope: canonical verification data; no adapters; no scenario execution

## Purpose

The Verification Data Framework is the canonical source of verification data
for DJConnect.

Scenarios define behavior. The Verification Matrix defines execution
conditions. The Verification Data Framework defines values, payloads,
boundaries and generated datasets.

```text
Scenario
  -> Verification Matrix
  -> Verification Data
  -> Execution
```

Adapters must consume data from this framework. They must not generate their
own ad hoc test data. Scenarios should not hardcode example values when a
generator or catalog entry can provide the same coverage.

## Philosophy

Verification should never depend on developer-specific data, temporary
fixtures, hardcoded strings or non-reproducible randomness.

Data is a platform asset. It should be:

- reusable across adapters;
- deterministic when a seed is provided;
- traceable to scenario categories and risk categories;
- versioned for migration;
- broad enough for functional, boundary, security, localization, performance
  and future fuzz testing;
- safe to store in the repository.

## Location

The framework lives in:

```text
verification/data/
```

Subdirectories:

- `catalogs/` - canonical category and boundary catalogs;
- `generators/` - generator registry and deterministic generation contract;
- `profiles/` - reusable data profiles such as smoke, regression and security;
- `security/` - security payload library;
- `localization/` - canonical and future-localization payloads;
- `examples/` - example datasets produced from the catalog/generator contract.

## Architecture

The framework supports:

- static datasets;
- generated datasets;
- deterministic datasets;
- random datasets;
- security datasets;
- boundary datasets;
- localization datasets;
- performance datasets;
- migration datasets;
- future AI-generated datasets.

Static catalogs are versioned JSON files. Future executable generators should
use the same IDs and metadata shape so generated values remain traceable.

## Canonical Data Categories

The canonical data categories are:

- strings;
- numbers;
- booleans;
- enums;
- arrays;
- objects;
- date/time;
- binary;
- domain data;
- security payloads;
- localization payloads;
- boundary values.

Each category should identify the purpose, risk, expected behavior and
applicable transports where relevant.

## Strings

String data must support normal strings, empty strings, whitespace, single
character values, very long values, maximum allowed length, maximum plus one,
Unicode, emoji, right-to-left text, combining characters, zero-width
characters, BOM, normalization variants, control characters, HTML, Markdown,
JSON, XML, SQL, JavaScript, command injection, prompt injection, path traversal,
Unicode homoglyphs, invalid UTF, unknown encoding and mixed encoding.

Every string payload should be categorized rather than described only by its
literal value.

## Numbers

Number data must support 0, 1, -1, integer maximum, integer minimum, floats,
NaN, infinity, maximum allowed, maximum plus one, minimum minus one, random,
negative, huge, scientific notation and hexadecimal where applicable.

## Booleans

Boolean data must support true, false, missing, null and unexpected values.

## Enums

Enum data must support valid, deprecated, unknown, future, wrong case,
whitespace, mixed case, invalid value and missing.

## Arrays

Array data must support empty, one item, many items, maximum allowed, maximum
plus one, duplicates, null entries, mixed types and random order.

## Objects

Object data must support minimal, typical, maximum, unknown fields, missing
required fields, recursive objects, deep nesting, duplicate keys where parsers
allow them and malformed objects.

## Date And Time

Date/time data must support epoch, leap year, DST transition, timezone,
future, past, current, maximum, minimum, invalid and malformed values.

## Binary

Binary data must support empty, small, large, maximum, corrupted, invalid
checksum and random payloads.

## Domain Data

Domain generators must support:

- profiles;
- households;
- guests;
- kids profiles;
- areas;
- rooms;
- playback zones;
- devices;
- music accounts;
- music backends;
- capabilities;
- sessions;
- private sessions;
- voice endpoints.

Domain data should use DJConnect terminology and never embed real user data or
real secrets.

## Security Payload Library

Security payloads live in `verification/data/security/payloads.json`.

Each payload includes:

- `id`;
- `purpose`;
- `category`;
- `risk`;
- `payload`;
- `expected_behavior`;
- `applicable_transports`;
- `traceability`.

Security categories include SQL injection, NoSQL injection, command injection,
JSON injection, XPath, LDAP, header injection, cookie injection, CRLF, prompt
injection, Markdown injection, HTML injection, script injection, path
traversal, double encoding, Unicode tricks, homoglyphs, zero-width characters,
malformed UTF, nested JSON, oversized payloads, malformed arrays and malformed
objects.

Expected behavior should generally be reject, sanitize, treat as inert text,
return a structured error or safely ignore, depending on the scenario.

## Boundary Library

Boundary values live in `verification/data/catalogs/boundaries.json`.

The library supports min, max, min minus one, max plus one, typical, huge,
overflow, underflow and invalid cases.

Boundaries are reusable across numeric, string, array, object, binary and
date/time generators.

## Localization Library

Localization payloads live in `verification/data/localization/payloads.json`.

The platform supports exactly:

```text
en
nl
de
fr
es
```

The library also includes future and stress locales: Japanese, Chinese,
Arabic, Hebrew, RTL, emoji, mixed language, normalization, long translations,
very short translations and future locale placeholders.

Future locales in this library do not change the platform-supported locale
contract. They are stress data for layout, parsing and future expansion.

## Data Profiles

Reusable profiles live in `verification/data/profiles/*.json`.

Profiles select categories and generator IDs for a run:

- Smoke;
- Regression;
- Boundary;
- Security;
- Localization;
- Performance;
- Migration;
- Compatibility;
- Accessibility;
- Chaos.

Profiles do not define expected behavior. They select data.

## Deterministic Generation

Every generated dataset must be reproducible from:

- seed;
- run ID;
- scenario ID;
- generator ID;
- generator version;
- data profile ID.

Recommended seed material:

```text
sha256(seed + run_id + scenario_id + generator_id + profile_id)
```

Random generators may be used only through deterministic seeded randomness.
Reports should record the seed and generator versions needed to recreate the
dataset.

## Data Versioning

Every catalog and generated dataset should record:

- `schema_version`;
- `dataset_version`;
- `generator_version`;
- `profile_version`;
- source catalog IDs;
- seed metadata where generated.

When a generator changes output semantics, increment the generator version.
When a static catalog changes meaning or removes IDs, increment the dataset
version and document migration.

## Traceability

Every generator and catalog should reference:

- scenario categories;
- verification modes or profiles;
- security categories;
- localization categories;
- risk categories;
- applicable transports.

Traceability allows future adapters to answer why a value was used without
reading adapter code.

## Performance Considerations

Large, fuzz, chaos and performance datasets should be selected by data profile.
They should not run in smoke verification by default.

Generated datasets should support bounded counts and maximum payload sizes so
CI and live devices are not accidentally overloaded.

## Ownership

The HA repository owns the canonical Verification Data Framework.

Adapters may cache resolved datasets for a run, but they must not fork,
redefine or silently mutate data definitions. Repository-specific data needs
must be added here or documented as temporary adapter-local debt.

## Future Extensions

Future phases may add executable generator code, schema validation for data
catalogs, fuzz minimization, corpus shrinking, generated binary corpora,
AI-assisted dataset generation and historical failure-based data selection.

Those extensions must preserve deterministic replay.

## Acceptance

The platform now has one canonical Verification Data Framework. Future
adapters can consume static and generated datasets for functional, boundary,
security, localization, performance, migration, compatibility and future fuzz
testing without hardcoding values in scenarios or adapters.
