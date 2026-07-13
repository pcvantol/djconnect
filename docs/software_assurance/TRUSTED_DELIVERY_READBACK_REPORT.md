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
| SHA enforcement | Disabled on all ten repositories because default-branch pinning remains incomplete |
| CODEOWNERS / qualification consumer | Present on governed PR branches; pending merge to default branches |

The Website `SYNC_PROMPTS.md` failure remains unrelated pre-existing CI debt.
It blocks Website PR #15 only and was not remediated.
