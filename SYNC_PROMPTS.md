# DJConnect Sync Prompts

This is the only canonical cross-repo sync prompt bundle for DJConnect. The
Home Assistant integration repo `pcvantol/djconnect` is the leading source for
this file. Do not copy this file into sibling repos and do not reintroduce
repo-local sync prompt files.

Canonical repo locations:

- Home Assistant integration: `pcvantol/djconnect`
- Central API backend: `pcvantol/djconnect-api`
- Apple app: `pcvantol/djconnect-app`
- Windows desktop app: `pcvantol/djconnect-windows`
- ESP firmware: `pcvantol/djconnect-esp32`
- Website/docs: `pcvantol/djconnect-website`
- Raspberry Pi client: `pcvantol/djconnect-pi`

## How To Update This File

From any DJConnect repo, update this file in the Home Assistant integration repo
only:

```sh
cd ../djconnect
$EDITOR SYNC_PROMPTS.md
```

If the Home Assistant integration repo is not available locally, open a follow-up
task against `pcvantol/djconnect` and do not create a local replacement. After
updating, run `git diff --check` in `pcvantol/djconnect` and commit the change
there. Sibling repos should reference `pcvantol/djconnect/SYNC_PROMPTS.md`
instead of storing their own copy.

## Current Protocol Line

The current shared protocol/release line is `3.2.x`; this bundle was last
aligned after Home Assistant integration release `v3.2.50`. DJConnect clients on the
`3.2.x` line are compatible with Home Assistant integration versions `>=3.2.0`
and `<3.3.0`.

3.2 transport contract:

- ESP32 and Raspberry Pi stay LAN-only local devices with mDNS, optional Client
  adres fallback and `/api/device/*`.
- iOS, macOS and Windows are inbound-only app clients. They pair locally by
  posting to `/api/djconnect/v1/pair`, expose no HA-callable `/api/device/*`, and
  may use `ha_remote_url` after local pairing when Home Assistant has an HTTPS
  external/Nabu Casa URL.
- watchOS uses the iPhone/iPad proxy and has no separate HA-direct local/remote
  pairing contract.
- Remote pairing is not allowed. Token bootstrap always happens locally.
- ESP32 and Raspberry Pi must never receive `ha_remote_url`.
- Local app clients may optionally use Home Assistant's native
  `/api/websocket` as a low-latency fast path after normal local pairing and HA
  websocket auth. Do not assume the DJConnect device token can authenticate the
  HA websocket itself; it is included in DJConnect payloads after HA websocket
  login. Capability-detect with `djconnect/capabilities`, then use
  `djconnect/command`, `djconnect/ask_dj/message` and
  `djconnect/track_insight` only when advertised. Payloads reuse the matching
  HTTP contracts and still include the DJConnect `device_token`, `device_id`
  and canonical `client_type`; HTTP remains canonical fallback for remote
  access, pairing, history clear/sync, voice uploads, image/TTS URLs and every
  websocket timeout/error/disconnect.

3.2 backend abstraction contract:

- Home Assistant HTTP routes, app clients, ESP/Raspberry Pi clients, Assist
  agent, HA services and future AI tools should route music actions through the
  DJConnect use-case layer.
- Spotify Direct remains the default backend through a `MusicBackend` adapter.
- Provider-neutral recommendation/profile payloads should use
  `listening_profile`; `spotify_profile` is retained only as a temporary legacy
  alias for older clients.
- Music Assistant support is a small backend adapter over a configured Home
  Assistant `media_player`. It is not a DJConnect-side Music Assistant clone,
  provider registry, universal library index, queue engine or grouping/sync
  engine.
- Backend choice is explicit: `Spotify Direct` or `Music Assistant`, no Auto.
  Spotify Direct keeps DJConnect Spotify PKCE OAuth and repairs. Music
  Assistant uses Music Assistant provider auth and must not ask for a DJConnect
  Spotify Client ID, run DJConnect Spotify OAuth, or create Spotify reauth
  repairs.
- Capability flags are part of the HA/backend contract. Unsupported Ask DJ,
  library, queue, recommendation, favorites or listening-history features must
  degrade through backend-neutral fallback text and existing response shapes.
- AI tools are thin HA-facing wrappers over DJConnect use-cases. They must not
  call Spotify Direct or Music Assistant directly.
- VibeCast uses `GET /api/djconnect/v1/vibecast` as a premium-ready Apple client
  feed over current backend playback context. macOS and iOS must use the same
  endpoint, response contract, item kinds, structured text segment types,
  disabled reasons, polling/cache semantics, entitlement behavior, TTL,
  revision handling and current-track resolution. Differences between macOS and
  iOS are presentation/capability-only. Clients that can render emoji safely
  should advertise `emoji_safe`; the backend may then return inline `emoji`
  rich-text segments.
- Music Discovery recommendations are backend-owned. Spotify recent/top profile
  data is used as server-side seed/context only; clients render backend
  `sections[]` such as `new_for_you` and `accepted_recommendations` and must not
  reconstruct cards from raw recent tracks.

## Client: VibeCast

```text
Sync the DJConnect client with the VibeCast backend contract.

VibeCast is backend-owned and source-of-truth playback comes from Home
Assistant. Clients poll:

GET /api/djconnect/v1/vibecast

Use the paired DJConnect device token plus canonical `device_id` and
`client_type`. Supported Apple client types are `ios`, `macos` and `watchos`.
macOS and iOS must behave the same functionally: same endpoint, same item
kinds, same structured text segment types, same disabled reasons, same
TTL/polling/cache semantics, same premium entitlement handling and same
current-track resolution. Platform differences are presentation-only or based
on reported render capabilities.

Render `items[].text[]` as safe structured text, not HTML or Markdown. Supported
segment types are `text`, `strong`, `emphasis`, `magnify`, `accent`, `emoji`
and `line_break`. Send `X-DJConnect-Render-Capabilities` with supported
features; include `emoji_safe` only when inline emoji segments render cleanly.
When `emoji_safe` is advertised, the backend may return one short `emoji`
segment with 1-3 decorative music/vibe symbols per bubble. Render it inline as
text and ignore unknown segment types safely. If a capability such as `magnify`
or `emoji` is not supported, degrade it gracefully without changing the item
meaning.

If `enabled:false`, hide or degrade VibeCast using `reason` and never show raw
provider, cache, decoding or generation errors.

VibeCast can include artist shout-out artwork when the Home Assistant backend
can resolve it from playback metadata or the selected music catalog. Prefer
`items[]` where `kind:"artist_fact"` and `image_url` is present; fall back to
`context.artist_image_url` if the item image is absent. `thumbnail_url` may be
used only when `image_url` is absent. `image_alt` can be used for
accessibility/VoiceOver. `image_source` is metadata/debug context and should not
be prominent UI copy. All artist artwork URLs are DJConnect image proxy URLs;
clients must load the DJConnect image proxy URL and must not perform their own
Spotify, Wikipedia, MusicBrainz or catalog image lookup. If a later VibeCast
response has no image fields, clear the previous shout-out image rather than
reusing stale artwork.
```

## Client: Music Discovery

```text
Sync the DJConnect client with the Music Discovery backend contract.

Music Discovery is backend-owned and source-of-truth data comes from Home
Assistant Music DNA. Clients use:

GET /api/djconnect/v1/music_discovery
POST /api/djconnect/v1/music_discovery/refresh
POST /api/djconnect/v1/music_discovery/play
POST /api/djconnect/v1/music_discovery/feedback

Use the paired DJConnect device token plus canonical `device_id`,
`client_type`, optional `client_id` and optional `music_dna_key`.

Before using websocket fast paths, call `djconnect/capabilities` and inspect
`features.music_discovery`, `features.music_discovery_feedback` and
`fallbacks`. If a websocket command is missing, use the advertised HTTP path;
if feedback is unavailable on both transports, hide negative-feedback controls
instead of faking a local blocklist. Do not parse HA integration versions to
infer support.

APNs event `music_discovery_ready` means Home Assistant has sent the daily
Ontdek reminder. It contains `open_target:"music_discovery"`,
`refresh_target:"music_discovery"`, `deeplink:"djconnect://music-discovery"` and
body text `Je nieuwe aanbevelingen staan klaar!`. On receipt/open, navigate to
Ontdek and refresh the backend feed through
`POST /api/djconnect/v1/music_discovery/refresh` or the websocket refresh
command. Do not render recommendations from the push payload.

Home Assistant also refreshes Music DNA and Music Discovery server-side about
once per hour when Music DNA is enabled. Spotify recently-played/top profile
data is seed/context only; raw recent tracks must not be displayed as Music
Discovery cards unless the backend explicitly returns them in `sections[]`.
The feed cache is context-aware: compact Music DNA changes such as new recent
track identities, changed top profile data, mood, Play Now choices or negative
feedback may cause the backend to rebuild the feed even before the normal TTL
expires. Clients should refetch after meaningful actions and render the returned
revision; do not infer cache invalidation locally.

Render `sections[].items[]` exactly from the backend. Do not generate
recommendations, reasons or based-on lists locally. Each item has backend
`id`, `kind`, `title`, `subtitle`, playable `uri`, optional `image_url`,
`reason`, `reason_sources`, `confidence`, optional `quality_score` 0-100,
`quality_band` and `quality_factors`. Reasons and quality may mention compact
backend-owned signals such as favorite artist, genre or recent listening
context; clients render them as text/hints and do not infer or rewrite them.

Render one card/row per unique backend-provided `id` or `uri`. Known current
sections include `new_for_you` for generated recommendations, `rediscover` for
known favorites worth replaying, `artist_spotlight` for artist anchors and
`accepted_recommendations` for earlier accepted choices, but clients must render
the backend-provided `sections[]` in order and must not hardcode section ids.
Do not resort by local heuristics; backend quality already influences item order.
The backend already filters known/recent/blocked items, collapses common title
variants such as live/remix/radio edit/remaster, avoids album/title duplicates
and limits artist overload. Do not re-expand or locally relax these filters.

Play buttons must call the Music Discovery play endpoint with
`section_id` and `discovery_item_id`; do not start generic playback directly
from the card. Successful plays are stored as compact Music DNA feedback and
become Ask DJ context for later recommendations.

Negative controls such as `Niet voor mij`, `Minder hiervan` and
`Verberg artiest` must call the Music Discovery feedback endpoint with
`feedback:"not_for_me"`, `"less_like_this"` or `"hide_artist"`. Do not keep a
client-owned long-lived blocklist; the backend records compact negative Music
DNA signals, filters future recommendations and feeds the avoid-signal back
into Ask DJ.

When `enabled:false`, hide or degrade Music Discovery using the stable
`reason` and never fabricate fallback recommendations.
```

## Shared Release Cycle

Every DJConnect release in any repo must follow the shared release hygiene
checklist. Apply the repo-specific commands and skip only steps that are truly
not applicable for that repo.

The central API backend `pcvantol/djconnect-api` is part of the DJConnect
platform. Include it in cross-repo contract reviews whenever APNs push relay,
Apple client wake/sync behavior, Home Assistant relay events, privacy/security
boundaries, API deployment, Cloudflare Workers/D1 schema, or release hygiene
changes.

Before publishing:

- Review `pcvantol/djconnect/PRODUCT_ROADMAP.md`.
- Keep product roadmap changes only in `pcvantol/djconnect/PRODUCT_ROADMAP.md`;
  do not keep repo-local roadmap copies in sibling repos.
- Keep shared example contract files such as `examples/voice_intents.json` and
  `VOICE_INTENT_DATA.md` aligned across repos that expose website/docs or
  voice-intent documentation.
- Check whether any roadmap item was implemented.
- Mark implemented roadmap items as checked.
- Add the implementing major.minor version in parentheses, for example
  `[x] Queue supports up to 100 items (3.1)`.
- If the implementation is client-specific, include the client after the
  version, for example `[x] ESP32 screenshot endpoint (3.1, ESP32)`.
- Do not delete recently implemented checked items during the release; keep
  them as product memory until a later roadmap cleanup.
- Update changelog with a new entry for the release. Do not collapse unrelated
  historical entries into one version.
- Use the release's changelog section as the public GitHub release notes/body
  when the repo publishes GitHub Releases; do not publish generic autogenerated
  release bodies when a version changelog entry is missing.
- Update README, handoff, Codex bootstrap guidance, tests, design
  decisions, Postman collections, third-party notices and repo-specific docs
  when product behavior, APIs, release flow, dependencies or public contracts
  changed.
- Use `pcvantol/djconnect/BOOTSTRAP_CODEX_SESSION.md` as the canonical clean
  Codex/AI-agent session bootstrap for every DJConnect repository.
- If a repo still carries `CODEX_RESTART_PROMPT.md`, keep it updated during the
  release cycle until it is retired or replaced by the canonical bootstrap
  procedure.
- Review and update all supported user-facing translations for changed setup,
  options, repair, entity and service strings in repos that ship localized UI.
  The HA integration supports `en`, `nl`, `de`, `fr` and `es`.
- Update `pcvantol/djconnect/SYNC_PROMPTS.md` when the cross-repo contract or
  release checklist changes, even when the release is made from another repo.
- Do not keep repo-local `SYNC_PROMPTS.md` copies in sibling repos. If a sibling
  repo contains one, remove it and reference the canonical HA repo file instead.
- Update `pcvantol/djconnect/PRODUCT_ROADMAP.md` before finishing release
  hygiene when a roadmap item changed or shipped. `SYNC_PROMPTS.md` and
  `PRODUCT_ROADMAP.md` remain only in `pcvantol/djconnect`.
- Bump the repo version according to that repo's release mechanism.
- Run build cleanup before release/build commands so stale assets do not leak
  into published artifacts.
- For repos with managed third-party build dependencies, update/upgrade
  frameworks, libraries and build tools before compiling release artifacts. If
  dependency versions changed, update third-party notices and dependency
  inventory/design documentation before publishing.
- For firmware/device repos that perform HTTPS downloads, revalidate embedded
  CA/certificate bundles against the current release/download hosts and update
  TLS trust material before publishing.
- Run the relevant automated tests for the repo.
- Run build/package validation for every supported target.
- Deploy to a connected app/device when the repo has a connected local target
  available and the release/change calls for it.
- Run smoke/monkey testing where the repo has an app, website, device or local
  UI surface. For ESP/device clients, keep monkey tests non-destructive:
  render/navigation only, no OTA, factory reset, WiFi changes, playback
  mutations or credential changes.
- Validate logs after smoke/monkey testing and explicitly check for crashes,
  watchdogs, panics, assertions, unhandled exceptions, repeated HTTP failures,
  memory allocation failures and secret leakage.

Publishing and cleanup:

- Publish the release through the repo's standard release script or workflow.
- Verify published artifacts/assets are present and named according to the
  current contract.
- Delete old GitHub releases that should not be retained.
- Delete old Git tags that should not be retained.
- Delete old GitHub Actions workflow runs that should not be retained.
- Keep only the agreed latest stable/beta releases for that repo.
- Re-run or verify cleanup scripts where the repo provides them.
- Confirm the final release state in docs/changelog/handoff and note any
  skipped validation with the reason.

---

## Cross-Repo Quick Prompts

Use these prompts when handing work between the Home Assistant integration,
central API backend, Apple app, Windows desktop app, ESP firmware, Raspberry Pi
client, and website/docs repos.

Canonical repo locations:

- Home Assistant integration: `pcvantol/djconnect`
- Central API backend: `pcvantol/djconnect-api`
- Apple app: `pcvantol/djconnect-app`
- Windows desktop app: `pcvantol/djconnect-windows`
- ESP firmware: `pcvantol/djconnect-esp32`
- Website/docs: `pcvantol/djconnect-website`
- Raspberry Pi client: `pcvantol/djconnect-pi`

## Client: Music DNA

```text
Sync the DJConnect client with the current server-side Music DNA contract.

Music DNA is owned by the Home Assistant integration. Clients must not build,
persist or infer their own favorite genres, favorite artists, energy profile,
mood profile, taste direction or profile summary from local chat/playback
history. Clients send identity, language/locale and realtime mood, then render
the backend profile.

Endpoints:
- POST /api/djconnect/v1/music_dna/profile
- POST /api/djconnect/v1/music_dna/settings
- POST /api/djconnect/v1/music_dna/clear

Requests should include `client_id`, `client_type`, `device_id`,
`device_name`, optional `music_dna_key`, `language`, `locale` and optional
`mood` 0..100.

Rendering rules:
- Respect `enabled`; while disabled, show the opt-in state and do not fake a
  profile.
- Render backend `summary`, `favorite_genres`, `favorite_artists`,
  `recent_tracks`, `energy_profile`, `mood_profile`, `taste_direction`,
  `snapshot_history`, `discovery_feedback`, `privacy_dashboard`, `based_on` and
  `updated_at` when present.
- Accept both strings and objects with fields such as `name`, `title`,
  `artist`, `count`, `score` and `genres`.
- Preserve backend order and show compact top values, usually 3-5 items.
- Hide empty cards or show a clean "not enough signals" state.
- Do not show BPM or toonsoort/key anywhere in Music DNA.
- Clear wipes server profile data but preserves the opt-in setting; after clear,
  enabled profiles learn again from empty data.

Backend builds Music DNA from successful playback/Play Now choices, recent
playback metadata including artist genres where available, Track Insight
energy/genre analysis, realtime mood samples and compact Spotify profile
snapshots when available. Snapshot history is backend-owned, bounded and compact;
clients must not reconstruct trends from local playback or Ask DJ history. The
client only sends realtime context and renders
`privacy_dashboard` as transparency metadata: active sources, rough counts,
retention limits and controls. Never infer or display raw prompts, raw audio,
OAuth tokens or full listening history.
the server-authoritative profile.
```

