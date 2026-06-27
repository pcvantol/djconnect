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
DJConnect protocol line `3.2.x`.

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

### Use-Case Layer Before Music Backends

Pattern:

- `custom_components/djconnect/use_cases.py` defines the internal
  `DJConnectUseCases` service layer, a small `MusicBackend` protocol and
  capability flags.
- Current migrated paths call `run_music_command(...)` or typed use-case methods
  instead of importing Spotify Direct helpers directly. This includes
  `/api/djconnect/command`, app/ESP status playback refresh, Ask DJ, voice
  processor commands and HA playback entities.
- HA and AI-facing tool surfaces call `run_music_command(...)` or
  `run_text_command(...)`: developer services, the Assist conversation agent,
  HTTP command/status routes, Ask DJ and playback entities should stay thin and
  should not import backend adapters or processor internals directly.
- `SpotifyDirectBackend` is the default adapter. It delegates to the existing
  Spotify Web API implementation while keeping OAuth refresh, Spotify Connect
  device handling, playlists, queue, recent-played, favorites and URI mapping
  behind the adapter boundary.
- Capability checks fail with a backend error before executing unsupported
  actions, so a future backend can report that it lacks queue, output, volume,
  favorites, recommendations or profile support without leaking provider
  details into HTTP handlers.
- Music Assistant is another adapter behind this interface. DJConnect must not
  build a Music Assistant clone, global provider registry, universal library
  index, queue engine or player grouping/sync engine.

Primary source files:

- `custom_components/djconnect/use_cases.py`
- `custom_components/djconnect/spotify_backend.py`
- `custom_components/djconnect/http.py`
- `custom_components/djconnect/ask_dj.py`
- `custom_components/djconnect/processor.py`
- `custom_components/djconnect/sensor.py`
- `custom_components/djconnect/number.py`
- `custom_components/djconnect/select.py`
- `custom_components/djconnect/switch.py`
- `custom_components/djconnect/button.py`

Why:

- Keeps DJConnect as the DJ/voice/intent/personality/memory layer.
- Prevents new app, Assist, service or future AI-tool code from growing deeper
  Spotify-specific dependencies.
- Preserves Spotify Direct for users who do not run Music Assistant.

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
- Runtime mood is a prompt input, not a user-facing DJ style setting. Numeric
  client mood is mapped to `chill`, `groove`, `energy` or `party` and the
  generated DJ announcement receives the matching style guidance. Missing mood
  keeps the hardcoded default style.
- The DJ announcement prompt may include compact DJ Memory and explicitly shared
  smart-home context for one short personal intro line. Weather or temperature
  references are allowed only when they come from configured read-only
  `smart_home_context_entities`; arbitrary HA state is never added.
- Clear direct playback requests are parsed deterministically before relying on
  stale playback context. Multi-word artist requests such as `speel dj paul
  elstak` must resolve from the current user text, not from a previous Spotify
  result.
- When an artist request starts playback and Spotify returns the concrete
  started track in the command response, the response generator merges that
  just-returned track metadata into the DJ announcement media context. It does
  not read stale `runtime.last_playback` as a substitute for the current
  command result.
- Album playback responses keep album and track fields separate. Album requests
  put the requested album in album metadata; when Spotify starts the first track,
  that track becomes the track/title field used in announcement text.
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
- ESP32/Raspberry Pi DJ response delivery posts text plus optional `audio_url`
  to the local `/api/device/dj_response` endpoint.
- App Ask DJ clients render response/history themselves and fetch response
  audio/images through HA `/api/djconnect/...` URLs. Remote-capable app
  responses can use an HTTPS external/Nabu Casa base URL when the request/app
  context requires it.
- Local-device temporary audio uses the shared local Home Assistant URL
  resolver, not a single HA network helper version.

Primary source files:

- `custom_components/djconnect/dj_response.py`
- `custom_components/djconnect/ha_urls.py`
- `custom_components/djconnect/tts.py`

Why:

- ESP32 and Raspberry Pi can fetch local DJ announcement audio without requiring
  Nabu Casa/cloud routing, while app clients can use remote-capable HA URLs for
  response/history/proxy assets when outside the LAN.
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
- Current values are `esp32`, `ios`, `macos`, `watchos`, `raspberry_pi` and `windows`.
- ESP32 and Raspberry Pi are local-device clients. They can use local mDNS,
  Client adres fallback and `/api/device/*` APIs.
- iOS, macOS and Windows are inbound-only app clients. They do not expose a
  HA-callable local API, do not need Client adres in setup, and may receive
  `ha_remote_url` after local pairing when Home Assistant has an HTTPS external
  URL. watchOS uses the iPhone proxy instead of a HA-direct pairing contract.
- ESP32 gets hardware-specific entities such as battery, WiFi RSSI, screen,
  LED, device settings, OTA and reboot controls.
