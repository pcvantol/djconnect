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

The qualified macOS runner is also the single approved deployment relay for
the maintainer's private Pi/ESP32 network. This is a narrow deployment-only
exception: it consumes qualified artifacts, can initiate a Home Assistant
Update-entity OTA request and can read back a Pi SSH or ESP32 web-runtime
health result. It never compiles Pi/ESP32 source, generates artifacts or
publishes a release.

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
