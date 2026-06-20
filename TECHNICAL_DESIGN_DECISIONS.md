# DJConnect Technical Design Decisions

This document records code-level design decisions, implementation patterns,
coding conventions and third-party dependencies for the DJConnect Home Assistant
integration.

Sources used for this document:

- Local source tree under `custom_components/djconnect/`.
- Home Assistant integration metadata in `custom_components/djconnect/manifest.json`.
- HACS metadata in `hacs.json`.
- Existing architecture and release notes in `README.md`, `AGENTS.md`,
  `HANDOFF.md`, `SYNC_PROMPTS.md` and `THIRD_PARTY_NOTICES.md`.
- Unit tests under `tests/`.

When a runtime dependency is provided by Home Assistant rather than pinned by
this repository, the version is documented as the minimum component/runtime
contract that this repo declares.

## Scope

This repository contains the MIT-licensed Home Assistant custom integration
for DJConnect. Related DJConnect client and firmware repositories are also
MIT-licensed unless their own repository metadata states otherwise.

The integration domain is `djconnect`. The current implementation targets
DJConnect protocol line `3.1.x`.

## Python Design Decisions

### Home Assistant Runtime As The Composition Root

Pattern:

- Home Assistant owns setup, config entries, platform loading, HTTP view
  registration, services, diagnostics and repairs.
- DJConnect stores one `DJConnectRuntime` object per config entry in
  `hass.data[DOMAIN][entry.entry_id]`.
- Entity platforms read and observe that runtime instead of duplicating state.

Primary source files:

- `custom_components/djconnect/__init__.py`
- `custom_components/djconnect/sensor.py`
- `custom_components/djconnect/button.py`
- `custom_components/djconnect/number.py`
- `custom_components/djconnect/select.py`
- `custom_components/djconnect/switch.py`
- `custom_components/djconnect/update.py`
- `custom_components/djconnect/media_player.py`

Why:

- Matches Home Assistant's custom integration lifecycle.
- Keeps one in-memory authority for device state, Spotify state and voice
  debug data.
- Lets non-polling entities update immediately through runtime listeners.

### Runtime State Object With Listener Fan-Out

Pattern:

- `DJConnectRuntime` is a dataclass with transient fields such as
  `last_text`, `last_dj_text`, `last_playback`, `device_status`,
  `device_token`, `pairing_device_id`, OTA state and latest Spotify token
  metadata.
- Entities append callbacks to `runtime.listeners`.
- `runtime.update(...)` writes fields, mirrors last-known values into
  `device_status`, then notifies listeners.

Primary source files:

- `custom_components/djconnect/__init__.py`
- `custom_components/djconnect/sensor.py`

Why:

- Avoids Home Assistant polling for frequent local status changes.
- Keeps `last_command`, `last_track` and DJ announcement debug values stable
  across sparse payloads.
- Makes tests lightweight because runtime can be represented by simple stubs.

### Guarded STT Correction Before Intent Parsing

Pattern:

- Physical PTT and `djconnect.test_ptt_text` can call
  `correct_stt_text_with_assist(...)` after STT and before
  `process_text_with_assist(...)`.
- The correction prompt asks HA Assist to return only corrected command text,
  with no JSON, URI or explanation.
- The helper falls back to the original STT text when Assist is unavailable,
  returns a Home Assistant device lookup error, leaks prompt text, returns
  structured data or produces an implausibly long response.
- `last_stt_text` keeps the raw transcript and `last_corrected_text` records
  the corrected command only when it changed.
- If no explicit Assist conversation agent is configured, the helper calls
  Home Assistant's default conversation agent instead of skipping correction.

Primary source files:

- `custom_components/djconnect/pipeline.py`
- `custom_components/djconnect/processor.py`
- `custom_components/djconnect/http.py`

Why:

- Dutch STT often approximates English artist, track, album and playlist names.
- A small correction pass improves Spotify search quality without adding direct
  external AI dependencies.
- Guardrails prevent prompt leaks or smart-home device lookup errors from
  becoming Spotify queries or user-facing DJ announcement text.

### Generated DJ Announcement With Guarded Fallback

Pattern:

- `generate_dj_response_with_assist(...)` asks Home Assistant conversation for
  the spoken DJ announcement after Spotify intent/playback has resolved media
  metadata.
- The configured `dj_response_prompt` is used only in this response-generation
  step, never in Spotify intent parsing.
