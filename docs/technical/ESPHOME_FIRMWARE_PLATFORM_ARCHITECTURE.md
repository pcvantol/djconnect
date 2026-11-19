# ESPHome Firmware Platform Architecture

**Status:** Canonical target architecture; implementation and runtime behavior unchanged.

## Scope

This document defines the long-term ESPHome firmware architecture for
DJConnect-supported ESP hardware. It preserves all existing DJConnect Runtime,
pairing, renderer, transport and Home Assistant integration contracts.

It does not describe ESPHome Voice Hosts. Those remain independent Home
Assistant-managed Voice Interaction Hosts and are not DJConnect device
firmware.

## Platform position and ownership

ESPHome is a first-class, preferred Firmware Platform for an exact board only
after qualification. It is not a generic requirement that every ESPHome device
becomes a DJConnect device.

| Repository | Owns | Must not own |
| --- | --- | --- |
| `djconnect-esp32` | ESPHome source, board declarations, reusable packages, custom components, board-specific composition, source tests and baseline qualification | Published release assets or backend Runtime ownership |
| `djconnect-firmware` | Compiled images, manifests, checksums, stable/beta release notes, OTA/Web Installer artifacts and rollback metadata | Firmware source, board logic or product Runtime logic |
| `djconnect` | Existing OTA selection/orchestration and all existing HA contracts | ESPHome board enablement or compiled artifacts |
| Device Installer | Device catalog and manifest consumption | Firmware-specific business logic or a second provisioning protocol |

## Source layout

`djconnect-esp32` uses modular composition rather than monolithic board YAML:

```text
esp32/
  native/                 # legacy/alternative source while explicitly supported
  esphome/
    boards/               # small board composition files
    packages/             # reusable DJConnect feature packages
    components/           # narrowly scoped custom components
    firmware/             # variant entry points and build metadata
    baselines/            # upstream URL, pinned revision, attribution and qualification record
```

Board files select a pinned hardware baseline and compose packages; packages
must not reimplement baseline display, touch, button, audio, microphone,
PSRAM or networking initialization without a reviewed exception.

## Hardware baseline governance

Every adopted community baseline records its upstream source, license and
attribution, immutable revision, supported board, qualification evidence and
known limitations. A baseline update is a proposed source change, not an
automatic upstream sync. It must be built and qualified against the exact
board before beta promotion; stable promotion requires the full release gate.

Divergence is limited to DJConnect behavior or a documented board-specific
fix. A broad local driver fork requires a new ADR explaining why upstream
reuse, configuration or a thin extension is insufficient.

## Release qualification gate

Before a board/variant may appear in a published manifest, qualification proves
on the exact baseline revision and compiled artifact:

1. successful boot and display initialization, including no persistent white screen;
2. touchscreen and physical controls;
3. audio and microphone operation where the board provides them;
4. PSRAM and network stability;
5. Wi-Fi provisioning, pairing and runtime connection;
6. existing renderer projection and device UI operation;
7. OTA install, checksum validation and reboot recovery; and
8. rollback/recovery evidence appropriate to the selected channel.

Failure in any required applicable item keeps the variant unpublished. This is
a firmware qualification gate, not a change to the existing Runtime or API
qualification model.

## Distribution and installer

ESPHome variants are first-class entries in the existing `djconnect-firmware`
distribution architecture. The stable and beta channels, manifest validation,
checksums, OTA and release evidence remain common to native and ESPHome
artifacts. A variant is explicit in its manifest identity; no client infers
implementation technology from a board name.

The planned installer flow remains:

```text
devices.djconnect.dev -> Device Catalog -> ESP Web Tools -> Firmware Manifest
-> provisioning -> existing pairing
```

The installer selects a qualified artifact through manifest metadata and stays
agnostic about whether it was built with ESPHome or the temporarily supported
native path.

## Implementation roadmap

1. Inventory supported boards and record the attributed, pinned upstream
   baseline for each candidate.
2. Build reusable packages and minimal board compositions in `djconnect-esp32`.
3. Qualify one board/variant end-to-end, beginning with the proven display
   baseline, without changing DJConnect contracts.
4. Publish a beta manifest/artifact through `djconnect-firmware`.
5. Complete stable-channel and rollback qualification, then extend board by
   board.

No step authorizes a runtime redesign, pairing change, renderer contract change
or Home Assistant integration change.
