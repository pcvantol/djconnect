# Action Pinning PR Risk Classification Matrix

Status: point-in-time classification; no pull request was merged
Read-back date: 2026-07-13

| Repository / PR | Changed scope | Risk | Protected-path result | Required checks | Human approval under proposed policy | Auto-merge eligibility |
| --- | --- | --- | --- | --- | --- |
| `djconnect` [#78](https://github.com/pcvantol/djconnect/pull/78) | Six CI/release workflow action SHA pins; Batch 1–4 registry and migration evidence; removal of superseded non-canonical Prompt 3 copy; this single-maintainer governance decision and target policy. | `HIGH_RISK` | Software Assurance and review-governance control policy changed. | canonical validation, CodeQL, Semgrep, Verification, qualification and explicit owner approval | Yes | No; may not auto-merge until owner approval and all checks pass. |
| `djconnect-api` [#34](https://github.com/pcvantol/djconnect-api/pull/34) | CI, CodeQL and Semgrep action/reusable-workflow SHA pins. | `LOW_RISK` | None. | `Validate`, security/analysis and qualification | No | Yes after all required checks and qualification pass. |
| `djconnect-app` [#12](https://github.com/pcvantol/djconnect-app/pull/12) | Apple/firmware CI, CodeQL, security, unsigned release and TestFlight action SHA pins. | `NORMAL_RISK` | Release workflow touched, but only immutable references changed; permissions, triggers, signing and publication behavior preserved. | CI, firmware/security checks and qualification | No | Yes after all required checks and qualification pass. |
| `djconnect-pi` [#34](https://github.com/pcvantol/djconnect-pi/pull/34) | Workflow SHA pins plus removal of a byte-identical duplicate test. | `NORMAL_RISK` | None; no governance or release semantic change. | Python tests, Ruff, contract/security checks and qualification | No | Yes after all required checks and qualification pass. |
| `djconnect-website` [#15](https://github.com/pcvantol/djconnect-website/pull/15) | Workflow SHA pins and exact SHA test expectation. | `LOW_RISK` | None; deploy workflow semantics unchanged. | website validation, security/analysis and qualification | No | Not until the separate `SYNC_PROMPTS.md` CI debt is resolved. |
| `djconnect-windows` [#8](https://github.com/pcvantol/djconnect-windows/pull/8) | Workflow SHA pins plus workflow-hygiene behavior changed from broad prose matching to immutable `uses:` validation. | `HIGH_RISK` | GitHub Actions governance/check semantic changed. | CI, contract/security checks, qualification and explicit owner approval | Yes | No; may not auto-merge until owner approval and all checks pass. |
| `djconnect-esp32` [#15](https://github.com/pcvantol/djconnect-esp32/pull/15) | CI, CodeQL, release and secret-scan action SHA pins. | `NORMAL_RISK` | Release workflow touched, but only immutable references changed; release token, trigger, asset and publication semantics preserved. | firmware CI, native tests, security and qualification | No | Yes after all required checks and qualification pass. |

`SYNC_PROMPTS.md` in `djconnect-website` is pre-existing unrelated CI debt. It
blocks only Website PR #15 and is not a reason to block the governance-policy
decision. It remains unchanged pending separate authorization.