- The helper uses the configured conversation agent when present, otherwise
  resolves Home Assistant's preferred/default Assist pipeline and uses its
  conversation engine.
- DJConnect also exposes its own Home Assistant conversation agent entity so
  Assist satellites such as Voice Preview Edition can route recognized speech
  directly into `process_text_command(...)` and receive the generated DJ
  response as Assist speech.
- Dutch prompts include an instruction to pronounce English artist, album and
  track names in English inside Dutch sentences.
- When an artist request starts playback and Spotify returns the concrete
  started track in the command response, the response generator merges that
  just-returned track metadata into the DJ announcement media context. It does
  not read stale `runtime.last_playback` as a substitute for the current
  command result.
- Prompt leaks, Spotify URIs, structured dictionaries and Home Assistant
  device-lookup errors are blocked before they can be sent to a device.

Primary source files:

- `custom_components/djconnect/pipeline.py`
- `custom_components/djconnect/processor.py`

Why:

- Keeps the DJ announcement generative when the user configured a default AI
  conversation agent through Home Assistant Assist but did not explicitly
  select an Assist pipeline in DJConnect.
- Prevents the local "Daar is ..." fallback from hiding normal AI response
  generation.
- Keeps the fallback deterministic and safe when HA Assist cannot produce a
  usable spoken response.

### Temporary Device Audio URLs

Pattern:

- HA TTS audio is stored in memory under a temporary token and exposed through
  `/api/djconnect/tts/{token}.wav` or `.mp3`.
- DJ response delivery posts text plus optional `audio_url` to the client local
  `/api/device/dj_response` endpoint.
- The base URL for temporary audio uses the shared local Home Assistant URL
  resolver, not a single HA network helper version.

Primary source files:

- `custom_components/djconnect/dj_response.py`
- `custom_components/djconnect/ha_urls.py`
- `custom_components/djconnect/tts.py`

Why:

- ESP/app clients can fetch local DJ announcement audio without requiring Nabu
  Casa/cloud routing.
- Older and newer Home Assistant versions expose different network helpers; the
  shared resolver preserves audio delivery across those versions.

### Merge-Only Device Status Cache

Pattern:

- Device status updates merge known fields into `runtime.device_status`.
- Sparse command, voice or playback payloads must not replace the whole status
  snapshot with empty/default values.
- `ha_pairing_status` does not silently fall back to `pending` when a payload
  omits it.

Primary source files:

- `custom_components/djconnect/__init__.py`
- `custom_components/djconnect/http.py`
- `custom_components/djconnect/sensor.py`

Why:

- ESP/app clients frequently send partial command or voice payloads.
- Home Assistant sensors should preserve last-known useful values while a
  device or backend is temporarily unavailable.

### Explicit Client-Type Branching

Pattern:

- `client_type` is the canonical runtime discriminator.
- Current values are `esp32`, `ios`, `macos`, `watchos` and `raspberry_pi`.
- ESP32 gets hardware-specific entities such as battery, WiFi RSSI, screen,
  LED, OTA and reboot controls.
- iOS, macOS, watchOS and Raspberry Pi clients keep backend/playback/client entities
  only. Firmware channel and OTA controls are ESP32-only; Apple clients update
  through app distribution/TestFlight and Linux/Raspberry Pi clients update
  through their own source/install flow.
- Config-flow client type choices are ordered iOS, macOS, Apple Watch, Linux/Raspberry Pi
  and ESP32, and setup method is chosen only in the first config-flow step.

Primary source files:

- `custom_components/djconnect/const.py`

### Server-Side DJ Memory

Pattern:

- `Ask DJ` context is owned by the Home Assistant integration, not by iOS,
  macOS, watchOS, Raspberry Pi or ESP32 clients. iOS, macOS, watchOS and
  Raspberry Pi can render Ask DJ text chat; ESP32 is excluded from Ask DJ
  chat/history and keeps the existing command/PTT flow.
- Runtime session memory keeps bounded recent turns for follow-ups and may be
  lost on Home Assistant restart.
- Persistent memory uses Home Assistant `Store(hass, 1, "djconnect_memory")`;
  no recorder database or vector database is used for v1.
- Memory keys prefer HA user id when available and fall back to stable
  DJConnect client/device id.
