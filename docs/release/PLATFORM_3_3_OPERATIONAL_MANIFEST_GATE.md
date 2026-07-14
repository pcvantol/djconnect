# Platform Release 3.3 — Operational Manifest Gate

Date: 2026-07-14  
Decision: `PLATFORM_RELEASE_3_3_MANIFEST_REAPPROVAL_REQUIRED_AFTER_PI_ARTIFACT_REBINDING`

## Result

The `3.3.0` Internal Release now has an exact-SHA, checksum-bound manifest
candidate: [`PLATFORM_3_3_CURRENT_MAIN_MANIFEST_PROPOSAL.json`](PLATFORM_3_3_CURRENT_MAIN_MANIFEST_PROPOSAL.json).

| Gate | Result |
| --- | --- |
| Required target set | Complete |
| Exact source SHA and artifact ID/checksum bindings | Complete and verified |
| Artifact publication | Complete for the applicable distribution repositories |
| Deployment evidence | Not started |
| Post-deployment smoke evidence | Not started |
| Explicit operational-manifest approval | Reapproval required after Pi artifact rebinding |

## Consequence

The previous approval is superseded by the qualified Pi artifact rebinding:
source `661e26e7`, checksum `6fa3f2f3de6062b8d69c48886bf04374592bbbe404a2856b89450e1acbe1422a`.
No release artifact has been deployed, installed, signed, OTA-applied or
smoke-tested. Each target remains a separate, manifest-bound operation.

## Next action

Obtain fresh explicit approval of the exact rebound manifest. Afterwards,
obtain explicit authorization for one target-scoped deployment. Its
post-deployment smoke may run only after that target's successful deployment;
other targets remain independent.
