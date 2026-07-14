# Platform Release 3.3 — Operational Manifest Gate

Date: 2026-07-14  
Decision: `PLATFORM_RELEASE_3_3_MANIFEST_APPROVED_DEPLOYMENT_DISPATCH_PENDING`

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
| Explicit operational-manifest approval | Approved at `2026-07-14T15:28:33Z` |

## Consequence

The manifest is approved, but no deployment, signing, installation, OTA or
smoke dispatch has been authorized or started. Each target remains a separate,
manifest-bound operation.

## Next action

Obtain explicit authorization for one target-scoped deployment. Its
post-deployment smoke may run only after that target's successful deployment;
other targets remain independent.
