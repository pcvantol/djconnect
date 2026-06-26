# Changelog

## 3.1.99

- Add a free online MetaBrainz metadata/context provider for Ask DJ technical
  track analysis, using MusicBrainz and ListenBrainz with compact caching,
  rate-limit protection and explicit limitations that it does not measure BPM,
  waveform, stems or exact arrangement sections.

## 3.1.98

- Extend Ask DJ technical track analysis to provider-neutral contract v2 with
  client-ready `analysis.sections[]`, `analysis.timeline[]` and
  `analysis.dj_tips[]` while preserving the v1 measured/inferred/limitations
  fields for existing clients.
- Add canonical Ask DJ track-analysis v2 response fixtures and contract tests so
  clients can build and validate their UI against stable golden samples.
- Add provider plug-in contract v1 for Ask DJ track analysis with explicit
  `analysis.providers[]` status reporting for Spotify measured analysis, Home
  Assistant Conversation inference and local fallback providers.

## 3.1.97

- Move Ask DJ technical track analysis into a dedicated provider-neutral
  `track_analysis.py` aggregator so `ask_dj.py` only routes the intent and
  future user-configured providers can be added without growing the chat
  handler.

## 3.1.96

- Promote Ask DJ technical track analysis to a provider-neutral v1 contract with
  `analysis.mode`, `analysis.measured`, `analysis.inferred` and
  `analysis.limitations`, keeping the feature local-first and free of any
  required DJConnect central backend.
- Include Home Assistant Conversation or local fallback musical duiding in
  technical track analysis responses while preserving measured-vs-inferred
  source boundaries and read-only playback behavior.

## 3.1.95

- Add deterministic offline Ask DJ E2E contract cases, including exact coverage
  for every prompt returned by the Ask DJ help function.
- Expand Ask DJ playback/list intents for artist tracks, albums, mixes, current
  track variants, genre questions, DJ announcements and Play Now response
  validation.
- Add read-only technical track analysis support for prompts such as
  `Analyseer dit nummer`, returning Spotify playback/audio-analysis metadata
  without mutating playback.
- Return speaker selection actions when an Ask DJ playback request cannot start
  because Spotify has no active output, then replay the original request after
  the user chooses a speaker.
- Document the updated Ask DJ help, E2E contract flow, technical analysis
  response shape and no-active-output speaker follow-up behavior.

## 3.1.94

- Add Ask DJ intent `zet huidig nummer in favorieten` / `save this track to
  liked songs`, backed by Spotify `save_current_track` and text-only client
  responses.
- Add a `save_current_track` control action to current-track Ask DJ responses so
  clients can show a direct `Zet in favorieten` button from Ask DJ and Now
  Playing surfaces.
- Support current-track seed mix requests such as `maak playlist obv huidig
  nummer`, `ik wil meer van deze muziek horen` and `heb je meer nummers die
  hierop lijken`, using the active Spotify track URI as the Spotify
  recommendations seed.
- Queue current-track recommendation requests such as `ik wil vergelijkbare
  tracks` immediately and return the first 10 queued recommendations as Play Now
  rows.
- Treat broad genre/vibe mix requests such as `maak een 90s dance mix` as genre
  recommendation seeds and return individual Play Now track rows plus a whole
  `track_mix` action.
- Add `user-library-modify` to required Spotify OAuth scopes for saving the
  current track to Liked Songs/favorites.

## 3.1.93

- Scope `/api/djconnect/ask_dj/history/clear` to the authenticated Home
  Assistant user/context and keep `clear_revision` as the authoritative client
  cache clear marker.
- Add a best-effort next-queue Play Now row after Ask DJ next/previous playback
  commands so clients can show the following queued track without reusing stale
  media chrome.

## 3.1.92

- Add richer Ask DJ Play Now list responses for fuzzy Spotify searches, genre
  and vibe requests, user playlists, artist discography prompts and contextual
  `Meer van <artiest>` follow-ups.
- Add server-side Ask DJ controls for resume, volume up/down, shuffle toggles
  and repeat options while keeping pure status/control answers text-only when
  they should not show media chrome.
- Improve Ask DJ contextual follow-ups, including artist carry-over for
  `ik wil Zombie horen`, album overview questions and queue/mood mix previews
  with clickable rows.
- Add a DJ Memory-only Ask DJ intent for questions such as `wat weet je nu over
  mij?`, with text-only responses, source `djconnect_memory`, no artwork and no
  Play Now actions.
- Refresh Ask DJ help, voice-intent data and client rendering documentation for
  the new memory, search, action-button and Play Now response shapes.

## 3.1.91

- Return a live Spotify playback snapshot from `/api/djconnect/status` for
  watchOS, iOS and macOS clients, matching the `command: "status"` response
  shape and always including explicit `playback.has_playback` metadata.
- Keep app status refreshes successful when no playback is active while marking
  `backend_available` false only when the playback backend cannot be reached.
- Avoid false Spotify authorization repairs for Apple Watch/app entries that do
  not own Home Assistant Spotify OAuth configuration.

## 3.1.90

- Route `wat speelt hierna` and similar next-track questions to the Spotify
  queue reader instead of the generic Ask DJ music-info response.
- Route `wat speelde hiervoor` and similar previous-track questions to Spotify
  recently played history without triggering the playback `previous` control.
- Use the richer DJ announcement pipeline for Ask DJ `next` / `previous`
  playback controls, so skipping tracks can return a contextual DJ response
  with current playback metadata instead of only the fixed control sentence.

## 3.1.89

- Make Ask DJ message responses include canonical `messages: [user, assistant]`
  exchange ordering with shared `exchange_id` and `exchange_order`, so clients
  can always render the question above the answer even when HTTP, push and
  history sync timing overlap.
- Return speaker selection actions instead of an HTTP 400 when a Play Now
  recommendation is requested while no Spotify output is active.
- Send plain text to Home Assistant TTS before SSML so spoken DJ answers no
  longer read XML markup aloud on TTS backends that do not support SSML.
- Keep proxied Ask DJ image URLs from being proxied a second time, preserving
  album art in queue/list responses.
- Use explicit `Play Now` labels for queue playback actions and support both
  singular and plural playlist search requests such as `heb je een playlist van
  snowpatrol` and `heb je playlists van snowpatrol`.

