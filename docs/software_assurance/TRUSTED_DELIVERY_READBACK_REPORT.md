# Trusted Delivery Read-Back Report

Date: 2026-07-13

| Control | Read-back result |
| --- | --- |
| Active repository inventory | Ten repositories from `REPOSITORY_OWNERSHIP.md` |
| Branch protection | Active on `main` for all ten repositories |
| Required check | `Trusted Delivery / Qualify trusted delivery`, strict freshness enabled |
| Fixed approvals | `0` on all ten repositories |
| Conversation resolution | Enabled on all ten repositories |
| Linear history | Enabled on all ten repositories |
| Force push / deletion | Disabled on all ten repositories |
| Rulesets | `Trusted Delivery main integrity` active on all ten repositories |
| Auto merge / merged-branch deletion | Enabled on all ten repositories |
| Workflow permissions | Default `read`; PR-review approval disabled |
| Trusted App contract | Least-privilege contents, pull-request, checks/status read contract retained; no administration/secrets permission |
| SHA enforcement | Effective `false` on all ten under accepted compatibility exception `TD-GITHUB-001`; recursive immutable workflow governance remains required |
| CODEOWNERS / qualification consumer | Present on all merged default branches |

The native setting's incompatibility was reproduced in an isolated repository:
direct SHA-pinned actions pass, while the tested valid cross-repository
reusable-workflow graph fails before job creation. This is governed by
`TD-GITHUB-001`, not treated as a DJConnect implementation defect.
