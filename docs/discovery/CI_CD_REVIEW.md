# CI/CD Review

## Summary

The source repositories have strong CI. Release-only repositories are the clear gap.

## Strong baselines

- `djconnect`: tests, ruff, bandit, hassfest, HACS validation, Semgrep and CodeQL.
- `djconnect-api`: typecheck, Wrangler dry-run, D1 migrations, Vitest, Postman, secret scan, deploy and smoke.
- `djconnect-website`: tests, i18n, screenshots, smoke, build and deploy.
- `djconnect-esp32`: native tests, PlatformIO build, release dry-run, CodeQL and secret scan.
- `djconnect-app`: Swift tests, contract fixtures, localization, unsigned builds and release workflows.
- `djconnect-windows`: .NET tests, contract fixtures, formatting, secret-like scan, builds, CodeQL and Semgrep.
- `djconnect-pi`: pytest, shared Python workflow, contract fixtures, Postman and release publishing.

## Gaps

- Release-only repositories have no visible CI.
- Cross-repo fixture conformance is not summarized centrally.
- Product-language drift checks do not exist.
- Foundation AGENTS conformance is not checked.

## Recommendations

1. Add minimal validation to release-only repos or explicitly document that validation is upstream-only.
2. Add a contract fixture compatibility suite/report.
3. Add product-language lint for website and public release docs.
4. Add an AGENTS/foundation conformance check for sibling repos.
