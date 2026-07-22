# DJConnect Product Roadmap

**Status:** Canonical Generation 2 product roadmap

## Active roadmap

This is the single active roadmap for DJConnect Product Development. Every
active item below has this program as owner and uses one of the canonical
statuses: Completed, Operational, In Progress, Planned, Backlog, Innovation
Lab or Deferred. `ROADMAP_INDEX.md` owns cross-program navigation.

| Initiative | Status | Dependencies | Delivery order |
| --- | --- | --- | --- |
| Product Definition and Community/Personal proposition | Completed | `docs/product/PRODUCT_DEFINITION.md` | 1 |
| DJConnect v4 Architecture Definition | Completed | Architecture Review; `DJCONNECT_V4_ARCHITECTURE.md` | 2 |
| DJ Session Runtime Contracts | Completed | v4 Architecture Definition; `DJ_SESSION_RUNTIME_CONTRACTS.md` | 3 |
| Persistent Session Architecture | Completed | DJ Session Runtime Contracts; `PERSISTENT_SESSION_ARCHITECTURE.md` | 4 |
| Rolling Session Horizon Architecture | Completed | DJ Session Runtime Contracts; `ROLLING_SESSION_HORIZON_ARCHITECTURE.md` | 5 |
| DJConnect V4 Completion Roadmap | Completed | Persistent Session and Rolling Horizon architectures; `DJCONNECT_V4_COMPLETION_ROADMAP.md` | 6 |
| Persistent Session Foundation | Completed | Persistent Session Architecture; PR #292 | 5 |
| Session Intelligence Runtime Integration | Completed | DJ Session Runtime Contracts, Planner, Knowledge Engine, DJ Moment Engine, Session Flow and Broadcast | 7 |
| Universal Receiver V1 foundation | Completed — Architecture plus Broadcast Connection, Session Flow Timeline, renderer-safe Playback Projection and Now Playing are operational | Session Intelligence Runtime; `docs/technical/UNIVERSAL_RECEIVER_ARCHITECTURE.md` | 8 |
| Automated Session Intelligence E2E Verification | In Progress — primary active Epic; Architecture, Bootstrap and Scenario Driver are complete, Immutable E2E Session Capture is next | Session Intelligence Runtime; operational Universal Receiver foundation; `docs/product/DEVELOPER_EXPERIENCE_ROADMAP.md` | 9 |
| Deterministic Scenario Driver | Completed — fixed `SI-GOLDEN-001` input reaches only the existing Runtime boundary | Developer Session Bootstrap; PR #372 | 10 |
| Developer Session Bootstrap | Completed — bounded machine-invokable lifecycle for `SI-GOLDEN-001` | Approved Automated E2E Verification Architecture; PR #370 | 10 |
| Apple experience delivery | Planned | Stable Renderer Host and developer-verification access contracts | 11 |
| Windows experience delivery | Planned | Stable Renderer Host and developer-verification access contracts | 12 |
| Raspberry Pi experience delivery | Planned | Stable Renderer Host and developer-verification access contracts | 13 |
| Voice experience delivery | Planned | Stable current/historical Moment contracts and Assist capability validation | 14 |
| Session Simulation and accelerated execution | Planned within the Automated E2E Verification Epic | Bootstrap, scenario, capture and clock architecture | 15 |
| Preferences and Music DNA expansion | Deferred | Existing Profile and Planner influence boundaries | 15 |
| Narrative Sequencing, Lyrics and Discover Evolution | Deferred | Existing Planner, Knowledge and DJ Moment Engine abstractions | 16 |
| Audience Intelligence | Deferred | Explicit bounded Planner-influence policy; remains intentionally deferred | 17 |
| Playback Observation Stage 2 and Continue Stage 2 | Deferred | External Observation Boundary capability conditions | 18 |

The retained material after this section is pre-Generation 2 product and
release memory. It is not an active roadmap, does not establish current
ownership or priority, and must not be used to bypass the table above.

Innovation Lab is the source of potential future product candidates. A
candidate appears in this roadmap only after an explicit GO and promotion
decision; its receiving Product Development record then has a new owner and a
new `Planned` or `Backlog` status.

## Session Intelligence Runtime milestone