## 3.1.88

- Add deterministic Ask DJ follow-up support for current-track album context:
  `wat speelt er`, `op welk album werd dit nummer uitgebracht` and
  `speel album` now use Spotify playback metadata to answer with the current
  track, artist and album, then start the current album when explicitly asked.
- Add Ask DJ lookup support for `speel het album met nummer X van artiest Y` by
  resolving track `X` via Spotify, reading its album context and starting that
  album.
- Add Ask DJ lookup support for `van wie is ook alweer het nummer X?`, returning
  the artist and album plus Play Now actions for both the track and its album.
- Improve the setup flow for app-like clients by including Windows in the first
  setup screen and avoiding ESP32-specific defaults when an app client is being
  paired or discovered.

## 3.1.87

- Add Windows as a first-class app-like client type (`client_type=windows`) with
  `djconnect-windows-XXXXXXXXXXXX` IDs, mDNS/pairing-info discovery, Ask DJ
  voice handling and config-flow labels.
- Keep backend playback controls from briefly becoming unavailable when app
  clients send sparse status updates or Spotify returns an idle playback
  snapshot without control metadata.
- Keep music-related backend sensors such as Spotify status, last track, sound
  output, queue, playlists and outputs from falling back to unknown during
  sparse app/client status updates.
- Make APNs test push diagnostics report missing bootstrap/install-token setup
  before rate limiting, and prevent dry-run diagnostics from consuming the rate
  limiter.
- Prevent `send:true` APNs test pushes from rate-limiting themselves by running
  the diagnostic preflight without consuming the push limiter.

## 3.1.86

- Remove the native Home Assistant playback proxy `media_player` entity. Backend
  playback still works through DJConnect commands and the remaining volume,
  output, repeat, shuffle, queue, playlist and status entities, but the proxy no
  longer appears on the Home Assistant device page.
- Rename the user-facing firmware/client version sensor label to `App version`
  / `App versie`, and read Apple client versions from `app_version` / `version`
  before falling back to legacy `firmware` while keeping the existing entity id
  stable.
- Add the `djconnect.test_apns_push` developer diagnostic service and make the
  APNs test button report actionable relay/bootstrap errors instead of `1`.

## 3.1.85

- Stop Home Assistant entity churn caused by Spotify progress-only playback
  refreshes by ignoring volatile progress/timestamp fields in runtime update
  signatures while still notifying on real playback metadata/state changes.

## 3.1.84

- Reduce post-pairing Home Assistant state churn by suppressing unchanged
  runtime listener notifications and exposing compact debug/status attributes
  instead of full playback/device payloads.
- Harden watchOS Bonjour discovery by accepting Apple pairing-code aliases from
  TXT and pairing-info payloads, and cover the full watchOS discovery-to-pairing
  config-flow path with tests.

## 3.1.83

- Make the backend playback proxy event-driven as well, so the Home Assistant
  device page no longer keeps polling the final media player entity after
  pairing.

## 3.1.82

- Keep mDNS/pairing-info discovered device names authoritative in the pairing
  form so selecting `DJConnect Mac` or `DJConnect iPhone` does not append an
  extra client-type suffix.
- Stop post-pairing entity update storms by making secondary backend sensors,
  numbers, switches and selects event-driven; the playback proxy remains the
  single periodic backend playback poller.

## 3.1.81

- Remove the Spotify market/region selector from the normal pairing and Spotify
  OAuth setup flow while keeping the internal default for Spotify Web API calls.
- Reduce stale-client log noise by throttling repeated bearer-token mismatch
  warnings without logging token values or derived token identifiers.
- Stabilize post-pairing entity updates by skipping unchanged runtime listener
  notifications and preventing sparse status heartbeats from replacing a known
  pairing state with `unknown`.

## 3.1.80

- Add a `Test push message` button entity for paired iOS, macOS and watchOS
  clients so APNs relay delivery can be tested from Home Assistant without
  sending prompt text or secrets.
- Harden Apple push registration validation for iOS, macOS and watchOS by
  requiring matching `client_type`/`device_id` prefixes, safe APNs token strings
  and explicit `sandbox` or `production` environments.
- Fix watchOS client runtime matching for push registration by recognizing
  `djconnect-watchos-XXXXXXXXXXXX` device ids.

## 3.1.79

- Refresh the Ask DJ recent listening-history contract in README, API docs,
  Postman examples and cross-repo sync notes, including compact `items[]`
  rendering guidance for tracks, albums, artists and playlist contexts.
- Expand the canonical voice intent data with Ask DJ help, speaker/output,
  retry and richer recently-played examples for website and client chips.

## 3.1.78

- Fix the native playback proxy setup lifecycle so backend status refreshes no
  longer try to write Home Assistant state before the media player has an entity
  id.
- Treat negative Spotify/device volume sentinel values such as `-1` as unknown
  instead of publishing invalid `number.djconnect_volume` states.

## 3.1.77

- Fix Spotify OAuth/reauthorization UX so the Home Assistant external step shows
  a useful DJConnect authorization page and stale Spotify repair issues are
  cleared when valid credentials are present.
- Treat fresh app-client pairings as backend-playback capable when any loaded
  DJConnect entry has valid Spotify credentials, avoiding false "playback not
  available" warnings immediately after macOS/iOS pairing.
- Refresh Spotify-backed Home Assistant entities from live backend state for
  playback proxy, volume, output, repeat, shuffle, playlists, queue, outputs and
  playback availability, including album art/current track metadata and the
  native Spotify 0-100 volume scale.
- Add Ask DJ recent-played history intents for tracks, albums, artists and
  playlists using Spotify recently-played data, returning structured `items[]`
  and image metadata for compact client-side list rendering.
- Keep Ask DJ recommendation Play Now controls labeled as `Play Now` instead of
  using artist or item names as the button label.

## 3.1.76

- Clear server-side DJ Memory and Ask DJ history when the last DJConnect Home
  Assistant config entry is unloaded, preventing deleted clients from seeing old
  chat state after re-pairing.
- Reject stale client requests when their `device_id` or bearer token no longer
  matches any loaded DJConnect runtime instead of falling back to another active
  entry.
