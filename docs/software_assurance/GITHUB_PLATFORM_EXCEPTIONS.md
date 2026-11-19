# GitHub Platform Exceptions

## TD-GITHUB-001 — GitHub native SHA enforcement compatibility

| Field | Record |
| --- | --- |
| Classification | `GITHUB_PLATFORM_COMPATIBILITY_EXCEPTION` |
| Scope | Repository Actions setting `sha_pinning_required` |
| Status | Accepted |
| Reason | GitHub reproducibly returns pre-job `startup_failure` for the tested valid cross-repository reusable-workflow graph. |
| Evidence | `SHA_ENFORCEMENT_MINIMAL_REPRODUCER.md`, `GITHUB_SHA_ENFORCEMENT_SUPPORT_CASE.md`, recursive closure evidence and representative platform runs. |
| Compensating controls | Recursive immutable workflow closure, terminal action SHA validation, canonical pin registry and consistency validation, Trusted Delivery qualification, read-back and representative CI. |
| Review trigger | GitHub platform change, GitHub Support response, or future Platform Evolution. |

This is neither DJConnect technical debt nor a DJConnect platform defect. It
does not weaken immutable workflow governance: all remote actions and reusable
workflow references remain subject to the canonical recursive validator.