The Session Intelligence Runtime Integration Epic is complete. The server now
uses one canonical Runtime lifecycle for every supported Track Started decision:
Planner selection, Knowledge resolution, DJ Moment realization, Session Flow
publication and Broadcast distribution. The legacy Track Started path is only
bounded runtime protection for lifecycle failure.

Future intelligence capabilities extend the existing Planner, Knowledge Engine
and DJ Moment Engine abstractions; they do not create another Runtime pipeline.
The active roadmap now moves from runtime-architecture construction to
experience expansion and verification. Universal Receiver V1 has an operational
foundation; **Automated Session Intelligence E2E Verification** is now the
primary active Epic. Its Architecture and the first bounded Developer Session
Bootstrap and Deterministic Scenario Driver are complete; Immutable E2E Session
Capture is next.
Audience Intelligence remains deferred and is not an active priority.

Canonical product roadmap for all DJConnect repositories. This file lives only
in the Home Assistant integration repo `pcvantol/djconnect` and is the leading
product roadmap for:

- `pcvantol/djconnect`
- `pcvantol/djconnect-app`
- `pcvantol/djconnect-esp32`
- `pcvantol/djconnect-windows`
- `pcvantol/djconnect-website`
- `pcvantol/djconnect-pi`
- `pcvantol/djconnect-api`

This roadmap is broader than `TODO.md`: not every idea here is committed scope.
Use it to shape releases, validate demand and decide what belongs in the free
local/Home Assistant product versus optional premium features.

Product Strategy lives in `docs/product/PRODUCT_STRATEGY.md`. The Generation 2
table above is the active Product Development roadmap; the retained sections
below are pre-Generation 2 product and release memory only. Innovation Labs
remain the canonical home for unvalidated product ideas.

## Product Proposition

DJConnect. Muziekbediening met karakter.

Core promise:

- Fast physical music control without opening a phone.
- Natural voice-driven music requests through Home Assistant Assist.
- A calm now-playing experience for shared living spaces.
- Local-first control, with Home Assistant owning backend credentials.
- One shared backend contract across ESP32 hardware, Apple clients, Raspberry
  Pi/Linux clients, Windows client and the website/docs experience.

## Release Cycle Rule

Every release must review this roadmap.

- Update `pcvantol/djconnect/PRODUCT_ROADMAP.md` even when the release or
  product change originates in another DJConnect repo.
- Do not keep repo-local `PRODUCT_ROADMAP.md` copies in sibling repos. If a
  sibling repo contains one, remove it and reference the canonical HA repo file
  instead.
- Move implemented items from unchecked to checked in the relevant category.
- Add the implementing major.minor version in parentheses, for example
  `[x] Queue supports up to 100 items (3.1)`.
- If an item ships only for one client, mark the client explicitly, for example
  `[x] ESP32 screenshot endpoint (3.1, ESP32)`.
- Do not remove shipped ideas immediately; keep checked items as product memory
  until a later roadmap cleanup.
- Update README, changelog, handoff, fresh-chat bootstrap prompt, tests and
  design decisions when a roadmap item changes product behavior or public
  contract. Cross-repo contract changes belong only in
  `pcvantol/djconnect/SYNC_PROMPTS.md`.

## Production Release Must-Haves

### General Product Development

- [x] Stable `3.2.x` client/integration compatibility policy, with clear
  major.minor mismatch errors and no automatic token wipe.
- [x] Redacted diagnostics for support without bearer tokens, Spotify tokens,
  WiFi passwords, Home Assistant tokens or temporary media URLs.
- [ ] Clear error states for unpaired, stale token, backend unavailable, version
  mismatch, Home Assistant unreachable, STT failed and TTS failed.
- [ ] Release hygiene across all repos: docs, changelog, handoff, technical
  design decisions, canonical roadmap, tests and cleanup reviewed before every
  release; cross-repo sync prompts are reviewed only in
  `pcvantol/djconnect/SYNC_PROMPTS.md`.
- [ ] Public download/update path for every released client.
- [ ] Manual smoke checklist for website, Home Assistant integration, ESP32,
  Apple clients, Raspberry Pi client and Windows client.

### HACS / Home Assistant Integration

- [ ] Stable HACS installation path with polished icon, description, website
  link, README rendering and restart/repair text.
- [ ] Robust Spotify OAuth refresh-token rotation without normal playback repair
  loops.
