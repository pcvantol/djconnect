# Platform Release 3.3 — Artifact Manifest

Artifact publication is approved as the required distribution destination for
the requested `3.3.0` Internal Release. No 3.3 artifact exists yet, so the
current execution state is `PUBLICATION_APPROVED_ARTIFACTS_PENDING`.

| Artifact class | Scope | State |
| --- | --- | --- |
| Candidate build artifacts | HA, API, Apple, Windows, Pi, ESP32, Website | exact-SHA production artifacts pending |
| Distribution artifacts | firmware via `djconnect-firmware`; Pi via `djconnect-pi-releases`; unsigned Apple handoff via `djconnect-app-releases` | publication destination approved; no 3.3 upload or release yet |
| Qualification evidence | verification, assurance, trusted delivery, coverage, platform qualification | coverage valid; runtime evidence retained locally |
| Release evidence | graph, version matrix, readiness, dry-run report, simulation manifest | generated in canonical documentation |
| Rollback checkpoints | release control, source candidates, distribution candidates | planned only; tags not applicable in simulation |

ESP32 and Pi targets consume published artifacts and never create source
builds. The three distribution repositories were cleared of their pre-3.3
GitHub Release records and release-assets on 2026-07-14; source repositories
and tags were preserved. The next release records must contain only immutable
3.3 artifacts with their exact checksums.

`djconnect-app-releases` may publish only the exact unsigned Apple handoff
artifact and non-secret integrity metadata. It must never publish signed Apple
artifacts or represent TestFlight, App Store or Mac App Store distribution.
