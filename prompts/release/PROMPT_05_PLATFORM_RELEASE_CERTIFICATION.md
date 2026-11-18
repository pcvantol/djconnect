# Platform Release Engineering — Prompt 5 of 5

## Status

`AWAITING_BURN_IN_EVIDENCE_AND_EXPLICIT_EXECUTION_AUTHORIZATION`

## Mission

Perform objective Platform Release Certification for an exact immutable
candidate evidence bundle. Consume the qualified Generation 1 release
capability, completed dry-run evidence, Verification Runtime, Software
Assurance, Trusted Delivery, deployment and Operational Burn-in evidence.

The reusable certification process and record contract are defined in
`docs/release/PLATFORM_RELEASE_OPERATIONAL_MODEL.md`. This prompt may execute
only after that process has its required candidate-bound evidence.

Do not redesign Platform Release Engineering. Do not publish, create tags,
create GitHub Releases, deploy, upload or announce a release.

## Required decision

Return exactly one decision:

```text
CERTIFIED
```

or

```text
CERTIFIED_WITH_ACCEPTED_EXCEPTIONS
```

or

```text
NOT_CERTIFIED
```

Certification must fail closed when required evidence is missing, stale,
misaligned or not bound to the exact candidate. An accepted exception requires
an approved engineering decision plus owner, mitigation, review date and
impact assessment; certification cannot create a new exception.