- [ ] Clear Spotify Direct Premium/Developer-app requirement, Music Assistant
  alternative and resilient Spotify reauthorization flow.
- [ ] Reliable Assist STT/TTS setup guidance and diagnostics.
- [ ] Stable entity model per client type:
  ESP32 hardware entities, app-like client runtime entities and backend/playback
  entities without irrelevant controls.
- [ ] HA sensors stay stable after status sync and do not fall back to unknown
  after initial valid values.
- [x] Split transport/pairing model where ESP32/Raspberry Pi stay local-device
  clients and iPhone/iPad, Apple Watch, macOS and Windows become inbound-only remote-capable app clients
  after local pairing (3.2, HA/client contract).
- [x] Add an internal DJConnect use-case layer and Spotify Direct backend
  adapter boundary so migrated command, Ask DJ, processor and entity paths no
  longer call Spotify helpers directly (3.2, HA).
- [x] Add a small Music Assistant backend adapter behind the DJConnect use-case
  layer without rebuilding provider registries, universal library search,
  queue/grouping engines or Music Assistant setup flows (3.2, HA).
- [x] Add an explicit Home Assistant options-flow action to switch between
  Spotify Direct and Music Assistant without removing the integration, while
  preserving pairing/history/memory and bumping `music_backend_revision` (3.2,
  HA).
- [x] Harden backend/client contracts with backend summary fields, backend-aware
  playback actions, stale-action rejection and unsupported capability errors
  for client implementation prompts (3.2, HA).
- [x] Add HA/AI tool surfaces as thin wrappers over DJConnect use-cases, never
  as direct Spotify or Music Assistant calls (3.2, HA).
- [ ] mDNS pairing plus manual Client adres fallback for ESP32/Raspberry Pi
  networks where Bonjour is filtered, stale or unavailable.
- [x] Queue/up-next response returns max 100 real backend items, artwork URLs,
  context URI and no artificial duplicate padding (3.2, HA).
- [x] Ask DJ server-side chat history sync supports bounded history,
  cross-device clear, retention metadata and client cache trimming (3.1, HA).
- [x] Ask DJ supports confirmation-style follow-up actions with Ja/Nee buttons
  and server-side pending follow-up execution (3.1, HA).
- [x] Ask DJ supports morning startup suggestions from listening memory and
  sleep phrases that pause playback (3.1, HA).
- [x] Ask DJ recommendations can return Play Now actions with artwork without
  mutating playback until explicit confirmation (3.1, HA).
- [x] Ask DJ hardened fallback handles gibberish and prompt-injection-like
  requests without playback mutation or prompt disclosure (3.1, HA).
- [x] Ask DJ recent-played questions return read-only track, album, artist and
  playlist-context lists with art/icon metadata from Spotify recently played
  data (3.1.77, HA/client contract).
- [x] Keep backend playback state out of separate Home Assistant playback
  entities; clients, Ask DJ and DJConnect commands own playback UX while HA
  remains the credential/backend orchestrator (3.2, HA).
- [x] Add a premium-ready VibeCast backend feed for Apple clients, with macOS
  and iOS sharing the same endpoint, response contract, item kinds, disabled
  reasons, structured text model and polling/cache semantics (3.2, HA/client
  contract).
- [x] Last STT text, resolved Spotify result, DJ announcement and last track are
  visible through focused entities or redacted status/debug attributes, without
  low-value standalone command/STT sensors (3.2, HA).
- [ ] DJ announcement prompt is configurable, multiline and isolated from
  Spotify search/device lookup prompts.
- [x] DJConnect is exposed as a Home Assistant Assist conversation agent for
  Assist satellites such as Voice Preview Edition, with compact relevant
  options (3.1, HA).
- [x] ESP32 wake-word toggle is exposed as a native HA switch and filtered out
  for iOS, macOS, Raspberry Pi and Windows clients (3.1, ESP32/HA).
- [x] DJ announcement generation includes the concrete Spotify track returned
  by the just-executed artist playback command when Spotify provides one (3.1,
  HA).
- [x] End-to-end and contract tests cover pairing, voice/PTT, HA STT provider
  compatibility, Spotify search, queue, refresh-token rotation, mDNS discovery,
  non-ESP entity filtering, backend switching and OTA offers (3.2, HA).

### Website / Docs

