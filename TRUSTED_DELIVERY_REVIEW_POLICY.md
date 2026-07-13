# Trusted Delivery Review Policy

Status: proposed implementation policy
Owner: `pcvantol/djconnect`
Applies to: active repositories discovered in `REPOSITORY_OWNERSHIP.md`

## Risk classes

| Class | Approval | Mandatory conditions | Merge behavior |
| --- | --- | --- | --- |
| `LOW_RISK` | None | PR, current branch, required checks, risk classification, qualification, resolved conversations and no blocking finding. | Trusted Delivery App may enable auto-merge. |
| `NORMAL_RISK` | None | LOW_RISK conditions plus Balanced qualification evidence and a completion/report reference when the scoped policy requires one. | Trusted Delivery App may enable auto-merge. |
| `HIGH_RISK` | Trusted Delivery Owner Authorization | NORMAL_RISK conditions plus protected-path finding, technical Trusted Delivery PASS, SHA-bound Owner Authorization evidence and no emergency exception. | Merge remains disabled until both required statuses pass. |

## Protected-path policy

The classifier assigns `HIGH_RISK` when a change alters any protected control
surface, including:

- Platform Strategy and Foundation: `PLATFORM_STRATEGY.md`,
  `DJCONNECT_CONSTITUTION.md`, `FOUNDATION_INDEX.md`,
  `CANONICAL_REFERENCES.md`, `PRODUCT_VISION.md`, `DESIGN_*.md`,
  `ARCHITECTURE_*.md`, `DOMAIN_MODEL.md`, `CLIENT_CAPABILITY_MATRIX.md`;
- Software Assurance control policy: `SOFTWARE_ASSURANCE_GOVERNANCE.md`,
  `SOFTWARE_ASSURANCE_IMPLEMENTATION*.md`, `SOFTWARE_ASSURANCE_QUALITY_GATES.md`,
  `software_assurance/policy/**`, `software_assurance/schema/**`,
  `software_assurance/templates/**` and `tools/software_assurance/**`;
- Verification Platform and Runtime control surfaces: `docs/verification/**`,
  `tools/verification/**`, verification policy/configuration and canonical
  verification prompts;
- Repository and GitHub governance: `REPOSITORY_OWNERSHIP.md`,
  `PLATFORM_GOVERNANCE.md`, `CI_CD_RELEASE_GOVERNANCE.md`, `CODEOWNERS`,
  `.github/CODEOWNERS`, ruleset/branch-protection definitions and Dependabot
  configuration;
- secrets, signing and release-trust configuration: secret/credential handling,
  signing keys or provenance settings, environment protection, release-token
  scope, release publication permissions and release-governance definitions;
- workflow behavior that changes permissions, event trust boundaries,
  `pull_request_target` use, secret/environment access, signing, publication,
  deployment or required-check/qualification semantics.

An ordinary immutable action-reference migration is not HIGH_RISK merely
because it edits a workflow or release workflow. It remains LOW_RISK or
NORMAL_RISK when it preserves triggers, permissions, secrets, signing,
publication behavior and governance semantics. A classifier must inspect the
semantic diff rather than use a broad `.github/workflows/**` path match.

## Qualification contract

`Trusted Delivery qualification` is a required, source-bound check with a
unique check name. It must publish the evaluated head SHA, risk class,
protected-path findings, current-branch result, required-check results,
conversation-resolution result, blocking-finding result, completion-evidence
reference and, for HIGH_RISK, the owner-review identity and reviewed SHA.

The check fails closed if risk classification or any required evidence is
missing. HIGH_RISK authorization is performed by the internal Trusted Delivery
Owner Authorization workflow, not a GitHub review. It may not infer success
from a bot, stale SHA, or prior authorization. The App may enable auto-merge
only after every required technical and governance status passes.

## Emergency override

An owner emergency override is exceptional and must be recorded in the PR:
reason, affected risk, head SHA, timestamp, owner identity, compensating
verification and follow-up review date. It cannot be represented as a routine
direct push and does not waive required evidence without an explicit audit
record.