- Stored memory is compact and excludes bearer tokens, Spotify OAuth tokens,
  Home Assistant tokens, raw audio and full prompts.
- Text Ask DJ requests from app/display clients enter through
  `POST /api/djconnect/ask_dj/message`; service `djconnect.ask_dj` and
  `POST /api/djconnect/ask_dj` remain developer/raw entrypoints.
- Renderable Ask DJ chat history is separate from DJ Memory and uses Home
  Assistant `Store(hass, 1, "djconnect_ask_dj_history")`. It is keyed by HA
  user id, keeps at most 1000 messages per user and stores user/assistant
  messages with images, links, sources, audio_url and playback_actions.
- When the 1000-message limit is exceeded, trimming happens server-side before
  the history is returned. The backend exposes `history_limit`,
  `history_trimmed_before` and `history_trimmed_count` so clients can trim
  local caches without parsing visible text. A bounded assistant-only system
  message with `origin:"history_retention"` and intent
  `history_limit_reached` is added as normal chat history, but no audio is
  generated for it.
- `client_message_id` provides idempotency for retried message posts. `client_id`
  and `client_type` stay metadata for origin/device diagnostics and must not be
  used as the primary history key.
- Pending Ask DJ follow-ups are stored compactly in DJ Memory with a short TTL
  so a confirmation question can survive a cross-device reply. The first
  implementation uses a 10 minute expiry and stores only the proposed command
  metadata needed to execute or decline the follow-up.
- Follow-up questions expose `confirmation_actions[]` and confirmation-style
  `playback_actions[]`. Clients render them as Ja/Nee controls and answer via
  `POST /api/djconnect/command` with
  `command:"ask_dj_followup_response"`. A positive answer executes the stored
  proposal; a negative answer consumes it and leaves playback unchanged.
- Ask DJ audio generation is policy-based. `audio_response:auto` avoids TTS for
  informational text chat to keep the chat UI fast, but keeps TTS for
  playback/hybrid intents and voice/PTT interactions. `always` and `never`
  provide explicit client overrides.
- App Ask DJ Push-To-Talk enters through the existing `/api/djconnect/voice`
  WAV route when a client supports voice. iOS, macOS and watchOS transcripts are
  routed to the same Ask DJ handler as text chat. Raspberry Pi Ask DJ is
  text-only unless a future Pi capability explicitly advertises voice support.
  ESP32 WAV remains on the command-parser playback flow and is not attached to
  Ask DJ chat history. This keeps one authenticated voice endpoint while
  preserving client-specific semantics.
- Intent routing is deliberately split into informational, playback/device
  action and hybrid buckets. Informational answers can use playback context and
  memory but must not mutate Spotify/Home Assistant playback.
- Smart-home context is opt-in and read-only. DJConnect reads only Home
  Assistant entities explicitly listed in `smart_home_context_entities`, adds a
  compact state summary to Ask DJ prompt context and never exposes all HA
  states by default. This prepares future system-message intents such as weather,
  room temperature, appliance-ready or scene-changed prompts without giving Ask
  DJ broad Home Assistant control. If such a prompt proposes music, playback
  must still go through confirmation-style Ja/Nee actions before starting.
- Lifecycle utterances are routed explicitly: `ik ga slapen` pauses playback,
  while `goedemorgen` returns a morning recommendation with confirmation
  controls instead of starting playback automatically.
- Obvious gibberish and sandbox/prompt-injection attempts return the neutral
  unknown-intent answer and must not trigger Spotify search, HA device lookup,
  prompt disclosure or playback actions.
- `personal_music_profile_analysis` is a dedicated informational intent. It
  parses common period phrases, defaults to the last 30 days, summarizes only
  available DJ Memory/playback data and returns an insufficient-data answer when
  there is not enough history. It must not call mutating Spotify/Home Assistant
  actions.
- Spotify listening-profile enrichment is non-mutating and uses official Web
  API reads only: `/me/player/recently-played` and `/me/top/{artists,tracks}`.
  The integration caches compact profile snapshots in DJ Memory with a
  multi-hour TTL instead of storing unlimited raw listening history.
- Ask DJ profile responses expose `sources[]` metadata so clients can show
  Spotify recently played/top-items and DJConnect Memory provenance separately
  from normal links.
