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

For the maintainer's private network, the qualified self-hosted macOS runner
is the controlled deployment relay. It may use target-scoped credentials only
in an explicit deployment job to start a Pi exact-artifact install or request
an ESP32 OTA through the Home Assistant Update entity. It then reads back Pi
runtime or ESP32 internal-IP web-server health. The relay never builds source,
generates artifacts or publishes a release; Pi and ESP32 remain artifact
consumers and Verification targets.

Deployment evidence records artifact and target identity, timestamp, outcome
and recovery reference; it is distinct from build provenance.
