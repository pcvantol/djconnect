# Platform Release Engineering — Prompt 5 of 5

## Status

`AWAITING_EXPLICIT_AUTHORIZATION`

## Mission

Perform objective Platform Release Certification for an exact immutable
candidate evidence bundle. Consume the qualified Generation 1 release
capability, completed dry-run evidence, Verification Runtime, Software
Assurance and Trusted Delivery evidence.

Do not redesign Platform Release Engineering. Do not publish, create tags,
create GitHub Releases, deploy, upload or announce a release.

## Required decision

Return exactly one decision:

```text
PLATFORM_RELEASE_CERTIFIED
```

or

```text
PLATFORM_RELEASE_NOT_CERTIFIED
```

Certification must fail closed when required evidence is missing, stale,
misaligned or not bound to the exact candidate.