- iOS, macOS, watchOS, Raspberry Pi and Windows clients keep backend/playback/client entities
  only. Apple clients additionally expose APNs readiness diagnostics and a
  privacy-safe test-push button. Raspberry Pi clients additionally expose local
  restart/shutdown buttons. Firmware channel and OTA controls are ESP32-only;
  Apple clients update through app distribution/TestFlight and Linux/Raspberry
  Pi and Windows clients update through their own source/install flow.
- Assist Conversation Agent-only entries load only the conversation platform
  and minimal diagnostics sensor, without playback, device-control, firmware or
  push-action entities.
- Config-flow setup is split into Assist Conversation Agent, local device
  pairing and app pairing. Local device pairing offers ESP32/Raspberry Pi;
  app pairing offers iOS/macOS/Windows.

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
- `personal_memory_summary` is narrower than profile analysis. It answers
  privacy-style questions such as `wat weet je nu over mij?` from server-side
  DJ Memory only, returns source `djconnect_memory`, no images and no playback
  actions, and must not fetch Spotify listening-profile enrichment or reuse the
  current playback media card.
- Spotify listening-profile enrichment is non-mutating and uses official Web
  API reads only: `/me/player/recently-played` and `/me/top/{artists,tracks}`.
  The integration caches compact profile snapshots in DJ Memory with a
  multi-hour TTL instead of storing unlimited raw listening history.
- Ask DJ profile responses expose `sources[]` metadata so clients can show
  Spotify recently played/top-items and DJConnect Memory provenance separately
  from normal links.
- `recently_played_history` is a separate read-only Ask DJ intent for questions
  about recently played tracks, albums, artists and playlist contexts. It uses
  Spotify `/me/player/recently-played`, returns display-ready `items[]` plus
  proxied `images[]`, sets `action:"none"` and never creates playback actions
  unless a future backend path explicitly opts in.
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
  runtime/config-entry data/config-entry options/config token sources before
  creating a Repair issue.
- A token returned by Spotify's refresh endpoint is persisted to the config
  entry whenever it differs from stored data, even if runtime memory already
  contains that rotated value.

Primary source files:

- `custom_components/djconnect/spotify_backend.py`
- `custom_components/djconnect/spotify_oauth.py`
- `custom_components/djconnect/repairs.py`

Why:

- Devices/apps stay backend-agnostic and do not receive playback credentials.
- Spotify token expiry and token rotation should be invisible to clients.
- A user-facing Repair is only appropriate when Spotify rejects every known
  stored refresh token.

### Music Backend Boundary

Pattern:

- `custom_components/djconnect/use_cases.py` is the thin use-case boundary for
  playback and natural-language command execution.
- `SpotifyDirectBackend` wraps the existing Spotify Web API backend.
- `MusicAssistantBackend` targets one configured Music Assistant
  `media_player` through Home Assistant `media_player` services.
- Music Assistant is documented as the no-DJConnect-Spotify-OAuth route:
  provider login, library browsing, queue semantics and grouping/sync stay in
  Music Assistant, while DJConnect stores only the configured target player.
- The selected backend is explicit: `spotify_direct` or `music_assistant`.
  There is no automatic fallback mode.
- Capabilities describe which user-visible features are available. Ask DJ and
  entities degrade on unsupported capabilities instead of rebuilding Spotify
  features locally.
- Backend switching is an explicit options-flow action, not a silent dropdown
  and not a reinstall requirement. This keeps users in control of provider
  consequences while preserving pairing, device tokens, Ask DJ history, DJ
  Memory and push registrations. A monotonic `music_backend_revision` lets
  clients invalidate old backend-specific playback actions after a switch.
- The backend contract is exposed in pair/status/command responses rather than
  requiring client-specific discovery endpoints. Errors are normalized to safe
  `music_backend_error`, `stale_backend_action` and
  `unsupported_backend_capability` shapes so clients can recover without
  seeing raw provider exceptions or secrets.

Why:

- DJConnect clients keep one backend-neutral command/response contract.
- Music Assistant remains the owner of provider auth, library, queues and
  grouping/sync behavior.
- Spotify OAuth, scopes and repairs stay scoped to Spotify Direct entries.

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

- Diagnostics redact keys containing `token`, `password`, `secret`, `proof`,
  `authorization`, `prompt`, `history`, `memory` or `raw_audio`.
- Logs use metadata instead of raw secrets, raw prompts, raw audio, Ask DJ
  history, memory dumps or full payload dumps.
- Spotify token logs include expiry timing, source names and rotation status,
  never token values.
- Diagnostics expose Assist STT/TTS readiness as metadata only: configured
  pipeline id, resolved pipeline names, provider engine ids, helper
  availability and boolean readiness. They do not include raw audio, prompts,
  transcript history, TTS voice ids or generated audio.

Primary source files:

