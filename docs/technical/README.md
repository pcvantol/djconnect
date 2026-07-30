# DJConnect Technical Implementation Reference

Status: Phase 6 technical reconstruction
Date: 2026-07-10
Scope: current implementation archaeology, not redesign

This directory documents how the current DJConnect platform really works as
observed from local source code, tests, fixtures and repository-local docs.

For guidance on where new technical discoveries belong, read
`../meta/META_ENGINEERING_INDEX.md` and `../meta/DECISION_PATTERNS.md`.

Classification tags used throughout:

| Tag | Meaning |
| --- | --- |
| `CONFIRMED_CODE` | Directly observed in implementation source. |
| `CONFIRMED_TEST` | Directly observed in automated tests or fixtures. |
| `CONFIRMED_RUNTIME` | Observed only from runtime evidence. None was collected in this phase. |
| `DOCUMENTED_ONLY` | Stated in docs or AGENTS but not confirmed in code during this pass. |
| `TARGET_ARCHITECTURE` | Accepted future architecture; it does not claim current implementation. |
| `INFERRED` | Reasonable conclusion from multiple source facts; not directly asserted by code. |
| `UNKNOWN` | Not confidently determined. |

## Layers

Foundation defines product and architecture intent. Platform Baseline v1 defines
accepted architecture after the profile-platform work. This technical reference
documents current implementation. Verification scenarios then validate whether
the implementation satisfies the accepted baseline.

Do not treat this directory as a new platform design.

## Documents

- [TECHNICAL_OVERVIEW.md](TECHNICAL_OVERVIEW.md)
- [BROADCAST_TRANSPORT.md](BROADCAST_TRANSPORT.md)
- [DJ_MOMENT_ENGINE.md](DJ_MOMENT_ENGINE.md)
- [PAIRING.md](PAIRING.md)
- [CLIENT_SERVER_TRANSPORT.md](CLIENT_SERVER_TRANSPORT.md)
- [HTTP_API.md](HTTP_API.md)
- [WEBSOCKET_API.md](WEBSOCKET_API.md)
- [CAPABILITY_DISCOVERY.md](CAPABILITY_DISCOVERY.md)
- [CLIENT_LOGGING.md](CLIENT_LOGGING.md)
- [CLIENT_STORAGE.md](CLIENT_STORAGE.md)
- [CACHE_MODEL.md](CACHE_MODEL.md)
- [ERROR_MODEL.md](ERROR_MODEL.md)
- [VOICE_TRANSPORT.md](VOICE_TRANSPORT.md)
- [BUILD_VARIANTS.md](BUILD_VARIANTS.md)
- [PUSH_NOTIFICATIONS.md](PUSH_NOTIFICATIONS.md)
- [UPDATE_MODEL.md](UPDATE_MODEL.md)
- [ESPHOME_FIRMWARE_PLATFORM_ARCHITECTURE.md](ESPHOME_FIRMWARE_PLATFORM_ARCHITECTURE.md) — accepted target architecture; not implementation archaeology
- [TECHNICAL_DRIFT.md](TECHNICAL_DRIFT.md)
- [UNKNOWNS.md](UNKNOWNS.md)

Machine-readable inventories live in [inventory/](inventory/).
