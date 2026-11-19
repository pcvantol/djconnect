# Trusted Delivery Governance Target Matrix

Status: implementation-preparation target; no GitHub setting has been changed
Date: 2026-07-13

## Common `main` target

All ten active repositories require a PR, strict/current-branch required
checks, conversation resolution, force-push prohibition, protected-branch
deletion prohibition, automatic source-branch deletion after merge, and
auto-merge enabled. The required approving-review count becomes `0`; the
required `Trusted Delivery qualification` and `Owner Authorization` statuses.
Owner Authorization is automatically `NOT_REQUIRED` for LOW/NORMAL work and
requires exact-SHA owner evidence for HIGH_RISK work. No routine direct push is
permitted.

The owner emergency override must be auditable and must not be configured as a
silent standing bypass. The Trusted Delivery App retains least privilege and
may enable auto-merge only after qualifying LOW_RISK/NORMAL_RISK results.

| Repository | Target PR rule | Required checks | Merge method | Protected-path/approval gate | Current read-back gap |
| --- | --- | --- | --- | --- | --- |
| `djconnect` | PR, conversation resolution, freshness | canonical CI, Verification and `Trusted Delivery qualification` | squash | conditional HIGH_RISK owner approval | review count 1; no required checks or conversation resolution |
| `djconnect-api` | PR, conversation resolution, freshness | `Validate`, security/analysis and qualification | squash | conditional HIGH_RISK owner approval | review count 1; qualification missing |
| `djconnect-app` | PR, conversation resolution, freshness | `CI`, firmware/security checks and qualification | squash | conditional HIGH_RISK owner approval | review count 1; conversation/qualification missing |
| `djconnect-pi` | PR, conversation resolution, freshness | Python validation, contract/security checks and qualification | squash | conditional HIGH_RISK owner approval | review count 1; required checks/qualification missing |
| `djconnect-esp32` | PR, conversation resolution, freshness | firmware CI, native tests, security and qualification | squash | conditional HIGH_RISK owner approval | review count 1; required checks/conversation/qualification missing |
| `djconnect-website` | PR, conversation resolution, freshness | website validation, security/analysis and qualification | squash | conditional HIGH_RISK owner approval | required checks/conversation/qualification missing |
| `djconnect-windows` | PR, conversation resolution, freshness | CI, contract/security checks and qualification | squash | conditional HIGH_RISK owner approval | `main` unprotected |
| `djconnect-firmware` | PR, conversation resolution, freshness | release artifact validation and qualification | squash | conditional HIGH_RISK owner approval | `main` unprotected |
| `djconnect-app-releases` | PR, conversation resolution, freshness | artifact/release validation and qualification | squash | conditional HIGH_RISK owner approval | `main` unprotected |
| `djconnect-pi-releases` | PR, conversation resolution, freshness | artifact/release validation and qualification | squash | conditional HIGH_RISK owner approval | `main` unprotected |

Use a repository ruleset where the account plan supports the full target;
otherwise use one `main` branch-protection rule plus the required qualification
check. GitHub's fixed approval-count control is not used for risk-conditional
approval, because it cannot express that condition. Existing merge methods may
remain temporarily during migration, but the final target is squash merge to
maintain a linear, auditable delivery history.