- `custom_components/djconnect/diagnostics.py`
- `custom_components/djconnect/__init__.py`
- `custom_components/djconnect/http.py`
- `custom_components/djconnect/spotify_backend.py`
- `custom_components/djconnect/assist_stt.py`
- `custom_components/djconnect/tts.py`

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
- The HACS integration stores only per-install central API settings:
  `api_base_url`, stable `ha_install_id` and a secret `djci_` install token in
  Home Assistant config entry options. It must not contain a global relay
  secret.
- Apple clients (`ios`, `macos`, `watchos`) can supply a short-lived
  `bootstrap_proof` during push registration or pairing/status. HACS uses that
  proof only to mint the per-install `djci_` token through `/v1/install/token`;
  without a proof HACS does not attempt blind/public token minting. ESP32,
  Raspberry Pi, Windows and Assist-agent-only entries do not require this proof because
  they do not use APNs push.
- APNs provider `.p8` keys, provider JWT signing, proof validation, topics,
  retries and invalid-token handling live in the central API.
- Push events are generated only for explicit Ask DJ response and confirmation
  attention events. Track, playback, queue, volume, mood, idle suggestion,
  status and polling updates are default suppressed.
- Runtime rate limiting allows at most one Ask DJ push per 30 seconds and five
  pushes per ten minutes per HA user plus device/client. Foreground or recently
  active clients are suppressed when status payloads expose usable activity
  state.
- `sensor.djconnect_apns_registration` is the user-facing registration summary.
  Known relay/bootstrap failures should surface as `error` plus
  `last_push_error`; a missing install token without a known registration/error
  remains `disabled`.
- `djconnect.test_apns_push` is the developer diagnostic surface for this path.
  Dry-run mode evaluates the HA push policy and returns relay/config/status
  flags without sending. `send:true` calls the central relay once and returns
  `sent`, `error`, `result`, `decision` and redacted `push_statuses`. The
  response must expose only presence booleans for secrets such as
  `install_token_present` and `bootstrap_proof_present`, never raw APNs tokens,
  bearer tokens, proofs or `djci_` values.

Primary source files:

- `custom_components/djconnect/push.py`
- `custom_components/djconnect/http.py`
- `custom_components/djconnect/__init__.py`
- `custom_components/djconnect/sensor.py`

Why:

- Keeps APNs platform credentials centralized and out of end-user Home Assistant
  instances.
- Avoids shipping a shared HACS relay secret while still requiring an
  Apple-client pairing proof before a new central install token can be minted.
- Prevents notification overload from ordinary playback state changes.
- Preserves privacy by sending only generic wake/sync hints while clients fetch
  real content through `/api/djconnect/ask_dj/history`.

## Ask DJ Backend Response Shaping Inventory

As of `3.2.x`, Ask DJ may still use Spotify-specific retrieval paths for
Spotify Direct only, but client-visible playback actions must carry backend-aware
metadata. The reusable `backend`, `provider`, `music_backend_revision` and
nested `value` fields are owned by `custom_components/djconnect/use_cases.py`
through `music_backend_action_fields(...)`, not by Ask DJ.

Migrated safe surface:

- Search, playlist, album, recommendation and artist Play Now action metadata
  now uses the backend/use-case helper for the stable backend-aware envelope.
- Spotify Direct keeps legacy top-level `uri`, `context_uri` and `offset_uri`
  fields for existing clients while also exposing the generic nested `value`.
- Music Assistant actions use generic `item_id`, `media_type`,
  `target_player_id` and `provider` in `value`, so future non-Spotify action
  execution does not require clients to assume Spotify URIs.

Remaining Spotify-specific shaping by design:

- Spotify Direct search helpers still filter `spotify:track`, `spotify:album`,
  `spotify:artist` and `spotify:playlist` URIs before creating actions.
- Recently played, top-items, listening-profile, queue and playlist-save
  responses still expose Spotify source labels because those capabilities are
  only available from Spotify Direct today.
- User-facing fallback text may mention Spotify OAuth/scopes only when the
  selected backend is Spotify Direct; unsupported capability fallbacks for other
  backends must use `MusicBackendCapabilityError`.

Migration rule:

- New client-visible Ask DJ action shapes should call backend/use-case helpers
  for backend metadata first, then add provider-specific compatibility fields
  only when the active adapter needs them.

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
| MusicBrainz API | Optional Ask DJ technical track-analysis metadata/context enrichment through `metabrainz_metadata` | External API; no library is vendored. Requests use JSON, a meaningful DJConnect User-Agent, compact runtime caching and one-request-per-second protection. | MusicBrainz/MetaBrainz terms and data licenses | https://musicbrainz.org/doc/MusicBrainz_API |
| ListenBrainz API | Optional Ask DJ technical track-analysis public listen/metadata context through `metabrainz_metadata` | External API; no library is vendored. Requests are unauthenticated, cached compactly and failure-tolerant. | ListenBrainz/MetaBrainz terms and data licenses | https://listenbrainz.readthedocs.io/en/latest/users/api/index.html |
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
