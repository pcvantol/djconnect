# ADR-0018: Platform Device Distribution and Provisioning

## Status

Accepted

## Decision

DJConnect has one product-facing Device Installer at `devices.djconnect.dev`,
owned by the future independent `djconnect-device-installer` repository. It is
separate from the marketing website, has its own deployment cadence and
contains no DJConnect Runtime, pairing, credential, OTA or firmware business
logic. It consumes only qualified published catalog and manifest metadata.

`djconnect-firmware` is the single authoritative public distribution repository
for every DJConnect physical-device artifact: native and ESPHome images, RP2
firmware, Raspberry Pi bootstrap artifacts and their referenced renderer
packages, manifests, OTA assets, checksums, release notes and stable/beta
channel metadata. Platform repositories continue to own source, builds,
qualification and CI; no platform bypasses this distribution boundary.

The catalog is product-first (for example Voice Controller, Editorial Display,
DJPrint, Wall Panel and Kitchen Display). Hardware, board and installer
technology remain an explicit compatibility detail, never the primary product
selection surface.

## Consequences

- ESP uses standard ESP Web Tools/WebSerial manifest installation followed by
  existing network provisioning and pairing. No DJConnect-specific flashing
  protocol is justified.
- RP2 participates in the same Installer experience. It uses browser WebUSB or
  WebSerial only where its bootloader/browser combination supports it, with a
  signed/checked UF2 download-and-copy fallback.
- Raspberry Pi Zero 2 W and Pi 5 use Raspberry Pi Imager with official
  Raspberry Pi OS Lite, then a qualified first-boot bootstrap that installs the
  selected renderer, registers systemd and enters existing pairing. DJConnect
  does not maintain custom Pi images unless a later appliance-specific decision
  proves that bootstrap cannot meet qualification or maintenance requirements.
- The canonical human journey is Install -> Network Provisioning -> Device
  Startup -> Pairing Code -> Home Assistant Pairing -> Renderer Host. A
  platform may vary only in its physical flash or OS-write mechanism.

## Alternatives considered

- Putting installer pages in the marketing website: rejected; installer
  deployment and safety must not depend on marketing releases.
- Per-platform artifact repositories: rejected; they fragment channel,
  checksum, release-note and catalog truth.
- Custom Pi images by default: rejected; they multiply OS, security and image
  maintenance. Official OS Lite plus bootstrap is the lean default.

## Related documents

- `docs/technical/DEVICE_DISTRIBUTION_AND_PROVISIONING_ARCHITECTURE.md`
- `docs/adr/0017-esphome-firmware-platform.md`