- Ask DJ recommendations use a two-step model. The informational
  `personal_music_recommendations` response may expose Spotify-only
  `playback_actions[]`, but playback starts only after the explicit
  `ask_dj_play_recommendation` command. This prevents accidental playback
  mutations while still giving clients a Play Now affordance.
- Ask DJ concert agenda lookups are informational and non-mutating. The
  `artist_concerts` intent resolves an explicit artist, current playback artist
  or recent conversation artist and reads upcoming event data from Bandsintown
  through Home Assistant's aiohttp client. Responses include a compact
  date/location/link list plus `links[]` entries with `source: bandsintown`.
  If the source is unavailable or empty, DJConnect returns an honest no-data
  message instead of inventing tour dates.
- Ambient Ask DJ facts are generated from Spotify playback status, not from a
  user message. `spotify_backend.playback_state()` calls a small ambient helper
  after updating `runtime.last_playback`; the helper dedupes on normalized
  `artist|album`, asks HA conversation for a short reliable text-only fact and
  appends an assistant-only `ambient_music_fact` message to Ask DJ history with
  `message_kind:"system"` and `origin:"spotify_playback_context"` for client
  styling. If Assist cannot provide a reliable fact or returns `SKIP`, no
  message is stored.
- Clear/history state is revision-based: `history_revision` advances when a
  user/assistant exchange is stored or history is cleared; `clear_revision`
  advances only on clear. Clients compare local clear revision with
  `GET /api/djconnect/ask_dj/history` or the developer history-state service
  before rendering and clear local cache when the server value is newer.
- Images are represented as structured `images[]` entries and any external
  image URL is registered behind the Home Assistant route
  `/api/djconnect/image_proxy/{token}`. Source links remain explicit `links[]`
  entries and are not mixed with images.

Primary source files:

- `custom_components/djconnect/memory.py`
- `custom_components/djconnect/ask_dj.py`
- `custom_components/djconnect/http.py`
- `custom_components/djconnect/processor.py`
- `custom_components/djconnect/config_flow.py`
- `custom_components/djconnect/sensor.py`
- `custom_components/djconnect/button.py`
- `custom_components/djconnect/number.py`
- `custom_components/djconnect/update.py`

Why:

- Prevents app-like clients from showing ESP-only controls.
- Keeps one integration contract while supporting multiple client runtimes.

### Local HTTP Views For Protocol Boundaries

Pattern:

- Home Assistant registers explicit HTTP views for DJConnect protocol routes:
  pairing, status, command, voice, event, TTS and Spotify callback.
- Each route owns its input parsing, auth checks and response shape.

Primary source files:

- `custom_components/djconnect/__init__.py`
- `custom_components/djconnect/http.py`

Why:

- Keeps device/app protocol contracts isolated from Home Assistant entity code.
- Lets tests exercise routes without a full Home Assistant runtime.

### Bearer-Token Pairing And Auth

Pattern:

- Pairing creates and stores a per-device bearer token.
- Device/app calls authenticate with `Authorization: Bearer <device_token>`.
- Device ID and `client_type` are validated against known model/client ID
  shapes.
- Spotify credentials are never returned in pair/status responses.

Primary source files:

- `custom_components/djconnect/__init__.py`
- `custom_components/djconnect/http.py`
- `custom_components/djconnect/config_flow.py`

Why:

- Keeps Home Assistant as the trusted backend.
- Prevents DJConnect clients from storing Spotify OAuth or Home Assistant
  long-lived credentials.

### Discovery Strategy Object

Pattern:

- `DiscoveredClient` is a small dataclass that represents one mDNS-discovered
  DJConnect client.
- Discovery first parses TXT/service metadata, then probes
  `/api/device/pairing-info`.
- Pairing-info is authoritative over mDNS TXT data.
- Dedupe is by stable `device_id`.

Primary source files:

- `custom_components/djconnect/discovery.py`
- `custom_components/djconnect/config_flow.py`

Why:

- mDNS TXT data can be stale or incomplete.
- The local Client adres can change for app-like clients.
- Pairing-info gives the best current device ID, client type, name, version,
  pairing code and local URL.

### Adapter Functions Around Home Assistant APIs

Pattern:

- Helper modules hide Home Assistant API variations and optional runtime
  capabilities.
- Examples include HA URL resolution, Assist/STT probing, TTS generation,
  firmware release fetching and BLE provisioning.

Primary source files:

