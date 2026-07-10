# Technical Drift

This file records genuine implementation drift only. Intentional runtime
differences are not drift.

## Intentional Differences

`CONFIRMED_CODE` ESP32 and Pi expose local `/api/device/*` APIs because HA must
control local hardware/runtime functions. Apple and Windows do not expose a
device API in the current outbound HA pairing flow.

`CONFIRMED_CODE` Pi ignores `ha_remote_url` in local pairing because Pi is
local-only. Windows stores remote URL/capabilities after local pairing for
fallback.

`CONFIRMED_CODE` Voice differs by client: ESP32 has PTT WAV upload; Pi AGENTS
explicitly says no PTT/local DJ response audio unless product scope changes;
Apple supports Ask DJ PTT paths.

## Genuine Drift / Risk

`INFERRED` App and local-device pairing use different authorities and token
issuance direction. This is currently functional, but verification adapters
must model both instead of assuming one pairing contract.

`INFERRED` Websocket support exists as an optional fast path, not as a universal
transport. Verification must validate HTTP fallback and not require websocket
for all clients.

`DOCUMENTED_ONLY` Apple entitlements/background push behavior is described by
platform intent, but was not fully code-confirmed here.

`UNKNOWN` Complete cache/profile-switch behavior differs by client and needs
runtime or deeper source verification.

## Verification Mapping

`CAPABILITY-*`, `SETUP-*`, `NETWORK-*`, `VOICE-*`, client-specific scenario
families.