- Return and deliver a normal DJ announcement, including optional replayable
  audio, after successful Ask DJ Play Now actions.
- Keep unknown or unsupported Ask DJ informational fallback responses text-only
  instead of attaching current playback album art.
- Return actionable `Ja graag` / `Nee dank je` confirmation buttons for generic
  playlist/recommendation offers instead of a plain text prompt with stale art.

## 3.1.75

- Refresh the public and cross-repo Ask DJ documentation for help prompts,
  speaker/output actions, album lists, retry behavior, Resume controls,
  deterministic playback parsing and mood-driven DJ announcements.
- Add DJ announcement prompt guidance for short personal intro lines from compact
  DJ Memory and explicitly shared weather/temperature smart-home entities.

## 3.1.74

- Fix album playback announcements so album requests keep album and first-track
  metadata separate, for example Radiohead `OK Computer` with first track
  `Airbag`.
- Route `hervat muziek` / `resume music` directly to backend playback and return
  a `Resume` action after pause/stop responses.
- Improve Ask DJ playback parsing for clear multi-word artist requests such as
  `speel dj paul elstak` so stale previous playback context is not reused.

## 3.1.73

- Add text-only Ask DJ help output for `help`, `hulp` and
  `welke commando's`, including a categorized list of supported prompt options.
- Return speaker/output questions as a text list plus `Activeer` output actions,
  without reusing artwork from a previous music response.
- Return album-discography questions as album lists with direct Play Now album
  actions.
- Make `Probeer opnieuw` replay the previous retryable playback request instead
  of treating the retry phrase as a new music query.

## 3.1.72

- Require a pairing/bootstrap proof before HACS requests a central `djci_` install token, avoiding blind/public token minting without adding a global HACS secret.
- Accept bootstrap proofs from pairing-info, pairing, status and push-registration payloads, use them only for central token bootstrap and redact them from logs/diagnostics.

## 3.1.71

- Add a diagnostic APNs registration sensor for DJConnect app/client entries so users can inspect push registration state without exposing tokens.
- Keep Assist Conversation Agent-only entries focused on the conversation agent plus diagnostics instead of exposing device/app playback controls.
- Add automated Postman collection validation to CI, covering collection schema, placeholder secrets, auth headers, client identity examples and JSON content types.
- Document Postman validation as part of the release checklist and cleanup workflow.

## 3.1.70

- Add production-safe central DJConnect API support with automatic per-install `djci_` token bootstrap, stable `ha_install_id` storage and configurable API base URL.
- Replace HACS push relay environment secrets with per-install bearer-token calls to the central API, keeping event payloads limited to privacy-safe sync metadata.
- Keep the install-token handshake invisible to users: Home Assistant calls `/v1/install/token` under the hood and stores the returned token in config entry storage.
- Add central API tests for automatic token bootstrap, bearer authorization, atomically successful token rotation and privacy-safe push event payloads.
- Document that install tokens are internal secrets and must never be pasted into issues or logs.

## 3.1.69

- Add a strict Ask DJ push policy with no playback, track, queue, volume, mood, status or idle-suggestion pushes.
- Rate-limit Ask DJ push relay events to one push per 30 seconds and five pushes per ten minutes per HA user and device/client.
- Suppress Ask DJ pushes to foreground or recently active clients when client status reports usable activity state.
- Keep Ask DJ push payloads generic and privacy-safe with `thread-id: djconnect.askdj`, no raw prompts, assistant responses, memory, history or tokens.
- Fix HACS/hassfest release validation metadata and translation URL placeholders for the v3.1.69 release branch.

## 3.1.68

- Add central `djconnect-api` backend setup guidance to the cross-repo sync prompts so the Cloudflare APNs relay remains aligned with the HACS integration.
- Move HACS push support to a relay-only architecture: Home Assistant forwards authenticated Apple client registrations/events to `djconnect-api` and no longer contains direct APNs provider-key, JWT, topic or token-invalidation logic.
- Ignore local environment files and APNs `.p8` keys to keep relay credentials and development secrets out of the repository.

## 3.1.67

- Add server-side Apple push registration endpoints for iOS, macOS and watchOS clients with Home Assistant Store persistence, bearer-token auth and APNs provider-token delivery.
- Send privacy-safe Ask DJ push wake signals after server-side history updates, including `history_revision` sync hints without raw prompts, full responses, tokens or memory context.
- Report push capability and registration status in client status responses, and disable invalid APNs tokens after BadDeviceToken/Unregistered-style failures.
- Make DJ announcement style runtime mood-driven by removing the user-facing DJ style/prompt choice and falling back to a hardcoded default when no client mood is known.
- Document APNs configuration, sandbox vs production behavior, push privacy rules and client sync requirements in the API contract and README.

## 3.1.66

- Raise the server-side Ask DJ history retention limit from 200 to 1000 messages per HA user while keeping trim metadata and retention system messages.
- Prepare Ask DJ for read-only smart-home context by adding an explicit Home Assistant entity allowlist for future event-aware prompts and confirmation suggestions.
- Add shared DJConnect mood-zone support for Apple Watch/iOS/backend Ask DJ requests, mapping numeric mood values to Chill, Groove, Energy and Party prompt context.
- Document the current Ask DJ client contract for server-side history, follow-up confirmations, idle suggestions and playback action handling.
- Keep the repository bootstrap prompt aligned with the released integration version.
- Refresh DJConnect release metadata and firmware manifest examples for the 3.1.66 release.

## 3.1.65

- Add text-only ambient Ask DJ music facts when Spotify playback moves to a new artist/album combination, deduped so multiple tracks from the same album/artist do not create repeated chat messages.
- Make Ask DJ history production-safe with a 200-message server-side limit, retention system messages and explicit `history_limit`, `history_trimmed_before` and `history_trimmed_count` sync metadata for clients.
- Add Ask DJ follow-up confirmation buttons through `playback_actions[]` / `confirmation_actions[]` with `command:"ask_dj_followup_response"`, server-side pending follow-up state and Ja/Nee handling.
- Add morning startup support for `Goedemorgen` / `Good morning` when playback is idle, returning a personalized morning suggestion with Ja/Nee buttons without starting playback automatically.
- Treat sleep phrases such as `ik ga slapen` as direct pause/stop playback requests.
- Harden Ask DJ fallback handling for gibberish, sandbox escape and prompt-injection style input so those requests do not reach the conversation agent or playback paths.
- Expand Ask DJ playback/search behavior for English `next`, queue listing, playlist search, album/artist disambiguation, recommendation lists, repeat responses and safer generated DJ announcements.

