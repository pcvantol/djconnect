# Verification Platform and Release Engineering Boundary

Status: `ARCHITECTURE_CORRECTED`

| Domain | Owner |
| --- | --- |
| Physical device and runtime validation, hardware qualification, functional/integration testing, burn-in | Verification Platform |
| Reproducible builds, artifacts, signing, version alignment, release metadata, candidate SHA validation, publication and deployment orchestration | Platform Release Engineering |

Release Engineering consumes valid Verification evidence for the candidate SHA.
It does not repeat physical-device validation merely to build or publish an
internal release. A profile can explicitly require post-release runtime
validation.
