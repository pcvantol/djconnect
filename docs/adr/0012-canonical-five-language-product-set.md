# ADR-0012: DJConnect Supports One Canonical Five-Language Product Set

Status: Accepted
Date: 2026-07-10

## Context

DJConnect spans ten repositories: Home Assistant integration, Apple clients,
Windows client, Raspberry Pi client, ESP32 firmware, central API, website and
release distribution repositories.

Inconsistent locale support causes product drift. Partial translations create
broken onboarding, privacy and release experiences. Website, clients and
release surfaces must behave as one product.

## Decision

DJConnect supports one canonical product-language set:

```text
en
nl
de
fr
es
```

New user-facing strings require all five translations in the same product
change unless explicitly experimental and hidden from release builds.

English is the fallback language.

Machine-readable values are never translated, including API paths, JSON keys,
service names, protocol values and stable error codes.

New supported languages require a platform-level change and coordinated
rollout.

CI should validate key and placeholder parity where practical. Repositories may
use native localization tooling as long as the observable contract is the same.

## Consequences

- Each user-facing string requires additional implementation and review work.
- Cross-platform UX becomes more reliable.
- Store, website and release surfaces stay consistent with clients.
- The verification harness must exercise all five locales.
- Distribution repositories must treat release/install copy as user-facing
  product copy when applicable.

## Alternatives Rejected

- Let each repository choose its own locale set.
- Allow English-only fallback without completeness validation.
- Translate only apps but not website or release surfaces.
- Translate machine-readable error values.

## Affected Repositories

- `pcvantol/djconnect`
- `pcvantol/djconnect-app`
- `pcvantol/djconnect-windows`
- `pcvantol/djconnect-pi`
- `pcvantol/djconnect-esp32`
- `pcvantol/djconnect-api`
- `pcvantol/djconnect-website`
- `pcvantol/djconnect-firmware`
- `pcvantol/djconnect-app-releases`
- `pcvantol/djconnect-pi-releases`

## Related Foundation Documents

- `LOCALIZATION_STANDARD.md`
- `PRODUCT_LANGUAGE.md`
- `PLATFORM_QUALITY_STANDARD.md`
- `PLATFORM_BASELINE_v1.md`
- `REPOSITORY_OWNERSHIP.md`
- `docs/localization/LOCALIZATION_VALIDATION_SPEC.md`
- `docs/localization/LOCALIZATION_REPOSITORY_AUDIT.md`