## 3.1.64

- Make Ask DJ text chat conversation-aware by using recent server-side history before routing intents, so short follow-ups like "Geeft niet", "Dank je" and "Laat maar" get natural text-only replies without rerunning lookups or mutating playback.
- Treat short clarifications such as "alleen tussen 1980 en 1990" as context for the previous Ask DJ request before continuing through the normal informational/playback routing.
- Answer Ask DJ album-discography questions from Spotify artist album data, including current-artist follow-ups such as "Welke albums bracht deze artiest uit?" and proxied chronological album-cover lists.
- Answer Ask DJ similar-artist questions from the current playback artist or recent conversation artist context using Spotify related artists when available.
- Treat "Speel wat anders" as a personal recommendation request that returns Play Now actions from DJConnect Memory plus Spotify recent/top profile data without immediately changing playback.
- Answer Ask DJ genre/style questions such as "Wat voor muziek maakt artiest X?" from Spotify artist profile genres with natural phrasing and optional artist artwork.
- Answer Ask DJ concert-agenda questions such as "Wanneer speelt artiest X in Nederland?" from Bandsintown web data with a formatted date/location list and clickable source links.

## 3.1.63

- Add cross-device Ask DJ history sync with HA-user scoped persistent history, `/api/djconnect/ask_dj/message`, `/api/djconnect/ask_dj/history` and revision-based clear support.
- Add Ask DJ `audio_response` policy so informational text chat is text-only by default while playback/hybrid and voice/PTT responses still generate replayable TTS audio when available.
- Clarify DJConnect client authentication warnings so app clients are no longer logged as ESP requests and bearer-token mismatches identify the entry mismatch without exposing token values.
- Fix Ask DJ voice/PTT playback requests so commands such as "speel Armin van Buuren" and bare artist names route to the playback parser instead of the informational music fallback.
- Fix Ask DJ text playback requests so playback/parser failures return a normal chat response instead of HTTP 500 `ask_dj_unavailable`.
- Fall back to the local Spotify music parser when Assist cannot parse a direct Ask DJ playback request, so "Speel Armin" still becomes an artist search for `Armin`.

## 3.1.61

- Add server-side DJ Memory groundwork for future Ask DJ clients, including HA Store persistence, runtime session context, playback/Ask DJ context tracking and watchOS voice metadata support.
- Add the Ask DJ backend text API and services, including intent routing for informational questions versus playback actions, shared memory clear/history-state checks, proxied images, source links and optional audio responses.
- Add Ask DJ intent `personal_music_profile_analysis` for non-mutating personal listening-profile analysis over periods such as last month, last 30 days and this year.
- Add Spotify listening-profile enrichment for Ask DJ using recently played tracks and top artists/tracks, with compact DJ Memory snapshots and response `sources[]` metadata.
- Add Ask DJ Push-To-Talk support for iOS/macOS/watchOS WAV uploads on `/api/djconnect/voice`, including transcript responses, shared Ask DJ memory/context handling and capability flags.
- Add Ask DJ Play Now support for personal recommendations through non-mutating `playback_actions[]` plus explicit `ask_dj_play_recommendation` command handling.
- Add a Postman collection for the DJConnect Home Assistant HTTP API and include it in the release-cycle checklist.

## 3.1.60

- Add `watchos` as a first-class DJConnect app client type, including pairing, status, command, voice upload, mDNS discovery, entity filtering, translations and documentation.

## 3.1.59

- Rename the Bluetooth WiFi setup method to clarify that it configures ESP32 device WiFi.
- Use static Spotify repair issue IDs so Home Assistant can show translated repair titles and descriptions.

## 3.1.58

- Remove the repeated setup method selector from the pairing step, show client type choices as iOS, macOS, Linux/Raspberry Pi and ESP32, and keep firmware channel selection ESP32-only.

## 3.1.57

- Hide device-only DJ response playback and firmware channel controls from the Assist Conversation Agent setup flow.

## 3.1.56

- Select `Assist Conversation Agent` by default in the Add Integration setup method step.
- Add a direct Spotify Developer Dashboard URL to the Spotify setup instructions.
- Rename the client/device setup option to `DJConnect app of device koppelen`.
- Cache the ESP status request source IP and retry OTA against cached IP fallbacks when the `.local` device URL cannot be reached.

## 3.1.55

- Fetch stable firmware manifests directly from GitHub's latest release download URL before falling back to release metadata, improving OTA discovery when latest release JSON is unavailable or incomplete.

## 3.1.54

- Remove the Home Assistant deep-link button from the Spotify OAuth result page because the DJConnect config flow is not complete yet at that point.
- Remove user-facing advanced compatibility, OTA battery and DJ announcement audio TTL fields from config/options flow while keeping their internal defaults.
- Require users to enter their own Spotify Developer app Client ID and show the exact Home Assistant redirect URI that must be registered in Spotify.
- Document DJConnect's AI-assisted/Codex development workflow and related security expectations in contribution and security docs.
- Add a local development environment guide for tests, Docker Home Assistant sync/restart and manual UI validation.
- Answer DJ questions such as "Welk nummer draait er nu?" by reading the current Spotify playback state and generating a DJ response without starting new playback.
- Add direct DJ playback controls for stop/start music, volume up/down by 10, next track and previous track without running Spotify search.
- Update the canonical voice intent data and add `VOICE_INTENT_DATA.md` for current-track and playback-control intent families.

## 3.1.53

- Add community and security policy documentation for public repository hygiene.
- Standardize the fresh-chat prompt filename across DJConnect repositories as `CHAT_BOOTSTRAP.md`.
- Align DJConnect security policies across the Home Assistant, Apple app, ESP32 firmware, website and Raspberry Pi repositories with the shared `security@djconnect.dev` contact path.

## 3.1.52

