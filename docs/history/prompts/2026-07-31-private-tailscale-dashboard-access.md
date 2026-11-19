# Private Tailscale dashboard access

**Prompt ID:** `PRIVATE_TAILSCALE_DASHBOARD_ACCESS`
**Generation and engineering program:** Engineering Platform 1.5 / Platform
Engineering
**Branch:** `codex/tailscale-private-dashboard-access`
**Commit:** `44b06e7c`
**Pull request:** [#649](https://github.com/pcvantol/djconnect/pull/649)
**Implementation merge:** `31198276733fdac29bd2ea2d0d5ed2961595afb3`
**Decision and execution date:** 2026-07-31
**Created:** 2026-07-31
**Updated:** 2026-07-31

## Immutable implementation prompt

The owner accepted the immediately preceding bounded proposal to implement
private iPhone access to the Engineering Dashboard through the local Tailscale
address. The exact owner approval was:

```text
Ja
```

The accepted scope was a read-only dashboard listener on the locally reported
Tailscale IPv4 address, while retaining loopback access. It explicitly excluded
Funnel, port forwarding, ACL changes and other Tailscale network-policy
changes.

## Decision

`GO_PRIVATE_TAILSCALE_DASHBOARD_ACCESS_IMPLEMENTED`

The dashboard binds only to `127.0.0.1` and, when available, the concrete
`100.64.0.0/10` address reported by the local Tailscale client. It never binds
a wildcard, LAN or public address. Tailscale remains the authenticated private
access boundary.

## Validation

- Focused dashboard, remote-engineering, platform-productization and
  onboarding-package tests passed.
- Ruff, Engineering Platform version validation and `git diff --check` passed.
- Local listener verification confirmed loopback and the current local
  Tailscale address.
- GitHub Actions passed build, validation, qualification, security, HACS,
  Hassfest, CodeQL and advisory smoke checks.

## Known limitations

The dashboard remains status-only and read-only. It does not publish status
itself; absent local status remains an explicit degraded projection. Tailnet
authorization remains owned by existing Tailscale policy.

## Deferred work

No Tailscale policy automation, ACL management, Funnel, port forwarding,
public exposure, execution authority or dashboard transaction controls are
included.

## Recommended next prompt

Return to the current canonical Product Development or Platform Evolution
assessment. Do not expand remote dashboard authority without a separately
authorized bounded increment.