## Client: Track Insight

```text
Sync the DJConnect client with the current Track Insight contract.

Track Insight is server-side in Home Assistant. Clients call
POST /api/djconnect/v1/track_insight with identity, auth, language/locale,
realtime `mood` and optional track metadata. Render either a direct response
with top-level `track`/`analysis`, or a wrapped response under
`track_insight.track`/`track_insight.analysis`.

Request fields:
- `client_id`, `client_type`, `device_id`, `device_name`
- `language`, `locale`, `mood`, optional `music_dna_key`
- optional track aliases: `title`/`track_name`/`media_title`,
  `artist`/`artist_name`/`media_artist`, `album`/`album_name`/`media_album`,
  `artwork_url`/`image_url`/`album_image_url`, `uri`, optional `genres[]`
- send language and mood headers when the platform supports them:
  `Accept-Language`, `X-DJConnect-Language`, `X-DJConnect-Locale`,
  `X-DJConnect-Mood`

Response fields to render:
- `track`: title, artist, album, artwork_url, duration_ms, progress_ms,
  is_playing, backend, optional `genres[]`
- `analysis`: summary, full_text, genre, subgenre, mood, vibe, texture,
  emotional_tone, energy, danceability, intensity, confidence,
  production_notes, instrumentation, arrangement_notes, listening_cues,
  similar_tracks
- `visual_profile`: palette, motion_style, pulse_speed, wave_amplitude,
  particle_density, glow_strength, spectrum_bias, seed
- `mood_context`, `language`, `cache`

Important:
- Remove BPM, tempo-BPM, toonsoort/key, key-signature UI cards, model fields,
  placeholders, snapshots and tests. These fields are not part of the contract.
- Render genre from `analysis.genre` first, `analysis.subgenre` as detail, and
  fallback/context from `track.genres[]`. Hide the genre card if all are empty.
- Energy/danceability/intensity/confidence are floats 0..1; render percentages
  only visually where useful.
- Client mood may override Track Insight screen colors, but must not rewrite
  analysis text. Backend `mood_context` is the source of truth for the resolved
  zone.
- Do not translate backend analysis text client-side. If language content is
  wrong, fix server language handling.
- Handle `404 no_track_playing`, `429 rate_limited` and transient failures with
  clean empty/retry states. Never reuse old insight data for another track.
```

## Client: Mood Voice Profiles

```text
Sync DJ announcement/generative-text behavior with the current mood-to-voice
profile contract.

When the client sends realtime `mood`, the Home Assistant backend maps it to
the effective DJ voice profile for every DJ announcement, TTS prompt and
generated Ask DJ response. The configured backend voice profile is fallback
only when no valid mood is present.

Mapping:
- 0..24 `chill` -> `late_night`
- 25..59 `groove` -> `classic_radio`
- 60..84 `energy` -> `energy`
- 85..100 `party` -> `clean_host`

Clients should send `mood` on Ask DJ, Track Insight, status and command calls
where available. Clients should not send or persist a separate user-facing DJ
style selector. If a legacy `voice_profile`/`dj_style` is sent together with a
valid mood, the backend mood mapping wins.
```

## Website/Docs

```text
Sync the DJConnect website/docs with the Home Assistant integration, Apple app,
central API backend, ESP firmware and Raspberry Pi client contracts.

Requirements:
- Keep the canonical production domain `https://djconnect.dev`; keep
  `https://www.djconnect.dev` as a permanent redirect to the apex domain.
- Keep `djconnect.pages.dev` only as the Cloudflare Pages fallback URL.
- Keep homepage navigation focused on cross-page and product routes:
  `Features`, `Ask DJ`, `Spraak`, `Blog`, `Installeren`, `Support` and
  `Privacy`, plus the primary `Aan de slag` CTA. Do not add a `Hoe werkt het`
  self-link to the homepage top navigation.
- Treat Ask DJ as a major website/docs product feature for iOS, macOS,
  Apple Watch and Raspberry Pi clients. Explain that it is an AI-DJ chat for natural-language
  music questions, personal recommendations, playback actions and
  cross-device chat continuity, powered by the Home Assistant DJConnect
  integration and server-side Music DNA/history. ESP32 does not get Ask DJ chat
  history/UI; ESP32 remains a physical voice/playback remote.
- Ask DJ website/docs copy must make clear that recommendations do not start
  playback automatically. Clients show `Play Now` for concrete
  recommendations, and playback starts only after the user explicitly taps it.
- Ask DJ website/docs should mention that follow-up questions can show Ja/Nee
  controls, for example after `Goedemorgen` or `Wil je dit nu afspelen?`.
- Ask DJ website/docs should explain that server-side chat history is bounded;
  when the limit is reached, Home Assistant removes oldest messages and sends a
  normal system bubble plus trim metadata so clients can clean their local
  cache.
- Ask DJ website/docs copy must mention compact privacy boundaries: clients do
  not store Music DNA; Home Assistant stores compact context/history per user;
  Spotify OAuth tokens, bearer tokens, raw audio and full prompts are not kept
  in Music DNA/history; raw voice audio is not stored by default.
- Ask DJ voice/PTT documentation should explain that iOS, macOS and Apple Watch
  can use voice/PTT through Home Assistant STT, with optional TTS audio replies
  when available. Raspberry Pi Ask DJ is `readonly_actions`: history/status
  display plus HA-provided structured action buttons, without Pi voice, free
  text, TTS or local audio. Informational text chat is text-only by default;
  replay is shown only when an audio response exists.
- Keep Ask DJ requirements visible and user-facing: Home Assistant, HACS
  DJConnect integration v3.2.18 or newer, an Assist pipeline with STT/TTS for
  voice/audio, and one selected music backend. Spotify Direct requires Spotify
  Premium, the user's own Spotify Developer app with Client ID and preferably
  Nabu Casa or another stable HTTPS external URL for Spotify OAuth. Music
  Assistant requires Music Assistant installed/configured in Home Assistant with
  a usable player and does not require DJConnect Spotify OAuth.
- Canonical spoken music intent example data lives in
  `examples/voice_intents.json` and `VOICE_INTENT_DATA.md` in the Home
  Assistant integration repo. Keep
  the same intent families and example wording aligned in website and client
  documentation: generic artist requests stay artist-first; explicit
  `nummer`/`liedje`/`track`/`song` requests become track searches; explicit
  `album`/`plaat` requests become album searches; explicit
  `playlist`/`afspeellijst` requests become playlist searches; and default
  playlist/favorites phrases map to the configured default playlist. Current
  track questions and direct playback controls must not be documented as
  Spotify search intents.
- Keep the voice commands page at `/voice-commands` aligned with Home Assistant
  intent parsing and local fallback behavior. It must document the canonical
  music intent families from `examples/voice_intents.json` plus the
  website-only expandable playback-control family in Dutch and English. Keep
  the examples in a maintainable data/config object and render only the
  selected NL or EN examples according to the website language toggle.
- Keep homepage voice example chips sourced from the same voice intent data as
  `/voice-commands`, not as a separate hardcoded marketing list. The homepage
  should show a compact varied selection and link to the full Spraak/Voice page.
- Use `VOICE_INTENT_DATA.md` and `examples/voice_intents.json` when the Home
  Assistant integration needs to hand over only updated voice/PTT intent data
  to the website. That handoff must request structured data only and exclude
  website rendering, styling, release, changelog and deploy instructions.
- Keep macOS, iOS, Raspberry Pi/Linux and ESP32 pages minimal: app/device pages
  should label the platform route as `Home` and avoid cross-link clutter in
  their top menus.
- Keep `macos-download` retired. The canonical macOS page is `/macos`.
- Do not render `pcvantol/djconnect-app-releases` as a public Apple download.
  It is an internal unsigned artifact-handoff surface. Render public Apple
  distribution only from an explicitly approved App Store Connect destination;
  until then, show no public Apple download. Render ESP32 firmware downloads
  from `pcvantol/djconnect-firmware` and Raspberry Pi/Linux downloads from
  `pcvantol/djconnect-pi-releases`.
- Show only the latest GitHub release in ESP32 firmware and Raspberry Pi/Linux
  download blocks. Apple download UI uses only an explicitly approved App
  Store Connect link; it never falls back to an internal unsigned artifact.
- Render GitHub release body text as an expandable changelog in client
  latest-version download blocks where public release data is embedded.
- Route website-originated download clicks through `/go/download` so aggregate
  click counters can be combined with GitHub release asset download_count.
- Route the public Raspberry Pi/Linux installer through `/go/linux-install`;
  generate the install command from the latest `djconnect-pi-*` tarball and run
  `sudo ./scripts/install.sh`.
- Keep click/download analytics cookieless and aggregate-only: no cookies, IP
  addresses, user agents, referrers or visitor identifiers.
- Keep operator surfaces protected and out of public navigation/search.
  `operator.html` reads privacy-friendly website stats through `/api/stats`
  and calls operator-only central API actions through server-side Pages
  Functions under `/api/operator/*`.
- Website operator functions may use `DJCONNECT_RELAY_SECRET` only server-side.
  The secret must never appear in browser bundles, static HTML, screenshots,
  logs or fixtures.
- The operator install-token revoke UI must call the website function
  `POST /api/operator/install-token/revoke`, which forwards to central API
  `POST /v1/operator/install-token/revoke`. Browser payloads contain only
  `ha_install_id`, central API `token_id` and a short reason; never raw
  `djci_...` token material.
- Keep SEO metadata, sitemap, canonical URLs and social preview images current
  for the production domain.
- Keep the translated footer privacy notice and the footer website version on
  every public page.
- Keep bonus game names aligned with the current app labels: Paddle Rally,
  Meteor Run, Sky Dash and Maze Chase.
- Keep tests for translation coverage, current navigation, latest-only embeds,
  tracked redirects, retired routes, SEO canonicals, link checking, voice
  command intent-family docs and stale pre-flashed copy.
- Keep release documentation, handoff, tests, changelog, design decisions,
  roadmap and third-party notices current before every website release.
- Keep old website releases, tags and workflow runs cleaned up by default after
  publishing.
```

## Central API Backend

```text
Sync the DJConnect central API backend with the Home Assistant integration,
Apple app, Raspberry Pi client, ESP firmware and website/docs contracts.

Repository:
- `pcvantol/djconnect-api`

Purpose:
- The central API backend is a Cloudflare Worker for APNs push relay.
- It exists so Home Assistant/HACS users and client apps never receive the APNs
  `.p8` provider private key.
- It is expected to be reachable at `https://api.djconnect.dev` after deploy.

Requirements:
- Keep the APNs private key only in Cloudflare secrets/configuration. Never
  commit `.p8` files, relay secrets, APNs device tokens, Home Assistant tokens,
  Spotify tokens, Cloudflare API tokens, production install IDs, raw prompts,
  raw assistant responses or chat history.
- Treat the repo as public/open-source. Use only example fixtures such as
  `example-ha-install`, `example-user-hash`, `example-apns-token` and
  `dev.djconnect.ios`.
- Keep central relay endpoints under `/v1/push/register`,
  `/v1/push/unregister` and `/v1/push/event`. These are HA-to-central-API
  endpoints and are separate from the Home Assistant client-facing
  `/api/djconnect/v1/push/register` and `/api/djconnect/v1/push/unregister`
  endpoints.
- Require per-install `djci_` bearer auth on all `/v1/push/*` calls. Do not
  allow anonymous register/event calls and do not require or distribute a
  global HACS relay secret.
- Provide `POST /v1/install/token` for HACS token bootstrap with a short-lived
  Apple-client pairing/bootstrap proof. The proof is only needed for Apple push
  clients (`ios`, `macos`, `watchos`) and must be bound to `ha_install_id`,
  `client_type` and `device_id`/client install ID. ESP32, Raspberry Pi, Windows
  and Assist-agent-only entries do not need this proof because they do not use
  APNs push.
- Keep `POST /v1/install/rotate` authenticated with the current `djci_` install
  token and replace tokens atomically.
- Provide operator-only endpoints for the website/admin surface:
  `GET /v1/admin/registrations` for a privacy-safe Apple registration overview
  and `POST /v1/operator/install-token/revoke` to disable one compromised
  install token by `ha_install_id` plus central API token ID. These endpoints
  require bootstrap/operator auth using `DJCONNECT_RELAY_SECRET`, reject
  per-install `djci_...` bearer tokens and must never return raw APNs tokens,
  ciphertext, nonces, relay secrets, prompts, responses or chat history.
- Use APNs provider-token auth with ES256 JWT and these config/secrets:
  `APNS_TEAM_ID`, `APNS_KEY_ID`, `APNS_PRIVATE_KEY`, `APNS_TOPIC_IOS`,
  `APNS_TOPIC_MACOS`, `APNS_TOPIC_WATCHOS`, `APNS_ENVIRONMENT` and
  `APNS_TOKEN_ENCRYPTION_KEY`.
- Store APNs tokens encrypted at rest with AES-GCM using
  `APNS_TOKEN_ENCRYPTION_KEY`. Planned key rotation must follow
  `pcvantol/djconnect-api/OPERATOR_RUNBOOK.md`; the current runtime uses one
  active key, so zero-downtime rotation requires temporary dual-key/backfill
  tooling before replacing the secret.
- Keep sandbox endpoint `https://api.sandbox.push.apple.com` and production
  endpoint `https://api.push.apple.com`; select the endpoint from each
  registration environment.
- Mark APNs `BadDeviceToken`, `Unregistered` and HTTP 410 responses as
  disabled/invalid registrations.
- Store only push routing metadata and minimal audit rows in D1. Do not store
  prompts, assistant responses, full chat history, Music DNA, Home Assistant
  tokens or Spotify tokens.
- APNs payloads must remain generic wake/sync hints. For Ask DJ, use concise
  localized copy from central relay message keys for `en`, `nl`, `de`, `fr` and
  `es`; do not embed prompts, responses or history. Include only optional sync
  hints like `event_type`, `history_revision`, `client_message_id`,
  `open_target` and privacy-safe `announcement{delivery,audio_available,
  speaker_delivery}`. Push never transports TTS audio or generated text.
- Push policy is strict: send APNs only for `ask_dj_response` after an explicit
  user Ask DJ request and `ask_dj_confirm` when confirmation actions wait for a
  user choice. Do not push `track_change`, `playback_change`, `queue_change`,
  `volume_change`, `mood_change`, idle suggestions, ambient/system messages,
  status refreshes, polling or Spotify progress updates. Coalesce Ask DJ pushes
  with `thread-id: djconnect.askdj` and apply per-user/device rate limits.
- Apple clients must always sync with their own Home Assistant instance after
  opening, especially `GET /api/djconnect/v1/ask_dj/history`.
- Keep `README.md`, `API_CONTRACT.md`, `SECURITY.md`, `CHANGELOG.md`,
  `HANDOFF.md`, `TODO.md`, `ISSUES.md`, `TECHNICAL_DESIGN_DECISIONS.md`,
  `THIRD_PARTY_NOTICES.md`, `DEVELOPMENT_ENVIRONMENT.md`, `CONTRIBUTING.md`,
  `CODE_OF_CONDUCT.md`, `CHAT_BOOTSTRAP.md`, `AGENTS.md` and `LICENSE`
  production-ready.
- Release validation should run `npx wrangler types`, `npx tsc --noEmit`,
  `npm test`, `npx wrangler d1 migrations apply djconnect_api --local`, the
  public repository secret scan and `./cleanup_old_releases.sh --keep 1` as a
  dry-run. CI should also run the staging-safe E2E smoke test when GitHub
  Actions secret `DJCONNECT_RELAY_SECRET` is configured: bootstrap proof,
  install token, example APNs registration and event flow. Attempt remote D1
  migration and Worker deploy when Cloudflare credentials are valid, and
  document skipped remote steps with the reason.
```

## Home Assistant Integration

```text
Sync the DJConnect Home Assistant integration with the central API backend,
Apple app, ESP client, Raspberry Pi client and Windows client contracts.

Requirements:
- Treat iOS/macOS/watchOS/Raspberry Pi/Windows as app-like clients, not ESP hardware devices.
- Home Assistant may relay privacy-safe push registration and event data to the
  central `pcvantol/djconnect-api` backend, but it must never receive or store
  the APNs provider private key. HA-to-central-API calls must not contain raw
  prompts, raw assistant responses, full chat history, Music DNA, Home
  Assistant tokens or Spotify tokens.
- Home Assistant stores only `api_base_url`, stable `ha_install_id` and a
  per-install `djci_` token for central API calls. It must never contain
  `DJCONNECT_RELAY_SECRET` or any global relay/operator secret. If an Apple
  client supplies `bootstrap_proof` during push registration, HACS may use it
  once to mint the `djci_` token; without a proof HACS keeps Apple push disabled
  instead of attempting blind/public token minting.
- Home Assistant push events must follow the strict Ask DJ attention policy:
  only explicit `ask_dj_response` and confirmation-wait `ask_dj_confirm` are
  pushable. Track/playback/queue/volume/mood changes, idle suggestions,
  ambient/system messages, status refreshes and polling must not generate
  push. Suppress foreground/recent-active targets when known and rate-limit to
  at most one push per 30 seconds and five pushes per ten minutes per HA user
  plus device/client.
