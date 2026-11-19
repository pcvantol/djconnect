# Platform Release 3.3 — Release Completion Record

**Decision:** `RELEASE_COMPLETE`
**Completion date:** 2026-07-19
**Release identifier:** `release-3.3.0-internal-20260714`
**Certification reference:** `CERT-3.3.0-20260719` — `CERTIFIED`
**Release owner:** DJConnect Platform Release Engineering
**Maintenance owner:** DJConnect Product Engineering, with component owners
responsible for their supported maintenance deliveries

## Completion summary

Platform Release 3.3 is formally complete. The release completed Development,
Verification, Qualification, Internal target deployment, Operational Burn-in
and Release Certification for the immutable manifest identified above. This
record closes active release execution and transfers the certified 3.3 train to
Maintenance. It does not create a new release, deployment, manifest or version
change.

## Supported component versions

| Component | Supported version |
| --- | --- |
| DJConnect Home Assistant integration | `3.3.1` |
| DJConnect API | `3.3.0` |
| DJConnect Apple clients | `3.3.0` |
| DJConnect Windows client | `3.3.0` |
| DJConnect Raspberry Pi client | `3.3.0` |
| DJConnect ESP32 firmware | `3.3.0` |
| DJConnect website | `3.3.0` |

The component identities and artifacts remain bound to
`PLATFORM_3_3_CURRENT_MAIN_MANIFEST_PROPOSAL.json`. The Home Assistant `3.3.1`
patch is a compatible component patch within Platform Release 3.3, not a new
platform release.

## Maintenance transition

Maintenance is limited to:

- defect fixes;
- security updates;
- compatible component patch releases; and
- operational support.

Each maintenance delivery remains within the Platform 3.3 Major.Minor train,
keeps its own traceable component evidence, and must not retroactively alter
this completion record. Product Engineering and Innovation Engineering resume
their normal active focus; release engineering does not remain an active work
stream for Platform Release 3.3.

## Reopening criteria

The completed release may be reopened only for evidence that invalidates its
certification, supported-component set or completion decision, or for an
in-scope release-blocking defect or security issue requiring coordinated
release response. A reopening records its reason and affected scope, preserves
this record, and restarts at the earliest invalidated lifecycle stage.

Platform-level architectural changes do not reopen Platform Release 3.3; they
require a new Platform Release lifecycle.