- Align repository documentation with the project-wide MIT licensing model and remove the separate proprietary firmware binary license document.
- Add contribution guidelines for DJConnect integration changes, tests, documentation and licensing expectations.

## 3.1.51

- Hide the DJ announcement playback toggle from the compact Assist conversation-agent options flow; Assist satellites speak the returned conversation response through their configured pipeline TTS.
- Add an initial setup choice for an Assist Conversation Agent-only DJConnect entry, without requiring a DJConnect client pairing code.
- Name the conversation entity `DJConnect DJ` directly instead of letting Home Assistant prefix it with the configured client/device name.

## 3.1.50

- Remove the Spotify source override and default playlist override from config/options flows so the conversation-agent options stay focused on DJ response behavior.
- Rename the user-facing Client API URL labels to Client adres.

## 3.1.48

- Add the DJConnect Assist conversation agent platform so Home Assistant Voice Preview Edition and other Assist satellites can route recognized speech directly to DJConnect for Spotify playback and DJ response speech.
- Simplify DJConnect options to the conversation-agent relevant controls: DJ response enable/style/prompt and Spotify playback overrides, while preserving hidden device, firmware and Assist pipeline settings.
- Start Spotify repair OAuth from the translated `authorize` external step so the Home Assistant repair popup shows explanatory text instead of an empty website dialog.

## 3.1.47

- Simplify DJConnect voice setup to a single Assist pipeline selection: standalone STT engine and TTS engine/language/voice fields are no longer shown in config/options flows.
- Ignore legacy DJConnect `stt_engine` and `tts_*` option values at runtime, using the selected/preferred Home Assistant Assist pipeline for STT and DJ announcement TTS so stale language/voice overrides cannot block `audio_url` generation.
- Keep using the selected/default Assist conversation agent for Spotify intent detection, STT correction and DJ announcement generation, while prefixing DJ response prompts with DJConnect-specific instructions that override global smart-home agent guidance.
- Update DJ announcement prompt presets and the free-form prompt frame to ask for artist, album and track when known.

## 3.1.46

- Send Home Assistant STT metadata as native audio enums, including `channel`, `sample_rate` and `bit_rate`, so OpenAI STT can construct a valid WAV upload for PTT audio.

## 3.1.45

- Send plural `channels` STT metadata for Home Assistant/OpenAI speech-to-text providers while keeping a legacy `channel` fallback for older providers.

## 3.1.44

- Load the DJConnect OAuth callback logo through Home Assistant's executor so rendering the Spotify OAuth result page no longer performs blocking file I/O in the event loop.
- Treat Home Assistant Assist "area called ..." prompt leakage as a device lookup error so iPhone PTT music requests fall back to DJConnect's local music parser instead of failing the command flow.

## 3.1.43

- Remove the config-flow prerequisite for an official Home Assistant Spotify `media_player` entity; DJConnect uses its own Spotify OAuth credentials and Spotify Web API backend playback.

## 3.1.42

- Block DJConnect client setup until Home Assistant has an Assist pipeline with both STT and TTS configured, with translated config-flow guidance.
- Add DJ announcement prompt presets for neutral/business, warm/personal and humorous/witty styles while keeping the existing free-form prompt option.

## 3.1.41

- Add an ESP-only `switch.djconnect_wake_word` entity that mirrors `wake_word_enabled` / `wake_word` from ESP status payloads and sends the canonical `wake_word` device command to enable or disable local wake-word detection.
- Include the concrete current Spotify track returned by the just-executed playback command in generated DJ announcement metadata, so artist requests such as `Speel Pearl Jam` can mention the started number when Spotify returns one.
- Prevent stale Assist music context or stale playback aliases from overriding deterministic local artist parsing, so a fresh request such as `Speel Nirvana` cannot keep starting or announcing a previous artist such as Red Hot Chili Peppers.
- Build temporary DJ announcement `audio_url` values through the shared local Home Assistant URL resolver, so HA versions without the older `network.async_get_url` helper can still send WAV/MP3 URLs to ESP devices.
- Update wake-word protocol documentation, translations, sync prompts and regression coverage.

## 3.1.40

- Resolve the preferred/default Home Assistant Assist pipeline conversation engine for generated DJ announcements when no explicit DJConnect Assist pipeline is selected, so the configured `dj_response_prompt` is sent to the real conversation agent instead of falling through to the local "Daar is ..." fallback.
- Fix generic album fallback wording for album-only resolved media such as `Ten` by `Pearl Jam`.
- Add regression coverage for generated album DJ announcements and default Assist pipeline conversation-agent resolution.

## 3.1.39

- Make `pcvantol/djconnect/PRODUCT_ROADMAP.md` the only canonical product roadmap source and document that sibling repos must not keep local roadmap copies.
- Update the shared release hygiene instructions so roadmap changes from any DJConnect repo are recorded centrally in this HA integration repo.

## 3.1.38

- Update all public product website references from `https://djconnect.pages.dev` to `https://djconnect.dev`.
- Make `pcvantol/djconnect/SYNC_PROMPTS.md` the only canonical cross-repo sync prompt source and document that sibling repos must not keep local copies.

## 3.1.37

- Add the missing options-flow `local_url` label translation so the read-only Client adres field no longer appears as a raw key.
- Add translation coverage for the read-only Client adres label in options.
- Page Spotify playlist browsing internally with Spotify-safe `limit=50` requests while still returning up to 100 playlists to app-like clients, preventing Spotify HTTP 400 `Invalid limit` errors.
- Prefer deterministic local music-intent parsing over generic/stale Assist search results, so requests such as `Speel Nirvana` cannot be overwritten by an old artist context while generated DJ announcements still keep useful Assist text.
- Cache backend playback state returned through the Home Assistant playback proxy so play/pause state, album art, volume and selected output update from the Spotify backend response.
- Add regression coverage for playlist pagination, local intent guardrails and playback proxy state caching.

## 3.1.36

