# Platform Release Deployment Architecture

Status: `ARCHITECTURE_CORRECTED`

Deployment consumes an artifact that a qualified GitHub Actions source build
already produced. It never compiles source on the destination.

| Target | Artifact source | Rule |
| --- | --- | --- |
| ESP32 | `pcvantol/djconnect-firmware` | HA polls published metadata, validates compatibility, exposes an Update entity and installs only after explicit user approval. |
| Raspberry Pi | `pcvantol/djconnect-pi-releases` | Deployment installs the published Pi artifact; Pi never builds it. |
| Apple / Windows | qualified native build artifact | Internal deployment records exact artifact SHA. |
| HA / API / Website | qualified GitHub Actions artifact | Deployment is an explicit graph node only if the selected profile deploys. |

Deployment evidence records artifact and target identity, timestamp, outcome
and recovery reference; it is distinct from build provenance.
