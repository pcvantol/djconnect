# Platform Release 3.3 — Operational Manifest Gate

Date: 2026-07-14  
Decision: `PLATFORM_RELEASE_3_3_MANIFEST_PREPARED_PENDING_EXPLICIT_APPROVAL`

## Result

The `3.3.0` Internal Release now has an exact-SHA, checksum-bound manifest
candidate: [`PLATFORM_3_3_CURRENT_MAIN_MANIFEST_PROPOSAL.json`](PLATFORM_3_3_CURRENT_MAIN_MANIFEST_PROPOSAL.json).

| Gate | Result |
| --- | --- |
| Required target set | Complete, pending approval |
| Exact source SHA and artifact ID/checksum bindings | Complete and verified |
| Artifact publication | Complete for the applicable distribution repositories |
| Deployment evidence | Not started |
| Post-deployment smoke evidence | Not started |
| Explicit operational-manifest approval | Missing |

## Consequence

No deployment, signing, installation, OTA or smoke dispatch is currently
authorized. The artifact manifest is complete enough for maintainer review,
but `approval.state` remains `MISSING` until the exact manifest ID is
explicitly approved.

## Next action

The maintainer may explicitly approve
`release-3.3.0-internal-20260714`. After that approval, deployment and smoke
remain separate, target-scoped actions and must not start automatically.
