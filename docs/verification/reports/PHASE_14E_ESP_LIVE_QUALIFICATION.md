# Phase 14E ESP Live Qualification

Status: `ESP_LIVE_QUALIFIED`

Date: 2026-07-12

Branch: `main`

Base SHA: `57bd7d45dc006f0b4411fc2a443c2e9123321061`

## Executive Summary

Phase 14E qualified the ESP32 live hardware path against a connected LilyGO
T-Embed ESP32-S3 device. The ESP32 adapter executed the canonical hardware
scenario set `HARDWARE-001` through `HARDWARE-010` against the flashed device
and all ten scenarios passed.

Qualification decision:

```text
ESP_LIVE_QUALIFIED
```

## Scope

Implemented:

- rebuilt the dedicated local Home Assistant verification lab for the current
  repository SHA;
- detached the connected Espressif USB serial/JTAG device from the Parallels
  Windows VM so macOS could expose `/dev/cu.usbmodem101`;
- built and flashed DJConnect ESP32 firmware `3.2.11` from the sibling
  `pcvantol/djconnect-esp32` checkout;
- executed the ESP32 adapter against the live LilyGO hardware;
- executed `HARDWARE-001` through `HARDWARE-010`.

Out of scope:

- Phase 15 DJConnect Voice Assistant Verification Adapter;
- Phase 15E Voice Assistant live qualification;
- Phase 16 Cross-Platform Qualification;
- ESP firmware source changes;
- OTA mutation beyond the explicit USB flash required for the lab run;
- broad non-hardware platform scenario coverage.

## Implementation

No repository source changes were required.

The live lab used the existing ESP32 adapter and a destructive flash opt-in:

```text
DJCONNECT_VERIFICATION_ESP32_ALLOW_SERIAL=true
DJCONNECT_VERIFICATION_ALLOW_DESTRUCTIVE=true
```

The connected ESP32 device was visible as:

```text
/dev/cu.usbmodem101
```

USB metadata:

```text
USB Product Name: USB JTAG/serial debug unit
USB Vendor Name: Espressif
USB Serial Number: 94:A9:90:09:B7:90
```

## Verification

Home Assistant lab recreation:

```bash
python -m tools.verification.cli lab ha recreate --allow-destructive
```

Result:

```text
ha_lab_lifecycle: PASS
source_sha: 57bd7d45dc006f0b4411fc2a443c2e9123321061
safe_for_verification: true
```

ESP32 firmware flash:

```bash
DJCONNECT_RELEASE_BUILD=1 \
DJCONNECT_BUILD_FLAGS='-DDJCONNECT_VERSION=3.2.11 -DDJCONNECT_VERSION_TAG=v3.2.11 -Os' \
/Users/pcvantol/.platformio/penv/bin/pio run -e t_embed_cc1101 -t upload --upload-port /dev/cu.usbmodem101
```

Result:

```text
SUCCESS
Hash of data verified.
Hard resetting with RTC WDT.
```

ESP32 adapter and planner regression subset:

```bash
python -m pytest tests/verification/test_esp32_adapter.py tests/verification/test_planning_engine.py -q
```

Result:

```text
15 passed
```

Live ESP32 hardware scenarios:

```text
HARDWARE-001 PASS
HARDWARE-002 PASS
HARDWARE-003 PASS
HARDWARE-004 PASS
HARDWARE-005 PASS
HARDWARE-006 PASS
HARDWARE-007 PASS
HARDWARE-008 PASS
HARDWARE-009 PASS
HARDWARE-010 PASS
```

Repository hygiene:

```bash
git diff --check
```

Result:

```text
passed
```

## Evidence

Primary passing ESP live smoke evidence:

```text
artifacts/verification/evidence/djv-20260712T151318Z-f838e458f3/
```

Full ESP hardware scenario evidence:

```text
artifacts/verification/evidence/djv-20260712T151519Z-81422a10e9/
artifacts/verification/evidence/djv-20260712T151536Z-44e88c3c12/
artifacts/verification/evidence/djv-20260712T151554Z-9b9a4e240d/
artifacts/verification/evidence/djv-20260712T151612Z-70b80e264c/
artifacts/verification/evidence/djv-20260712T151629Z-d267d7a2b9/
artifacts/verification/evidence/djv-20260712T151647Z-effd29bf17/
artifacts/verification/evidence/djv-20260712T151704Z-4812d802c5/
artifacts/verification/evidence/djv-20260712T151721Z-46a3279eda/
artifacts/verification/evidence/djv-20260712T151738Z-2d2395afff/
artifacts/verification/evidence/djv-20260712T151756Z-d4dc9fc4f8/
```

Post-flash serial evidence included:

```text
DJConnect v3.2.11 / 3.2.11 booting
Board: LilyGO T-Embed-CC1101
Device model: lilygo-t-embed-s3
Home Assistant pairing: paired
Playback credentials are managed by Home Assistant
```

Firmware artifact hash from the local release build:

```text
a7e4524ee95e6967bfbdd70a39f17c5416db1bc695ff23012fe14ae3264898eb
```

The public firmware repository `v3.2.11` artifact hash remains:

```text
da239c450c96aff4d9f36758c3c1733522ab2a0efc19d64280ba0566703a440b
```

The local lab build used source checkout build flags and is not a public
release artifact replacement.

## Investigation

Initial live execution was blocked before scenario mutation because the
existing Home Assistant Docker lab container was stale and marked unsafe for
the current repository SHA.

Classification:

```text
environment issue remediated
```

Owner:

```text
Verification Execution Environment / local HA lab
```

Remediation:

```text
python -m tools.verification.cli lab ha recreate --allow-destructive
```

After recreation, the lab container was labelled with the current SHA and the
hardware scenarios passed.

## Known Issues

- ESP32 firmware native code coverage is not part of this phase. Phase 14E
  proves live hardware scenario execution, not firmware unit/code coverage.
- The local HA lab doctor saw a transient WebSocket probe timeout after lab
  recreation, while REST, token, source SHA and safety checks were healthy.
  The subsequent scenario execution accepted the qualified runtime and passed.
- `HARDWARE-001` through `HARDWARE-010` are adapter-backed hardware scenarios.
  Broader cross-platform behavior remains Phase 16 scope.

## Technical Debt

No new Verification Runtime technical debt was introduced.

## Product Debt

No product debt was introduced. The ESP firmware remained within its runtime,
UI, audio, device API and credential-boundary responsibilities.

## Recommendations

Proceed to Phase 15 DJConnect Voice Assistant Verification Adapter from a clean
session. Do not start Phase 15E or Phase 16 until Phase 15 returns its adapter
qualification decision.

## Readiness

Phase 14E is qualified. ESP live hardware qualification no longer blocks the
remaining Platform Qualification roadmap.

## Next Phase

Next engineering action:

```text
Phase 15 DJConnect Voice Assistant Verification Adapter
```

Clean-session bootstrap command:

```text
Read BOOTSTRAP_CODEX_VERIFICATION.md and execute the active phase referenced in PROMPT_INDEX.md.
```
