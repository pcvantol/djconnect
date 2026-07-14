# Post-Deployment Smoke Evidence Schema

Status: `ARCHITECTURE_ALIGNED`  
Schema version: `1`

Every manifest-allowlisted post-deployment smoke target produces one immutable,
redacted evidence record. It is deployment evidence, distinct from build, CI,
coverage, Verification, Software Assurance, Trusted Delivery and qualification
evidence. A smoke workflow may read those records but may never replace or
mark them qualified.

## Required fields

| Field | Meaning |
| --- | --- |
| `repository` | Repository that owns the deployed component. |
| `candidate_sha` / `platform_version` / `manifest_id` | Exact release identity. |
| `deployment_workflow_run` / `smoke_workflow_run` | Immutable execution references. |
| `runner_identity` | Relay identity and labels, without secrets. |
| `target` / `route_type` / `protocol` / `endpoint_class` | Manifest-bound target and canonical route classification. |
| `authentication_mode` | Redacted authentication class, never a credential. |
| `artifact_id` / `artifact_sha256` | Artifact identity bound to the manifest. |
| `expected_version` / `observed_version` | Version read-back comparison. |
| `health_result` / `websocket_result` | Route-health results; WebSocket is separately recorded when applicable. |
| `startup_marker_result` / `crash_log_result` | Bounded startup and crash-finding result. |
| `retry_count` / `stabilization_window` / `timestamps` | Finite execution timing. |
| `final_result` / `failure_classification` / `recovery_reference` | Decision and safe recovery pointer. |

For Apple iOS deployment, the record additionally contains the direct typed
target (`macbook`, `iphone` or `ipad`) and the manifest-bound
`paired_watch_validation` result where applicable. A Watch has no independent
artifact or smoke target in Generation 1.

## Redaction and integrity

Evidence must not include credentials, tokens, full sensitive URLs, private IP
details unless policy expressly permits them, complete logs, personal data,
provisioning profiles or signing material. Log findings are redacted and may
use hashes or permitted bounded excerpts. The record carries the exact
manifest/artifact binding and final target result; stale, missing or
inconsistent evidence fails closed for required targets.