- `custom_components/djconnect/ha_urls.py`
- `custom_components/djconnect/assist_stt.py`
- `custom_components/djconnect/tts.py`
- `custom_components/djconnect/github.py`
- `custom_components/djconnect/ble.py`

Why:

- Home Assistant helper APIs vary across releases.
- Small adapter modules keep fallback behavior testable and localized.

### Spotify Backend As An Internal Gateway

Pattern:

- `spotify_backend.py` is the only module that directly executes Spotify Web
  API playback commands.
- It maps generic DJConnect commands to Spotify API calls.
- Access tokens are cached until shortly before expiry.
- Spotify API `401` clears the access token and retries once.
- Refresh-token rotation is persisted immediately.
- If Spotify rejects one refresh token, the backend retries newer stored
  runtime/config-entry/config token sources before creating a Repair issue.

Primary source files:

- `custom_components/djconnect/spotify_backend.py`
- `custom_components/djconnect/spotify_oauth.py`
- `custom_components/djconnect/repairs.py`

Why:

- Devices/apps stay backend-agnostic and do not receive playback credentials.
- Spotify token expiry and token rotation should be invisible to clients.
- A user-facing Repair is only appropriate when Spotify rejects every known
  stored refresh token.

### Assist And TTS As Home Assistant-Native Gateways

Pattern:

- Raw WAV PTT uploads are processed by HA STT/Assist helpers.
- `pipeline.py` asks HA Assist for DJConnect intent data, but
  `music_intent.py` keeps a deterministic local parser for common
  Dutch/English PTT phrases. `spotify.py` and the pipeline both use that parser
  as a guardrail. Generic music requests stay artist-first; explicit media
  words map to Spotify Search types (`track`, `album`, `playlist`) or the
  configured default playlist.
- `examples/voice_intents.json` is the shared data file for website/client
  examples of supported spoken intent families and handling order.
  `VOICE_INTENT_DATA.md` documents the maintenance contract for that data.
- DJ announcement text is generated through Home Assistant Assist where
  possible, then converted to a temporary WAV/MP3 URL through HA TTS.
- Local fallback text is deliberately neutral and not a hidden prompt-style
  generator.

Primary source files:

- `custom_components/djconnect/assist_stt.py`
- `custom_components/djconnect/pipeline.py`
- `custom_components/djconnect/processor.py`
- `custom_components/djconnect/spotify.py`
- `custom_components/djconnect/dj_response.py`
- `custom_components/djconnect/tts.py`
- `custom_components/djconnect/wav_util.py`

Why:

- Keeps active routes inside Home Assistant's configured Assist/TTS setup.
- Avoids direct external AI/STT/TTS dependencies in this integration.
- Prevents broad or ambiguous STT text from becoming arbitrary track/album
  searches while still supporting explicit user phrasing for tracks, albums and
  playlists.
- Keeps DJ response audio on the DJConnect device, not the Spotify playback
  device.

### Repair Flow For User-Actionable Failures

Pattern:

- Missing Spotify credentials, missing scopes and revoked refresh tokens create
  Home Assistant repair issues.
- The Spotify repair path opens OAuth and only closes after a new token is
  stored.
- The first OAuth repair step is the translated `authorize` external step. This
  avoids blank Home Assistant repair popups when the frontend renders the
  website-opening dialog.

Primary source files:

- `custom_components/djconnect/repairs.py`
- `custom_components/djconnect/http.py`
- `custom_components/djconnect/spotify_backend.py`

Why:

- Access-token refresh is automatic, but OAuth reauthorization cannot be done
  silently when Spotify revokes the refresh token.
- Repairs keep unavoidable user action inside native Home Assistant UX.
- Repair prerequisites read both config entry data and options so newly paired
  clients do not create false missing-token/client/scope issues when credentials
  are stored outside the primary data dict.

### Localized Safe Fallback Copy

Pattern:

- Device/client DJ response fallback text is generated from a fixed localized
  copy table, selected by the configured device language.
- Raw exceptions, Assist prompts, Spotify response bodies and parser prompts
  are not forwarded as spoken/displayed DJ response text.
- Known Home Assistant Assist device-lookup errors are mapped to a friendly
  DJConnect request retry message instead of leaking prompt fragments such as
  "Noem de artiest..." to the client.

Primary source files:

- `custom_components/djconnect/http.py`
- `custom_components/djconnect/pipeline.py`
- `custom_components/djconnect/dj_response.py`

