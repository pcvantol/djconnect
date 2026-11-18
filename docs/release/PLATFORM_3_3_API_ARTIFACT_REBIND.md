# Platform Release 3.3 — API Artifact Rebind

Date: 2026-07-14
Decision: `PLATFORM_RELEASE_3_3_API_ARTIFACT_REBIND_APPROVED`

## Exact replacement binding

| Field | Value |
| --- | --- |
| Manifest | `release-3.3.0-internal-20260714` |
| Target | `cloudflare_workers_production` |
| Repository | `pcvantol/djconnect-api` |
| Source candidate | `6f6dee8a6edf72b8a48fa347ef587ede2976badd` |
| Artifact ID | `8323208436` |
| SHA-256 | `f9d8c29787297a939d16e6f3fab3f9cd4455518def4565830b5ca57f76a80819` |
| Artifact workflow | [29363742261](https://github.com/pcvantol/djconnect-api/actions/runs/29363742261) |

## Evidence and rationale

The artifact workflow completed successfully after main validation. It embeds
the immutable source SHA into the Worker health response. The deployment
workflow now validates the approved central manifest instead of unconditionally
refusing dispatch, and the post-deployment smoke now verifies the exact
manifest release version, source SHA, Worker runtime and public health route.

The earlier API artifact `8309742606` could not provide this runtime identity.
It is replaced, not deployed. This rebind does not change the completed
Raspberry Pi deployment evidence.

## Authorization boundary

The rebound exact manifest received fresh explicit approval at
`2026-07-14T20:03:33Z`. A separate authorization is still required before a
remaining target deployment can be dispatched. No deployment or smoke is
started by this record.
