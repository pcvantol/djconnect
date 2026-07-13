# Trusted Delivery Compliance Matrix

Date: 2026-07-13

| Repository group | GitHub branch/rules configuration | Qualification consumer and CODEOWNERS | SHA enforcement | GitHub Native Compatibility | Compliance |
| --- | --- | --- | --- | --- |
| Seven source integration PRs | Active | Merged | Native setting disabled; recursive immutable closure enforced | `PLATFORM_EXCEPTION` (`TD-GITHUB-001`) | Compliant |
| Three release repository PRs | Active | Merged | Native setting disabled; recursive immutable closure enforced | `PLATFORM_EXCEPTION` (`TD-GITHUB-001`) | Compliant |
| Default branches | Active protection/ruleset/permissions | Present | Native setting disabled; recursive immutable closure enforced | `PLATFORM_EXCEPTION` (`TD-GITHUB-001`) | Compliant |

The policy is operationally configured and rollout PRs are merged. Immutable
workflow governance is validated independently of GitHub's incompatible native
setting under accepted platform exception `TD-GITHUB-001`.
