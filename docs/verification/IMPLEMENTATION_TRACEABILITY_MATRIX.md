# Implementation Traceability Matrix

Status: Phase 7 traceability baseline
Date: 2026-07-10

This matrix links important platform capabilities across foundation, ADRs,
technical design, scenarios, implementation, tests and verification readiness.

| Capability | Foundation / Baseline | ADR | Technical Design | Scenario IDs | Implementation | Tests / Fixtures | Verification Readiness | Missing Links |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Profile primary identity | Constitution Laws 1/4, Domain Model, Platform Baseline v1 | ADR-0001 | `TECHNICAL_OVERVIEW.md`, `CLIENT_STORAGE.md` | `PROFILE-*`, `SETUP-011..012`, `EXPORT-*`, `IMPORT-*` | `custom_components/djconnect/domain/*`, `profile_context.py` | `tests/test_domain.py`, `tests/test_profile_storage.py`, `tests/test_profile_context.py` | HA adapter ready | Client UI/profile-switch evidence |
| Request Context / Resolver | Architecture Principles, Baseline resolver order | ADR-0011 | `CAPABILITY_DISCOVERY.md`, Phase 6 docs | `RESOLVER-*`, `VOICE-*` | `domain/resolver/profile_resolver.py`, `profile_context.py`, `conversation.py` | `tests/test_domain.py`, `tests/test_profile_context.py`, `tests/test_conversation_agent.py` | HA adapter ready | Live Voice Endpoint evidence |
| Device pairing and token | AGENTS, Domain Model Device law, Baseline device mapping | ADR-0011 related | `PAIRING.md`, `http_routes.json`, `pairing_flows.json` | `SETUP-013..015`, `SETUP-021..022`, `NETWORK-*` | HA `http.py`, ESP `DJConnectApiServer.cpp`, Pi `client_api.py`, Windows `DJConnectApiClient.cs` | Windows tests, ESP native tests, HA helper tests | HA pair endpoint ready | Apple live pair evidence; device adapter evidence |
| Authentication and secrets | Constitution privacy, AGENTS secret rules, Quality Standard | ADR-0003 related | `ERROR_MODEL.md`, `CLIENT_STORAGE.md`, `PUSH_NOTIFICATIONS.md` | `PRIVACY-*`, `BACKEND-*`, `SETUP-016..018` | HA auth helpers, Spotify backend, central API auth, client secure stores | `tests/test_diagnostics.py`, `tests/test_music_dna_api_handlers.py`, API tests | HA partial | Full central/live token rotation evidence |
| Capability discovery | Baseline Capability Contract v1, Client Capability Matrix | ADR-0011/0012 adjacent | `CAPABILITY_DISCOVERY.md`, `WEBSOCKET_API.md` | `CAPABILITIES-*` | `websocket_api.py`, HA status/pair responses, device info endpoints | `tests/test_websocket_api.py`, `tests/test_client_contract_snapshots.py` | HA producer ready | Client no-version-inference evidence |
| HTTP API | Repository ownership, Baseline request sources | None specific | `HTTP_API.md`, `http_routes.json` | Many categories | `custom_components/djconnect/http.py`, `api_handlers.py` | Broad HA tests | HA adapter ready | Live HA runtime evidence |
| WebSocket API | Capability discovery baseline | None specific | `WEBSOCKET_API.md`, `websocket_commands.json` | `CAPABILITIES-*`, `ASKDJ-*`, `MUSICDNA-*`, `DISCOVER-*` | `websocket_api.py`; client fast paths | `tests/test_websocket_api.py`, client fixtures | HA producer ready | Client adapter evidence |
| Ask DJ history | Constitution backend owns intelligence, Baseline profile state | ADR-0003 | `HTTP_API.md`, `CACHE_MODEL.md` | `ASKDJ-*`, `PRIVACY-*` | `ask_dj_history.py`, `api_handlers.py`, `http.py` | `tests/test_ask_dj_history.py`, `tests/test_http_voice_helpers.py` | HA adapter ready for deterministic paths | Profile-native migration verification for legacy keys |
| Music DNA | Constitution Law 1/6, Baseline Profile owns DNA | ADR-0001/0003 | `CLIENT_STORAGE.md`, `CACHE_MODEL.md` | `MUSICDNA-*`, `DISCOVER-*`, `PRIVACY-*` | `music_dna.py`, `api_handlers.py`, `music_discovery.py` | `tests/test_music_dna_api_handlers.py`, `tests/test_music_discovery.py` | HA adapter ready | Live Spotify profile snapshot evidence |
| Discovery | Product Vision Discover, backend-owned recommendations | ADR-0003 | `HTTP_API.md`, `WEBSOCKET_API.md` | `DISCOVER-*` | `music_discovery.py` | `tests/test_music_discovery.py`, websocket tests | HA deterministic partial | Live recommendation/provider evidence |
| Track Insight | Backend owns intelligence, Client Capability Matrix | ADR-0003 | `HTTP_API.md` | `TRACKINSIGHT-*` | `track_insight` handlers/use cases | `tests/test_track_insight.py` | HA adapter ready | Client rendering evidence |
| Playback backend | Backend law, Music Backend adapter baseline | ADR-0002 | `CLIENT_SERVER_TRANSPORT.md`, `ERROR_MODEL.md` | `PLAYBACK-*`, `BACKEND-*` | `spotify_backend.py`, Music Assistant integration paths, command handlers | `tests/test_switch.py`, HTTP helper tests | HA fixture partial | Live Spotify/MA evidence |
| Localization | Product Language, Localization Standard, ADR-0012 | ADR-0012 | `CLIENT_LOGGING.md`, `BUILD_VARIANTS.md` indirectly | `LOCALIZATION-*` | HA `translations/*.json`; sibling catalogs | localization audit/tests | Static partial | Website/release/client screenshot evidence |
| Privacy/redaction | Constitution privacy, Quality Standard | ADR-0001/0003 | `CLIENT_LOGGING.md`, `CLIENT_STORAGE.md`, `ERROR_MODEL.md` | `PRIVACY-*`, `EXPORT-*`, `IMPORT-*` | diagnostics/export/redaction modules | `tests/test_diagnostics.py`, export/import tests | HA adapter ready | Evidence manager redaction implementation |
| Export/import | Baseline Privacy Contract v1 | ADR-0001 | `CLIENT_STORAGE.md`, `CACHE_MODEL.md` | `EXPORT-*`, `IMPORT-*` | `profile_export.py`, `api_handlers.py`, Music DNA export/import | profile export/import tests, Music DNA tests | HA adapter ready | Cross-client restore evidence |
| Push/APNs | Client matrix notifications, central API ownership | None accepted | `PUSH_NOTIFICATIONS.md`, `push_routes.json` | Apple/network/privacy scenarios only | HA `push.py`, `djconnect-api` Worker | API tests, partial HA tests | Needs Apple/API adapter | Dedicated push scenarios |
| Voice/PTT | Client matrix, Voice Endpoint model | ADR-0011 | `VOICE_TRANSPORT.md` | `VOICE-*`, `ESP-*`, `APPLE-*` | HA `http.py`, `assist_stt.py`, ESP voice code, Apple PTT source | `tests/test_http_voice_helpers.py`, ESP native tests | HA helper partial | Real STT/audio/hardware evidence |
| ESP OTA/update | Device law, release governance | None accepted | `UPDATE_MODEL.md`, `BUILD_VARIANTS.md` | `HARDWARE-*`, `RELEASE-*`, `SETUP-007` | HA `github.py`/`update.py`, ESP OTA code | ESP native tests, HA update tests partial | Needs ESP/release adapter | Real OTA hardware evidence |
| Pi updater | Ambient client ownership | None accepted | `UPDATE_MODEL.md`, `CLIENT_STORAGE.md` | `RELEASE-*`, Pi implied | Pi `updater.py`, update UI | Pi tests | Needs Pi adapter | Release artifact evidence |
| Verification harness | Verification Vision/Architecture | None | Phase 6 technical docs | All scenarios | `tools/verification/*` scaffold | harness validation tests if present | Phase 8 can implement HA adapter | Actual adapters/evidence execution |

## Missing Traceability Links

- Push lacks first-class scenario IDs and an accepted ADR for central trust/APNs
  if this becomes a durable platform contract.
- Website and release repositories are represented in foundation/quality docs
  and scenarios, but current implementation traceability is thin.
- Apple storage/logging/build entitlement details lack strong implementation to
  tests to scenario links.
- Client-specific scenario families are implied by examples and adapter names,
  but not surfaced as dedicated scenario groups in the catalog summary.
- Verification reports do not yet ingest technical design coverage or adapter
  readiness automatically.