Why:

- App/device screens are user-facing surfaces, not debug logs.
- Keeps command failures readable in the user's language while preserving
  detailed diagnostics in Home Assistant logs/entities.

### Defensive Diagnostics And Logging

Pattern:

- Diagnostics redact keys containing `token`, `password` or `secret`.
- Logs use metadata instead of raw secrets or full payload dumps.
- Spotify token logs include expiry timing, source names and rotation status,
  never token values.

Primary source files:

- `custom_components/djconnect/diagnostics.py`
- `custom_components/djconnect/__init__.py`
- `custom_components/djconnect/http.py`
- `custom_components/djconnect/spotify_backend.py`

Why:

- Pairing, BLE WiFi and Spotify OAuth all touch sensitive values.
- Debugging should not create accidental credential disclosure.

### Lightweight Unit Tests With Home Assistant Stubs

Pattern:

- Tests use Python `unittest`.
- Home Assistant modules/classes are stubbed where possible.
- Tests target helper logic, route parsing, entity behavior and protocol
  contracts without a full Home Assistant installation.

Primary source files:

- `tests/`

Why:

- Keeps the test suite fast enough for every release.
- Makes protocol regressions visible even outside a Home Assistant dev
  container.

## Python Coding Style Conventions

Observed conventions:

- `from __future__ import annotations` at the top of Python modules.
- Async Home Assistant naming: `async_setup_entry`, `async_unload_entry`,
  `async_*` helpers and non-blocking `aiohttp` client sessions.
- Constants are uppercase and centralized in `const.py`.
- Integration-wide logger names use `logging.getLogger(__name__)`.
- Dataclasses are used for structured internal records:
  `DJConnectRuntime`, `DiscoveredClient`, `FirmwareRelease`, `FirmwareAssets`,
  `TtsAudio` and similar small value objects.
- Home Assistant entity classes set `_attr_has_entity_name = True` and stable
  `_attr_translation_key` / `_attr_unique_id` values where applicable.
- Entity unique IDs are derived through `entry_unique_id(...)` so multiple
  DJConnect entries do not collide.
- User-facing strings live in Home Assistant translation files:
  `strings.json`, `translations/en.json`, `translations/nl.json` and
  `services.yaml`.
- Broad `except Exception` blocks are used only around optional Home Assistant
  APIs, third-party runtime helpers or best-effort cleanup, usually with debug
  logging.
- Secrets are never intentionally logged.

Sources:

- Home Assistant integration entry points and entity APIs in
  `custom_components/djconnect/*.py`.
- Translation files under `custom_components/djconnect/translations/` and
  `custom_components/djconnect/strings.json`.
- Service descriptions in `custom_components/djconnect/services.yaml`.

## JSON And YAML Design Decisions

### Home Assistant Manifest

Pattern:

- `custom_components/djconnect/manifest.json` declares the integration domain,
  version, Home Assistant dependencies, HACS-visible documentation URLs,
  Bluetooth discovery UUID and Python requirements.

Why:

- This is the canonical Home Assistant custom integration metadata contract.

### Translations

Pattern:

- English and Dutch translations are maintained in Home Assistant translation
  JSON files.
- Config-flow, options-flow, repair and entity labels should not rely on raw
  key names in the UI.

Why:

- DJConnect is used in both Dutch and English Home Assistant environments.
- Translation coverage is tested.

### Service Schema

Pattern:

- `services.yaml` documents developer/test services such as Spotify OAuth,
  command tests and TTS tests.
- `DEVELOPER_SERVICE_SCHEMAS` in `__init__.py` registers matching runtime
  schemas for the same services, including the explicit `command_text` and
  `dj_response_text` fields plus the legacy `text` alias.

Why:

- Home Assistant's Developer Actions UI reads this metadata.
- Runtime schemas keep fields visible when Home Assistant refreshes service
  metadata after the action selector has already rendered.

### Firmware Manifest Example

Pattern:

- `examples/firmware_manifest.json` documents the public firmware manifest
  shape expected by the OTA update entity.

Why:

- The HA integration consumes public firmware releases while firmware source
  lives in the separate MIT-licensed firmware repository.

## Bash Design Decisions

### Release Script

Pattern:

- `release.sh` validates semantic versions, updates version metadata, stages,
  commits, tags, pushes and creates a GitHub release.
