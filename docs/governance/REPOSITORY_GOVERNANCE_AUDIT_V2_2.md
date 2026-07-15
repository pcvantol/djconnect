# DJConnect Repository Governance Audit — Version 2.2

**Decision:** `DJCONNECT_REPOSITORY_GOVERNANCE_AUDIT_PASSED`
**Audit date:** 2026-07-15

All active DJConnect source and distribution repositories have merged separate
Version 2.2 governance adoption PRs. Each references central governance rather
than copying it and provides local bootstrap/status/roadmap/prompt navigation,
immutable history, lifecycle/reconciliation and native DoD/release profile.

| Repository | PR | Merge commit |
| --- | --- | --- |
| `djconnect-app` | #26 | `49279991e79c159655556461ad12e3e381eb9cfc` |
| `djconnect-windows` | #16 | `c8fc837d1f3653adc8c6f9cba8e600d42f425bc7` |
| `djconnect-pi` | #47 | `0ac1266ddc96dc87ed7e7ceb3aeb00e68c193014` |
| `djconnect-esp32` | #24 | `63ce22ede36e30bd09cc6baa17eef687dae466ab` |
| `djconnect-firmware` | #8 | `c525d6a3c69f8cf45bd5cbd06f2cbac2cac9082e` |
| `djconnect-api` | #46 | `71fdf4057f9dd3a5d17c358f84a63ca3f281fa92` |
| `djconnect-website` | #24 | `64f95dcb8a2cf2da523c46f08ed5b07fdcdf6daa` |
| `djconnect-app-releases` | #9 | `7224ee8888f7ea1d68a4b81aa718b77047837be8` |
| `djconnect-pi-releases` | #8 | `fe8c8086095549d55a3bb16e9d245472429f8790` |

Native profiles remain product-specific: Apple signed apps, Windows packages,
Pi Linux service/display bundles, ESP32 binaries/OTA, Worker/D1, website
hosting, and distribution manifests/checksums. Docker is not universal.
`NOT_FOUND` verification-runtime/release repositories and the out-of-scope SHA
reproducer received no adoption prompt.

This audit verifies governance adoption only; it does not authorize product
qualification, release execution or deployment.