- [ ] Canonical domain, SEO metadata, sitemap, redirects and social preview are
  current.
- [ ] Setup page remains the single source for installation guidance.
- [ ] Compatibility matrix for ESP32, iOS, macOS, Raspberry Pi/Linux, Windows
  and Home Assistant versions.
- [ ] Troubleshooting pages for Spotify OAuth, STT failed, TTS failed, mDNS
  discovery, Client adres, OTA and pairing reset.
- [ ] Product screenshots/videos show PTT, queue, DJ announcement, hardware UI
  and Home Assistant entities.
- [ ] Privacy notice accurately describes website and product behavior.
- [ ] Aggregate download/HACS counters remain cookieless.
- [ ] Link checker, translation coverage and Playwright smoke checks run in
  release validation.

### ESP32 Firmware

- [ ] Stable Home Assistant pairing with model-specific device IDs,
  `client_type=esp32`, mDNS discovery, pairing token storage and stale-pairing
  recovery.
- [ ] OTA reliability with board-specific firmware selection, SHA256
  verification, low-memory handling, useful progress/errors and safe reboot.
- [ ] Wake-word and PTT reliability: Okay Nabu false positives/misses, silence
  auto-stop, WAV capture quality, STT failure handling and DJ-announcement
  playback.
- [ ] Playback command reliability from device, web and HA: play/pause,
  previous, next, volume, shuffle, repeat, output transfer, standard playlist
  and queue item playback.
- [ ] Power and battery stability: no low-battery flicker, predictable
  charging/deep-sleep behavior and first input after screen-off only wakes the
  display.
- [ ] Web portal polish: mobile layout, album art popover, queue refresh, games,
  settings, diagnostics and OTA upload in the DJConnect blue/purple style.
- [ ] LilyGO T-Embed S3 builds, manifests, docs and OTA selection remain in
  lockstep.
- [ ] Serial/web logs remain atomic, searchable and useful for support.
- [x] Up Next stores and renders up to 100 queue items from Home Assistant
  before local truncation (3.1, ESP32).
- [x] Local debug screenshot and screen-open endpoints support automated screen
  capture in development firmware (3.1, ESP32).

### Apple Clients: iOS / macOS

- [x] Stable inbound app pairing through Home Assistant with one persistent
  device ID per installation and no client-hosted local API requirement (3.2,
  iPhone/iPad, Apple Watch, macOS and Windows contract).
- [ ] Clear LAN pairing and remote URL guidance.
- [ ] Current playback, queue, DJ announcement and status views match the shared
  Home Assistant contract.
- [ ] App-side diagnostics copy/export with redaction and issue-template links.
- [ ] Demo mode remains local and does not create Home Assistant devices.
- [ ] App Store/TestFlight readiness checklist for permissions, privacy copy,
  onboarding and failure states.

### Raspberry Pi / Linux Client

- [ ] Stable pairing with persistent `djconnect-raspberry-pi-XXXXXXXXXXXX`
  device ID.
- [ ] mDNS advertisement and pairing-info endpoint for HA discovery.
- [ ] Kiosk/full-screen now-playing wall display with album art, queue and DJ
  announcement.
- [ ] Touch/mouse/keyboard input model for playback, queue and settings.
- [ ] Capability reporting so HA does not require unsupported local audio,
  voice or DJ-response endpoints.
- [ ] Safe startup service, update flow and diagnostics for unattended displays.

## Killer Features

### General

- [ ] Natural music request to real playback: artist, track, album, playlist,
  mood and intent start on the right output.
- [ ] Personal DJ announcements based on resolved music metadata and the user's
  custom DJ prompt.
- [ ] One Home Assistant hub, many clients: ESP32, iOS, macOS, Raspberry Pi,
  Windows and website/docs share one pairing and protocol model.
- [ ] Privacy-first local control: no DJConnect account required for core use.
- [ ] Personal music memory for preferred artists, disliked results, common
  playlists and announcement style.

### HACS / Home Assistant

- [ ] Setup health check screen: Spotify Premium, OAuth, STT, TTS, playback
  device, mDNS and client reachability in one place.
- [ ] Built-in test wizard: STT test, TTS test, Spotify play test, DJ
  announcement test and pairing callback test.
