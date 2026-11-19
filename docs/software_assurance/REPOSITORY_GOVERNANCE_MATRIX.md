# Repository Governance Matrix

Date: 2026-07-13
Status: post-merge read-back

| Repository | Rollout PR / merge | `main` protection and ruleset | Required qualification check | SHA enforcement | Result |
| --- | --- | --- | --- | --- | --- |
| `djconnect` | #78 / `1ff14bcc` | active | configured | rolled back to false | blocked by nested reusable-workflow pin audit |
| `djconnect-api` | #34 / `30c2ccb0` | active | configured | rolled back to false | blocked by nested reusable-workflow pin audit |
| `djconnect-app` | #12 / `9ca2bf25` | active | configured | rolled back to false | blocked by nested reusable-workflow pin audit |
| `djconnect-app-releases` | #4 / `ed41d944` | active | configured | rolled back to false | blocked by nested reusable-workflow pin audit |
| `djconnect-esp32` | #15 / `39701f0f` | active | configured | rolled back to false | blocked by nested reusable-workflow pin audit |
| `djconnect-firmware` | #4 / `2d9fc2d6` | active | configured | rolled back to false | blocked by nested reusable-workflow pin audit |
| `djconnect-pi` | #34 / `bfcbc3f6` | active | configured | rolled back to false | representative CI exposed blocker |
| `djconnect-pi-releases` | #4 / `5d7eb6f9` | active | configured | rolled back to false | blocked by nested reusable-workflow pin audit |
| `djconnect-website` | #15 / `1bab9e29` | active | configured | rolled back to false | blocked by nested reusable-workflow pin audit |
| `djconnect-windows` | #8 / `57441242` | active | configured | rolled back to false | blocked by nested reusable-workflow pin audit |

All repositories retain read-only default workflow tokens, disabled workflow
PR-review approval, active `Trusted Delivery main integrity` rulesets and
strict `Trusted Delivery / Qualify trusted delivery` branch checks.

## Workflow-class migration matrix

| Repository | CI / Qualification | Artifact / Release Evidence | Deployment | Migration state |
| --- | --- | --- | --- | --- |
| `djconnect` | Validate, CodeQL, Semgrep, Trusted Delivery | Owner authorization, post-merge reconciliation | Verification-runtime Docker publication | Docker publication must be split from build/test and made dispatch-only. |
| `djconnect-app` | CI, firmware CI/security | Post-merge reconciliation | Unsigned public release, TestFlight | Tag-triggered/publication and build-publication coupling require remediation. |
| `djconnect-windows` | CI, CodeQL, Semgrep | Post-merge reconciliation | Unsigned public release | Publication must consume a qualified artifact rather than build-and-publish. |
| `djconnect-pi` | Validate, CodeQL, Semgrep | Post-merge reconciliation | Pi publication/target deployment | Publication and target deployment require dispatch-only separation. |
| `djconnect-esp32` | Firmware CI, CodeQL, secret scan | Post-merge reconciliation | Firmware publication | Tag-triggered build-and-publication requires separation. |
| `djconnect-api` | Validate, CodeQL, Semgrep | Post-merge reconciliation | `Deploy API production` | Dispatch-only isolation implemented; readiness/artifact preconditions remain under qualification. |
| `djconnect-website` | Validate, CodeQL, Semgrep | Post-merge reconciliation | `Deploy Cloudflare Pages` | Dispatch-only isolation implemented; readiness/artifact preconditions remain under qualification. |
| Distribution repositories | Governance/integrity CI | Distribution integrity and post-merge reconciliation | Artifact distribution only | Evidence separation implemented; publication remains explicit deployment work. |
