# Platform Device Distribution and Provisioning Architecture

**Status:** Canonical target architecture; no runtime, pairing, renderer or OTA implementation change.

## Canonical model

```text
Product catalog -> Device Installer -> qualified firmware manifest/artifact
-> platform install mechanism -> network provisioning -> device startup
-> existing pairing code -> Home Assistant pairing -> Renderer Host
```

`devices.djconnect.dev` is a standalone Device Installer application. It is
independently released and deployed from the marketing website. It presents
products first, consumes published metadata only and does not own credentials,
runtime state, pairing rules, OTA behavior or platform firmware logic.

## Ownership

| Owner | Responsibility | Exclusion |
| --- | --- | --- |
| `djconnect-device-installer` | Product catalog UI, compatibility selection, manifest consumption and platform flashing/bootstrap orchestration | Firmware source, artifacts, pairing and Runtime logic |
| `djconnect-firmware` | All physical-device distribution artifacts, manifests, channels, checksums, OTA assets and release notes | Source builds, product UX and Runtime logic |
| Platform source repositories | Source, build, qualification and CI | Public distribution truth or installer UX |
| `djconnect` | Existing pairing and OTA orchestration contracts | Installer business logic or artifact creation |

No hardware platform bypasses `djconnect-firmware`. Raspberry Pi renderer
packages may remain built in their source repository, but their installer-safe
bootstrap reference and public device-distribution metadata are published
through `djconnect-firmware`.

## Product catalog

The primary catalog vocabulary is a supported product, not a chip or board.
Each product declares its compatible hardware variants, required capabilities,
install mechanism, supported channel and recovery guidance. The catalog may
show technical hardware compatibility after a product choice; it must not make
users select an implementation merely to begin installation.

## Platform installation adapters

| Platform | Canonical install | Provisioning deviation |
| --- | --- | --- |
| ESP32 / ESP32-S3 | ESP Web Tools and browser WebSerial from a qualified manifest | Browser/device connection only; then common network and pairing flow |
| RP2 / Pico 2 W | Same Installer catalog; WebUSB/WebSerial when supported, otherwise verified UF2 download and bootloader copy | Bootloader transfer may be manual; no different pairing model |
| Raspberry Pi Zero 2 W / Pi 5 | Raspberry Pi Imager writes official Raspberry Pi OS Lite; first-boot bootstrap installs the selected renderer and systemd service | OS imaging and first boot replace microcontroller flashing |

No DJConnect-specific flashing protocol is introduced. The Installer adapts to
platform-standard transports and presents one recovery-oriented product flow.

## Raspberry Pi maintenance posture

Official Raspberry Pi OS Lite plus a versioned, qualified bootstrap is the
default. It reduces image rebuilds, security-patch lag, board-image matrices and
support burden while keeping Pi Zero 2 W and Pi 5 on one provisioning model.
Custom images are a future exception only after a separate appliance decision,
maintenance owner, update/recovery evidence and clear proof that bootstrap is
insufficient.

## Release and qualification

Every catalog entry resolves to an exact artifact identity, checksum, channel,
platform compatibility and recovery reference. Source repositories qualify
their exact artifact before publication; `djconnect-firmware` publishes only
that evidence-bound result. Stable and beta are common channel concepts, not
ESP-only concepts. The installer never builds firmware or invents compatibility.

## Delivery roadmap

1. Define the catalog/manifest schema and product-to-hardware compatibility.
2. Establish the standalone installer repository and static deployment path.
3. Add ESP, RP2 and Pi adapters against existing qualified artifacts.
4. Qualify one product per platform, including install, provisioning, pairing,
   update/recovery and renderer-host startup.
5. Promote variants through beta then stable under existing release governance.