- [ ] Routine hooks for Home Assistant automations when music is requested,
  playback starts, output changes or DJ announcement is generated.

### Website / Docs

- [ ] Guided "How to start" wizard with exact HACS repo, Spotify Premium
  requirement, HA Assist setup and client pairing steps.
- [ ] Release-aware update dashboard showing latest integration/client/firmware
  versions and compatibility.
- [ ] Public product demo with screenshots and short videos per client.

### ESP32 Firmware

- [ ] Always-listening "oke nabu" with local wake-word detection, LED/listening
  feedback and no cloud wake-word dependency.
- [ ] Room-aware hardware remote: one-touch output transfer to known rooms with
  remembered preferred output.
- [ ] Standard playlist button starts configured playlist, enables shuffle and
  disables repeat.
- [ ] Local visual personality: animated splash, LED ring states, game LED
  feedback, DJ-announcement ring and battery/charging states.
- [ ] Smart queue view with album art, per-item play, refresh and no fake
  duplicated current tracks.

### Apple Clients

- [ ] iOS widgets for quick playback, voice request and current track.
- [ ] macOS menu bar mini remote.
- [ ] Continuity-friendly handoff between Mac/iPhone/iPad and room devices.
- [ ] Voice/debug replay UI for the last WAV/STT/TTS response where HA exposes
  safe debug media.
- [x] Ask DJ chat consumes server-side history, clear revisions, retention
  metadata, Play Now actions and confirmation actions from the HA backend
  contract (3.1, iOS/macOS/watchOS/Raspberry Pi/Windows). ESP32 intentionally stays
  outside Ask DJ chat/history.

### Raspberry Pi / Linux

- [ ] Shared now-playing wall: cover art, current track, next item, clock and DJ
  text for living-room display.
- [ ] Party display mode with guest QR code, queue and host moderation status.
- [ ] HyperPixel/kiosk themes optimized for wall-mounted displays.

## New Feature Ideas

### General Product Development

- [ ] Configurable standard playlist from HA, web portal, Apple client and
  device menu.
- [ ] DJ modes: concise, enthusiastic, radio host, kid-friendly, Dutch/English
  mixed or no-spoken-announcement.
- [ ] Party mode with locked simple controls, high brightness, persistent queue
  and limited settings access.
- [ ] Quiet hours to dim screens, lower cue volume and suppress non-critical
  sounds.
- [ ] Accessibility mode with bigger text, reduced animation and high contrast.
- [ ] Listening history with replay or add-to-playlist actions after an
  explicit user confirmation.
- [ ] Multi-room scene buttons for cooking, dinner, party, focus and sleep.
- [ ] Typed music search in clients: search by album, artist or track name from
  ESP/web, Apple, Raspberry Pi and Windows clients, then let Home Assistant resolve and
  start the selected result through the shared backend playback contract.

### HACS / Home Assistant

- [x] Expanded Dutch/English local fallback parser for explicit artist, track,
  album, playlist and default-playlist commands (3.1, HA).
- [x] Guarded post-STT fuzzy correction for likely English artist, track,
  album and playlist recognition mistakes before Spotify intent parsing
  (3.1, HA).
- [ ] Parsed intent debug attributes: media type, query, artist, title,
  playlist, market and Spotify result.
- [ ] Correction/follow-up commands: "niet deze", "de live versie", "meer zoals
  dit", "speel het album hiervan".
- [ ] Search result disambiguation when Spotify returns weak matches.
- [ ] Artist radio fallback when direct artist start is unavailable.
- [ ] Playlist name search across user playlists first, then public playlists.
- [ ] Repair issues for missing STT provider, missing TTS provider, missing
  Spotify Premium/device and invalid Client adres.
- [ ] Optional persistent debug history with last N requests, redacted by
  default.
- [ ] More granular sensors for backend health, client health and Spotify auth
  state.
- [ ] HA automation blueprint pack for low battery, startup, pairing issues, DJ
  response errors, OTA notifications, parties and quiet hours.

### Website / Docs

- [ ] Dedicated troubleshooting pages for common support logs.
- [ ] Product architecture page explaining local-first design and where secrets
  live.
- [ ] Download/release page with board-specific firmware and app links.
- [ ] Support intake page that points users to redacted diagnostics.
- [ ] Roadmap page generated from this canonical file or a curated subset.

