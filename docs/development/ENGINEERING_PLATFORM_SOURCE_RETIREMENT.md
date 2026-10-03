# DJConnect embedded EP source retirement

Assignment: `L5-DJCONNECT-EP-SOURCE-RETIREMENT-V1-20261003`

Owning decision: [LANE_5 register](../governance/LANE_5_EP_SOURCE_RETIREMENT.md)

Owning issue: [#1098](https://github.com/pcvantol/djconnect/issues/1098)

## Current boundary

DJConnect owns its Home Assistant product, verification scenarios, developer
host, onboarding, repository governance and CI. Standalone
`pcvantol/engineering-platform` owns the generic execution host, watcher,
Operations Console, storage, queue, provider/recovery stack, installation and
release lifecycle. DJConnect's `.engineering-platform/repository.json` remains
its declarative project identity. The current supported EP submission ingresses
are Server HTTP JSON, installed CLI and Server-owned File Inbox; the historical
Local Consumer API is not a supported ingress.

No DJConnect product or CI path imports standalone EP internals, reads its
SQLite store, constructs an EP data root or starts a live EP service. The
repository-level compatibility check only installs published release bytes in
an ephemeral environment and exercises installed command help. It does not
submit an Engineering Action.

## Focused dependency disposition

| Group | Disposition | Reason |
| --- | --- | --- |
| `tools/engineering/**`, its embedded assets, wrappers and generic EP contracts | Remove | Transferred generic EP runtime and Operations Console. |
| `tests/engineering/**` | Remove | Tests solely for the transferred EP runtime, browser and internal coverage. Standalone EP owns those qualifications. |
| `scripts/engineering/audit_ep_extraction_baseline.py` | Remove | Pre-extraction audit expected the embedded source to remain. Preserve its manifest and receipts as historical evidence. |
| Root `package.json`, lockfile and `playwright.config.mjs` | Remove | Only the embedded dashboard browser suite consumed Playwright. |
| `.github/workflows/engineering-platform-validation.yml` | Replace | Its old source imports, qualification and browser shards are replaced by a fail-closed retirement guard and exact installed-wheel compatibility check. |
| `.github/workflows/golden-qualification-ci.yml` and DJConnect product/verification tests | Retain | DJConnect Golden and product behavior stay DJConnect-owned. |
| Trusted Delivery, owner authorization, security and product CI workflows | Retain | They enforce DJConnect repository assurance; their historical manifest classification does not make them obsolete. |
| `onboarding/**`, `scripts/runner/**` | Retain | DJConnect-owned host setup already excludes EP service management; refresh onboarding documentation and its tracked generated package. |
| `.engineering-platform/repository.json` | Retain | Canonical DJConnect project declaration. |
| `.engineering-platform/release-pin.json` and `requirements.txt` | Add | Exactly pinned standalone release and immutable wheel digest for the remaining declarative consumer boundary. |
| `docs/engineering/**`, ADRs, extraction manifest, migration and run evidence, immutable Prompt History | Retain | Historical provenance; old path names remain valid as history. |

## Standalone artifact identity

- Distribution: `engineering-platform==2.3.106`, published to PyPI.
- Exact wheel: `engineering_platform-2.3.106-py3-none-any.whl`.
- SHA-256: `9d25a53d75b61d43d665d9f8290a968dc3e63d12d2037eae8ef31ee810eb6694`.
- Source revision: `7b99b578153ae5d72372a09db194306b49ec9f9c`.
- Published [terminal release receipt](https://github.com/pcvantol/engineering-platform/releases/download/engineering-platform-v2.3.106/engineering-platform-release-complete-2.3.106-7b99b578153ae5d72372a09db194306b49ec9f9c.json): `RELEASE_COMPLETE`, qualified production wheel and PyPI readback `PASS`.
- Wheel Python contract: `>=3.14,<3.15`; repository compatibility CI uses 3.14.

The local pin file records the supported installed CLI/Server HTTP boundary,
not a dependency on the retired Local Consumer API. The compatibility job
downloads the exact wheel with hash checking, installs it without sibling
source or developer packages, reads its installed version and checks the
published command surfaces without starting a service or submitting work.

## Qualification and delivery evidence

Record the exact candidate, clean-checkout results, static/security and
product tests, coverage applicability, independent review, protected PR merge,
post-main checks and Finalization in this assignment's PR and issue. None of
those gates is inferred from the owner waivers. Historical receipts retain
their original names and paths.