- Ask DJ / Music DNA is server-side in the Home Assistant integration. iOS,
  macOS, watchOS, Raspberry Pi and Windows clients must not store Music DNA.
  Music DNA is explicit opt-in; while disabled, HA must not build Music DNA
  knowledge from Ask DJ, listening profiles, recent tracks or preferences.
  Clients use `POST /api/djconnect/v1/music_dna/profile`, `/settings` and
  `/clear` to show structured DNA, enable/disable learning and clear learned DNA
  at any time. Clients may send optional `mood` (0-100), `dj_style` and
  `music_dna_key` hints on status/voice/command payloads, but HA may normalize
  or override the resolved `music_dna_key`. ESP32 is excluded from Ask DJ
  chat/history and keeps its voice/playback command flow.
- Numeric `mood` remains the cross-client wire contract. HA maps it to
  DJConnect mood zones for prompts and recommendations: `chill` for `0`-`24`,
  `groove` for `25`-`59`, `energy` for `60`-`84`, `party` for `85`-`100`.
  Clients may show title-case mode labels locally, but do not need to send
  `mood_zone`; HA derives the canonical lowercase value from `mood`.
- DJ announcement intros may become more personal using compact Music DNA. Clients must not collect or send arbitrary HA states or local personal memory for this.
- DJ announcements use explicit output modes: `client_device`, `both`,
  `ha_speaker` and `text_only`. HA owns the optional
  `dj_announcement_speaker_entity_id`; clients may only change the output mode.
  If no HA speaker is configured, app clients expose `client_device` and
  `text_only` only. Raspberry Pi exposes `text_only` and, when configured,
  `ha_speaker`; it has no local audio output. ESP32 keeps the existing
  `/api/device/dj_response` path. For `ha_speaker`, HA plays TTS server-side and
  sends no client `audio_url`; for `both`, HA plays server-side and returns
  `audio_url`; for `text_only`, HA skips TTS. Spotify Direct must not pause,
  resume or change Spotify volume for announcements.
- Ask DJ text chat for iOS/macOS/watchOS/Raspberry Pi/Windows uses POST /api/djconnect/v1/ask_dj/message.
  Request identity can be top-level or inside `identity`; include
  client_message_id for retry dedupe and client_id as origin metadata. Response
  shape includes success, text/dj_text/message, optional audio_url, images[],
  links[], sources[], playback_actions[], confirmation_actions[], intent,
  action, user_message, assistant_message, history_revision, clear_revision,
  history_limit, history_trimmed_before and history_trimmed_count.
- Ask DJ supports audio_response auto|always|never. Default auto is text-only
  for informational text chat, TTS for playback/hybrid intents and TTS for
  voice/PTT. Use always when the client wants replayable audio for an
  informational answer; use never for text-only.
- Ask DJ history is server-side per Home Assistant user. Sync with GET
  /api/djconnect/v1/ask_dj/history?since_revision=<number>. Response includes
  user_id, history_revision, clear_revision, messages[], server_time,
  history_limit and optional trim metadata. The current server limit is 1000
  messages per HA user. If history_trimmed_before is present, clients should
  remove local Ask DJ messages older than that timestamp.
- When the user removes the DJConnect client/device integration from Home
  Assistant, clients must not remain visually paired just because a token and
  chat cache still exist locally. If HA returns `401`/`403`, `not_configured` or
  stale-pairing for a previously paired device_id/token, clear local paired state
  and local Ask DJ cache for that HA installation. HA clears server-side
  Music DNA and Ask DJ history when the last DJConnect config entry unloads.
- Ask DJ may include assistant system messages such as `origin:
  history_retention` or `origin: spotify_playback_context`. Clients should
  style them as system/ambient assistant bubbles and must not auto-play audio
  for retention messages.
- Ask DJ Push-To-Talk for iOS/macOS/watchOS/Windows uses POST /api/djconnect/v1/voice with
  Content-Type audio/wav. The response includes transcript/recognized_text and
  the same rich Ask DJ fields. Send optional X-DJConnect-Mood,
  X-DJConnect-DJ-Style and X-DJConnect-Music-DNA-Key headers when available.
  Raspberry Pi Ask DJ is `readonly_actions`: it may display history/status and
  render HA-provided structured action buttons, but must not advertise or
  implement voice support unless a future Pi capability explicitly changes this.
- Pairing/status responses expose ask_dj_supported, ask_dj_mode,
  ask_dj_free_input_supported, ask_dj_actions_supported,
  ask_dj_voice_supported, voice_supported, tts_supported,
  local_audio_supported and ask_dj_audio_response_supported.
- Ask DJ clear sync uses POST /api/djconnect/v1/ask_dj/history/clear. Clients
  clear local chat cache immediately when the response has `success:true`,
  `cleared:true`, `ask_dj_clear_required:true` or a newer `clear_revision`.
  Then store the returned sync revisions and reload server history if needed.
  Raspberry Pi must observe clear_revision through history sync, but must not
  expose a local clear action.
- Ask DJ follow-up questions can include `confirmation_actions[]` and
  confirmation-style `playback_actions[]` for Ja/Nee buttons. Send the selected
  answer to POST /api/djconnect/v1/command with command
  `ask_dj_followup_response`. The pending proposal lives server-side and
  expires, so clients should not reconstruct the action locally. Raspberry Pi
  may render HA-provided structured action controls from its Ask DJ screen and
  send only the structured action payload through the normal command contract;
  it must not expose free prompt/message input.
- Ask DJ clients must render `playback_actions[]` by action `kind` and must not
  reuse stale image/media metadata from a previous bubble. If a response has no
  `images[]`, render it as text-only. Output/speaker answers use
  `kind:"output"` with `Activeer` / `Actief` labels. Pause/stop answers may use
  `kind:"control"`, `command:"play"` and `label:"Resume"` for a Resume button.
  Album-discography answers use `kind:"album"` Play Now actions and should be
  rendered as an album list, optionally with a short intro above it.
- Ask DJ recent-played history answers use intent `recently_played_history` and
  return `items[]` / `assistant_message.items[]` for `tracks`, `albums`,
  `artists` or `playlists`. Render them as a compact vertical list with the
  returned art or a local fallback icon at the left, not as one oversized media
  card. Keep the answer read-only: do not auto-start playback and do not invent
  Play Now buttons unless `playback_actions[]` is explicitly present.
- Ask DJ help phrases such as `help`, `hulp`, `wat kun je?` and
  `welke commando's?` return a text-only categorized list of supported prompts.
  Clients should not add media cards or action rows unless the server response
  includes them.
- `Probeer opnieuw` / `retry` is resolved server-side against the previous
  retryable playback request. Clients should send the retry phrase as a normal
  message and keep the visible user bubble; do not rebuild or replace it with
  locally stored command text.
- Ask DJ greetings such as `Goedemorgen` return a personalized morning
  suggestion with confirmation controls. Sleep phrases such as `Ik ga slapen`
  pause playback directly.
- Generic playlist/recommendation offers can return confirmation actions labeled
  `Ja graag` and `Nee dank je`. Render them as buttons, send their
  `ask_dj_followup_response` command unchanged, and keep the card text-only when
  `images: []` is present.
- Ask DJ unknown/safety fallback should show the returned neutral text, for
  example `Sorry, ik begrijp niet wat je bedoelt.`, without retry loops or
  client-side reinterpretation. Unknown/unsupported informational fallbacks are
  text-only; if the response has `images: []`, do not reuse current playback
  album art from an earlier bubble.
- Ask DJ images must be proxied through Home Assistant/DJConnect URLs such as
  /api/djconnect/v1/image_proxy/{token}; source links are separate links[] entries.
- Ask DJ personal recommendations may include playback_actions[] for Play Now
  buttons, but must not start playback until the client sends POST
  /api/djconnect/v1/command with command ask_dj_play_recommendation and a Spotify
  track/album/artist/playlist URI payload. Raspberry Pi may render and send
  these actions only when HA supplies them as structured action payloads; it
  must not invent playback payloads or send free text prompts. Use successful
  commands from interactive clients as positive Music DNA signals. Successful
  Play Now command responses include `dj_text`, `dj_response` and optional
  `audio_url`/`audio_type`; clients should render/play that normal DJ
  announcement immediately. Ambient `DJ feitje` messages are separate system
  messages and must not be treated as the Play Now announcement.
- For Spotify Direct playback, require DJConnect's own Spotify OAuth setup with
  a user-owned Spotify Developer Client ID and PKCE redirect URI. Do not
  require an official Home Assistant Spotify `media_player` entity. For Music
  Assistant playback, require a configured Music Assistant player and do not ask
  for DJConnect Spotify OAuth fields.
- Pair app-like clients through POST /api/djconnect/v1/pair.
- Pair ESP32 and Raspberry Pi local-device clients through their local
  /api/device/pair flow after resolving /api/device/pairing-info and verifying
  the visible pair_code.
- Accept stable device_id, device_name, client_type, firmware, app_version,
  platform and optional capabilities. Raspberry Pi status/pairing payloads may
  advertise capabilities such as touch=true, ask_dj_supported=true,
  ask_dj_mode=readonly_actions, ask_dj_free_input_supported=false,
  ask_dj_actions_supported=true, voice=false, voice_supported=false,
  tts_supported=false, local_audio=false, local_audio_supported=false and
  local_dj_response_endpoint=false.
- Accept the app-generated code as pair_code, pairing_code, or pairing_token.
- Return a DJConnect bearer token on success. The current compatible field is
  device_token; bearer_token and token may also be returned.
- Return ha_local_url during successful app pairing. Do not return
  device_language/language for iOS, macOS, watchOS, Raspberry Pi or Windows clients; those
  clients determine their UI language locally.
- Keep cloud/remote URLs out of Apple app runtime traffic; cloud URLs are only
  needed by Home Assistant-owned Spotify OAuth config flows.
- Spotify OAuth in the Home Assistant integration uses PKCE with a user-owned
  Spotify Developer app. The setup flow must ask for `spotify_client_id`, show
  the exact redirect URI to register in Spotify Developer Dashboard, prefer a
  stable Nabu Casa HTTPS external URL, and not rely on a shared built-in Client
  ID for arbitrary user Home Assistant callback URLs.
- When pairing an app-like client, ask for or use the Client adres shown in
  the client pairing sheet. Do not assume a changing Bonjour hostname remains
  the canonical callback target after pairing.
- Implement full HA-side mDNS autodiscovery for Raspberry Pi clients in the
  pairing config-flow. Browse Bonjour/mDNS service `_djconnect._tcp`, resolve
  each service, validate `client_type=raspberry_pi` against device IDs shaped
  `djconnect-raspberry-pi-XXXXXXXXXXXX`, build the local Client adres from
  service address/port or `local_url`, then always probe
  `GET /api/device/pairing-info` when the URL is reachable. Pairing-info is
  authoritative for `local_url`, `device_id`, `client_type`, `device_name`,
  `pair_code`/`pairing_code`, `pairing_path`, `pair_path`,
  `version/app_version/firmware`, `api`, `model` and `paired`.
- The HA pairing form must prefill Raspberry Pi `Client adres`,
  `client_type=raspberry_pi`, `device_name`, stable `device_id` and visible
  `pair_code` from pairing-info. If exactly one Pi is discovered, select it by
  default but still require user confirmation; if multiple clients are found,
  show a discovered-client selector with useful labels. Discovery is
  convenience only and must never mark a device paired by itself.
- If Pi mDNS TXT is visible but `/api/device/pairing-info` fails, treat it as a
  stale/unreachable discovery record and hide it from the discovered-client
  selector on the next scan. Keep manual Client adres entry available and
  surface a clear pairing error when the user-provided URL cannot be probed
  instead of silently falling back to `djconnect-{pair_code}`. Do not create a
  second HA entry when the discovered Pi `device_id` is already configured;
  guide the user to reset or re-pair that existing client.
- Add/keep HA tests for Raspberry Pi discovery: service TXT acceptance,
  pairing-info override, stale/unreachable probe filtering, config-flow prefill
  for one Pi, selector behavior for multiple clients, duplicate `device_id`
  handling, manual Client adres fallback, and proof that Pi pairing uses the stable discovered
  `djconnect-raspberry-pi-XXXXXXXXXXXX` instead of `djconnect-{pair_code}`.
- Return ha_version or ha_major_minor on status/command responses so Apple
  clients can enforce the matching major.minor contract.