### ESP32 Firmware

- [ ] Favorite outputs pinned above live output discovery.
- [ ] Queue search/filter in the web portal for long queues.
- [ ] Album art cache controls: size, clear cache and age/count cap.
- [ ] One-click web UI to capture all screens and download a zip/contact sheet.
- [ ] Hardware self-test for display, buttons, encoder, speaker, mic, LED ring,
  WiFi and battery.
- [ ] Guided captive setup wizard for WiFi, HA pairing, language, brightness and
  speaker cue volume.
- [ ] Voice debug tools showing last WAV duration/size, STT text, TTS URL status
  and provider error body.
- [ ] Offline-friendly setup screen with QR/deeplink to HA integration
  instructions.
- [ ] Better battery, charging and OTA safety telemetry.

### Apple Clients

- [ ] Local demo mode metadata with clear "not connected to HA" boundaries.
- [ ] Client-side "can Home Assistant reach me?" indicator.
- [ ] Queue editor: reorder, remove or pin upcoming tracks when backend support
  is available.
- [ ] Rich album art popover and lock-screen/current-track affordances.
- [ ] Share diagnostics into GitHub issue template.
- [ ] Apple Watch request/cancel controls.

### Raspberry Pi / Linux

- [ ] Safe local update service and rollback instructions.
- [ ] Configurable display themes and burn-in protection.
- [ ] Touch-first queue and output switcher.
- [ ] Offline fallback screen with pairing recovery steps.
- [ ] Local logs/diagnostics page for kiosk deployments.

## Premium / Paid Feature Candidates

Premium ideas should add convenience, polish or optional hosted services while
keeping the core local/Home Assistant experience useful without payment.

### General Premium

- [ ] Advanced DJ personalities with curated style packs, multi-language voices,
  seasonal themes and custom prompt presets.
- [ ] Household profiles with per-user music preferences, language, family-safe
  rules and announcement tone.
- [ ] Smart music memory: favorite artists by room/time, request history,
  negative feedback and "more like this" suggestions.
- [ ] Advanced analytics: privacy-preserving request summaries, room usage,
  top artists and client usage.
- [ ] Remote support mode with time-limited, opt-in diagnostics sharing.
- [ ] Priority support, setup review or assisted onboarding.

### HACS / Home Assistant Premium

- [ ] Advanced automation recipe pack for parties, dinner, bedtime, wake-up
  music, quiet hours and scenes.
- [ ] Cloud-assisted diagnostics bundle with redacted setup health report.
- [ ] Hosted release/update dashboard for installed client versions and firmware
  readiness.

### Website Premium

- [ ] Account-backed optional theme/personality downloads.
- [ ] Support dashboard for premium users.
- [ ] Hosted guest request pages, only when privacy model is explicit.

### ESP32 Premium

- [ ] Premium LED/screen themes, animated idle screens and seasonal packs.
- [ ] Hardware bundle provisioning/support flow.
- [ ] Advanced local self-test and support bundle export.

### Apple Client Premium

- [ ] iOS widgets, Apple Watch controls and macOS menu bar extras.
- [ ] Premium queue editing tools and saved queue templates.
- [ ] Cross-device sync for DJ persona/profile settings.

### Raspberry Pi / Linux Premium

- [ ] Premium wall-display themes.
- [ ] Multi-display orchestration for synchronized rooms.
- [ ] Party-mode display with guest voting/moderation.

## Free vs Paid Guardrails

- Core pairing, local control, Home Assistant integration, basic PTT, basic DJ
  announcement and essential entities remain free.
- Paid features must not require DJConnect to collect Spotify credentials.
- Paid features should be optional enhancements, not mandatory infrastructure
  for local control.
- ESP32, Apple and Raspberry Pi/Linux clients remain usable with the free Home
  Assistant integration.
- Any hosted premium service needs a clear privacy model before implementation.
- Premium must not weaken the local-first default experience.

## Parking Lot

- [ ] Support future playback providers beyond Spotify through the generic HA
  playback command proxy.
- [ ] Local non-cloud LLM/DJ announcement generation if HA exposes a reliable
  local model path.
- [ ] Signed firmware manifests.
- [ ] Hardware bundle SKU planning.
- [ ] White-label hardware provisioning process.
- [ ] App Store/TestFlight production-readiness scope.
