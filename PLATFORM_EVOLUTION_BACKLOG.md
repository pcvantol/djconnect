# DJConnect Platform Evolution Backlog

**Owner:** Platform Evolution
**Status:** Canonical active backlog

Platform Evolution is supporting work, not the primary roadmap. Items enter
this backlog only after objective evidence shows that product delivery, safety
or governed operations are constrained.

| Initiative | Priority | Status | Dependencies | Promotion path |
| --- | --- | --- | --- | --- |
| Component Release Mode | P2 | Backlog | release evidence and current manifest model | bounded architecture review if contracts change |
| GitHub Actions retention policy | P2 | Backlog | operational evidence and governance review | governed workflow change |
| Public distribution: Apple | P1 | Backlog | qualified Internal Release consumers and explicit authorization | release-operational work |
| Public distribution: Windows | P1 | Backlog | qualified Internal Release consumers and explicit authorization | release-operational work |
| Public HACS distribution | P1 | Backlog | fresh candidate and release authorization | release-operational work |
| Firmware OTA publication and staged rollback | P1 | Backlog | manifest-bound consumer qualification | release-operational work |
| Website production deployment and announcements | P1 | Backlog | approved manifest and consumer qualification | release-operational work |
| Technical Debt Assessment Engine | P2 | Backlog | product-delivery evidence and Software Assurance compatibility | scoped Platform Evolution proposal |
| SBOM generation | P2 | Backlog | Trusted Delivery compatibility assessment | scoped Platform Evolution proposal |
| Release Health and observability | P2 | Backlog | operational release evidence | scoped Platform Evolution proposal |
| Platform diagnostics | P3 | Backlog | privacy and redaction review | scoped Platform Evolution proposal |
| Future governance improvements | P3 | Backlog | governance evidence | governance review |

## Current operational work

Platform Release 3.3 Internal is **Operational** but remains blocked. It needs
a fresh exact-SHA candidate manifest, qualified manifest-bound deployment and
smoke consumers for every required target, and explicit dispatch authorization.
It is documented in `docs/release/PLATFORM_RELEASE_MANAGEMENT_SUMMARY.md`; it
does not become a fourth program.
