# Platform Release 3.3 — Artifact Manifest

All items below are dry-run plans. Their publication state is
`PLANNED_NOT_PUBLISHED`.

| Artifact class | Scope | State |
| --- | --- | --- |
| Candidate build artifacts | HA, API, Apple, Windows, Pi, ESP32, Website | planned in GitHub Actions; no publication |
| Distribution artifacts | firmware via `djconnect-firmware`; Pi via `djconnect-pi-releases`; Apple release surface | planned; no upload or release |
| Qualification evidence | verification, assurance, trusted delivery, coverage, platform qualification | coverage valid; runtime evidence retained locally |
| Release evidence | graph, version matrix, readiness, dry-run report, simulation manifest | generated in canonical documentation |
| Rollback checkpoints | release control, source candidates, distribution candidates | planned only; tags not applicable in simulation |

ESP32 and Pi targets consume published artifacts and never create source
builds. The firmware manifest for the existing public binary was deliberately not
rewritten: a 3.3.0 firmware entry without a real binary and checksum would be
false evidence. Apple and Pi release scripts were run only in dry-run mode.
