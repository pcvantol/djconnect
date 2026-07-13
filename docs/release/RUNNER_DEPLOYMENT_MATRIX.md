# Runner Deployment Matrix

Date: 2026-07-13

| Repository | Workflow / job class | Platform action | Current runner | Required qualified runner | Artifact / target | Current state |
| --- | --- | --- | --- | --- | --- | --- |
| `djconnect` | HA integration CI and verification Docker release | HA package/tests; verification image | GitHub-hosted Linux | Home Assistant / Deployment | integration package; internal HA / verification image | Migration required |
| `djconnect-api` | `ci-cd.yml` validate/deploy | Worker test and Cloudflare deployment | GitHub-hosted Linux | Deployment | Worker deployment | Migration required |
| `djconnect-app` | `ci.yml`, `public-unsigned-release.yml`, `testflight-beta.yml` | Apple build/archive | GitHub-hosted macOS | Apple | developer build/archive | Migration required; public/TestFlight paths remain out of internal release scope |
| `djconnect-windows` | `ci.yml`, `public-unsigned-release.yml` | Windows package/build | GitHub-hosted Windows/macOS/Linux | Windows | unsigned internal package / Windows VM | Migration required |
| `djconnect-pi` | `validate.yml`, `publish-release.yml` | Pi package/build | GitHub-hosted Linux | Pi | Pi package / `rbpi-djconnect.local` validation | Migration required |
| `djconnect-esp32` | `ci.yml`, `release-firmware.yml` | PlatformIO firmware build | GitHub-hosted Linux | Firmware | firmware binary/checksum/internal OTA artifact | Migration required |
| `djconnect-website` | `validate.yml`, `deploy-pages.yml` | website build/Pages deploy | GitHub-hosted Linux | Deployment | Pages deployment | Migration required |
| `djconnect-firmware` | governance / trusted delivery | distribution governance only | GitHub-hosted Linux | No platform build runner | release metadata | No build migration |
| `djconnect-app-releases` | governance / trusted delivery | distribution governance only | GitHub-hosted Linux | No platform build runner | release metadata | No build migration |
| `djconnect-pi-releases` | governance / trusted delivery | distribution governance only | GitHub-hosted Linux | No platform build runner | release metadata | No build migration |

GitHub-hosted governance workflows are retained because they do not compile or
publish an internal platform release. Any job that builds, packages, signs,
deploys or validates a platform artifact moves to the role listed above.
