# Platform Release Runner Architecture

Status: `ARCHITECTURE_CORRECTED`

GitHub Actions is the only platform-build execution surface. Codex is the
control plane and never runs compilers, package builders, signing tools or
target-device builds.

| Build class | Canonical runner |
| --- | --- |
| Apple application | qualified self-hosted macOS |
| Windows application | qualified self-hosted Windows |
| Home Assistant integration | GitHub-hosted Linux |
| Central API | GitHub-hosted Linux |
| Website | GitHub-hosted Linux |
| ESP32 firmware | GitHub-hosted Linux |
| Raspberry Pi client package | GitHub-hosted Linux |
| Private-network deployment relay | qualified self-hosted macOS; deployment-only |

The Apple and Windows exceptions are native-toolchain requirements. A physical
Pi or ESP32 is a deployment/Verification target, not a source build runner.

The qualified macOS runner has exactly three bounded capabilities: Apple Native
Build, Private-Network Deployment Relay and Apple Secure Distribution Relay.
The first is a native build capability. The latter two are distinct
deployment-only capabilities with separate jobs, permissions, secrets,
workspaces, target allowlists and evidence. Private-Network Deployment Relay
consumes qualified artifacts, can initiate a Home Assistant Update-entity OTA,
install the qualified Home Assistant integration on the maintainer's production
Home Assistant Pi 5, and read back Pi SSH, Home Assistant runtime or ESP32 web
health. Apple Secure Distribution Relay locally signs only qualified unsigned
Apple artifacts and deploys them to allowlisted private Apple devices. Neither
relay compiles Pi/ESP32/HA source, generates artifacts or publishes a release.

## Canonical workflow mapping

| Repository | Build/release workflow | Canonical build class |
| --- | --- | --- |
| `djconnect` | `validate.yaml`, verification Docker release | GitHub-hosted Linux |
| `djconnect-api` | `ci-cd.yml` | GitHub-hosted Linux |
| `djconnect-app` | `ci.yml`, release workflows | self-hosted macOS |
| `djconnect-windows` | `ci.yml`, release workflow | self-hosted Windows |
| `djconnect-pi` | `validate.yml`, `publish-release.yml` | GitHub-hosted Linux |
| `djconnect-esp32` | `ci.yml`, `release-firmware.yml` | GitHub-hosted Linux |
| `djconnect-website` | `validate.yml`, `deploy-pages.yml` | GitHub-hosted Linux |
