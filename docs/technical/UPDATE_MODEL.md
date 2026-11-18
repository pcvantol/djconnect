# Update Model

## ESP32 Firmware OTA

`CONFIRMED_CODE` HA selects firmware metadata from GitHub release/manifest code
and calls ESP32 `/api/device/ota`. ESP32 downloads firmware, follows redirects,
verifies SHA256, writes OTA partition and reboots after success.

`TARGET_ARCHITECTURE` Native and ESPHome firmware variants use this same
manifest, stable/beta channel and OTA ownership model. The manifest identifies
the qualified board/variant; HA and the Device Installer do not infer or own
the build technology. See `ESPHOME_FIRMWARE_PLATFORM_ARCHITECTURE.md`.

## Pi Updates

`CONFIRMED_CODE` Pi updater downloads release bundle/checksum, installs under
an install root such as `/opt/djconnect`, refreshes systemd units, keeps a
bounded number of releases and writes updater status.

## Windows Updates

`DOCUMENTED_ONLY` Windows release notes and workflows indicate public unsigned
release artifacts and release repos. No in-app auto-updater path was fully
confirmed in code during this pass.

## Apple Updates

`DOCUMENTED_ONLY` Apple distribution/update path is through app distribution
surfaces such as TestFlight/App Store equivalents. Exact implementation details
were not confirmed.

## HA Updates

`DOCUMENTED_ONLY` HA is a HACS custom integration. Version is `3.2.50` in code.

## Central API

`CONFIRMED_CODE` Cloudflare Worker deploys via wrangler. No runtime self-update
path exists.

## Verification Mapping

`RELEASE-*`, `ESP-*`, `PI-*`, `WINDOWS-*`, `APPLE-*`, `SETUP-004`.
