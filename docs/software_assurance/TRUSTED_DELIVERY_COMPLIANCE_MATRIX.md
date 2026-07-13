# Trusted Delivery Compliance Matrix

Date: 2026-07-13

| Repository group | GitHub branch/rules configuration | Qualification consumer and CODEOWNERS | SHA enforcement | Compliance |
| --- | --- | --- | --- | --- |
| Seven source integration PRs | Active | Merged | Disabled after rollback | Integrated; recursive pin audit blocked |
| Three release repository PRs | Active | Merged | Disabled after rollback | Integrated; recursive pin audit blocked |
| Default branches | Active protection/ruleset/permissions | Present | Disabled after rollback | Not complete |

The policy is operationally configured and rollout PRs are merged. It cannot be
certified until recursive action-pinning validation proves every reusable
workflow source is enforcement-safe and representative post-enforcement CI
passes.