- `--dry-run` is available.

Why:

- Keeps HACS release mechanics repeatable.
- Reduces version drift between `manifest.json`, `const.py`, README examples
  and release tags.

### Cleanup Script

Pattern:

- `cleanup_old_releases.sh` removes old semver releases/tags while keeping the
  configured number of latest releases.

Why:

- The project intentionally keeps only the current GitHub release unless a
  release-retention exception is requested.

## Markdown Documentation Conventions

Pattern:

- `README.md` is user-facing installation and architecture documentation.
- `CHANGELOG.md` keeps a separate block per release; release notes are no
  longer consolidated into one current block.
- `AGENTS.md` is the canonical in-repo working agreement for future coding
  agents.
- `HANDOFF.md`, `TODO.md` and `ISSUES.md` track operational state and known
  validation points.
- `SYNC_PROMPTS.md` is the only cross-repo prompt/contract file.
- This file, `TECHNICAL_DESIGN_DECISIONS.md`, records implementation design
  patterns, conventions and dependency inventory.

Why:

- Separates user documentation, release notes, implementation contracts and
  agent handoff state.
- Makes release hygiene explicit.

## Relay-Only Apple Push Policy

Pattern:

- Home Assistant keeps the authenticated client-facing
  `/api/djconnect/push/register` and `/api/djconnect/push/unregister` routes,
  but forwards registrations to the central `djconnect-api` relay instead of
  storing APNs tokens locally.
- The HACS integration only uses `DJCONNECT_PUSH_RELAY_URL` and
  `DJCONNECT_PUSH_RELAY_SECRET`. APNs provider `.p8` keys, provider JWT signing,
  topics, retries and invalid-token handling live in the central API.
- Push events are generated only for explicit Ask DJ response and confirmation
  attention events. Track, playback, queue, volume, mood, idle suggestion,
  status and polling updates are default suppressed.
- Runtime rate limiting allows at most one Ask DJ push per 30 seconds and five
  pushes per ten minutes per HA user plus device/client. Foreground or recently
  active clients are suppressed when status payloads expose usable activity
  state.

Primary source files:

- `custom_components/djconnect/push.py`
- `custom_components/djconnect/http.py`

Why:

- Keeps APNs platform credentials centralized and out of end-user Home Assistant
  instances.
- Prevents notification overload from ordinary playback state changes.
- Preserves privacy by sending only generic wake/sync hints while clients fetch
  real content through `/api/djconnect/ask_dj/history`.

## Third-Party Dependency Inventory

The table below lists direct runtime dependencies, Home Assistant component
dependencies and external APIs used by this repository. Transitive dependencies
of Home Assistant or its components are not individually pinned by this repo
unless imported or declared here.

