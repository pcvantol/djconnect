# DJConnect Platform Quality Standard

This document defines the desired quality baseline for every DJConnect repository.

It is a target standard. Not every repository is expected to meet it immediately, but Platform Discovery should measure gaps against it.

## Quality dimensions

Every repository should eventually be reviewed across:

1. product consistency;
2. architecture consistency;
3. documentation;
4. tests;
5. CI/CD;
6. security;
7. privacy;
8. release process;
9. localization;
10. accessibility where applicable.

## Required baseline for every repo

Each repository should have:

- clear `README.md`;
- `AGENTS.md` pointing to the canonical design foundation;
- license and third-party notices where applicable;
- clear build/test commands;
- CI workflow for primary validation;
- secret scanning or at least secret-regex release checks;
- release notes or changelog process;
- privacy/security notes when user data, tokens or network APIs are involved.

## Documentation standard

A repo should answer:

- what is this repository responsible for;
- what it must not own;
- how it fits the platform;
- how to build/test/release;
- which contracts it consumes or exposes;
- how to debug common failures;
- how to keep it aligned with canonical docs.

## Test standard

Recommended test levels:

- unit tests for pure logic;
- contract tests for shared backend/client payloads;
- integration tests for major flows;
- smoke tests for release artifacts;
- regression tests for privacy/security-sensitive behavior.

Minimum expected examples:

- HA repo: profile resolver, backend resolver, API endpoints, privacy/export behavior;
- API repo: relay auth, token validation, APNs payload safety, no secret leakage;
- Apple/Windows clients: pairing, contract parsing, local cache behavior, privacy clear;
- Pi: shared profile display rules, update flow, contract parsing;
- ESP32: command parsing, pairing, OTA safety, device runtime guards;
- Website: build, link check, SEO/sitemap, privacy page, Playwright smoke test.

## CI/CD standard

Recommended pipeline stages:

```text
format/lint
  -> unit tests
  -> contract tests
  -> security/dependency scans
  -> secret scan
  -> build artifacts
  -> release notes validation
  -> artifact integrity validation
  -> publish
```

Release pipelines should fail closed when secrets, missing artifacts or broken version metadata are detected.

## Security standard

Every repo should consider:

- no committed secrets;
- least-privilege tokens;
- dependency scanning;
- CodeQL or equivalent where applicable;
- signed or checksummed release artifacts where practical;
- safe logging;
- no raw OAuth tokens, APNs tokens, HA tokens or raw chat history in logs;
- token redaction in diagnostics.

## Privacy standard

Any feature touching profile data, Music DNA, chat history, guest pages, exports or cloud relay must define:

- what data is stored;
- where it is stored;
- how it is cleared;
- whether it is exported;
- whether it can appear on shared devices;
- whether it leaves local Home Assistant;
- how private sessions behave.

## Release standard

Every release should include:

- version number;
- compatibility notes;
- user-facing release notes;
- migration notes if needed;
- known issues;
- changed contracts if any;
- security/privacy notes if relevant;
- artifact links/checksums where applicable.

Release repositories are distribution surfaces. They must not become product-logic owners.

## Store readiness standard

For App Store, TestFlight, Microsoft Store or future Play Store routes, track:

- product description;
- screenshots;
- privacy labels;
- permissions rationale;
- beta/release notes;
- support URL;
- privacy URL;
- review notes;
- demo mode or reviewer guidance;
- subscription/IAP behavior if applicable.

## Localization and accessibility

User-facing clients and website should aim for:

- stable localization keys;
- no hardcoded user-facing strings in logic;
- accessible labels for controls and images;
- readable contrast;
- graceful rendering without emoji or advanced rich text support;
- platform-native accessibility where practical.

## Scorecard scale

Platform Discovery may score each dimension:

- 0: missing;
- 1: ad hoc;
- 2: partial;
- 3: adequate;
- 4: strong;
- 5: excellent/platform reference.

Scores are for prioritization, not blame.
