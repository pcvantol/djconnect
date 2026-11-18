# Platform Release 3.3 — ESP32 Deployment Completion

Date: 2026-07-15
Target: `esp32_lilygo_t_embed_s3`
Result: `DEPLOYMENT_OPERATIONAL`

## Exact binding

- Manifest: `release-3.3.0-internal-20260714`
- Source candidate: `9f8a32482b8ea9fb322a29688955f5a4f26b001d`
- Artifact:
  `release-asset:pcvantol/djconnect-firmware:v3.3.0:djconnect-lilygo-t-embed-s3-v3.3.0.bin`
- SHA-256: `c25444d3ef414489848fd2d8de624785c82eb90195cc861bcb63085e0df3ceeb`

## Evidence

- Deployment workflow: [29446964025](https://github.com/pcvantol/djconnect-esp32/actions/runs/29446964025)
  completed successfully after validating the approved manifest binding and
  requesting the Home Assistant Update-entity OTA operation.
- Post-deployment smoke: [29447045601](https://github.com/pcvantol/djconnect-esp32/actions/runs/29447045601)
  completed successfully after bounded polling for the firmware-update restart.
- The smoke verified version `3.3.0` through Home Assistant and through the
  device's local web/API surface. The direct local-device read-back is `PASS`.

## Completion decision

The ESP32 target is complete for this Internal Release. No other target is
implied by this result. Each remaining target still requires its own exact
authorization, manifest-bound deployment and immediate target-scoped smoke.
