# Engineering Platform 1.5 Extraction Readiness Audit

## Boundary

`tools/engineering/` is the prospective package boundary. Its public entry
points are `platform_api`, `execution_host`, `inbox_watcher`, `dashboard` and
`qualification`; implementation modules remain private.

## Dependency classification

| Dependency | Classification | 1.5 position |
| --- | --- | --- |
| Platform identity, runner, reports, qualification | PLATFORM | Independent of consumer product behavior. |
| Workspace name, branding and report navigation | WORKSPACE | Declarative configuration only. |
| GitHub repository metadata | REPOSITORY / PROVIDER | Configuration plus GitHub provider. |
| Codex, launchd, iCloud Inbox, Tailscale | PROVIDER | Qualified current implementations behind contracts. |
| Existing `.engineering` local state paths | IMPLEMENTATION | Canonical local workspace state, outside the product runtime. |

## Result

No Home Assistant or DJConnect runtime import is part of the Platform package.
Remaining DJConnect wording is workspace/onboarding material, not platform
behaviour. Package publishing and repository movement remain explicitly out of
scope; 1.6 audits imports, namespaces and packaging before extraction.