- Apple clients host local /api/device/* endpoints for HA -> client traffic,
  but must not implement ESP-only reboot or OTA routes. Raspberry Pi display
  clients may be outbound-only and must advertise capabilities so HA does not
  require local voice, audio, or dj_response endpoints.
- Persist client_type as ios, macos, watchos, raspberry_pi, windows, or esp32. Do not
  reintroduce device_type.
- Authenticated status/command/voice routes must accept Authorization: Bearer
  plus X-DJConnect-Device-ID.
- Support Apple app current-track seeking through
  `command:"seek_relative"` with integer millisecond offsets. Positive values
  seek forward, negative values seek backward. ESP clients may omit this UI.
- Validate that client_type matches the device_id prefix/model family:
  ios -> djconnect-ios-*, macos -> djconnect-macos-*, watchos -> djconnect-watchos-*, raspberry_pi -> djconnect-raspberry-pi-*, windows -> djconnect-windows-*, esp32 -> ESP
  model-specific ids such as djconnect-lilygo-t-embed-s3-*.
- During app pairing, 401/403 code mismatch responses stop polling, keep the
  visible app code, and do not rotate device_id automatically.
- Create native HA entities for paired app-like clients when status is
  received, including outbound-only Raspberry Pi clients that never expose
  /api/device/* endpoints.
- Create only client/runtime and backend/playback entities for ios, macos,
  watchos, raspberry_pi and windows clients; do not create ESP-only battery, Wi-Fi RSSI, screen
  state, LED state, screen brightness/timeout, speaker volume, device language,
  auto-off, theme/log-level, firmware OTA, or reboot entities for app-like
  clients. Raspberry Pi local settings such as screen blanking, logging and
  update channel are client-owned and should not be modeled as ESP hardware
  entities unless a future Pi-specific HA entity design is explicitly added.
- Support App Store review by allowing Apple clients to enter local Demo Mode
  without HA; Demo Mode must not create HA devices/entities, tokens, or backend
  traffic. Local sample DJ announcement audio/text in Demo Mode is app-local and
  is not proof of HA voice validation.
- Return HTTP 426 version_mismatch when client and HA major.minor protocol
  versions do not match; do not treat this as stale auth.
- Return backend_unavailable as HTTP 200 success:false with
  backend_available:false, not as HTTP 503.
```

## Apple App

```text
Sync the DJConnect Apple app with the Home Assistant integration contract.

Requirements:
- Keep one stable device_id per app installation across normal launches.
- Reset Pairing clears the DJConnect bearer token, rotates the app pairing
  code, and creates a fresh device_id for a new setup.
- Pair by polling POST /api/djconnect/v1/pair with pair_code, pairing_code, and
  pairing_token set to the same app-generated code.
- Store only the returned DJConnect bearer token in Keychain and persist
  ha_local_url, device_id, and client_type.
- Expose local /api/device/info, pairing-info, pair, command, dj_response, and
  forget routes for HA -> app traffic; do not expose ESP-only reboot/OTA.
- Send device_id, client_type, firmware, app_version, device_name, ha_local_url,
  and local_url on status payloads. Send device_id and client_type on command
  payloads. Always use the local Home Assistant URL for app-to-HA traffic.
- Treat backend_unavailable and version_mismatch as recoverable without
  clearing pairing.
- Treat authenticated 401/403/404 as stale/setup recovery while keeping the
  token until explicit user reset.
- Treat 401/403 during unauthenticated pairing polling as code/setup mismatch:
  stop polling, keep the visible app code, and ask the user to re-enter it.
- Show first-run onboarding once per installation with the Home Assistant setup
  link and backend requirements: Spotify Premium/Developer app for Spotify
  Direct, or a configured Music Assistant player for Music Assistant. Do not
  request Spotify credentials in the app.
- While unpaired, block runtime UI with a pairing sheet that shows the
  DJConnect banner, copyable Client adres, copyable app-generated pairing
  code, progress/status, and a green success state with `Let's Start!`.
- Keep the Client adres shown during pairing pinned locally until explicit
  pairing reset.
- Offer Demo Mode from the unpaired pairing sheet for App Store review and UI
  inspection without a Home Assistant backend. Demo Mode must use local sample
  data and must not store a bearer token.
- Fresh installs should default the Home Assistant URL field to
  `http://homeassistant.local:8123`, while paired runtime traffic must use the
  returned `ha_local_url`.
- Use the shared DJConnect blue/purple gradient canvas across iOS, iPadOS, and
  macOS screens.
- Settings may preflight Microphone and Speech Recognition. Do not fake a Local
  Network request button; Apple prompts when LAN/Bonjour access first occurs.
- Keep permission rows compact on iPhone/iPad.
- Local Games are app-only. When focused, game surfaces should consume arrow
  keys and space instead of triggering app navigation.
- Expose current-track seek controls on iOS/macOS/watchOS by sending
  `command:"seek_relative"` with integer millisecond offsets. Positive values
  seek forward, negative values seek backward. This is optional for ESP.
- Detect likely unclean exits and offer only user-mediated crash reporting:
  copy redacted diagnostics or open a prefilled `pcvantol/djconnect` issue.
- Do not log bearer tokens, HA tokens, Spotify secrets, or audio URLs.
```

## Windows Desktop Client

```text
Sync the DJConnect Windows desktop app with the Home Assistant integration
contract.

Repository:
- `pcvantol/djconnect-windows`

Requirements:
- Build as a .NET MAUI desktop app targeting Windows and macOS from one
  codebase. Current targets are `net10.0-windows10.0.19041.0` and
  `net10.0-maccatalyst`; macOS builds may require a matching Xcode/.NET
  MacCatalyst workload pair.
- Use `client_type:"windows"` and stable device IDs shaped like
  `djconnect-windows-XXXXXXXXXXXX`, where the suffix is derived from the first
  12 alphanumeric characters of the stable install ID.
- Treat Windows as an app-like desktop client, not ESP firmware. Do not create
  ESP-only HA entities such as battery, Wi-Fi RSSI, screen/LED state, speaker
  volume, firmware OTA or reboot for Windows clients.
- Home Assistant remains the trusted backend for pairing, DJConnect bearer-token
  lifecycle, Spotify OAuth/backend playback, Ask DJ history, Music DNA,
  Assist/STT/TTS and command execution.
- Store only the DJConnect bearer token in platform credential storage:
  Windows Credential Manager on Windows and macOS Keychain when the same MAUI
  app runs on macOS. Keep local JSON settings non-secret.
- Do not store Spotify credentials, Spotify OAuth tokens, Home Assistant
  long-lived access tokens, Music DNA, Ask DJ server history, raw audio,
  prompts or secret-bearing backend responses as source of truth.
- Pair with Home Assistant using the app-generated pairing code and send it as
  `pairing_token`, `pair_code` and `pairing_code` for compatibility with
  current HA builds. Store the returned `device_token` only in the platform
  credential store.
- Send status to `POST /api/djconnect/v1/status` with `device_id`, `device_name`,
  `client_type`, `firmware` and app version metadata. Treat `401`/`403` as
  stale pairing and HTTP `426` version_mismatch as update-required without
  clearing the token automatically.
- Ask DJ text chat uses `POST /api/djconnect/v1/ask_dj/message`; history sync uses
  `GET /api/djconnect/v1/ask_dj/history?since_revision=<number>`; clear uses
  `POST /api/djconnect/v1/ask_dj/history/clear`.
- Persist only local sync cursors such as `history_revision` and
  `clear_revision`. Clear local display cache when HA clear_revision advances,
  when a clear response includes `cleared:true`, or pairing becomes stale.
  Honor `history_trimmed_before` and
  `history_trimmed_count` without parsing visible retention-message text.
- Render Ask DJ `playback_actions[]` and `confirmation_actions[]` from HA.
  Confirmation actions use `command:"ask_dj_followup_response"`;
  recommendation Play Now actions use `command:"ask_dj_play_recommendation"`
  unless HA provides a more specific command. Do not reconstruct pending
  follow-up state locally.
- Render `recently_played_history` responses as compact `items[]` lists. Do
  not invent Play Now buttons or reuse stale artwork unless HA explicitly
  returns `playback_actions[]` or current response images.
- Playback buttons send generic commands to `POST /api/djconnect/v1/command`,
  including play, pause, next, previous and future backend commands. Spotify
  OAuth and backend playback remain HA-owned.
- Keep the Spotify trademark/non-affiliation notice visible in docs/About UI:
  `Spotify is a trademark of Spotify AB. DJConnect is not affiliated with,
  endorsed by, or sponsored by Spotify AB.`
- Keep `README.md`, `CHANGELOG.md`, `CHAT_BOOTSTRAP.md`, `docs/ARCHITECTURE.md`,
  `docs/API_CONTRACT.md`, `docs/DEVELOPMENT.md`, `docs/RELEASE.md`,
  `docs/HANDOFF.md`, `docs/TODO.md`, `docs/ISSUES.md`,
  `docs/TECHNICAL_DESIGN_DECISIONS.md`, `THIRD_PARTY_NOTICES.md`, `PRIVACY.md`
  and `SECURITY.md` current.
- Run `./run_tests.sh` after protocol/model changes. CI should run protocol
  tests plus Windows and Mac Catalyst build jobs. If Mac Catalyst is blocked by
  Xcode/.NET workload mismatch, document the exact Xcode and pack versions.
- Release helpers should keep old GitHub releases, tags and workflow runs
  cleaned up through `clear_old_releases.sh`; workflow-run cleanup requires
  GitHub Actions `actions: write` permission.
- Never log or commit bearer tokens, Home Assistant tokens, Spotify secrets,
  Keychain/Credential Manager values or raw secret-bearing payloads.
```

## Raspberry Pi Client

```text
Sync the DJConnect Raspberry Pi client with the Home Assistant integration contract.

Requirements:
- Keep one stable device_id per Pi installation across normal launches.
- Use client_type raspberry_pi and device IDs shaped like
  djconnect-raspberry-pi-XXXXXXXXXXXX.
- Treat the Pi as an app-like display remote with a local-device pairing API,
  not ESP firmware.
- Support the local Client API URL flow used by HA for local-device clients.
  The Pi exposes GET /api/device/info, GET /api/device/pairing-info,
  POST /api/device/pair, POST /api/device/command and POST /api/device/forget.
- Advertise `_djconnect._tcp` mDNS on the local Client API port with TXT records
  including name/device_name, device_id, client_type=raspberry_pi,
  version/firmware/app_version, paired, api=/api/device, local_url,
  pair_code/pairing_code, pairing_path, pair_path and model=raspberry_pi.
- Validate the visible pair_code during POST /api/device/pair before storing
  the per-device token and ha_local_url.
- Store only the returned DJConnect bearer token plus ha_local_url.
- Send status to POST /api/djconnect/v1/status with device_id, device_name,
  client_type, version, firmware, ha_pairing_status and display-remote
  capabilities.
- Send playback commands to POST /api/djconnect/v1/command. Supported first
  version commands are status, play, pause, next, previous, set_volume,
  set_shuffle and set_repeat.
- Implement Ask DJ as a read-only feed with structured touch actions. Use
  GET /api/djconnect/v1/ask_dj/history with history_revision/clear_revision to
  render server-side history, clear/trim metadata, assistant/system/status/user
  bubbles, images, links/sources and HA-provided action buttons. Raspberry Pi
  must not expose local message input, voice input, idle suggestions, history
  clear or free prompt sending from the Ask DJ screen. Action taps may only send
  the structured HA-provided action payload through POST /api/djconnect/v1/command.
- Do not implement PTT, microphone capture, POST /api/djconnect/v1/voice, Ask DJ
  message sending or local DJ response audio playback for Raspberry Pi.
  Raspberry Pi must not expose a Pi-local `/api/device/dj_response` endpoint.
- Do not expose ESP-only reboot, OTA, battery, Wi-Fi RSSI, screen brightness,
  screen timeout, speaker volume, LED, log-level or firmware entities.
- Keep the updater and OS maintenance daemon separate from the touch UI and
  keep the touch UI runnable without root privileges.
- Keep general Raspberry Pi OS bootstrap separate from the app release tarball.
  Repo-only bootstrap targets Raspberry Pi OS Lite 64-bit and may configure
  timezone, SSH, apt full-upgrade, minimal X11/Qt runtime dependencies,
  HyperPixel and optional Raspberry Pi Connect. It must not install or manage
  Glances.
- Public Raspberry Pi release tarballs are distribution artifacts, not source
  checkouts. They include `docs/`, `systemd/`, `scripts/install.sh` and a
  bundled wheel under `wheels/`, but not the loose `src/` app source tree or
  repo-only bootstrap helper.
- The public `scripts/install.sh` installer must be re-runnable and resumable:
  it verifies SHA256 release assets, requires Raspberry Pi OS Lite 64-bit,
  checks root, arm64/aarch64, Python >=3.11, writable install paths, GitHub
  release reachability, at least 3GB free disk space, at least 1GB active swap,
  and logs memory/swap/disk/inode plus thermal/throttling state around major
  steps. It installs from the bundled wheel, removes incomplete `.venv`
  directories before retrying dependencies, and keeps pip cache/temp files
  under `/var/cache/djconnect-pip`.
- Use unattended GitHub release updates only after verifying release assets with
  SHA256 at minimum; prefer signed manifests when available.
- Treat backend_unavailable and version_mismatch as recoverable without
  clearing pairing.
- Never log bearer tokens, HA tokens, Spotify secrets, Wi-Fi passwords or
  temporary audio URLs.
```

## DJ Announcement Output Sync

```text
Sync DJ announcement output behavior with the Home Assistant integration.

Home Assistant is the contract source for DJ announcement output modes:
- `client_device`: app/client receives replayable TTS audio.
- `both`: HA plays TTS server-side on the configured HA speaker and the client
  also receives replayable `audio_url`.
- `ha_speaker`: HA plays TTS server-side on the configured HA speaker; the
  client receives text/metadata and no client-playback `audio_url`.
- `text_only`: HA skips TTS entirely and returns text/metadata only.

HA owns the optional `dj_announcement_speaker_entity_id` selected in the
DJConnect config/options flow. Clients must not set or overwrite this HA entity.
Clients may only choose and send `dj_announcement_output`.

Client behavior:
- iOS, macOS, watchOS and Windows expose `client_device` and `text_only`
  always. Expose `both` and `ha_speaker` only when HA capabilities report an
  announcement speaker is configured. If a speaker was configured during HA
  setup, the HA default for app clients is `both`.
- Raspberry Pi has no local announcement audio output. Expose only `text_only`
  and, when HA reports a configured speaker, `ha_speaker`. Never try to play
  local TTS/audio from Pi.
- ESP32 does not use app announcement modes. Keep the existing
  `/api/device/dj_response` path with `text` plus optional `audio_url`.

Response handling:
- Prefer nested `announcement.audio_url` over legacy/top-level `audio_url`.
- If `announcement.delivery` is `ha_speaker` or `text_only`, do not play local
  client audio.
- If `announcement.audio_url` is absent, render text-only for local playback.
- Preserve/handle `announcement.target` and `announcement.warnings` as optional
  metadata; do not parse user-facing text to infer delivery state.
- Websocket Ask DJ responses use the same response shape. Audio remains fetched
  over the temporary HTTP `audio_url`, never as websocket binary payload.

Push behavior:
- Push is wake/sync only and never starts audio directly.
- Apple clients decide autoplay only after fetching canonical message/history
  data and checking local `auto_play_announcements`, app state, and response
  `announcement` metadata.
- Central API/APNs may carry only safe hints:
  `announcement.delivery`, `announcement.audio_available` and
  `announcement.speaker_delivery`. Never include generated text, prompts,
  history, Music DNA, TTS audio or temporary `audio_url` in push payloads.

Product/docs wording:
- Ask DJ is the intelligence/personality.
- A Home Assistant Voice satellite/speaker is an optional physical voice output
  for DJConnect announcements.
- With Spotify Direct, Spotify playback keeps playing normally; DJConnect does
  not pause, resume, duck or change Spotify volume. The DJ voice plays
  separately through the chosen HA speaker.
- Music Assistant may later support richer current-output/ducking behavior, but
  do not claim it is available unless implemented and tested.
```

## ESP Firmware

```text
Sync the DJConnect ESP firmware with the Home Assistant integration contract.

Requirements:
- ESP clients are physical DJConnect devices and must use client_type esp32.
- Use model-specific device_id values for supported ESP firmware builds. The
  current supported production build is LilyGO T-Embed S3:
  `djconnect-lilygo-t-embed-s3-XXXXXXXXXXXX`.
- ESP32-S3-BOX-3 is no longer built, released or published in the ESP firmware
  repo. Do not add BOX-3 PlatformIO targets, CI matrix entries, OTA manifest
  entries or release assets unless board support is explicitly reintroduced.
- Do not accept or generate legacy djconnect-XXXXXXXXXXXX ids.
- Expose local ESP endpoints: GET /api/device/info,
  GET /api/device/pairing-info, POST /api/device/pair,
  POST /api/device/command, POST /api/device/dj_response,
  POST /api/device/forget, plus ESP-only reboot/OTA routes where supported.
- /api/device/pairing-info must return the real device_id, visible pair_code,
  client_type esp32, firmware, device_name, and reachable local_url.
- POST /api/device/pair must require device_token and ha_local_url.
- Persist only the DJConnect device bearer token and ha_local_url. Do not store
  Spotify OAuth/client secrets, Home Assistant long-lived tokens, or playback
  backend credentials.
- Always use ha_local_url for ESP -> HA status, command, and voice traffic.
  Never use Nabu Casa/cloud URLs for device runtime traffic.
- Send device_id, client_type esp32, firmware, ha_pairing_status, local_url,
  language, log_level, wake_word_enabled/wake_word, and current device settings
  in status payloads.
- Support HA local device command `{"command":"wake_word","value":true|false}`
  to persistently enable/disable local wake-word detection. Default is off.
- Send raw WAV voice audio to POST /api/djconnect/v1/voice with Authorization:
  Bearer <device_token> and X-DJConnect-Device-ID.
- Keep Up Next queue capacity aligned with the shared contract: accept and
  render up to 100 real queue items from Home Assistant, then truncate locally.
  Do not pad short queues with repeated current-track entries.
- Treat backend_unavailable and version_mismatch as recoverable without
  clearing pairing.
- Treat authenticated 401/403/404 as stale/setup recovery while keeping
  enough diagnostics to recover.
- Never log bearer tokens, HA tokens, Spotify secrets, WiFi passwords, or
  temporary audio URLs.
```

---

## Detailed Home Assistant Sync Prompt

Use this prompt in the DJConnect Home Assistant integration repo when syncing with the ESP firmware.

```md
# Codex Prompt: Sync DJConnect HA Integration With ESP Firmware 3.2.x

Werk in de bestaande Home Assistant custom integration repo voor DJConnect.

## Doel

Synchroniseer de HA integratie met de ESP firmware contracten rond pairing, status, playback commands, sensoren, voice en multi-device OTA.

## Belangrijkste Contracten

### Pairing URL Contract

Bij `POST /api/device/pair` naar de ESP:

```json
{
  "device_id": "djconnect-lilygo-t-embed-s3-XXXXXXXXXXXX",
  "client_type": "esp32",
  "device_token": "...",
  "ha_local_url": "http://192.168.1.x:8123",
  "device_language": "nl"
}
```

Regels:

- `device_id` is model-specifiek. De huidige ondersteunde firmware build gebruikt `djconnect-lilygo-t-embed-s3-XXXXXXXXXXXX` voor LilyGO.
- ESP32-S3-BOX-3 wordt niet meer gebouwd, gereleased of gepubliceerd; voeg geen BOX-3 OTA manifest entry, release asset of CI/PlatformIO target toe tenzij support expliciet opnieuw wordt geïntroduceerd.
- De ESP mDNS hostname gebruikt exact dezelfde `device_id`, dus bijvoorbeeld `http://djconnect-lilygo-t-embed-s3-XXXXXXXXXXXX.local`.
- ESP mDNS TXT bevat minimaal `name`, `device_id`, `client_type=esp32`,
  `version`, `paired`, `api` en `model`.
- Gebruik het mDNS TXT veld `model` of de status/API `model` om het device model te bepalen; parse niet op de oude `djconnect-lilygo-` prefix.
- `ha_local_url` moet een echte LAN URL zijn.
- `ha_local_url` mag nooit `.ui.nabu.casa` bevatten.
- Stuur geen `ha_remote_url` naar de ESP en gebruik geen cloud/Nabu Casa URL voor ESP runtime verkeer.
- Als geen local URL bekend is, moet pairing pending/falen; zet cloud niet in local.
- Bepaal local via HA network config, internal URL, source IP of fallback `http://<HA LAN IP>:8123`.
- ESP firmware gebruikt uitsluitend `ha_local_url` voor `/api/djconnect/v1/status`, `/api/djconnect/v1/command` en `/api/djconnect/v1/voice`. Cloud URL is alleen relevant voor HA/backend OAuth-configuratie, niet voor ESP verkeer.

### ESP Payload Identity

Alle ESP -> HA JSON payloads naar `/api/djconnect/v1/status` en `/api/djconnect/v1/command` bevatten top-level:

```json
{
  "device_id": "djconnect-lilygo-t-embed-s3-XXXXXXXXXXXX",
  "client_type": "esp32"
}
```

Gebruik nergens meer `device_type`.

### Status Is Authoritative

`POST /api/djconnect/v1/status` is de enige bron voor HA sensoren zoals:

- pairing status
- firmware
- batterij
- WiFi RSSI
- schermstatus/brightness/settings
- LED status
- speaker/cue volume
- taal, theme, log level
- sound output
- OTA/update state

Playback command payloads zijn identity-only en mogen geen gedeeltelijke sensorstatus overschrijven.

### Playback Command Responses

Houd auth en backend availability gescheiden:

- HTTP 401/403/404 = stale pairing/token.
- Backend/player unavailable = HTTP 200 met `success:false`, `backend_available:false`.
- `invalid_client_type` is een firmware/contractfout, geen stale pairing.
- Firmware major.minor moet matchen met integratie major.minor, behalve firmware `0.0.0` dev builds.

### OTA Manifest / Multi Device Firmware

De publieke firmware release gebruikt een multi-device manifest. Gebruik geen
top-level `device`, `asset`, `sha256` of `size` fallback meer. Selecteer altijd
de juiste entry uit `firmwares[]` op basis van het ESP device model.

Manifestvorm:

```json
{
  "version": "3.2.x",
  "version_tag": "v3.2.x",
  "channel": "stable",
  "min_ha_integration": "3.1.0",
  "max_ha_integration": "3.3.0",
  "firmwares": [
    {
      "board": "t_embed_cc1101",
      "device": "lilygo-t-embed-s3",
      "asset": "djconnect-lilygo-t-embed-s3-v3.2.x.bin",
      "url": "https://github.com/pcvantol/djconnect-firmware/releases/download/v3.2.x/djconnect-lilygo-t-embed-s3-v3.2.x.bin",
      "sha256": "...",
      "size": 123
    }
  ]
}
```

Bij `POST /api/device/ota` naar de ESP:

```json
{
  "version": "3.2.x",
  "url": "https://...",
  "sha256": "...",
  "device": "lilygo-t-embed-s3",
  "asset": "djconnect-lilygo-t-embed-s3-v3.2.x.bin"
}
```

Regels:

- LilyGO gebruikt `device:"lilygo-t-embed-s3"` en asset `djconnect-lilygo-t-embed-s3-vX.Y.Z.bin`.
- ESP32-S3-BOX-3 wordt niet meer gebouwd of gepubliceerd; HA mag voor BOX-3 geen firmware-update aanbieden tenzij een toekomstige release expliciet opnieuw een matching `firmwares[]` entry publiceert.
- `min_ha_integration` en `max_ha_integration` volgen de firmware major.minor lijn: firmware `X.Y.Z` publiceert standaard `min_ha_integration:"X.Y.0"` en exclusief `max_ha_integration:"X.(Y+1).0"`.
- HA moet firmware alleen aanbieden/accepteren als de integratieversie `>= min_ha_integration` en `< max_ha_integration` is. Voor firmware `3.2.x` betekent dit dus `>=3.2.0` en `<3.3.0`.
- Dev firmware `0.0.0` blijft de uitzondering voor upgrade-aanbod vanaf lokale builds.
- Als er geen matching `firmwares[]` entry is, rapporteer duidelijk dat er geen firmware voor dit device type beschikbaar is.
- Versievergelijking blijft op manifest `version`/`version_tag`; de assetselectie is device-type specifiek.

### Queue / Up Next

Voor `POST /api/djconnect/v1/command` met `command:"queue"`:

```json
{
  "success": true,
  "context_uri": "spotify:playlist:...",
  "queue": [
    {
      "title": "Black",
      "subtitle": "Pearl Jam",
      "uri": "spotify:track:...",
      "album_image_url": "https://..."
    }
  ]
}
```

Regels:

- App-clients mogen `limit:100` meesturen; HA retourneert maximaal 100 echte
  backend queue-items. ESP firmware in de `3.2.x` lijn accepteert en toont
  maximaal 100 items.
- Retourneer de echte backend queue/context, niet dezelfde current track als padding.
- Als er maar 1 queue-item is, retourneer 1 item.
- `context_uri` blijft nodig voor ESP/web per-item play.
- Album art URLs mogen pass-through zijn; de ESP downloadt queue thumbnails niet, de browser lazy-loadt ze wanneer de web queue zichtbaar is.
- Firmware in de huidige `3.2.x` lijn dedupet defensief op `uri` of `title/subtitle`, maar HA moet nog steeds geen kunstmatige duplicaten genereren.

### Voice

ESP physical PTT uploadt WAV naar `/api/djconnect/v1/voice` met bearer token en `X-DJConnect-Device-ID`.
HA doet Assist/STT/TTS en retourneert DJ tekst plus optionele `audio_url`.

Firmware in de huidige `3.2.x` lijn kan de lokale PTT/DJ-aankondiging flow annuleren met de middelste encoderknop tijdens processing of het DJ-aankondiging scherm. HA hoeft hiervoor geen extra endpoint te implementeren; als een request al loopt mag de ESP de latere response lokaal negeren.

### Wake Word

Okay Nabu wake-word detectie draait lokaal op de ESP. HA hoeft geen wake-word audio te verwerken. Na detectie start de ESP dezelfde fysieke PTT flow en uploadt daarna een WAV naar `/api/djconnect/v1/voice`.

Regels:

- HA moet dezelfde `/api/djconnect/v1/voice` response blijven gebruiken voor PTT en wake-word activatie.
- STT/TTS fouten moeten als duidelijke JSON body terugkomen met `success:false`, `error` en `message`.
- Een optionele `audio_url` mag WAV of MP3 zijn.
- De ESP mag een late voice response negeren als de gebruiker de lokale flow heeft geannuleerd.
- Wake word staat standaard uit en moet expliciet door de gebruiker kunnen worden aangezet.
- ESP status mag `wake_word_enabled` of `wake_word` top-level of onder `settings` sturen; HA behandelt `settings.wake_word_enabled` als voorkeurswaarde, met fallback naar top-level `wake_word_enabled` en daarna `wake_word`.
- HA toont alleen voor `client_type:"esp32"` een native switch `Wake word`.
- HA stuurt bij toggle de canonical local device command payload `{"command":"wake_word","value":true|false}` naar `POST /api/device/command`. ESP mag command aliases `set_wake_word`, `wake_word_enabled` en `set_wake_word_enabled` blijven accepteren, maar HA gebruikt canonical `wake_word`.

## Acceptatiecriteria

- Na pairing logt ESP:

```text
Home Assistant local URL: http://192.168.1.x:8123
```

- Playback commands gebruiken local:

```text
url=http://192.168.1.x:8123/api/djconnect/v1/command
```

- De eerste ESP statuspost naar HA accepteert dezelfde `device_id`, `client_type:"esp32"` en `device_token` als de pairing callback. Een `401` op `/api/djconnect/v1/status` terwijl HA nog ESP `/api/device/*` commands kan sturen wijst op een HA-side token/device-id mismatch in de statusroute, niet op een ESP cloud-route fallback.

- Geen HA sensor valt enkele seconden na update terug naar `unknown`.
- `sensor.djconnect_ha_pairing_status` wordt `paired` zodra ESP `ha_pairing_status:"paired"` meldt.
- `queue` response bevat geen padding met herhaalde current-track entries.
- Geen payload gebruikt `device_type`.
- Geen pairing/token reset bij `invalid_client_type` of backend unavailable.
```

---

## Detailed ESP Firmware Sync Prompt

# Codex Prompt: Synchronize DJConnect ESP Firmware With HA Integration
Werk in de bestaande MIT-licensed ESP firmware repo pcvantol/djconnect-esp32.

Doel
Synchroniseer de ESP firmware met de actuele Home Assistant djconnect integration architectuur voor de `3.2.x` protocol lijn.

De HA integration is de trusted backend voor:

pairing;
bearer-token lifecycle;
backend playback;
Spotify OAuth;
Assist/STT/TTS;
OTA offer handling;
native HA entities.
De ESP blijft eigenaar van:

device runtime;
display/UI;
buttons/rotary;
LED-ring;
local speaker cues;
WiFi/setup;
raw WAV capture/upload;
local playback van HA DJ-aankondiging audio.
Belangrijke beslissingen
Eerdere non-HTTP control routes zijn verwijderd. ESP is geen backend music speaker/player.
ESP bewaart geen playback-backend credentials.
ESP stuurt generieke playback commands naar HA.
HA vertaalt playback commands naar Spotify of toekomstige backends.
ESP speaker is alleen voor local cues en DJ/voice response audio.
Okay Nabu wake-word support draait lokaal via TensorFlow Lite Micro en mag geen netwerk-I/O doen in het audio poll pad.
De middelste encoderknop moet een actieve PTT processing/DJ-aankondiging flow kunnen annuleren.
Oude backend-credential provisioning endpoints mogen niet bestaan of gebruikt worden.
Pairing/status/voice/command auth gebruikt alleen het device bearer token.
Device ID formats voor actuele firmware zijn model-specifiek. De huidige ondersteunde productiebuild is:
- LilyGO T-Embed S3: `djconnect-lilygo-t-embed-s3-XXXXXXXXXXXX`

ESP32-S3-BOX-3 wordt niet meer gebouwd, gereleased of gepubliceerd. Voeg geen BOX-3 PlatformIO target, CI matrix entry, OTA manifest entry of release asset toe tenzij support expliciet opnieuw wordt geïntroduceerd.
Accepteer geen legacy `djconnect-XXXXXXXXXXXX`, `djconnect-lilygo-XXXXXXXXXXXX` of `djconnect-[6-cijferige-code]` device IDs en bouw geen compatibility fallback voor die oude/tijdelijke formaten.
Alle user-facing tekst, filenames, namespaces, logs en provisioning labels gebruiken uitsluitend DJConnect / djconnect.
NVS taal key blijft provision.language.
NVS namespace is djconnect.
Secrets nooit loggen: geen device tokens, HA tokens, Spotify tokens, WiFi wachtwoorden of tijdelijke audio URL tokens.
Assets uit HA repo overnemen
Gebruik de echte DJConnect icon/logo assets uit pcvantol/djconnect; teken het logo niet opnieuw in firmware als er een bitmap/vector-conversie gebruikt kan worden.

Bronbestanden in de HA repo:

assets/djconnect/djconnect-icon.svg
assets/djconnect/djconnect-icon-256.png
assets/djconnect/djconnect-icon-512.png
assets/djconnect/djconnect-icon-1024.png
assets/djconnect/djconnect-logo.svg
assets/djconnect/djconnect-logo-512x256.png
website/assets/djconnect/icon.svg
website/assets/djconnect/icon-192.png
website/assets/djconnect/icon-512.png
website/assets/lilygo-t-embed-djconnect.svg als visuele referentie voor de landscape hero/device mockup.
Acties:

Kopieer of exporteer het echte DJConnect icoon naar het firmware assetformaat dat de LilyGO UI gebruikt.
Houd de paarse/blauwe DJConnect iconstijl intact: vinyl, DJ letters, toonarm/microfoon en gradient arc.
Gebruik het echte icoon op splash/pairing/idle/voice schermen waar nu nog een placeholder of opnieuw getekende benadering staat.
Gebruik firmware-native conversie tooling als assets naar RGB565/LVGL/C-array/binair formaat moeten.
Commit geen gegenereerde build-cache; commit alleen de bronasset en benodigde firmware-runtime asset.
Verwijder oude producticonen en logo’s als ze niet meer gebruikt worden.
Endpoint contract
ESP -> HA
Protected routes:

POST /api/djconnect/v1/status
POST /api/djconnect/v1/command
POST /api/djconnect/v1/voice
POST /api/djconnect/v1/event indien gebruikt
Headers:

Authorization: Bearer <device_token>
X-DJConnect-Device-ID: djconnect-<device-model>-XXXXXXXXXXXX
Content-Type: application/json
Voor PTT:

Authorization: Bearer <device_token>
X-DJConnect-Device-ID: djconnect-<device-model>-XXXXXXXXXXXX
Content-Type: audio/wav
HA -> ESP
Protected local ESP routes:

GET /api/device/info
GET /api/device/pairing-info
POST /api/device/pair
POST /api/device/command
POST /api/device/ota
POST /api/device/reboot
POST /api/device/forget
POST /api/device/dj_response
Header:

Authorization: Bearer <device_token>
Taken
1. Pairing-token synchronisatie
Controleer en fix:

ESP ontvangt device_token via POST /api/device/pair.
ESP ontvangt een echte LAN ha_local_url via POST /api/device/pair.
ESP ontvangt of bewaart geen ha_remote_url voor runtime verkeer.
ESP gebruikt uitsluitend ha_local_url voor status, playback en voice.
ESP accepteert en verwacht geen oud enkelvoudig HA-URL pairingveld meer.
ESP accepteert als persistent device ID alleen de eigen model-specifieke ID.
Een tijdelijke setup/pairing code mag alleen als `pair_code` bestaan; na pairing moet de firmware de echte model-specifieke device ID gebruiken.
ESP slaat exact die token persistent op.
Eerste call naar HA /api/djconnect/v1/command gebruikt exact die token.
Eerste call naar HA /api/djconnect/v1/status gebruikt exact die token.
Eerste call naar HA /api/djconnect/v1/voice gebruikt exact die token.
ESP mag pending pairing niet wissen bij tijdelijke Spotify/backend fouten.
ESP mag pending pairing alleen stale/invalid markeren bij echte HA auth/pairing errors:
401;
403;
404 met duidelijke stale pairing betekenis.
200 JSON met success:false en backend_unavailable betekent niet pairing wissen.
503 backend unavailable mag bij voorkeur ook niet direct NVS pairing wissen; toon pairing degraded/backend unavailable.
Veilige logs:

log device_token=present/missing, nooit de waarde;
log HA response status en error key;
log geen Authorization header.
Verwachte HA -> ESP pair payload:

{
  "pair_code": "123456",
  "device_id": "djconnect-lilygo-t-embed-s3-XXXXXXXXXXXX",
  "client_type": "esp32",
  "device_name": "DJConnect",
  "device_language": "nl",
  "language": "nl",
  "device_token": "<device-token>",
  "ha_local_url": "http://homeassistant.local:8123",
  "assist_pipeline_id": "..."
}
ha_local_url is verplicht en moet een LAN URL zijn. Stuur geen oud enkelvoudig HA-URL veld mee, stuur geen ha_remote_url naar de ESP en zet nooit Nabu Casa/cloud in ha_local_url.

2. Status payload uitbreiden
Zorg dat periodieke HA status payload actuele device settings bevat zodat HA native entities correct updaten.

Stuur minimaal:

{
  "device_id": "djconnect-lilygo-t-embed-s3-XXXXXXXXXXXX",
  "client_type": "esp32",
  "ha_pairing_status": "paired|pending|stale|unpaired",
  "local_url": "http://djconnect-lilygo-t-embed-s3-XXXXXXXXXXXX.local",
  "firmware": "3.2.x",
  "battery_percent": 85,
  "wifi_rssi": -55,
  "uptime": 123456,
  "free_heap": 123456,
  "screen_brightness": 75,
  "brightness": 75,
  "speaker_volume": 50,
  "cue_volume": 50,
  "screen_dim_timeout_ms": 60000,
  "turn_off_after_ms": 300000,
  "wake_word_enabled": false,
  "language": "nl",
  "theme": "dark",
  "log_level": "info",
  "ota_state": "idle",
  "update_state": "idle"
}
Gebruik aliases waar makkelijk, want de HA integration accepteert meerdere namen:

screen_brightness / brightness;
speaker_volume / cue_volume;
screen_dim_timeout_ms;
turn_off_after_ms;
wake_word_enabled / wake_word;
language;
theme;
log_level.
3. Generic playback command API naar HA
ESP stuurt playback commands naar:

POST /api/djconnect/v1/command
Payload voorbeelden:

{"device_id":"djconnect-lilygo-t-embed-s3-XXXXXXXXXXXX","client_type":"esp32","command":"status"}
{"device_id":"djconnect-lilygo-t-embed-s3-XXXXXXXXXXXX","client_type":"esp32","command":"devices"}
{"device_id":"djconnect-lilygo-t-embed-s3-XXXXXXXXXXXX","client_type":"esp32","command":"queue"}
{"device_id":"djconnect-lilygo-t-embed-s3-XXXXXXXXXXXX","client_type":"esp32","command":"playlists"}
{"device_id":"djconnect-lilygo-t-embed-s3-XXXXXXXXXXXX","client_type":"esp32","command":"pause"}
{"device_id":"djconnect-lilygo-t-embed-s3-XXXXXXXXXXXX","client_type":"esp32","command":"play"}
{"device_id":"djconnect-lilygo-t-embed-s3-XXXXXXXXXXXX","client_type":"esp32","command":"next"}
{"device_id":"djconnect-lilygo-t-embed-s3-XXXXXXXXXXXX","client_type":"esp32","command":"previous"}
{"device_id":"djconnect-lilygo-t-embed-s3-XXXXXXXXXXXX","client_type":"esp32","command":"set_output","value":"iPhone","play":true}
{"device_id":"djconnect-lilygo-t-embed-s3-XXXXXXXXXXXX","client_type":"esp32","command":"set_volume","value":35}
{"device_id":"djconnect-lilygo-t-embed-s3-XXXXXXXXXXXX","client_type":"esp32","command":"start_liked_proxy","play":true}
{"device_id":"djconnect-lilygo-t-embed-s3-XXXXXXXXXXXX","client_type":"esp32","command":"start_playlist","value":"spotify:playlist:...","play":true}
{"device_id":"djconnect-lilygo-t-embed-s3-XXXXXXXXXXXX","client_type":"esp32","command":"play_context_at","value":{"context_uri":"spotify:playlist:...","offset_uri":"spotify:track:..."}}
{"device_id":"djconnect-lilygo-t-embed-s3-XXXXXXXXXXXX","client_type":"esp32","command":"set_shuffle","value":true}
{"device_id":"djconnect-lilygo-t-embed-s3-XXXXXXXXXXXX","client_type":"esp32","command":"set_repeat","value":"context"}
Verwachte response shapes:

{
  "success": true,
  "playback": {
    "has_playback": true,
    "is_playing": true,
    "track_name": "Song",
    "artist_name": "Artist",
    "album_image_url": "https://...",
    "progress_ms": 12345,
    "duration_ms": 180000,
    "volume_percent": 32,
    "shuffle": false,
    "repeat_state": "off",
    "device": {
      "id": "spotify-device-id",
      "name": "iPhone",
      "type": "Smartphone",
      "active": true,
      "supports_volume": true,
      "volume_percent": 32
    }
  }
}
Command responses are transport/command success first, playback-state second.
A command response with `success:true` and `playback.has_playback:false` is not
an error state. `command:"status"` and `POST /api/djconnect/v1/status` must always
return a non-empty JSON body with `success`, `backend_available`, `ha_version`,
`ha_major_minor` and `playback`. If there is no active Spotify playback,
`backend_available` remains `true` when Spotify credentials/backend browsing are
valid; use `backend_available:false` only for genuine backend/auth failure.

`command:"playlists"` is browsing, not active playback. If Spotify credentials
are valid and playlist browsing succeeds, HA must return HTTP 200 with
`success:true`, `backend_available:true` and `playlists[]` items containing at
least `name`, `uri`, `owner` and `image_url`, even when Spotify playback is
idle. HA should also include client-compatible aliases: top-level `items`,
`data.playlists`, `data.items`, `result.playlists`, `result.items`, and `count`.
Per item, clients may read title from `name`, `title` or `display_title`; start
value from `uri`, `id`, `value` or `playlist_uri`; subtitle from `owner`,
`owner_name`, `description`, `artist`, `artists`, `subtitle` or `album`; and
artwork from `image_url`, `imageUrl`, `album_image_url`, `albumImageUrl`,
`album_art_url`, `media_image_url`, `entity_picture` or `thumbnail_url`.
Items without a title or playable URI may be ignored by clients. ESP32 clients
may send `limit`; HA must cap ESP responses at 20 and use a safe default of 20
when ESP omits it. App-like clients may request up to 100 playlists. HA must
page Spotify's `/me/playlists` provider API internally with Spotify-safe page
limits of at most 50 items, and must never forward client `limit=100` directly
to Spotify. Use
`backend_available:false` only when the backend is genuinely unavailable or
auth is invalid, and still return a non-empty JSON body with `success:false`,
`error:"playback_backend_unavailable"` and empty playlist aliases.

HA debug logging should include redacted request/response metadata for
`command:"status"`, `command:"devices"`, `command:"queue"`,
`command:"playlists"` and `POST /api/djconnect/v1/status`: command, client_type,
device_id, requested limit, playlist count and backend/auth unavailable reason.
Never log bearer tokens, refresh tokens, passwords or secrets.

When `playback.has_playback == false`, clients must treat the playback snapshot
as valid but empty. Playback fields may be `null` or empty strings, including
`progress_ms`, `duration_ms`, `volume_percent`, `device.volume_percent`,
`title`, `track_name`, `artist`, `album_name`, `uri`, `context_uri`,
`queue_context` and artwork URLs. Swift/Kotlin/TypeScript models must make
these fields nullable/optional and must not fail decoding because no playback is
active.

Backend unavailable/auth failure:

{
  "success": false,
  "error": "backend_unavailable",
  "message": "Spotify authorization has expired or was revoked. Reauthorize DJConnect.",
  "backend_available": false,
  "playback": {}
}
Belangrijk:

Dit is geen pairing failure.
Toon een backend/playback fout in UI.
Wis pairing niet.

Queue response handling:

{
  "success": true,
  "context_uri": "spotify:playlist:...",
  "queue": [
    {
      "title": "Black",
      "subtitle": "Pearl Jam",
      "uri": "spotify:track:...",
      "album_image_url": "https://..."
    }
  ]
}

Regels:

ESP bewaart `context_uri` voor per-item playback.
ESP deduplicates queue-items defensief op `uri`, of op `title` + `subtitle` wanneer geen URI beschikbaar is.
Als HA maar 1 item teruggeeft, mogen device en web maar 1 item tonen.
Queue thumbnail URLs zijn pass-through voor web lazy-loading; de ESP downloadt deze thumbnails niet alleen omdat de queue wordt opgehaald.
4. Device command API vanaf HA
Controleer POST /api/device/command voor device-instellingen:

{"command":"status"}
{"command":"screen_brightness","value":75}
{"command":"screen_dim_timeout","value":60000}
{"command":"turn_off_after","value":300000}
{"command":"speaker_volume","value":50}
{"command":"wake_word","value":true}
{"command":"language","value":"nl"}
{"command":"theme","value":"dark"}
{"command":"log_level","value":"info"}
{"command":"dj_response","text":"Daar gaan we.","audio_url":"http://..."}
Responses altijd JSON:

{"success":true}
of:

{"success":false,"error":"invalid_command","message":"..."}
5. PTT / voice
Physical PTT:

ESP records WAV
-> POST /api/djconnect/v1/voice raw audio/wav
-> HA does STT
-> HA may run a guarded HA Assist fuzzy-correction step on the recognized text
-> HA does Spotify intent parsing/playback/TTS
-> HA returns DJ text plus optional WAV/MP3 audio_url
-> ESP displays text and plays local response audio
The fuzzy-correction step is best-effort only: it corrects likely STT mistakes
in artist, track, album and playlist names, never sends credentials to Assist,
never controls Home Assistant devices, and must fall back to the original STT
text when Assist returns a device-lookup error, prompt leak, URI/JSON or empty
response.

Canonical spoken intent example data for website/client documentation lives in
`examples/voice_intents.json` and `VOICE_INTENT_DATA.md` in the HA repo. Keep the same intent families and
example wording aligned in client docs: generic artist requests stay
artist-first; explicit `nummer`/`liedje`/`track`/`song` requests become track
searches; explicit `album`/`plaat` requests become album searches; explicit
`playlist`/`afspeellijst` requests become playlist searches; and default
playlist/favorites phrases map to the configured default playlist. Current
track questions and direct playback controls are supported non-search intent
families.
Expected HA response:

{
  "success": true,
  "text": "Daar gaan we.",
  "dj_text": "Daar gaan we.",
  "audio_url": "http://homeassistant.local:8123/api/djconnect/v1/tts/token.mp3",
  "audio_type": "mp3"
}

`audio_url` is optional. HA should include it whenever HA TTS successfully
creates WAV or MP3 audio and a local Home Assistant URL can be resolved. HA must
build this URL from its local/LAN URL resolver, not from Nabu Casa/cloud. If
`audio_url` is absent, clients must display the text-only DJ response and should
not treat the command as failed.
Fout:

{
  "success": false,
  "error": "stt_failed",
  "message": "No STT provider configured..."
}
Acties:

Directe HA Assist WebSocket auth vanaf ESP niet gebruiken.
ESP uploadt alleen raw WAV.
ESP speelt WAV of MP3 audio URL af indien ondersteund.
Als `audio_url` ontbreekt: tekst tonen en text-only status/logging gebruiken.
Onbekend audioformaat: text-only tonen, niet crashen.
Geen tijdelijke audio URL tokens loggen.

PTT/wake-word runtime gedrag:

Encoder PTT start pas met opnemen na de start cue/settle delay; stop cue speelt pas nadat de WAV is afgesloten.
Wake-word detection start dezelfde lokale PTT WAV-upload flow als encoder PTT.
Wake-word tuning: Okay Nabu model, 10 ms feature step, 3-frame sliding window. LilyGO cutoff is 0.90.
Wake-word-started recording stopt automatisch na stilte en blijft altijd begrensd door de maximale opname-duur.
Tijdens processing of het DJ-aankondiging scherm annuleert een middelste encoderdruk de rest van de PTT flow zo snel mogelijk; lopende HA HTTP responses mogen lokaal genegeerd worden en response audio moet een stop request krijgen.
6. OAuth / Spotify secrets verwijderen
Controleer dat ESP:

geen backend OAuth/client-id/refresh-token secrets opslaat;
geen backend OAuth secrets verwacht in pair/status responses;
playback_configured is hooguit een backend/statushint, niet een request om playback credentials te ontvangen.
Verwijder/neutraliseer oude codepaden die Spotify credentials naar ESP provisionen.

7. OTA
Controleer:

OTA endpoint blijft POST /api/device/ota.
Bearer token verplicht.
Payload accepteert:
{
  "version": "3.2.x",
  "url": "https://...",
  "sha256": "...",
  "device": "lilygo-t-embed-s3",
  "asset": "djconnect-lilygo-t-embed-s3-v3.2.x.bin"
}
device moet matchen met het boardprofiel van de firmware:
- LilyGO productie: `lilygo-t-embed-s3`, asset `djconnect-lilygo-t-embed-s3-v3.2.x.bin`

ESP32-S3-BOX-3 wordt niet meer gebouwd of gepubliceerd; geen BOX-3 OTA payload target, asset of manifest entry toevoegen tenzij support expliciet opnieuw wordt geïntroduceerd.
Het manifest gebruikt alleen een `firmwares` array met board, device, asset,
sha256 en size per firmware. Geen top-level single-device `device`, `asset`,
`sha256` of `size` fallback.
Tijdens OTA:
duidelijke UI status;
paarse snelle LED-ring animatie;
release wake-word/TFLite en actieve voice/audio resources voordat firmware-download/TLS start;
status na reboot terug naar idle;
post-boot status naar HA met firmwareversie en idle state.
8. BLE WiFi provisioning
BLE provisioning doet alleen WiFi credentials.

Service/characteristics:

Service UUID: 7f705000-9f8f-4f1a-9b5f-570071fd0001
WiFi write characteristic: 7f705001-9f8f-4f1a-9b5f-570071fd0001
Status read/notify characteristic: 7f705002-9f8f-4f1a-9b5f-570071fd0001
Geen Spotify credentials, device tokens of andere secrets via BLE.

9. UI/UX
Device blijft koppelcode tonen tot HA pairing echt bevestigd is.
Gebruik het echte DJConnect icoon uit de overgenomen assets op het device-scherm; geen approximatie met eigen SVG/primitive drawing.
Na succesvolle HA direct pair en eerste geaccepteerde HA command/status mag UI naar paired/groen.
Backend unavailable mag niet terug naar pairing-code scherm forceren.
Pairing stale mag duidelijk tonen: reset/re-pair nodig.
Soft reset/reboot moet local cue sound en felle witte LED-ring flash tonen vlak voor reboot.
Bonus games Pong, Asteroids, Fly en Pacman mogen in UI blijven.
10. Tests
Voeg/update host tests waar mogelijk:

Pairing token opgeslagen en hergebruikt voor /status, /command, /voice.
Backend unavailable response wist pairing niet.
401/403/404 markeert pairing stale maar wist NVS niet automatisch.
Status payload bevat settings aliases.
Device command parsing voor brightness/speaker/language/theme/log_level.
PTT upload bouwt correcte headers en content type.
No Spotify OAuth secret keys in status/pair/provision payloads.
OTA payload device target matcht het boardprofiel (`lilygo-t-embed-s3` voor de huidige ondersteunde firmware build).
DJConnect asset conversie test of snapshot/checksum zodat het firmware asset niet per ongeluk terugvalt naar een oud producticoon.
Acceptatiecriteria
ESP pairt met HA en blijft paired na de eerste /api/djconnect/v1/command.
ESP gebruikt uitsluitend de eigen model-specifieke device ID als echte device ID en accepteert geen legacy `djconnect-XXXXXXXXXXXX`, `djconnect-lilygo-XXXXXXXXXXXX` of `djconnect-[6-cijferige-code]`.
ESP wist pairing niet door Spotify OAuth/backend failures.
ESP status houdt HA native entities actueel.
ESP gebruikt alleen de HA-native lokale API.
ESP bewaart geen Spotify credentials.
ESP stuurt generic playback commands naar HA.
ESP PTT uploadt raw WAV naar HA en speelt HA DJ-aankondiging lokaal af.
ESP annuleert PTT/DJ-aankondiging flow op middelste encoderdruk tijdens processing/response.
ESP deduplicates Up Next queue display so one real queue item is not shown repeatedly.
OTA gebruikt `djconnect-lilygo-t-embed-s3-vX.Y.Z.bin` met target `lilygo-t-embed-s3`; er worden geen BOX-3 firmware assets gepubliceerd.
Het device gebruikt de echte DJConnect icon assets uit pcvantol/djconnect in plaats van een opnieuw getekende benadering.
Logs bevatten geen secrets.

---

## Detailed iOS/macOS/watchOS App Handoff

# DJConnect iOS/macOS/watchOS App Sync Prompt / Handoff

This handoff is for building native iOS/macOS/watchOS DJConnect clients that use
the same Home Assistant custom integration backend as the ESP32 firmware.

Use this as the sync prompt for a new Apple-client repo. The current ESP
firmware contract line is `3.2.x`; Apple clients should follow the same
`3.2.x` Home Assistant integration protocol unless that backend contract is
changed deliberately.

The app should be functionally comparable to the ESP device at the Home
Assistant integration contract level, but it is not an ESP emulator. Use
`client_type` to identify the client family:

- iOS app: `ios`
- macOS app: `macos`
- ESP firmware remains: `esp32`

Do not use `device_type` for DJConnect client identity. `device_type` may only
appear as playback-output metadata if returned by the backend.

## Architecture

Home Assistant is the trusted DJConnect backend for:

- pairing;
- bearer-token lifecycle;
- backend playback commands;
- Spotify OAuth and future playback backend credentials;
- Assist/STT/TTS;
- OTA/update offers for device clients where applicable;
- native Home Assistant entities.

The iOS/macOS/watchOS app owns:

- native UI;
- local app state;
- local audio recording if voice/PTT is implemented;
- local playback of returned DJ announcement audio, if desired;
- local notifications/menus/widgets, if desired.

The app must not store or request Spotify OAuth secrets, refresh tokens, client
secrets, Sonos credentials, Home Assistant long-lived access tokens, or playback
backend credentials. The only DJConnect credential owned by the app is its
DJConnect device bearer token issued by the integration.

## Identity

Use a stable device id per app installation.

Suggested format:

- iOS: `djconnect-ios-<stable-install-id>`
- macOS: `djconnect-macos-<stable-install-id>`
- watchOS: `djconnect-watchos-<stable-install-id>`

The suffix should be stable across app launches, but should reset if the user
explicitly resets DJConnect pairing in the app. Avoid exposing Apple account,
device serial, hostname, WiFi SSID, or other private identifiers in the id.

Recommended fields:

```json
{
  "device_id": "djconnect-ios-8F3A2C91B45D",
  "device_name": "DJConnect iPhone",
  "client_type": "ios",
  "firmware": "3.2.18",
  "app_version": "3.2.18",
  "platform": "ios"
}
```

For macOS:

```json
{
  "device_id": "djconnect-macos-8F3A2C91B45D",
  "device_name": "DJConnect Mac",
  "client_type": "macos",
  "firmware": "3.2.18",
  "app_version": "3.2.18",
  "platform": "macos"
}
```

The HA integration currently uses `firmware` as the common client version field
for protocol compatibility checks. App clients may also send `app_version`, but
must keep `firmware` populated unless the backend contract is changed.

## Version Contract

DJConnect clients and the HA integration must share the same `major.minor`
protocol version:

- HA `3.1.z` accepts clients `3.1.z`.
- Patch versions may differ.
- `0.0.0` is reserved as a dev-client escape hatch.

If HA returns HTTP `426` with `error: "version_mismatch"`, the app must not
reset pairing or discard the token. Show an update-required state and pause
command/voice retries until the user updates the app or integration.

The public ESP firmware manifest uses `min_ha_integration` derived from the
firmware major/minor line (`X.Y.Z` -> `X.Y.0`). Apple clients should apply the
same major/minor compatibility rule locally even though they do not consume ESP
OTA firmware assets.

Expected response:

```json
{
  "success": false,
  "error": "version_mismatch",
  "message": "DJConnect Home Assistant integration and device firmware major.minor versions must match.",
  "ha_version": "3.2.18",
  "ha_major_minor": "3.2",
  "firmware": "3.1.9",
  "firmware_major_minor": "3.1"
}
```

## Pairing Flow

The app should pair with the Home Assistant DJConnect integration, not directly
with Spotify or any playback backend.

The app needs:

- Home Assistant base URL, local or remote;
- DJConnect pairing token issued by the integration;
- DJConnect bearer token returned/stored by the integration.

Recommended user flow:

1. User enters/selects their Home Assistant URL.
2. App opens the DJConnect pairing/setup flow in Home Assistant, or receives a
   pairing code/deep link depending on the final UX.
3. Integration creates or returns a DJConnect device bearer token for the app
   runtime.
4. App stores only the DJConnect bearer token in Keychain.
5. App starts sending authenticated status and command payloads with
   `client_type`.

Bearer token storage:

- iOS: Keychain item scoped to the app.
- macOS: Keychain item scoped to the app/bundle id.
- Never log the token.
- Never include the token in diagnostics exports.

Auth headers for app -> HA:

```http
Authorization: Bearer <device_token>
X-DJConnect-Device-ID: <device_id>
Content-Type: application/json
```

For raw voice audio:

```http
Authorization: Bearer <device_token>
X-DJConnect-Device-ID: <device_id>
Content-Type: audio/wav
```

## Local App Web API For HA -> App

To be functionally comparable to the ESP firmware, the Apple client must also
offer a small local authenticated Web API for Home Assistant -> app traffic.
Without this, HA can receive app status and playback commands from the app, but
cannot push native entity commands, DJ responses, pairing callbacks, or local
state requests back to the running client.

Run a local HTTP server while the app is reachable on the LAN:

- macOS: run while the app/menu-bar helper is active; optionally launch at
  login for persistent availability.
- iOS/iPadOS: run while the app is foreground/active and has Local Network
  permission. Do not assume a background HTTP server remains reachable after
  suspension; HA must tolerate the app being temporarily unreachable.

Advertise the app with Bonjour/mDNS using the same service as ESP clients:

```text
service: _djconnect._tcp
hostname: <device_id>.local
url: http://<device_id>.local:<port>
TXT: name, device_id, version, paired, api, model, client_type
```

Use stable app device IDs:

```text
djconnect-ios-<stable-install-id>
djconnect-macos-<stable-install-id>
djconnect-watchos-<stable-install-id>
```

Open local endpoints:

```http
GET /api/device/info
GET /api/device/pairing-info
```

Protected local endpoints require:

```http
Authorization: Bearer <device_token>
```

Recommended protected endpoints:

```http
POST /api/device/pair
POST /api/device/command
POST /api/device/dj_response
POST /api/device/forget
```

`POST /api/device/reboot` and `POST /api/device/ota` are ESP-specific and
should not be implemented unless the Apple app has a real equivalent.

App clients are inbound-only in the `3.2.x` contract. They do not expose
Home Assistant-callable `/api/device/*` endpoints. Pairing material is generated
by Home Assistant and the app posts it back to `/api/djconnect/v1/pair`.

The local app pairing payload sent to Home Assistant should include:

```json
{
  "device_id": "djconnect-ios-8F3A2C91B45D",
  "device_name": "DJConnect iPhone",
  "pair_code": "123456",
  "client_type": "ios",
  "firmware": "3.2.18",
  "app_version": "3.2.18",
  "platform": "ios"
}
```

For macOS, use `client_type:"macos"` and a `djconnect-macos-...` device id.
For watchOS, use `client_type:"watchos"`, `platform:"watchos"` and a
`djconnect-watchos-...` device id.
Never use `device_type` for identity.

Home Assistant responds with DJConnect pairing data such as:

```json
{
  "success": true,
  "device_token": "<device-token>",
  "ha_local_url": "http://192.168.1.x:8123",
  "ha_remote_url": "https://example.ui.nabu.casa"
}
```

Rules:

- Accept only this app installation's own `device_id`.
- Accept only the expected `client_type` for the target app (`ios`, `macos` or `watchos`).
- Store only the DJConnect bearer token, HA local URL and lightweight
  DJConnect settings.
- Keep `ha_local_url` as the normal route for app -> HA status, command, Ask DJ
  and voice calls; `ha_remote_url` is fallback/diagnostics for remote-capable
  iOS/macOS/Windows clients.
- Do not expose app-local `/api/device/*` endpoints for HA to call.
- Return concise JSON errors for unauthorized, wrong device id, wrong
  client_type, missing token, or unsupported command.

DJ announcements, Ask DJ messages, playback actions and history clear/sync use
the `/api/djconnect/v1/...` endpoints or the optional Home Assistant websocket fast
path. HTTP remains the canonical fallback.

## Status Endpoint

Post client status to:

```http
POST /api/djconnect/v1/status
```

Minimum payload:

```json
{
  "device_id": "djconnect-ios-8F3A2C91B45D",
  "client_type": "ios",
  "ha_pairing_status": "paired",
  "firmware": "3.2.18",
  "app_version": "3.2.18",
  "state": "online",
  "status": "online",
  "battery_percent": 85,
  "language": "nl",
  "theme": "dark",
  "log_level": "info"
}
```

Optional app-specific fields:

```json
{
  "platform": "ios",
  "os_version": "18.5",
  "app_build": "30900",
  "local_audio_supported": true,
  "voice_supported": true,
  "screen_state": "on",
  "network_type": "wifi"
}
```

Status responses may include:

```json
{
  "success": true,
  "client_type": "ios",
  "backend_available": true,
  "playback": {}
}
```

Home Assistant must not send `device_language` or `language` to iOS, macOS,
watchOS or Raspberry Pi clients in pairing/status responses. App-like clients
own their UI language setting locally.

Status is authoritative for Home Assistant entities that represent the app
client. Command payloads must not be used as partial status snapshots.

## Playback Commands

Send generic playback commands to:

```http
POST /api/djconnect/v1/command
```

All command payloads must include `device_id` and `client_type`.
Keep command payloads focused on playback commands and client identity. Do not
send partial device-status snapshots in `/api/djconnect/v1/command`; use
`/api/djconnect/v1/status` as the authoritative source for client status and
settings mirrored into Home Assistant entities.

Examples:

```json
{"device_id":"djconnect-ios-8F3A2C91B45D","client_type":"ios","command":"status"}
{"device_id":"djconnect-ios-8F3A2C91B45D","client_type":"ios","command":"devices"}
{"device_id":"djconnect-ios-8F3A2C91B45D","client_type":"ios","command":"queue","limit":100}
{"device_id":"djconnect-ios-8F3A2C91B45D","client_type":"ios","command":"playlists"}
{"device_id":"djconnect-ios-8F3A2C91B45D","client_type":"ios","command":"pause"}
{"device_id":"djconnect-ios-8F3A2C91B45D","client_type":"ios","command":"play"}
{"device_id":"djconnect-ios-8F3A2C91B45D","client_type":"ios","command":"next"}
{"device_id":"djconnect-ios-8F3A2C91B45D","client_type":"ios","command":"previous"}
{"device_id":"djconnect-ios-8F3A2C91B45D","client_type":"ios","command":"seek_relative","value":15000}
{"device_id":"djconnect-ios-8F3A2C91B45D","client_type":"ios","command":"seek_relative","value":-15000}
{"device_id":"djconnect-ios-8F3A2C91B45D","client_type":"ios","command":"set_volume","value":35}
{"device_id":"djconnect-ios-8F3A2C91B45D","client_type":"ios","command":"set_shuffle","value":true}
{"device_id":"djconnect-ios-8F3A2C91B45D","client_type":"ios","command":"set_repeat","value":"context"}
{"device_id":"djconnect-ios-8F3A2C91B45D","client_type":"ios","command":"start_liked_proxy","play":true}
{"device_id":"djconnect-ios-8F3A2C91B45D","client_type":"ios","command":"start_playlist","value":"spotify:playlist:...","play":true}
{"device_id":"djconnect-ios-8F3A2C91B45D","client_type":"ios","command":"set_output","value":"iPhone","play":true}
```

Playlist command responses should include playlist metadata and artwork when
available:

```json
{
  "success": true,
  "playlists": [
    {
      "id": "spotify:playlist:...",
      "name": "Friday Night",
      "uri": "spotify:playlist:...",
      "image_url": "https://..."
    }
  ]
}
```

For playlist artwork, clients should accept these aliases:

- `image_url`
- `album_image_url`
- `media_image_url`
- `entity_picture`

Home Assistant should prefer `image_url` for playlist artwork, but may also
return one of the aliases above when sharing code with queue/playback image
serializers. Queue items continue to use `album_image_url` as the primary field.

Apple app clients may expose current-track seek controls. Use
`command:"seek_relative"` with an integer `value` in milliseconds. Positive
values seek forward and negative values seek backward. Home Assistant should
clamp the resulting position to the current track and return the usual command
response. ESP clients may skip this UI capability.

Expected success shape:

```json
{
  "success": true,
  "playback": {
    "has_playback": true,
    "is_playing": true,
    "track_name": "Song",
    "artist_name": "Artist",
    "album_image_url": "https://...",
    "progress_ms": 12345,
    "duration_ms": 180000,
    "volume_percent": 32,
    "shuffle": false,
    "repeat_state": "off",
    "device": {
      "id": "spotify-device-id",
      "name": "iPhone",
      "type": "Smartphone",
      "active": true,
      "supports_volume": true,
      "volume_percent": 32
    }
  }
}
```

Command responses are transport/command success first, playback-state second.
A command response with `success:true` and `playback.has_playback:false` is not
an error state. `command:"status"` and `POST /api/djconnect/v1/status` must always
return a non-empty JSON body with `success`, `backend_available`, `ha_version`,
`ha_major_minor` and `playback`. If there is no active Spotify playback,
`backend_available` remains `true` when Spotify credentials/backend browsing are
valid; use `backend_available:false` only for genuine backend/auth failure.

`command:"playlists"` is browsing, not active playback. If Spotify credentials
are valid and playlist browsing succeeds, HA must return HTTP 200 with
`success:true`, `backend_available:true` and `playlists[]` items containing at
least `name`, `uri`, `owner` and `image_url`, even when Spotify playback is
idle. HA should also include client-compatible aliases: top-level `items`,
`data.playlists`, `data.items`, `result.playlists`, `result.items`, and `count`.
Per item, clients may read title from `name`, `title` or `display_title`; start
value from `uri`, `id`, `value` or `playlist_uri`; subtitle from `owner`,
`owner_name`, `description`, `artist`, `artists`, `subtitle` or `album`; and
artwork from `image_url`, `imageUrl`, `album_image_url`, `albumImageUrl`,
`album_art_url`, `media_image_url`, `entity_picture` or `thumbnail_url`.
Items without a title or playable URI may be ignored by clients. ESP32 clients
may send `limit`; HA must cap ESP responses at 20 and use a safe default of 20
when ESP omits it. App-like clients may request up to 100 playlists. HA must
page Spotify's `/me/playlists` provider API internally with Spotify-safe page
limits of at most 50 items, and must never forward client `limit=100` directly
to Spotify. Use
`backend_available:false` only when the backend is genuinely unavailable or
auth is invalid, and still return a non-empty JSON body with `success:false`,
`error:"playback_backend_unavailable"` and empty playlist aliases.

HA debug logging should include redacted request/response metadata for
`command:"status"`, `command:"devices"`, `command:"queue"`,
`command:"playlists"` and `POST /api/djconnect/v1/status`: command, client_type,
device_id, requested limit, playlist count and backend/auth unavailable reason.
Never log bearer tokens, refresh tokens, passwords or secrets.

When `playback.has_playback == false`, clients must treat the playback snapshot
as valid but empty. Playback fields may be `null` or empty strings, including
`progress_ms`, `duration_ms`, `volume_percent`, `device.volume_percent`,
`title`, `track_name`, `artist`, `album_name`, `uri`, `context_uri`,
`queue_context` and artwork URLs. Swift/Kotlin/TypeScript models must make
these fields nullable/optional and must not fail decoding because no playback is
active.

Backend unavailable is not an auth failure:

```json
{
  "success": false,
  "error": "backend_unavailable",
  "message": "Spotify authorization has expired or was revoked. Reauthorize DJConnect.",
  "backend_available": false,
  "playback": {}
}
```

When backend unavailable:

- keep pairing/token;
- show playback backend unavailable;
- do not send the user through app pairing again;
- throttle retries enough to avoid UI churn.

When HA returns 401/403:

- mark pairing stale/unauthorized;
- keep token until the user explicitly resets pairing;
- show setup-again guidance.

When HA returns 404:

- treat as integration route missing or stale pairing;
- do not erase Keychain automatically;
- show integration/setup recovery.

## Voice/PTT

If implementing push-to-talk:

1. App records mono PCM WAV.
2. App uploads raw WAV to HA:

```http
POST /api/djconnect/v1/voice
Content-Type: audio/wav
Authorization: Bearer <device_token>
X-DJConnect-Device-ID: <device_id>
```

3. HA owns STT, Assist, playback action and TTS.
4. HA returns DJ text and optional audio URL.
5. App displays text and may play returned WAV/MP3 audio locally.

Expected response:

```json
{
  "success": true,
  "text": "Daar gaan we.",
  "dj_text": "Daar gaan we.",
  "audio_url": "http://homeassistant.local:8123/api/djconnect/v1/tts/token.mp3",
  "audio_type": "mp3"
}
```

Rules:

- Do not connect directly to Home Assistant Assist WebSocket from the app for
  DJConnect PTT unless the backend contract is explicitly changed.
- Do not call OpenAI or Spotify directly from the app for DJConnect commands.
- Do not log temporary `audio_url` tokens.
- If returned audio cannot be played, show text-only response.
- If a user cancels the PTT/DJ-announcement flow locally, the app may ignore any
  late HA response from the in-flight request.
- If implementing wake-word support on Apple platforms, keep detection local to
  the app/device where Apple platform policy permits it, then start the same
  `/api/djconnect/v1/voice` WAV upload flow. HA should not need a separate
  wake-word endpoint.

## OTA And Device Updates

ESP OTA is board-specific and currently uses the public firmware manifest
`firmwares[]` entry for:

- `lilygo-t-embed-s3`

ESP32-S3-BOX-3 firmware is no longer built, released or published. Clients and
HA update logic must not expect a BOX-3 firmware asset unless a future release
explicitly reintroduces that board support.

Apple clients must not request or install ESP firmware assets. If the Home
Assistant integration exposes update information to Apple clients, it should be
app-store/TestFlight/direct-download metadata, not `/api/device/ota` with ESP
firmware binaries.

## App Settings

The ESP has device settings such as screen brightness, LED and speaker cue
volume. The iOS/macOS/watchOS app should not copy those settings blindly.

Suggested app-owned settings:

- HA URL selection;
- pairing reset;
- language;
- theme;
- voice/PTT enabled;
- local response audio enabled;
- diagnostics export;
- log level.

If app settings should be mirrored into HA entities, post them in status under
clear app-specific keys. Avoid reusing ESP-only settings like
`screen_brightness` unless the app truly implements equivalent behavior.

## UI Parity Goals

Functional parity with the ESP device should include:

- pairing/setup state;
- Home Assistant connection state;
- playback now-playing view;
- play/pause, previous, next;
- volume 0-60;
- shuffle toggle;
- repeat triple state: `off`, `track`, `context`;
- output selector;
- queue view;
- playlists/liked proxy start;
- DJ/voice response view if PTT is implemented;
- backend unavailable and version mismatch states.

iOS/macOS/watchOS-specific UX may add:

- menu bar control on macOS;
- lock screen/live activity on iOS if appropriate;
- media key integration, if it maps cleanly to DJConnect commands;
- widgets/shortcuts later.

## Security And Privacy

Never log:

- DJConnect device bearer token;
- Home Assistant tokens;
- Spotify refresh token;
- OAuth client secret;
- WiFi password;
- temporary TTS/audio URLs.

Diagnostics must redact:

- `Authorization`;
- `device_token`;
- any `token`;
- `audio_url` query strings;
- private HA URLs if the user chooses anonymized export.

## New Repo Suggested Shape

Suggested repository name:

```text
djconnect-apple
```

Suggested top-level structure:

```text
DJConnectApple/
  Package.swift or DJConnectApple.xcodeproj
  Sources/
    DJConnectCore/
      DJConnectClient.swift
      DJConnectModels.swift
      DJConnectPairing.swift
      DJConnectKeychain.swift
      DJConnectVoice.swift
    DJConnectIOS/
    DJConnectMac/
  Tests/
    DJConnectCoreTests/
  README.md
  PRIVACY.md
```

Core module responsibilities:

- build authenticated requests;
- serialize status/command/voice payloads;
- parse playback responses;
- classify errors: backend unavailable, auth stale, version mismatch,
  not configured, network;
- store and clear bearer token via a platform abstraction.

Do not put SwiftUI view logic into the HTTP client.

## Acceptance Criteria

- App pairs with the existing `djconnect` HA integration.
- App status posts include `client_type` as `ios`, `macos` or `watchos`.
- App command posts include `client_type` as `ios`, `macos` or `watchos`.
- App does not send `device_type` for identity.
- HA backend playback commands work without any Spotify credentials in the app.
- Backend unavailable does not reset pairing.
- HTTP 426 version mismatch shows update-required UI and keeps pairing.
- 401/403/404 show stale pairing/setup recovery and keep token until user reset.
- Voice/PTT, if implemented, uploads raw WAV to `/api/djconnect/v1/voice`.
- Apple clients do not consume ESP OTA firmware manifest assets.
- No secrets appear in logs or diagnostics.
- iOS and macOS clients can coexist with ESP32 clients in the same HA backend.

---

## Apple App Focused Sync Prompts

# Sync Prompts

Use these prompts when handing work between the Home Assistant integration,
central API backend, Apple app, Windows desktop app, ESP firmware, Raspberry Pi
client, and website/docs repos.

Canonical repo locations:

- Home Assistant integration: `pcvantol/djconnect`
- Central API backend: `pcvantol/djconnect-api`
- Apple app: `pcvantol/djconnect-app`
- Windows desktop app: `pcvantol/djconnect-windows`
- ESP firmware: `pcvantol/djconnect-esp32`
- Website/docs: `pcvantol/djconnect-website`
- Raspberry Pi client: `pcvantol/djconnect-pi`

## Home Assistant Integration

```text
Sync the DJConnect Home Assistant integration with the central API backend,
Apple app, ESP client, Raspberry Pi client and Windows client contracts.

Requirements:
- Treat iOS/macOS/watchOS/Raspberry Pi/Windows as app-like clients, not ESP hardware devices.
- Home Assistant may relay privacy-safe push registration and event data to the
  central `pcvantol/djconnect-api` backend, but it must never receive or store
  the APNs provider private key. HA-to-central-API calls must not contain raw
  prompts, raw assistant responses, full chat history, Music DNA, Home
  Assistant tokens or Spotify tokens.
- Home Assistant stores only central API settings scoped to one installation:
  `api_base_url`, stable `ha_install_id` and a per-install `djci_...` token.
  HACS must never contain `DJCONNECT_RELAY_SECRET` or any global
  relay/operator secret.
- Ask DJ / Music DNA is server-side in the Home Assistant integration. iOS,
  macOS, watchOS, Raspberry Pi and Windows clients must not store Music DNA.
  Music DNA is explicit opt-in; while disabled, HA must not build Music DNA
  knowledge from Ask DJ, listening profiles, recent tracks or preferences.
  Clients use `POST /api/djconnect/v1/music_dna/profile`, `/settings` and
  `/clear` to show structured DNA, enable/disable learning and clear learned DNA
  at any time. Clients may send optional `mood` (0-100), `dj_style` and
  `music_dna_key` hints on status/voice/command payloads, but HA may normalize
  or override the resolved `music_dna_key`. ESP32 is excluded from Ask DJ
  chat/history and keeps its voice/playback command flow.
- Ask DJ chat history is server-side per HA user and bounded. iOS, macOS,
  watchOS, Raspberry Pi and Windows clients
  must use `history_revision`, `clear_revision`, `history_trimmed_before` and
  `history_trimmed_count` from HA responses to reconcile local caches.
- iOS/macOS/watchOS render `confirmation_actions[]` and confirmation-style
  `playback_actions[]` as Ja/Nee controls, then answer with
  `command:"ask_dj_followup_response"`. Do not execute pending actions
  client-side. Raspberry Pi renders Ask DJ as `readonly_actions`: no free
  prompt controls, but HA-provided structured action buttons may be shown and
  sent through the normal command contract.
- Pair app-like clients through POST /api/djconnect/v1/pair.
- Pair ESP32 and Raspberry Pi local-device clients through their local
  /api/device/pair flow after resolving /api/device/pairing-info and verifying
  the visible pair_code.
- Accept stable device_id, device_name, client_type, firmware, app_version,
  platform and optional capabilities. Raspberry Pi status/pairing payloads may
  advertise capabilities such as touch=true, ask_dj_supported=true,
  ask_dj_mode=readonly_actions, ask_dj_free_input_supported=false,
  ask_dj_actions_supported=true, voice=false, voice_supported=false,
  tts_supported=false, local_audio=false, local_audio_supported=false and
  local_dj_response_endpoint=false.
- Accept the app-generated code as pair_code, pairing_code, or pairing_token.
- Return a DJConnect bearer token on success. The current compatible field is
  device_token; bearer_token and token may also be returned.
- Return ha_local_url during successful app pairing. Do not return
  device_language/language for iOS, macOS, watchOS, Raspberry Pi or Windows clients; those
  clients determine their UI language locally.
- Keep cloud/remote URLs out of Apple app runtime traffic; cloud URLs are only
  needed by Home Assistant-owned Spotify OAuth config flows.
- When pairing an app-like client, ask for or use the Client adres shown in
  the client pairing sheet. Do not assume a changing Bonjour hostname remains
  the canonical callback target after pairing.
- Implement full HA-side mDNS autodiscovery for Raspberry Pi clients in the
  pairing config-flow. Browse Bonjour/mDNS service `_djconnect._tcp`, resolve
  each service, validate `client_type=raspberry_pi` against device IDs shaped
  `djconnect-raspberry-pi-XXXXXXXXXXXX`, build the local Client adres from
  service address/port or `local_url`, then always probe
  `GET /api/device/pairing-info` when the URL is reachable. Pairing-info is
  authoritative for `local_url`, `device_id`, `client_type`, `device_name`,
  `pair_code`/`pairing_code`, `pairing_path`, `pair_path`,
  `version/app_version/firmware`, `api`, `model` and `paired`.
- The HA pairing form must prefill Raspberry Pi `Client adres`,
  `client_type=raspberry_pi`, `device_name`, stable `device_id` and visible
  `pair_code` from pairing-info. If exactly one Pi is discovered, select it by
  default but still require user confirmation; if multiple clients are found,
  show a discovered-client selector with useful labels. Discovery is
  convenience only and must never mark a device paired by itself.
- If Pi mDNS TXT is visible but `/api/device/pairing-info` fails, treat it as a
  stale/unreachable discovery record and hide it from the discovered-client
  selector on the next scan. Keep manual Client adres entry available and
  surface a clear pairing error when the user-provided URL cannot be probed
  instead of silently falling back to `djconnect-{pair_code}`. Do not create a
  second HA entry when the discovered Pi `device_id` is already configured;
  guide the user to reset or re-pair that existing client.
- Add/keep HA tests for Raspberry Pi discovery: service TXT acceptance,
  pairing-info override, stale/unreachable probe filtering, config-flow prefill
  for one Pi, selector behavior for multiple clients, duplicate `device_id`
  handling, manual Client adres fallback, and proof that Pi pairing uses the stable discovered
  `djconnect-raspberry-pi-XXXXXXXXXXXX` instead of `djconnect-{pair_code}`.
- Return ha_version or ha_major_minor on status/command responses so Apple
  clients can enforce the matching major.minor contract.
- Apple clients host local /api/device/* endpoints for HA -> client traffic,
  but must not implement ESP-only reboot or OTA routes. Raspberry Pi display
  clients may be outbound-only and must advertise capabilities so HA does not
  require local voice, audio, or dj_response endpoints.
- Persist client_type as ios, macos, watchos, raspberry_pi, windows, or esp32. Do not
  reintroduce device_type.
- Authenticated status/command/voice routes must accept Authorization: Bearer
  plus X-DJConnect-Device-ID.
- Validate that client_type matches the device_id prefix/model family:
  ios -> djconnect-ios-*, macos -> djconnect-macos-*, watchos -> djconnect-watchos-*, raspberry_pi -> djconnect-raspberry-pi-*, windows -> djconnect-windows-*, esp32 -> ESP
  model-specific ids such as djconnect-lilygo-t-embed-s3-*.
- During app pairing, 401/403 code mismatch responses stop polling, keep the
  visible app code, and do not rotate device_id automatically.
- Create native HA entities for paired app-like clients when status is
  received, including outbound-only Raspberry Pi clients that never expose
  /api/device/* endpoints.
- Create only client/runtime and backend/playback entities for ios, macos,
  watchos, raspberry_pi and windows clients; do not create ESP-only battery, Wi-Fi RSSI, screen
  state, LED state, screen brightness/timeout, speaker volume, device language,
  auto-off, theme/log-level, firmware OTA, or reboot entities for app-like
  clients. Raspberry Pi local settings such as screen blanking, logging and
  update channel are client-owned and should not be modeled as ESP hardware
  entities unless a future Pi-specific HA entity design is explicitly added.
- Support App Store review by allowing Apple clients to enter local Demo Mode
  without HA; Demo Mode must not create HA devices/entities, tokens, or backend
  traffic. Local sample DJ announcement audio/text in Demo Mode is app-local and
  is not proof of HA voice validation.
- Return HTTP 426 version_mismatch when client and HA major.minor protocol
  versions do not match; do not treat this as stale auth.
- Return backend_unavailable as HTTP 200 success:false with
  backend_available:false, not as HTTP 503.
```

## Apple App

```text
Sync the DJConnect Apple app with the Home Assistant integration contract.

Requirements:
- Keep one stable device_id per app installation across normal launches.
- Reset Pairing clears the DJConnect bearer token, rotates the app pairing
  code, and creates a fresh device_id for a new setup.
- Pair by polling POST /api/djconnect/v1/pair with pair_code, pairing_code, and
  pairing_token set to the same app-generated code.
- Store only the returned DJConnect bearer token in Keychain and persist
  ha_local_url, device_id, and client_type.
- Expose local /api/device/info, pairing-info, pair, command, dj_response, and
  forget routes for HA -> app traffic; do not expose ESP-only reboot/OTA.
- Send device_id, client_type, firmware, app_version, device_name, ha_local_url,
  and local_url on status payloads. Send device_id and client_type on command
  payloads. Always use the local Home Assistant URL for app-to-HA traffic.
- Treat backend_unavailable and version_mismatch as recoverable without
  clearing pairing.
- Treat authenticated 401/403/404 as stale/setup recovery while keeping the
  token until explicit user reset.
- Treat 401/403 during unauthenticated pairing polling as code/setup mismatch:
  stop polling, keep the visible app code, and ask the user to re-enter it.
- Show first-run onboarding once per installation with the Home Assistant setup
  link and backend requirements: Spotify Premium/Developer app for Spotify
  Direct, or a configured Music Assistant player for Music Assistant. Do not
  request Spotify credentials in the app.
- While unpaired, block runtime UI with a pairing sheet that shows the
  DJConnect banner, copyable Client adres, copyable app-generated pairing
  code, progress/status, and a green success state with `Let's Start!`.
- Keep the Client adres shown during pairing pinned locally until explicit
  pairing reset.
- Offer Demo Mode from the unpaired pairing sheet for App Store review and UI
  inspection without a Home Assistant backend. Demo Mode must use local sample
  data and must not store a bearer token.
- Fresh installs should default the Home Assistant URL field to
  `http://homeassistant.local:8123`, while paired runtime traffic must use the
  returned `ha_local_url`.
- Use the shared DJConnect blue/purple gradient canvas across iOS, iPadOS, and
  macOS screens.
- Settings may preflight Microphone and Speech Recognition. Do not fake a Local
  Network request button; Apple prompts when LAN/Bonjour access first occurs.
- Keep permission rows compact on iPhone/iPad.
- Local Games are app-only. When focused, game surfaces should consume arrow
  keys and space instead of triggering app navigation.
- Detect likely unclean exits and offer only user-mediated crash reporting:
  copy redacted diagnostics or open a prefilled `pcvantol/djconnect` issue.
- Do not log bearer tokens, HA tokens, Spotify secrets, or audio URLs.
```

## Windows Desktop Client

```text
Sync the DJConnect Windows desktop app with the Home Assistant integration
contract.

Repository:
- `pcvantol/djconnect-windows`

Requirements:
- Build as a .NET MAUI desktop app targeting Windows and macOS from one
  codebase. Current targets are `net10.0-windows10.0.19041.0` and
  `net10.0-maccatalyst`; macOS builds may require a matching Xcode/.NET
  MacCatalyst workload pair.
- Use `client_type:"windows"` and stable device IDs shaped like
  `djconnect-windows-XXXXXXXXXXXX`, where the suffix is derived from the first
  12 alphanumeric characters of the stable install ID.
- Treat Windows as an app-like desktop client, not ESP firmware. Do not create
  ESP-only HA entities such as battery, Wi-Fi RSSI, screen/LED state, speaker
  volume, firmware OTA or reboot for Windows clients.
- Home Assistant remains the trusted backend for pairing, DJConnect bearer-token
  lifecycle, Spotify OAuth/backend playback, Ask DJ history, Music DNA,
  Assist/STT/TTS and command execution.
- Store only the DJConnect bearer token in platform credential storage:
  Windows Credential Manager on Windows and macOS Keychain when the same MAUI
  app runs on macOS. Keep local JSON settings non-secret.
- Do not store Spotify credentials, Spotify OAuth tokens, Home Assistant
  long-lived access tokens, Music DNA, Ask DJ server history, raw audio,
  prompts or secret-bearing backend responses as source of truth.
- Pair with Home Assistant using the app-generated pairing code and send it as
  `pairing_token`, `pair_code` and `pairing_code` for compatibility with
  current HA builds. Store the returned `device_token` only in the platform
  credential store.
- Send status to `POST /api/djconnect/v1/status` with `device_id`, `device_name`,
  `client_type`, `firmware` and app version metadata. Treat `401`/`403` as
  stale pairing and HTTP `426` version_mismatch as update-required without
  clearing the token automatically.
- Ask DJ text chat uses `POST /api/djconnect/v1/ask_dj/message`; history sync uses
  `GET /api/djconnect/v1/ask_dj/history?since_revision=<number>`; clear uses
  `POST /api/djconnect/v1/ask_dj/history/clear`.
- Persist only local sync cursors such as `history_revision` and
  `clear_revision`. Clear local display cache when HA clear_revision advances
  or pairing becomes stale. Honor `history_trimmed_before` and
  `history_trimmed_count` without parsing visible retention-message text.
- Render Ask DJ `playback_actions[]` and `confirmation_actions[]` from HA.
  Confirmation actions use `command:"ask_dj_followup_response"`;
  recommendation Play Now actions use `command:"ask_dj_play_recommendation"`
  unless HA provides a more specific command. Do not reconstruct pending
  follow-up state locally.
- Render `recently_played_history` responses as compact `items[]` lists. Do
  not invent Play Now buttons or reuse stale artwork unless HA explicitly
  returns `playback_actions[]` or current response images.
- Playback buttons send generic commands to `POST /api/djconnect/v1/command`,
  including play, pause, next, previous and future backend commands. Spotify
  OAuth and backend playback remain HA-owned.
- Keep the Spotify trademark/non-affiliation notice visible in docs/About UI:
  `Spotify is a trademark of Spotify AB. DJConnect is not affiliated with,
  endorsed by, or sponsored by Spotify AB.`
- Keep `README.md`, `CHANGELOG.md`, `CHAT_BOOTSTRAP.md`, `docs/ARCHITECTURE.md`,
  `docs/API_CONTRACT.md`, `docs/DEVELOPMENT.md`, `docs/RELEASE.md`,
  `docs/HANDOFF.md`, `docs/TODO.md`, `docs/ISSUES.md`,
  `docs/TECHNICAL_DESIGN_DECISIONS.md`, `THIRD_PARTY_NOTICES.md`, `PRIVACY.md`
  and `SECURITY.md` current.
- Run `./run_tests.sh` after protocol/model changes. CI should run protocol
  tests plus Windows and Mac Catalyst build jobs. If Mac Catalyst is blocked by
  Xcode/.NET workload mismatch, document the exact Xcode and pack versions.
- Release helpers should keep old GitHub releases, tags and workflow runs
  cleaned up through `clear_old_releases.sh`; workflow-run cleanup requires
  GitHub Actions `actions: write` permission.
- Never log or commit bearer tokens, Home Assistant tokens, Spotify secrets,
  Keychain/Credential Manager values or raw secret-bearing payloads.
```

## Raspberry Pi Client

```text
Sync the DJConnect Raspberry Pi client with the Home Assistant integration contract.

Requirements:
- Keep one stable device_id per Pi installation across normal launches.
- Use client_type raspberry_pi and device IDs shaped like
  djconnect-raspberry-pi-XXXXXXXXXXXX.
- Treat the Pi as an app-like display remote with a local-device pairing API,
  not ESP firmware.
- Support the local Client API URL flow used by HA for local-device clients.
  The Pi exposes GET /api/device/info, GET /api/device/pairing-info,
  POST /api/device/pair, POST /api/device/command and POST /api/device/forget.
- Advertise `_djconnect._tcp` mDNS on the local Client API port with TXT records
  including name/device_name, device_id, client_type=raspberry_pi,
  version/firmware/app_version, paired, api=/api/device, local_url,
  pair_code/pairing_code, pairing_path, pair_path and model=raspberry_pi.
- Validate the visible pair_code during POST /api/device/pair before storing
  the per-device token and ha_local_url.
- Store only the returned DJConnect bearer token plus ha_local_url.
- Send status to POST /api/djconnect/v1/status with device_id, device_name,
  client_type, version, firmware, ha_pairing_status and display-remote
  capabilities.
- Send playback commands to POST /api/djconnect/v1/command. Supported first
  version commands are status, play, pause, next, previous, set_volume,
  set_shuffle and set_repeat.
- Implement Ask DJ as a read-only feed with structured touch actions. Use
  GET /api/djconnect/v1/ask_dj/history with history_revision/clear_revision to
  render server-side history, clear/trim metadata, assistant/system/status/user
  bubbles, images, links/sources and HA-provided action buttons. Raspberry Pi
  must not expose local message input, voice input, idle suggestions, history
  clear or free prompt sending from the Ask DJ screen. Action taps may only send
  the structured HA-provided action payload through POST /api/djconnect/v1/command.
- Do not implement PTT, microphone capture, POST /api/djconnect/v1/voice, Ask DJ
  message sending or local DJ response audio playback for Raspberry Pi.
  Raspberry Pi must not expose a Pi-local `/api/device/dj_response` endpoint.
- Do not expose ESP-only reboot, OTA, battery, Wi-Fi RSSI, screen brightness,
  screen timeout, speaker volume, LED, log-level or firmware entities.
- Keep the updater and OS maintenance daemon separate from the touch UI and
  keep the touch UI runnable without root privileges.
- Keep general Raspberry Pi OS bootstrap separate from the app release tarball.
  Repo-only bootstrap targets Raspberry Pi OS Lite 64-bit and may configure
  timezone, SSH, apt full-upgrade, minimal X11/Qt runtime dependencies,
  HyperPixel and optional Raspberry Pi Connect. It must not install or manage
  Glances.
- Use unattended GitHub release updates only after verifying release assets with
  SHA256 at minimum; prefer signed manifests when available.
- Treat backend_unavailable and version_mismatch as recoverable without
  clearing pairing.
- Never log bearer tokens, HA tokens, Spotify secrets, Wi-Fi passwords or
  temporary audio URLs.
```

## ESP Firmware

```text
Sync the DJConnect ESP firmware with the Home Assistant integration contract.

Requirements:
- ESP clients are physical DJConnect devices and must use client_type esp32.
- Use model-specific device_id values for supported ESP firmware builds. The
  current supported production build is LilyGO T-Embed S3:
  `djconnect-lilygo-t-embed-s3-XXXXXXXXXXXX`.
- ESP32-S3-BOX-3 is no longer built, released or published in the ESP firmware
  repo. Do not add BOX-3 PlatformIO targets, CI matrix entries, OTA manifest
  entries or release assets unless board support is explicitly reintroduced.
- Do not accept or generate legacy djconnect-XXXXXXXXXXXX ids.
- Expose local ESP endpoints: GET /api/device/info,
  GET /api/device/pairing-info, POST /api/device/pair,
  POST /api/device/command, POST /api/device/dj_response,
  POST /api/device/forget, plus ESP-only reboot/OTA routes where supported.
- /api/device/pairing-info must return the real device_id, visible pair_code,
  client_type esp32, firmware, device_name, and reachable local_url.
- POST /api/device/pair must require device_token and ha_local_url.
- Persist only the DJConnect device bearer token and ha_local_url. Do not store
  Spotify OAuth/client secrets, Home Assistant long-lived tokens, or playback
  backend credentials.
- Always use ha_local_url for ESP -> HA status, command, and voice traffic.
  Never use Nabu Casa/cloud URLs for device runtime traffic.
- Send device_id, client_type esp32, firmware, ha_pairing_status, local_url,
  language, log_level, and current device settings in status payloads.
- Send raw WAV voice audio to POST /api/djconnect/v1/voice with Authorization:
  Bearer <device_token> and X-DJConnect-Device-ID.
- Treat backend_unavailable and version_mismatch as recoverable without
  clearing pairing.
- Treat authenticated 401/403/404 as stale/setup recovery while keeping
  enough diagnostics to recover.
- Never log bearer tokens, HA tokens, Spotify secrets, WiFi passwords, or
  temporary audio URLs.
```