- Harden `command:"playlists"` responses so every success/failure path returns a non-empty JSON body with `playlists`, `items`, `data.playlists`, `data.items`, `result.playlists`, `result.items` and `count`, caps ESP playlist browsing at 20 items, adds playlist item aliases used by iOS/macOS/Pi/ESP clients, and logs playlist request/response metadata without secrets.
- Add HA version metadata and redacted debug logging to `command:"status"` and `/api/djconnect/status` responses so app clients can distinguish no active playback from backend/auth unavailability.
- Hide the “Retry pairing with current code” options-flow action unless the device pairing state is pending/stale, keeping the normal options UI focused on save, Spotify reauthorize and full re-pair.
- Add regression coverage for playlist response aliases, ESP playlist limit capping, nested playlist result normalization and conditional pairing retry visibility.

## 3.1.35

- Add Raspberry Pi-specific restart and shutdown button entities that call the Pi local Client API without reintroducing ESP-only reboot/OTA entities for app-like clients.
- Add regression coverage for Raspberry Pi power buttons.

## 3.1.34

- Restore robust playlist responses for DJConnect clients by always returning playlist aliases (`playlists`, `items`, `count`) and preserving request `client_type`/`limit` context even when clients send a `value` object.
- Add regression coverage for app/ESP playlist command response aliases and merged playlist command options.

## 3.1.33

- Let AI DJ announcement generation use Home Assistant's default conversation agent when no explicit Assist pipeline conversation agent is configured, instead of immediately falling back to the local "Daar is ..." response.
- Let the guarded post-STT correction step use Home Assistant's default conversation agent when no explicit Assist pipeline conversation agent is configured.
- Add Dutch DJ announcement prompt guidance so English artist, album and track names are spoken in English inside Dutch DJ announcements.
- Add a push-only `last_corrected_stt` sensor with cached last-value behavior, while keeping corrected STT metadata on the status and last-command sensor attributes.
- Register explicit runtime schemas for DJConnect developer actions so Home Assistant Developer Tools keeps the `command_text` / `dj_response_text` fields visible after service metadata refreshes.
- Prevent false Spotify token repair issues after pairing when Spotify credentials are available from config entry options rather than only from entry data.
- Add regression coverage for default conversation-agent DJ announcements, default conversation-agent STT correction and the new corrected-STT sensor.

## 3.1.32

- Add an opt-in HA Assist fuzzy-correction step after STT and before Spotify intent parsing for physical/developer PTT flows, so common STT mistakes in English artist, track, album and playlist names can be corrected before search.
- Expose the original STT text and corrected text in runtime diagnostics and sensor attributes.
- Add regression coverage for STT correction ordering and prompt-leak/device-lookup guardrails.

## 3.1.31

- Require a Spotify `media_player` entity before starting DJConnect setup and show a clear config-flow error when the Home Assistant Spotify integration is not configured yet.
- Add config-flow and translation coverage for Spotify media player prerequisite detection.
- Let options-flow re-pairing with a new pairing code reuse the stored Client adres when the URL field is left empty.
- Add regression coverage for re-pairing with an empty Client adres.
- Replace technical/English command-failure fallback text with localized, user-friendly DJ request messages and guard against prompt/error text leaking to the client display.
- Add regression coverage for localized command-failure fallback text.
- Return `backend_available:true` for successful ESP `command:"playlists"` responses even when Spotify playback is idle, and fetch up to 100 playlists from Spotify.
- Add HTTP/backend coverage for the ESP playlists command response contract.
- Respect ESP `command:"playlists"` `limit` values, default ESP playlist browsing to 20 items, and always return a non-empty JSON body with `playlists: []` on playlist backend failures.
- Prevent Home Assistant/front-end forced update refreshes from bypassing the firmware release-check throttle, while keeping OTA install-time refresh explicit.
- Add firmware update entity regression coverage for throttled force refreshes and install-time bypass.
- Expand local Spotify intent parsing for prefix-only track/artist/album requests such as `nummer Lithium`, `artiest Nirvana` and `album Nevermind`.
- Add support for artist-plus-track requests such as `Speel artiest Nirvana met nummer Lithium`.

## 3.1.30

- Add `djconnect.test_ptt_text`, a Developer Tools action that starts immediately after STT by accepting recognized natural-language text, then runs intent parsing, Spotify search/playback, DJ announcement generation, TTS audio creation and delivery to the connected DJConnect device/client.

## 3.1.29

- Expand local PTT Spotify intent parsing for explicit artist, track, album, playlist and default-playlist requests in Dutch and English.
- Keep generic spoken music requests artist-first, while explicit words such as `nummer`, `liedje`, `track`, `album`, `playlist` and `afspeellijst` select the corresponding Spotify Search type.
- Add regression coverage for spoken DJ request variants and Spotify backend search type routing for `track`, `album` and `playlist`.

## 3.1.28

- Complete the active Spotify reauthorization Repair flow from the OAuth callback, so Home Assistant can close the external-step popup after Spotify returns successfully instead of leaving an empty “Open website” dialog behind.
- Add regression coverage for carrying the repair flow id through Spotify OAuth pending state and calling Home Assistant's flow completion hook from the callback.
- Suffix the suggested Home Assistant device name with the discovered client type (`ESP32`, `iOS`, `macOS` or `Raspberry Pi`) so multiple DJConnect clients are easier to distinguish during setup.
- Add config-flow coverage for discovered app/Pi client name suffixes.

## 3.1.27

- Hide stale/unreachable mDNS clients from the pairing selector when `/api/device/pairing-info` can no longer be reached, so unplugged Raspberry Pi clients disappear after reopening Add integration.
- Add discovery coverage for stale Bonjour cache entries that still appear in mDNS but fail the pairing-info probe.

## 3.1.26

- Tighten mDNS discovery validation so ESP32 clients are only accepted with current model-specific IDs (`djconnect-lilygo-t-embed-s3-*` or `djconnect-esp32-s3-box-3-*`) and legacy ESP discovery IDs are ignored.
- Add regression coverage for rejecting legacy ESP32 device IDs during mDNS discovery.

## 3.1.25

- Prevent stale Spotify playback snapshots from being used as DJ announcement media after a new voice/playback request when fresh `resolved_media` is missing, so asking for Nirvana cannot generate a DJ response for a previous Red Hot Chili Peppers playback state.
- Add processor regression coverage for DJ response media selection when the latest Spotify command returns an older current-playback snapshot.
- Cap `queue` command responses at 100 real backend items before returning data to DJConnect clients or HA queue sensor attributes.
- Add Spotify backend coverage for the 100-item queue response cap.

