# ADR-0017: ESPHome is the preferred firmware platform for supported DJConnect ESP hardware

## Status

Accepted

## Date

2026-07-30

## Context

DJConnect needs reliable hardware enablement for supported ESP devices. A
community-maintained ESPHome implementation has proven complete initialization
of the ESP32-S3-BOX-3 hardware stack where an independently implemented native
driver path did not initialize the display beyond its backlight.

DJConnect must preserve the existing Home Assistant-owned Runtime, pairing,
renderer contracts, device capabilities, transport protocols and firmware
distribution model. The decision is about firmware implementation and hardware
enablement only. It must also not conflate a DJConnect firmware device with an
ESPHome Voice Host managed as a Home Assistant voice host.

## Decision

ESPHome is a first-class supported **Firmware Platform** and the preferred
hardware-enablement foundation for each DJConnect ESP board that has passed the
qualification gate. It is also a **Device Enablement Capability**, not a new
Runtime, Renderer Platform, pairing model or Home Assistant integration.

`pcvantol/djconnect-esp32` owns the ESPHome source tree, reusable DJConnect
packages, custom components, board declarations, firmware composition and
platform-specific code. `pcvantol/djconnect-firmware` owns only compiled,
immutable distribution outputs: manifests, stable/beta OTA artifacts, Web
Installer artifacts, checksums, release notes and rollback metadata.

The accepted hardware baseline is an attributed upstream community reference
pinned to a reviewed commit or release. DJConnect extends that baseline through
thin packages and custom components; it does not fork or rewrite low-level
display, touch, buttons, audio, microphones, PSRAM or board networking unless
an approved, board-specific defect requires it. Upstream tracking is never
continuous: an update is proposed, pinned, qualified and promoted separately.

The canonical layering is:

```text
Pinned community ESPHome hardware baseline
        ↓
DJConnect board packages and components
        ↓
DJConnect transport and device identity
        ↓
Existing pairing and renderer contracts
        ↓
Runtime projection
        ↓
Device UI
```

Native firmware remains a supported legacy/alternative implementation only
while a board-specific migration decision says so. It must not become the
default low-level hardware path for a board that has a qualified ESPHome
baseline.

## Consequences

- Firmware source and public firmware distribution remain separate repositories.
- A board is published only after boot, display/no-white-screen, touch,
  controls, audio/microphone where fitted, PSRAM, networking/provisioning,
  pairing, runtime connection, renderer operation, OTA and reboot recovery are
  qualified on that exact source/baseline/artifact combination.
- Stable and beta use the existing `djconnect-firmware` manifest and OTA
  architecture. A manifest declares the firmware variant and board identity;
  the Device Installer remains firmware-agnostic and consumes that manifest
  through device catalog -> ESP Web Tools -> provisioning -> pairing.
- The firmware neither gains ownership of credentials, intelligence nor
  protocol decisions, and no present runtime contract changes.

## Alternatives considered

### Continue independent low-level native drivers as the default

Rejected. It duplicates proven board enablement and leaves DJConnect carrying
the highest-risk, least differentiating hardware work.

### Treat ESPHome as an experimental reference only

Rejected. The successful hardware initialization is material evidence and the
platform needs a maintained, releasable path rather than an informal example.

### Make the installer ESPHome-specific

Rejected. Installer ownership is artifact/manifest consumption; it must remain
able to install any qualified DJConnect firmware variant.

## Related documents

- `docs/technical/ESPHOME_FIRMWARE_PLATFORM_ARCHITECTURE.md`
- `ARCHITECTURE_PRINCIPLES.md`
- `REPOSITORY_OWNERSHIP.md`
- `PRODUCT_ROADMAP.md`
- `PLATFORM_EVOLUTION_BACKLOG.md`
