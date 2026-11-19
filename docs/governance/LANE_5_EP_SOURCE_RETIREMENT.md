# LANE_5 — DJConnect embedded EP source retirement

Assignment: `L5-DJCONNECT-EP-SOURCE-RETIREMENT-V1-20261003`

Owner decision, 2026-10-03:

| Condition | Decision for this source retirement |
| --- | --- |
| A. Standalone EP distribution works independently | `OWNER_VALIDATED` |
| B. Real DJConnect Engineering Action through standalone EP | `WAIVED_BY_OWNER_FOR_SOURCE_RETIREMENT` |
| C. Real standalone EP self-development task | `WAIVED_BY_OWNER_FOR_SOURCE_RETIREMENT` |
| D. Functional and responsibility transfer | `OWNER_VALIDATED` |
| E. Remaining DJConnect source and consumer dependencies | `RESOLVED` |

B and C are waived prerequisites, not completed tests. Their waiver does not
change qualification requirements for other product work. No
`EP::STANDALONE_EP_VERIFIED` or `EP::SELF_HOSTED_ENGINEERING_VERIFIED` PASS is
claimed without its own evidence. Existing receipts and historical migration
records remain unchanged.

The owning execution issue is [#1098](https://github.com/pcvantol/djconnect/issues/1098).
This assignment uses isolated branch `codex/ep-source-retirement`, based on
protected `origin/main` SHA `4d3d84aea55802be3751633e5a2393b60c4a6f05`.
The owning writer is Codex in `LANE_5 / ARCHITECT_5`; no other repository or
lane source is in scope. The host desired-state verification exited 0 against
manifest version 3.3.0 and onboarding package 4.5.2, with every required row
matching.

## Protected delivery and qualification

Implementation PR [#1099](https://github.com/pcvantol/djconnect/pull/1099)
merged through branch protection as
`60d5ee2e034323515092cd4100b1683f588e59fc`, derived from final candidate
`3cdc09c406b10d7cdd33b614f606c55c5ebcf191`. The prior main/base was
`4d3d84aea55802be3751633e5a2393b60c4a6f05`. Exact-head Trusted Delivery,
Software Assurance and owner authorization passed; the independent review of
the final candidate found no remaining quality or safety issues.

The candidate removes the embedded generic EP runtime, exclusive tests,
browser assets and old source-dependent CI. DJConnect product, Golden and
security checks, declarative project identity and historical extraction,
ADR, Prompt History and forensic records remain. Current EP compatibility
uses the published `engineering-platform==2.3.106` wheel with SHA-256
`9d25a53d75b61d43d665d9f8290a968dc3e63d12d2037eae8ef31ee810eb6694`
through the supported installed CLI/Server boundary. No live EP service,
consumer action, host data, credential, product release or deployment was
mutated. The new onboarding package is 4.5.3; the prior 4.5.2 distribution
bytes are unchanged.

The final clean-checkout candidate passed 1,463 product tests (7 skipped),
68 onboarding tests (7 skipped), 5 retirement guards, package/projection
checks, Ruff and Bandit. The clean product-test environment had no standalone
EP package or sibling checkout. No retained DJConnect production source changed,
so the per-changed-production-file coverage condition had no applicable file.
Main workflow [37107663006](https://github.com/pcvantol/djconnect/actions/runs/37107663006)
passed with exact-main coverage evidence. Reconciliation run
[37107808478](https://github.com/pcvantol/djconnect/actions/runs/37107808478)
published `POST_MERGE_RELEASE_EVIDENCE_QUALIFIED` for that merge SHA with no
findings and evidence digest
`b1e710935d9c38bf3b5e6438d3581970849e67c64100a6b5957e3ff4a7a14c68`.

The older [run 36965764691](https://github.com/pcvantol/djconnect/actions/runs/36965764691)
on prior main `4d3d84ae` remains failed and is not retroactively treated as
qualified; its PR #1097 has a failing HIGH_RISK owner-authorization status.
The current exact-main reconciliation above is separate evidence. The
governance-only Finalization PR for this assignment remains to be merged;
`REPOSITORY_FINALIZATION = COMPLETE` must be recorded only afterward.