| Dependency | Used From | Version In This Repo | License / Terms | Source URL |
| --- | --- | --- | --- | --- |
| Python | Runtime language, tests, scripts | Not pinned by repo; Home Assistant runtime provides Python | Python Software Foundation License | https://github.com/python/cpython |
| Python standard library | `asyncio`, `json`, `logging`, `secrets`, `dataclasses`, `hashlib`, `base64`, `urllib.parse`, `wave`, `unittest`, etc. | Same as Python runtime | Python Software Foundation License | https://github.com/python/cpython |
| Home Assistant Core | Custom integration APIs, config entries, HTTP views, entities, repairs, diagnostics, Assist/TTS/STT hooks | HACS minimum `2025.1.0` from `hacs.json`; actual runtime supplied by user | Apache License 2.0 | https://github.com/home-assistant/core |
| Home Assistant `http` component | HTTP view registration and local API routes | Declared in `manifest.json` dependencies | Apache License 2.0 as part of Home Assistant Core | https://github.com/home-assistant/core |
| Home Assistant `zeroconf` component | `_djconnect._tcp` mDNS discovery | Declared in `manifest.json` dependencies | Apache License 2.0 as part of Home Assistant Core | https://github.com/home-assistant/core |
| Home Assistant `bluetooth` component | BLE discovery for setup-mode devices | Declared in `manifest.json` dependencies | Apache License 2.0 as part of Home Assistant Core | https://github.com/home-assistant/core |
| Home Assistant `bluetooth_adapters` component | Bluetooth adapter/runtime support | Declared in `manifest.json` dependencies | Apache License 2.0 as part of Home Assistant Core | https://github.com/home-assistant/core |
| Home Assistant `conversation` component | Assist text command processing | Declared in `manifest.json` dependencies | Apache License 2.0 as part of Home Assistant Core | https://github.com/home-assistant/core |
| Home Assistant `assist_pipeline` component | Assist/STT pipeline selection and fallback | Declared in `manifest.json` dependencies | Apache License 2.0 as part of Home Assistant Core | https://github.com/home-assistant/core |
| Home Assistant `tts` component | DJ announcement audio generation | Declared in `manifest.json` dependencies | Apache License 2.0 as part of Home Assistant Core | https://github.com/home-assistant/core |
| Home Assistant `cloud` component | Optional Nabu Casa external URL discovery for Spotify OAuth setup | Declared in `manifest.json` `after_dependencies` | Apache License 2.0 as part of Home Assistant Core | https://github.com/home-assistant/core |
| aiohttp | HTTP client timeouts/session usage and `aiohttp.web` helpers | `aiohttp>=3.9.0` in `manifest.json` | Apache License 2.0 | https://github.com/aio-libs/aiohttp |
| awesomeversion | Firmware semantic version comparison | `awesomeversion>=23.8.0` in `manifest.json` | MIT License | https://github.com/ludeeus/awesomeversion |
| voluptuous | Config-flow and repairs schema definitions | Provided by Home Assistant runtime; imported directly in `config_flow.py` and `repairs.py` | BSD-style license | https://github.com/alecthomas/voluptuous |
| zeroconf | Async mDNS service browser and service-state changes | Provided through Home Assistant zeroconf dependency; imported dynamically in `discovery.py` | LGPL-2.1-or-later | https://github.com/python-zeroconf/python-zeroconf |
| bleak | BLE GATT client for WiFi provisioning | Provided through Home Assistant Bluetooth stack; imported dynamically in `ble.py` | MIT License | https://github.com/hbldh/bleak |
| bleak-retry-connector | Robust BLE connection helper | Provided through Home Assistant Bluetooth stack; imported dynamically in `ble.py` | MIT License | https://github.com/Bluetooth-Devices/bleak-retry-connector |
| HACS | Distribution surface for this custom integration | HACS metadata in `hacs.json`; HACS version not pinned | MIT License | https://github.com/hacs/integration |
| DJConnect API relay | Central Apple push notification relay for DJConnect Apple clients | External DJConnect service; no library is vendored | DJConnect MIT-licensed service repo unless its own dependencies state otherwise | https://github.com/pcvantol/djconnect-api |
| Spotify Web API | User-authorized backend playback, OAuth token endpoint and search/playback endpoints | External API; no library is vendored | Spotify Developer Terms | https://developer.spotify.com/documentation/web-api |
| Bandsintown API | Ask DJ upcoming artist concert agenda lookups | External API; no library is vendored | Bandsintown API terms | https://www.artists.bandsintown.com/support/api-installation |
| GitHub REST API | Firmware release and release-asset discovery | External API; no library is vendored | GitHub Terms of Service | https://docs.github.com/rest |
| Home Assistant Cloud / Nabu Casa URL | Preferred external HTTPS callback URL for Spotify OAuth | Optional user runtime service; no library is vendored | Nabu Casa service terms | https://www.nabucasa.com |

## Bundled Assets And Local Project Files

| Asset / File Type | Location | Ownership / License |
| --- | --- | --- |
| DJConnect brand images | `assets/`, `brands/`, `custom_components/djconnect/brand/` | DJConnect project assets; MIT License via `LICENSE` unless a specific asset says otherwise |
| Home Assistant integration source | `custom_components/djconnect/` | MIT License via `LICENSE` |
| Firmware release references | examples and docs | MIT-licensed DJConnect firmware repositories; firmware source lives outside this integration repo |
| Tests | `tests/` | MIT License via `LICENSE` |

## Dependency Update Rules

- Update this document whenever `manifest.json`, `hacs.json`, Home Assistant
  component dependencies, imported third-party modules, external APIs, or
  architecture patterns change.
- Do not invent exact runtime versions for dependencies managed by Home
  Assistant. Record the repository-declared lower bound or component contract.
- Keep license information aligned with upstream source URLs and
  `THIRD_PARTY_NOTICES.md`.
- Re-run `python3 -m unittest discover -s tests` after code or contract changes.
