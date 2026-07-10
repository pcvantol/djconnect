# DJConnect Verification Data Framework

Status: Canonical data framework v1
Date: 2026-07-10

This directory owns reusable verification data for the DJConnect platform.

Scenarios define behavior. Matrix profiles define execution conditions. Data
profiles and generators define values.

Adapters must consume data from this directory rather than inventing their own
fixtures.

## Layout

- `catalogs/` - category, boundary and domain catalogs.
- `generators/` - generator registry and deterministic generation contract.
- `profiles/` - reusable data profiles.
- `security/` - security payload library.
- `localization/` - locale and layout stress payloads.
- `examples/` - example datasets.

## Reproducibility

Generated data must be reproducible from seed, run ID, scenario ID, generator
ID, generator version and data profile ID.

Static catalog IDs are stable. Do not rename IDs after they are referenced by
scenarios, reports or adapters.