## 3.1.24

- Harden Spotify refresh-token handling so a stale in-memory runtime token does not immediately create a Spotify reauthorization Repair when the config entry already contains a newer stored refresh token.
- Add safe debug logging around Spotify access-token cache expiry, refresh attempts, refresh-token source selection and token rotation persistence without logging token values.
- Add regression coverage for retrying a newer entry-stored Spotify refresh token after Spotify rejects an older runtime token.
- Add `TECHNICAL_DESIGN_DECISIONS.md` with reverse-engineered Python/JSON/YAML/Bash/Markdown design patterns, coding conventions and a dependency/license/source inventory.
- Add the technical design decisions document to the release documentation checklist so future releases keep it current.
- Update `release.sh` so releasing a new version only promotes the `Unreleased` changelog block and preserves older per-release changelog sections.

## 3.1.23

- Refresh HACS-facing copy and repository description with the DJConnect proposition: “Muziekbediening met karakter”.
- Add Home Assistant mDNS autodiscovery for `_djconnect._tcp` DJConnect clients during pairing, including iOS, macOS, Raspberry Pi and ESP32 client validation.
- Prefill Client adres, client type, device name and pairing code from discovered mDNS clients and authoritative `/api/device/pairing-info` responses when available.
- Prefer TXT `local_url` for discovered clients when advertised, then fall back to the resolved service address and port.
- Mark discovered Raspberry Pi clients as unverified when `/api/device/pairing-info` cannot be reached, show a translated pairing error, and keep manual Client adres correction available.
- Select a single discovered Raspberry Pi client by default while still requiring user confirmation; keep the selector visible when multiple clients are discovered.
- Use the discovered stable `djconnect-raspberry-pi-XXXXXXXXXXXX` ID for duplicate checks and pairing state instead of creating setup-code entries such as `djconnect-654321`.
- Keep manual Client adres pairing as fallback and ensure mDNS discovery never marks a device as paired by itself.
- Update translations, README and canonical sync prompts for the app-client autodiscovery contract.
- Add unit coverage for iOS/macOS/ESP/Raspberry Pi discovery validation, pairing-info metadata overrides, config-flow discovery prefill/selection, duplicate handling and unverified pairing-info fallback.
- Show the configured Client adres read-only in the options flow, so app-like client pairing can be inspected without accidentally changing the stored URL.
- Update README, handoff, AGENTS and canonical sync prompts to document the client-type split between shared backend/playback entities and ESP32-only hardware/update entities.
- Hide ESP-only hardware sensors (`battery`, `WiFi RSSI`, `screen_state` and `led_state`) for iOS, macOS and Raspberry Pi clients while keeping backend/playback sensors visible.
- Include playlist artwork aliases in `playlists` command responses for iOS/macOS/ESP/web clients.
- Add HA backend support for Apple app `seek_relative` playback commands with millisecond offsets.
- Prepare HA pairing/status validation for future Raspberry Pi clients with `client_type=raspberry_pi` and `djconnect-raspberry-pi-*` IDs.
- Consolidate all DJConnect cross-repo sync prompts into the single canonical `SYNC_PROMPTS.md` file and remove the retired loose prompt files.
- Document the DJConnect website How To Start requirements for HACS installation, Spotify Premium, Home Assistant Assist STT/TTS, local pairing and Spotify OAuth.
- Add the HACS custom-repository deeplink to the README installation section.
- Update handoff, TODO, AGENTS and sync prompts so website setup copy stays aligned with the Home Assistant integration flow.
- Show the public DJConnect website prominently in both the README and HACS `info.md`: `https://djconnect.dev`.
- Remove the repository-local `website/` product site now that the marketing website is maintained outside the Home Assistant integration repo.
- Update README, AGENTS, handoff, issue and todo documentation so release hygiene no longer treats the external website as part of this HACS package.
- Keep HACS/integration brand assets in `custom_components/djconnect/brand/` while dropping the duplicated static website asset tree.
- Refresh app-client validation notes for iOS/macOS Client adres pairing and non-ESP entity behavior.
- Serialize Spotify access-token refreshes so simultaneous iOS/macOS/PTT playback calls cannot race a rotated refresh token into a false `invalid_grant` repair.
- Retry once with the latest stored refresh token when Spotify returns `invalid_grant` after another concurrent call already rotated the token.
- Avoid Spotify's invalid artist-context offset payload by playing selected track URIs directly when queue playback originates from an artist context.
- Make DJ response generation rely on HA Assist output from resolved artist/track metadata plus the configured `dj_response_prompt`; remove hardcoded prompt-style response variants from the local fallback.
- Remove `ha_remote_url` from all device pairing/status payloads; DJConnect devices now receive only `ha_local_url`, while cloud/Nabu Casa URLs remain limited to the Spotify OAuth config/repair flow.
- Require `ha_local_url` for pairing instead of accepting a remote/cloud URL fallback.
- Make the TTS engine default truly use Home Assistant's default provider by storing/sending an empty engine instead of the invalid generic `tts` provider id.
- Prevent stale Spotify resolved-media cache from leaking into the DJ response prompt when a new artist query is being handled.
- Skip HA Assist DJ-response generation when no conversation agent is configured, avoiding Home Assistant device-lookup errors being spoken/displayed as DJ responses.
- Keep local DJ response fallback deliberately neutral and factual, so failed/unsupported generative response is visible instead of being hidden behind template text.
- Add support for reversed spoken artist requests such as `Nirvana wil ik wel horen`.
- Replace specific named test/changelog examples with generic artist prompt wording.
- Persist `last_track`, `last_command` and `last_dj_text` after voice/playback response handling, not only before processing starts, so Home Assistant reloads keep the actual latest values.
- Keep the `Laatste nummer` and `Laatste opdracht` sensors available even when the device/backend is temporarily unreachable; with cached values they stay visible instead of switching to unavailable.
- Add tests for runtime status persistence and last-value sensor availability.
- Add a deterministic artist fallback extractor for spoken STT commands before Spotify artist search.
- Extract artists from natural Dutch/English phrases such as `ik heb wel zin in Nirvana`, `ik wil wel Metallica horen`, `speel maar af Above & Beyond`, `zet heavn aan` and `zet london grammer op`.
- Keep explicit Assist-provided `artist` values authoritative while cleaning only fallback free-text queries.
- Add focused tests for spoken artist extraction variants.
- Make `sensor.djconnect_last_command` show the actual DJ response text that is spoken/displayed on the device, while keeping the original STT/user command available as attributes.
- Persist the latest DJ response text in the existing device-status cache so `Laatste opdracht` survives Home Assistant reloads/restarts instead of returning to unknown.
- Mirror non-empty runtime last command, DJ response and last track values into cached device status so sparse updates cannot erase them.
- Add tests for restored DJ response text and runtime caching of last command/track values.
- Filter unusable HA Assist DJ-response output before sending text to the ESP device, so Home Assistant device-lookup errors, Spotify URI dictionaries and prompt fragments are no longer spoken or displayed as DJ responses.
- Fall back to clean local DJ response text when HA Assist cannot generate a usable response, without pretending to implement prompt-specific DJ styles through hardcoded templates.
- Add tests for malformed Assist DJ-response output and radio-prompt fallback behavior.
- Update HA/ESP sync prompts and handoff documentation for the current `3.0.27` contract, including artist-only Spotify search, free-form `dj_response_prompt`, stable sensor caching and required `client_type`.
- Add `SYNC_PROMPTS.md` to document future `ios` and `macos` DJConnect clients without reintroducing `device_type` or client-side Spotify credentials.
- Keep the editable `dj_response_prompt` out of the Assist command-parser prompt, so text such as "Noem waar mogelijk..." can no longer leak into Spotify artist search queries like `Opdracht Metallica`.
- Broaden Assist device-lookup fallback handling so errors such as "Opdracht Metallica niet vinden" fall back to the original spoken command instead of failing playback.
- Replace the four fixed DJ style choices with one editable `dj_response_prompt` in the config/options flow; old `dj_style` and `dj_profile` compatibility paths are removed.
- Keep `sensor.djconnect_last_track` and `sensor.djconnect_last_command` stable by caching their last non-empty value at entity level, so temporary empty runtime/playback/status updates no longer make them unavailable or unknown.
- Restrict plain Spotify text searches to artists only; PTT/Assist music requests now resolve text to `type=artist` and start the artist context instead of selecting arbitrary track or album results.
- Persist the last known ESP device status in the Home Assistant config entry and restore it on integration reload/startup, so battery, firmware, sound output, screen/LED state and `ha_pairing_status=paired` do not fall back to unknown/pending while waiting for the next ESP status post.
- Expose PTT debugging as entity attributes on `sensor.djconnect_status` and `sensor.djconnect_last_command`, including `last_stt_text`, `last_spotify_search` and `last_resolved_media`.
- Generate the spoken PTT DJ response from resolved Spotify/playback metadata and the selected DJ style, so successful requests mention the actual track, artist, album or playlist instead of a generic “I’ll start it” fallback.
- Store resolved Spotify Search metadata with playback responses so device TTS can describe what actually started playing.
- Resolve plain Assist/voice search text through Spotify Search before starting playback, so commands like `ik wil Pearl Jam starten` are converted to a playable Spotify URI instead of being sent to `/me/player/play` as arbitrary text.
- Retry playback once when Spotify reports no active playback device: DJConnect now refreshes Spotify devices, selects the configured source by visible name or device ID when possible, transfers playback there and retries.
- Show Spotify source override in the normal config/options flow again, because it is needed for reliable voice playback routing.
- Preserve the parsed DJConnect intent when playback fails and include it in command-failed voice responses for easier Assist/Spotify debugging.
- Prevent Nabu Casa/cloud URLs from being sent as `ha_local_url`; pairing now uses Home Assistant's local/network URL, LAN source-IP fallback, or `http://homeassistant.local:8123` for `ha_local_url`.
- Keep the options-flow “re-pair with new pairing code” field empty instead of pre-filling the old stored pairing code.
- Set the Spotify repair OAuth popup title and description directly on the Repairs external-step result, so Home Assistant no longer shows a blank dialog when translation lookup misses the dynamic repair issue id.
- Add explicit Spotify repair-flow popup text for the initial repair action, so the Home Assistant repair dialog no longer opens as a blank external-website step.
- Harden device sensor caching: local ESP command responses, device-info refreshes, empty Spotify playback snapshots and accidental command/voice payloads can no longer replace the cached ESP status with empty/unknown values.
- Keep `ha_pairing_status`, firmware, battery, Wi-Fi RSSI, screen/LED state, sound output, volume and last track stable until a real `/api/djconnect/status` update or explicit user action changes them.
- Guard device sensors against command/voice payloads: `/api/djconnect/command` and voice-only payloads now explicitly avoid device sensor merges, so sparse command/status polls cannot reset battery, firmware, RSSI, pairing, output or screen/LED state to unknown/pending.
- Add an authenticated voice debug endpoint at `/api/djconnect/debug/last_voice.wav`; when DJConnect debug logging is enabled, HA keeps the last raw ESP WAV in memory so you can listen to exactly what STT received.
- Add `button.djconnect_refresh_up_next` to refresh the backend queue/up-next list from Home Assistant.
- Refresh Spotify output devices from the sound-output select so HA shows available outputs without needing a manual `devices` command first.
- Accept output aliases from `available_outputs`, `outputs`, `devices` and nested `items` payloads.
- Return queue `context_uri` / `contextUri` and queue item album-art aliases for ESP/web Up Next support.
- Keep queue context available from Spotify playback metadata and queue/status aliases.
- Improve playback proxy artwork fallback through `album_image_url`, `media_image_url`, `image_url` and `entity_picture`.
- Keep sparse ESP status heartbeats from clearing known sensor/entity values.
- Make Developer Actions UI fields explicit with `command_text` and `dj_response_text` while keeping legacy `text` YAML/scripts working.
- Fall back to a simple Spotify search intent when HA Assist treats the DJConnect parsing prompt as a normal smart-home device command.
- Document current HA button/entities, website HA-control copy, refresh flows and ESP sync contract.
- Extend tests for Up Next refresh, output refresh aliases, queue context, artwork fallback, developer action aliases and Assist fallback behavior.
