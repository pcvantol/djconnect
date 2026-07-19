# Verification Platform and Release Engineering Boundary

Status: `ARCHITECTURE_CORRECTED`

| Domain | Owner |
| --- | --- |
| Physical device and runtime validation, hardware qualification, functional/integration testing, and behavioural burn-in | Verification Platform |
| Reproducible builds, artifacts, signing, version alignment, release metadata, candidate SHA validation, deployment orchestration, bounded non-destructive post-deployment smoke, operational burn-in evidence collection and Release Certification | Platform Release Engineering |

Release Engineering consumes valid Verification evidence for the candidate SHA.
It does not repeat physical-device validation merely to build or publish an
internal release. A profile can explicitly require post-release runtime
validation.

Post-deployment smoke validation is not that full runtime validation. It is
limited to canonical-route reachability, read-only protocol handshakes, version
read-back, bounded startup health and immediate-crash absence. It does not
invoke functional scenarios, hardware qualification, destructive testing or
behavioural burn-in owned by the Verification Platform. Operational burn-in
uses those validated signals and existing target operations as certification
evidence; it does not duplicate Verification Platform scenarios.
