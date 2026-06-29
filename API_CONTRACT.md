# DJConnect API Contract

This document summarizes the client-facing DJConnect Home Assistant API contract.
It is intentionally compact; `README.md` remains the full user/developer guide.

## Client Identity

Pairing, status, command, Ask DJ and voice requests use canonical
`client_type` values to distinguish runtimes. Current values are `esp32`, `ios`,
`macos`, `watchos`, `raspberry_pi` and `windows`.

Client ids must match their client type prefix and use the first 12
alphanumeric characters of the stable client install id where applicable:

- `ios`: `djconnect-ios-XXXXXXXXXXXX`
- `macos`: `djconnect-macos-XXXXXXXXXXXX`
- `watchos`: `djconnect-watchos-XXXXXXXXXXXX`
- `raspberry_pi`: `djconnect-raspberry-pi-XXXXXXXXXXXX`
- `windows`: `djconnect-windows-XXXXXXXXXXXX`

ESP32 and Raspberry Pi are local devices. They may advertise `_djconnect._tcp`
with TXT records including `device_id`, `client_type`, `device_name`,
`local_url`, `version`/`app_version` and pairing code aliases. Home Assistant
treats `GET /api/device/pairing-info` as authoritative when reachable.
No app-client mDNS/local-API discovery is supported.

iOS, macOS, watchOS and Windows are inbound-only app clients. They do not expose a
Home Assistant-callable `/api/device/*` API, do not need a Client address in the
Home Assistant setup flow, and post local pairing requests to
`POST /api/djconnect/pair`. Home Assistant generates the app pairing code. The
iPhone app pairs by scanning a QR/deep-link payload:

```text
djconnect://pair?ha_url=<local-ha-url>&pair_code=<code>&client_type=ios&pair_path=/api/djconnect/pair
```

Apple Watch pairs through the iPhone proxy: the iPhone scans the Watch QR/deep-link
payload and forwards the pairing material to the paired Watch, which then uses
`client_type=watchos` and its own `djconnect-watchos-*` device id. The Watch must
not require manual HA URL entry:

```text
djconnect://pair?ha_url=<local-ha-url>&pair_code=<code>&client_type=watchos&pair_path=/api/djconnect/pair
```

macOS and Windows clients pair by manually entering the local Home Assistant URL
and the HA-generated pairing code. After app pairing, Home Assistant returns
`device_token`, `ha_local_url`, optional `ha_remote_url`, capability flags and
API paths. `ha_remote_url` is only returned to `ios`, `macos` and `windows`
when Home Assistant has an HTTPS external/Nabu Casa URL. ESP32 and Raspberry Pi
must never receive `ha_remote_url`.

## Backend-Independent Response Shapes

DJConnect clients should consume DJConnect response shapes, not Spotify Web API
objects directly. In `3.2.x`, Spotify Direct is the default backend adapter, but
commands and Ask DJ actions are routed through an internal use-case layer before
the selected music backend.

Stable client-facing fields include:

- `playback`
- `queue`
- `items`
- `playlists`
- `devices` / `outputs`
- `images`
- `sources`
- `playback_actions`
- `backend_available`
- `music_backend`
- `music_backend_name`
- `music_backend_available`
- `music_backend_revision`
- `music_backend_capabilities`
- `music_target_player`
- `music_backend_error`
- `provider` / `source`

Clients may display provider/source labels when present, but must not require
provider-specific fields for core rendering. `music_backend_error` is either
`null` or a small safe object with `code` and user-facing `message`; it never
contains raw exceptions, OAuth tokens, Music Assistant secrets or Home
Assistant long-lived tokens.

Pairing, status and command-status responses expose the active backend and a
monotonic `music_backend_revision`. Clients should treat cached/pending
backend-specific Play Now actions, recommendations and confirmation actions as
stale when their local revision is lower than the server revision. The backend
switch keeps pairing, device tokens, Ask DJ history, Music DNA and APNs
registrations; only backend-specific pending playback actions are invalidated.

Music Assistant is a backend-neutral target-player route, not a Spotify Direct
fallback. When `music_backend` is `music_assistant`, clients should expect
Music Assistant to own provider authentication, library browsing, queue
semantics and grouping/sync. DJConnect may expose playback/control actions for
the configured target player, but Spotify-only features such as recently played
history, top artists/tracks, Spotify library favorites and Spotify OAuth repairs
must be hidden or shown as unsupported based on `music_backend_capabilities`.

Unsupported backend capabilities use this stable shape instead of vague 500s:

```json
{
  "success": false,
  "error": "unsupported_backend_capability",
  "capability": "supports_recently_played",
  "backend": "music_assistant",
  "message": "The selected music backend does not provide recent listening history."
}
```

Stale backend-specific actions return:

```json
{
  "success": false,
  "error": "stale_backend_action",
  "message": "This action was created for a previous music backend. Ask DJ again for a fresh recommendation."
}
```

## Local WebSocket Fast Path

Local app clients may use Home Assistant's native websocket API as an optional
low-latency transport for DJConnect commands. This is a fast path for local
control only; HTTP remains canonical and must remain available for remote use,
pairing, Ask DJ history sync, clear/history requests, voice uploads, image
proxy URLs, TTS/audio downloads and fallback behavior.

Connect to Home Assistant's normal websocket endpoint derived from the local HA
URL:

- `ws://<local-ha-host>/api/websocket`
- `wss://<local-ha-host>/api/websocket`

Authenticate with Home Assistant's native websocket auth flow. The paired
DJConnect device token is not accepted as the initial Home Assistant websocket
login token unless Home Assistant itself explicitly supports that in a tested
deployment. Product clients should assume they need an HA websocket access token
or another HA-supported websocket auth mechanism before this fast path is
product-ready. After HA websocket login, feature-detect DJConnect support with:

```json
{
  "id": 1,
  "type": "djconnect/capabilities"
}
```

A supporting server returns a successful result with
`websocket_supported:true`, `transports.websocket:true` and
`commands[]` containing supported DJConnect websocket message types. Clients
must fall back to HTTP if a needed websocket command is missing, errors, times
out or reports unsupported capabilities.

Send commands with the same semantic payload used for
`POST /api/djconnect/command`:

```json
{
  "id": 2,
  "type": "djconnect/command",
  "device_id": "djconnect-ios-XXXXXXXXXXXX",
  "client_type": "ios",
  "client_id": "djconnect-ios-XXXXXXXXXXXX",
  "device_name": "Peter's iPhone",
  "device_token": "<paired DJConnect device token>",
  "command": "next",
  "value": null,
  "play": false
}
```

Alternatively clients may put the command fields under `payload`; nested payload
values win over top-level defaults. The server translates `device_token` or
`authorization` into the same bearer-token check used by HTTP, and validates
`device_id`/`client_type` with the normal DJConnect pairing rules. The Home
Assistant websocket login is not a replacement for the DJConnect device token,
and the DJConnect device token is not a replacement for the Home Assistant
websocket login.

Supported fast-path commands are the existing `/command` actions, including
`play`, `pause`, `next`, `previous`, `status`, `devices`, `queue`, `playlists`,
`set_volume`, `volume_delta`, `set_shuffle`, `set_repeat`, `set_output`,
`ask_dj_followup_response`, `ask_dj_play_recommendation`,
`ask_dj_play_recommendation_on_output`, `ask_dj_play_request_on_output` and
`ask_dj_message` when a client already routes that action through
`/api/djconnect/command`. Chat clients should still prefer
`POST /api/djconnect/ask_dj/message` for normal text chat because that endpoint
owns history append, `messages[]` ordering and push/history synchronization.

Servers that advertise the message type may also accept normal Ask DJ chat on:

```json
{
  "id": 3,
  "type": "djconnect/ask_dj/message",
  "device_id": "djconnect-ios-XXXXXXXXXXXX",
  "client_type": "ios",
  "device_token": "<paired DJConnect device token>",
  "client_message_id": "client-generated-id",
  "text": "Wat draait er nu?",
  "audio_response": "auto"
}
```

This route is the websocket equivalent of
`POST /api/djconnect/ask_dj/message`: it appends server-side history, returns
the same `messages[]`, `history_revision` and `clear_revision` sync fields, and
uses the same push/confirmation policy. Clients may use it as a local fast path
only after capability detection; HTTP remains the fallback and remains required
for remote-only sessions.

Idle suggestions can use:

```json
{
  "id": 4,
  "type": "djconnect/ask_dj/idle_suggestion",
  "device_id": "djconnect-ios-XXXXXXXXXXXX",
  "client_type": "ios",
  "device_token": "<paired DJConnect device token>",
  "music_dna_key": "optional-client-key",
  "mood": 72
}
```

The response is the websocket equivalent of
`POST /api/djconnect/ask_dj/idle_suggestion`: it appends the server-generated
system suggestion to user-scoped Ask DJ history and returns the same sync
metadata as HTTP.

Track Insight can use:

```json
{
  "id": 5,
  "type": "djconnect/track_insight",
  "device_id": "djconnect-macos-XXXXXXXXXXXX",
  "client_type": "macos",
  "device_token": "<paired DJConnect device token>",
  "title": "Windowlicker",
  "artist": "Aphex Twin"
}
```

The response is the same normalized Track Insight shape as
`POST /api/djconnect/track_insight`. If `title`/`artist` are omitted, the
backend resolves Now Playing through the selected music backend just like the
HTTP route.

Music DNA can use these websocket equivalents when advertised in
`djconnect/capabilities.commands[]`:

```json
{
  "id": 6,
  "type": "djconnect/music_dna/profile",
  "device_id": "djconnect-ios-XXXXXXXXXXXX",
  "client_type": "ios",
  "device_token": "<paired DJConnect device token>",
  "music_dna_key": "optional-client-key"
}
```

```json
{
  "id": 7,
  "type": "djconnect/music_dna/settings",
  "device_id": "djconnect-ios-XXXXXXXXXXXX",
  "client_type": "ios",
  "device_token": "<paired DJConnect device token>",
  "enabled": true
}
```

```json
{
  "id": 8,
  "type": "djconnect/music_dna/clear",
  "device_id": "djconnect-ios-XXXXXXXXXXXX",
  "client_type": "ios",
  "device_token": "<paired DJConnect device token>"
}
```

The response shapes match `POST /api/djconnect/music_dna/profile`,
`/settings` and `/clear`. HTTP remains the canonical fallback.

Clients should treat websocket failures as transport failures, not pairing
failures. On disconnect, auth error, HA websocket error, DJConnect websocket
capability miss, timeout or protocol mismatch, immediately retry the user action
through HTTP and reconnect the websocket later with backoff. Suggested client
timeouts are about 2 seconds for short playback controls, 5 seconds for
status/list requests and the existing longer Ask DJ/action timeout for commands
that already wait on backend work. Never log HA auth tokens, DJConnect device
tokens, authorization headers, raw prompts, raw audio, Ask DJ history or Music
DNA while diagnosing websocket transport state.

## Ask DJ Mood Zones

iOS, macOS and watchOS clients send `mood` as an optional integer-like value from
`0` to `100`. The Home Assistant integration accepts the value on:

- `POST /api/djconnect/ask_dj/message`
- `POST /api/djconnect/ask_dj/idle_suggestion`
- `POST /api/djconnect/voice`
- `POST /api/djconnect/status`

The server clamps out-of-range values before using them:

- `-10` becomes `0`
- `120` becomes `100`

The canonical server-side zones are lowercase:

| Mood range | Zone | Client mode |
| --- | --- | --- |
| `0`-`24` | `chill` | Chill |
| `25`-`59` | `groove` | Groove |
| `60`-`84` | `energy` | Energy |
| `85`-`100` | `party` | Party |

Clients may send only `mood`; `mood_zone` is derived by Home Assistant. If a
client includes `mood_zone` for display/debugging, HA still treats the numeric
`mood` as canonical. Missing or invalid mood keeps the existing default Ask DJ
behavior.

The zone is used in Ask DJ prompt/context generation, recommendations, idle
suggestions, Music DNA prompt context, spoken DJ announcement style and
status/debug context. DJ announcement style is not a client or config option:
when runtime mood is available, the mood zone drives the final announcement
tone; otherwise DJConnect uses its hardcoded default announcement style.
Responses do not need to echo mood fields.

Spoken DJ announcements may include one short personal intro line when compact Music DNA makes that natural. Clients must not send arbitrary Home Assistant state or local memory for this.

## Track Insight

Track Insight is a backend-independent analysis feature for the currently
playing track or an explicit artist/title. All entry points use the shared
Track Insight service layer and the selected DJConnect music backend abstraction;
clients must not assume Spotify, Music Assistant or a specific `media_player`.

Entry points:

- Ask DJ prompts such as `Tell me about this track`, `What is special about this
  song?`, `What is the vibe of this track?`, `Geef Track Insight voor dit
  nummer` or `Give me Track Insight`.
- `POST /api/djconnect/track_insight` with Home Assistant auth.
- Home Assistant service `djconnect.track_insight`, which fires
  `djconnect_track_insight` with the normalized result.

Request fields may include `title`, `artist`, `album`, `entity_id`,
`player_id`, `music_backend`, `force_refresh`, `locale`,
`include_visual_profile` and `include_raw_response`. If `title` and `artist`
are present, the backend analyzes that explicit track; otherwise it resolves
Now Playing through the music backend/status context.

Responses use normalized TrackInsight JSON with `id`, `created_at`, `source`,
`track`, `analysis`, `music_dna`, `visual_profile` and `cache`. Numeric
analysis and visual values are normalized from `0.0` to `1.0`. `music_dna`
contains a deterministic `match_percent` hint plus a short label/summary so
clients can render Music DNA Match without treating it as a measured scientific
score. `visual_profile` is deterministic and is only a rendering hint; clients
remain responsible for final visualization and must not expect server-generated
images or video. Structured errors use `error`/`message`, for example
`no_track_playing`.

## Music DNA Profile Contract

Music DNA is a first-class opt-in feature. Clients must not assume it is
enabled. Home Assistant only builds Music DNA knowledge after the resolved
user/client context has explicitly opted in, and disabling Music DNA clears
learned knowledge and stops future collection. Clearing Music DNA is always
available and preserves the current opt-in setting; if it remains enabled, new
knowledge starts building again from an empty profile.

HTTP endpoints use the regular DJConnect bearer token, `device_id` and
canonical `client_type` identity contract:

- `POST /api/djconnect/music_dna/profile`
- `POST /api/djconnect/music_dna/settings`
- `POST /api/djconnect/music_dna/clear`

`/music_dna/settings` accepts:

```json
{
  "device_id": "djconnect-ios-...",
  "client_type": "ios",
  "enabled": true
}
```

`/music_dna/profile` and `/music_dna/clear` accept the same identity fields and
optional `music_dna_key`. Profile responses are structured for the Music DNA
screen:

```json
{
  "success": true,
  "music_dna_key": "user:abc123",
  "enabled": true,
  "generation": 2,
  "clear_requested_at": null,
  "updated_at": "2026-06-29T12:00:00+00:00",
  "profile": {
    "summary": "Je Music DNA bevat nu genres zoals ambient, techno.",
    "favorite_genres": [{"name": "ambient"}],
    "favorite_artists": [{"name": "The xx"}],
    "recent_tracks": [{"title": "Intro", "artist": "The xx"}],
    "top_tracks_by_range": {},
    "top_artists_by_range": {},
    "mood": {"value": 65, "zone": "energy", "prompt_hint": "..."},
    "time_patterns": [],
    "recommendation_signals": [],
    "blocked_artists": [],
    "blocked_items": [],
    "last_profile_refresh": "2026-06-29T12:00:00+00:00",
    "consent_updated_at": "2026-06-29T11:50:00+00:00"
  },
  "sources": [{"source": "djconnect_music_dna", "kind": "source", "title": "Music DNA"}]
}
```

When Music DNA is disabled, `enabled:false` and `profile:{}` are returned.
Clients should show an opt-in state instead of deriving a fake profile from
local Track Insight history.

Home Assistant developer actions mirror the HTTP contract:

- `djconnect.music_dna_profile`
- `djconnect.set_music_dna_enabled`
- `djconnect.clear_music_dna`

The conversation/AI tool allowlist also exposes read-only
`djconnect_music_dna_profile` so the DJConnect conversation agent can inspect
the same structured profile without mutating playback or consent.

## AI Conversation Tools

DJConnect exposes AI/conversation tools through an explicit allowlist, not by
publishing every Home Assistant service as a tool. Read-only tools may inspect
Track Insight, playback status, Music DNA, recent history, search results,
outputs and recommendation candidates. Playback mutation is limited to a
server-side confirmation pair:

- `djconnect_track_insight`
- `djconnect_now_playing`
- `djconnect_music_dna_profile`
- `djconnect_music_dna_summary`
- `djconnect_recently_played`
- `djconnect_search_music`
- `djconnect_list_outputs`
- `djconnect_build_recommendations`
- `djconnect_prepare_playback_action`
- `djconnect_execute_confirmed_action`

`djconnect_prepare_playback_action` stores a bounded pending confirmation in
Music DNA and returns confirmation actions only; it must not start playback.
`djconnect_execute_confirmed_action` may execute only the latest stored
DJConnect AI-tool confirmation payload and must not accept arbitrary
`command`/`value` input.

The registry and implementation are intentionally separate. `tool_registry.py`
is the contract surface for tool names, JSON schemas and read-only flags.
`tool_handlers.py` is the backend use-case layer and is the only place where AI
tools call DJConnect backend primitives. Ask DJ uses the same handlers for
now-playing, outputs, Track Insight, recent history, search and recommendation
workflows so those routes cannot drift from the exposed Home Assistant AI tools.

## Ask DJ Message Actions

`POST /api/djconnect/ask_dj/message` responses may include
`playback_actions[]`. Clients should render actions by `kind` and must not infer
missing media from previous chat bubbles. If a response has no `images[]`, show
it as text-only.

Message responses include `user_message`, `assistant_message` and, on current
servers, a canonical `messages[]` array in render order. For a normal exchange
that array contains `[user, assistant]`. Both messages share an `exchange_id`;
`exchange_order` is `0` for the user question and `1` for the assistant answer.
Clients should prefer `messages[]` when merging the immediate HTTP response into
local chat UI, and use `exchange_order` as the tie-breaker when optimistic UI,
push events or history sync arrive close together. Older servers may omit these
fields; in that case, keep the existing fallback of rendering the user message
before the assistant message for the same `client_message_id`.

Supported action kinds:

- `album`: direct Play Now action for an album. The action includes
  backend-aware metadata, `title`, optional `subtitle`/artist and optional
  proxied `image_url`. Spotify Direct actions keep legacy `uri`/`context_uri`
  fields; clients should prefer the nested `value` object when present.
- `output`: backend output/player selection. Render the action as an output row
  or button. Use `label`/`button_label` such as `Activeer`; an already active
  output may use `Actief`.
- `control`: immediate playback control action. Pause/stop responses can return
  `command:"play"` with `label:"Resume"` / `button_label:"Resume"` so clients
  show a Resume button. Clients may also send direct control commands such as
  `volume_delta`, `set_shuffle`, `set_repeat`, `save_current_track` and
  `set_current_track_favorite` through
  `POST /api/djconnect/command`. Current-track Ask DJ responses such as
  `wat speelt er` may include a `set_current_track_favorite` control action
  with `toggle:true`, `favorite_status`, `toggle_state:"on"|"off"|"unknown"`,
  a boolean `value` target and `client_prompt` (`Zet huidig nummer in favorieten`
  or `Haal huidig nummer uit favorieten`). Render it as an immediate Now
  Playing / Ask DJ toggle button and do not route it through
  `ask_dj_play_recommendation`.
- `confirmation`: Ja/Nee follow-up action with
  `command:"ask_dj_followup_response"` and a server-side pending proposal.
  Generic playlist/recommendation offers may use labels such as `Ja graag` and
  `Nee dank je`; render them as actionable buttons and do not add album art when
  the response contains `images: []`.
- Recommendation kinds `track`, `artist`, `playlist`, `album` and `track_mix`
  remain Play Now candidates and must be sent back through
  `command:"ask_dj_play_recommendation"` unless the action explicitly uses a
  direct control/output command. A successful Play Now response returns
  `dj_text`, `dj_response`, optional `audio_url`/`audio_type` and playback
  metadata so clients can show and play the DJ announcement immediately instead
  of waiting for ambient playback facts.

Playback actions are backend-aware. Clients must not assume Spotify URIs:

```json
{
  "id": "spotify:track:123",
  "kind": "track",
  "command": "ask_dj_play_recommendation",
  "label": "Play Now",
  "backend": "spotify_direct",
  "provider": "spotify",
  "music_backend_revision": 1,
  "value": {
    "uri": "spotify:track:123",
    "title": "Track Title",
    "subtitle": "Artist Name",
    "image_url": "/api/djconnect/image_proxy/token"
  }
}
```

Music Assistant actions use provider-neutral item metadata and include the
configured target player:

```json
{
  "id": "ma:track:123",
  "kind": "track",
  "command": "ask_dj_play_recommendation",
  "label": "Play Now",
  "backend": "music_assistant",
  "provider": "music_assistant",
  "music_backend_revision": 4,
  "value": {
    "item_id": "ma:track:123",
    "provider": "music_assistant",
    "media_type": "track",
    "title": "Track Title",
    "subtitle": "Artist Name",
    "image_url": "/api/djconnect/image_proxy/token",
    "target_player_id": "media_player.mass_woonkamer"
  }
}
```

Speaker/output questions such as `welke speakers zijn er?` or
`wissel van uitvoer` return a short text intro plus one `output` action per
available backend output/player. They must not include stale album art from an
earlier music response.

Album-discography questions such as `Welke albums bracht Nirvana uit?` return a
formatted album list and `album` Play Now actions. Album playback announcements
keep album and track fields separate: album requests set album metadata on
`album`/`album_name`, and if Spotify starts the first track it appears as
`track_name`/`title`. Clients should display the returned text instead of
rewriting album responses locally.

Help requests such as `help`, `hulp`, `wat kun je?` and `welke commando's?`
return a text-only categorized command list. `Probeer opnieuw` / `retry` replays
the previous retryable playback request server-side; clients should send the
user's retry text normally and let the server resolve the prior request.
The help list includes exact prompt examples that are covered by
`examples/ask_dj_e2e_cases.json`; for example `Geef Track Insight voor dit
nummer` maps to the read-only `track_insight` intent.

Personal memory questions such as `wat weet je nu over mij?`, `wat staat er in
mijn Music DNA?` and `what do you know about me?` return
`intent.intent:"personal_music_dna_summary"` and `action:"music_dna_summary"`. The
response is Music DNA-only: `sources[]` contains `djconnect_music_dna`, `images`
and `playback_actions` are empty, and the backend must not use live playback
artwork or Spotify listening-profile enrichment for the answer.

Unknown, unsupported or low-confidence informational answers are text-only and
return `images: []`. Clients must not reuse current-track album art for these
fallback responses.

## Ask DJ E2E Contract Validation

Ask DJ client behavior can be validated with the shared case file
`examples/ask_dj_e2e_cases.json`. Each case contains a request payload fragment
and expected response contract fields such as intent, action, confirmation
buttons, playback actions, source metadata, text snippets and allowed Spotify
backend calls.

Run the deterministic offline contract tests with mocked Spotify/Assist
backends:

```bash
python3 -m unittest tests.test_ask_dj_e2e_contract
```

Run the same cases against a live Home Assistant instance with the HACS
integration loaded:

```bash
python3 tools/run_ask_dj_e2e.py \
  --base-url http://localhost:8123 \
  --token "$HA_TOKEN" \
  --cases examples/ask_dj_e2e_cases.json \
  --out reports/ask_dj_e2e_results.json
```

The live runner posts each case to `/api/djconnect/ask_dj/message` with a
stable watchOS-style test identity. Offline tests additionally record backend
commands so cases can assert that informational intents do not mutate playback.
When adding a new client-visible Ask DJ intent, add or update a case in
`examples/ask_dj_e2e_cases.json` together with the normal unit tests.

The offline contract test also checks that every prompt returned by the Ask DJ
help function appears exactly once or more in the shared case file. This keeps
client-visible help text aligned with implemented intent behavior.

## Ask DJ Recent Listening Lists

Ask DJ supports read-only recent listening-history questions through Spotify
`/me/player/recently-played`. Examples:

- `welke nummers heb ik afgelopen uur afgespeeld?`
- `welke albums heb ik vandaag geluisterd?`
- `welke artiesten hoorde ik net?`
- `welke playlists heb ik afgelopen uur gespeeld?`
- `which tracks did I play in the last hour?`

These responses use:

- `intent.category: "informational"`
- `intent.intent: "recently_played_history"`
- `intent.action: "recently_played"`
- `intent.item_type: "tracks" | "albums" | "artists" | "playlists"`
- `action: "none"`
- `sources[]` including `spotify_recently_played`

If the selected music backend does not expose recent listening history, the
response keeps `intent:"recently_played_history"`, `action:"none"` and empty
playback actions, but returns a short backend-capability fallback text instead
of Spotify OAuth or scope repair instructions.

The response may include top-level `items[]` and the same list under
`assistant_message.items[]`. Each item is display-ready:

```json
{
  "kind": "track",
  "title": "Even Flow",
  "subtitle": "Pearl Jam",
  "uri": "spotify:track:...",
  "image_url": "/api/djconnect/image_proxy/...",
  "thumbnail_url": "/api/djconnect/image_proxy/...",
  "played_at": "2026-06-23T12:34:56Z",
  "played_at_label": "12:34"
}
```

Clients should render `items[]` as a compact vertical list with the returned art
or a local fallback icon for the item kind. Do not render these answers as one
large media card, do not reuse artwork from earlier chat bubbles, and do not add
Play Now controls unless the backend explicitly returns `playback_actions[]`.
Spotify's recently-played context may expose only a playlist URI without a
playlist display name; in that case the backend can return a generic title such
as `Spotify playlist` until richer playlist metadata is available.

## Ask DJ Track Insight

Ask DJ supports read-only Track Insight questions through the unified Track
Insight contract. Examples:

- `geef Track Insight voor dit nummer`
- `analyseer dit nummer`
- `tell me about this track`
- `what is special about this song?`
- `give me Track Insight`

These responses use:

- `intent.category: "informational"`
- `intent.intent: "track_insight"`
- `intent.action: "track_insight"`
- `action: "track_insight"`
- `type: "track_insight"`
- `open_screen: "track_insight"`
- `playback_actions: []`
- top-level `track_insight{}` with normalized `track`, `analysis`,
  `music_dna`, `visual_profile` and `cache`

Track Insight is the only Ask DJ current-track insight contract. It must not
expose a parallel response shape or a backend-specific Spotify audio-analysis
command path.

## Ask DJ Playback Without Active Speaker

When a playback or hybrid Ask DJ intent cannot start because Spotify reports no
active output device, the backend should not return a dead-end generic playback
failure if available Spotify devices can be listed. Instead it returns:

- `success: true`
- `error: "no_active_output"`
- `action: "select_output"`
- the original playback intent in `intent{}`
- `playback_actions[]` / `items[]` containing speaker rows with `kind:"output"`
  and `command:"ask_dj_play_request_on_output"`

Each output action carries `value.output_id` and `value.request.text`, so clients
can post it unchanged to `/api/djconnect/command`. The command handler first
sets the selected Spotify output and then replays the original Ask DJ playback
request server-side. Clients must not reconstruct the original prompt locally.

## Ask DJ History

Ask DJ history is server-side and HA-user scoped. App clients synchronize through
`GET /api/djconnect/ask_dj/history?since_revision=<number>` and clear through
`POST /api/djconnect/ask_dj/history/clear`.

`clear_revision` is the authoritative full-clear marker. When a history or clear
response contains a higher `clear_revision` than the client has locally, the
client must wipe its local Ask DJ cache for that HA user/context before merging
new server messages.

Current retention limit: `1000` messages per HA user.

History responses include `history_limit`, `history_trimmed_before` and
`history_trimmed_count`. When trimming occurs, clients should delete local
messages older than `history_trimmed_before` and must not parse retention message
text.

When the last DJConnect Home Assistant config entry is unloaded or removed, HA
clears server-side Music DNA and Ask DJ history. A deleted app/device entry must
not keep using another active DJConnect runtime: requests with a stale
`device_id` or bearer token are rejected instead of falling back to the current
active entry. Clients should treat `401`/`403` and `not_configured`/stale-pairing
responses as a reason to leave paired state and clear local Ask DJ cache for that
HA installation.

## Apple Push Notifications

Apple push notification support is server-side and best-effort. Push is only a
wake/attention signal; clients must always sync through authenticated DJConnect
APIs when opened, especially `GET /api/djconnect/ask_dj/history`.

Endpoints:

- `POST /api/djconnect/push/register`
- `POST /api/djconnect/push/unregister`

Both endpoints require the existing DJConnect bearer token and support only
`ios`, `macos` and `watchos` clients. Home Assistant validates the client
request, hashes the HA user id, and relays registration/unregistration to the
central `djconnect-api` push relay. Home Assistant does not persist APNs tokens
and never requires the APNs provider `.p8` key.

Register payload:

```json
{
  "device_id": "djconnect-ios-...",
  "client_type": "ios",
  "push_token": "...",
  "push_environment": "sandbox",
  "app_bundle_id": "dev.djconnect.app",
  "app_version": "3.2.5",
  "locale": "nl-NL",
  "notification_categories": ["ask_dj_response", "ask_dj_confirm", "playback_change"]
}
```

Unregister payload:

```json
{
  "device_id": "djconnect-ios-...",
  "client_type": "ios",
  "push_token": "..."
}
```

Registration responses include `push_supported`, `push_registered` and, when
registered, `push_environment`. Status/capability responses may include
`push_supported`, `push_registered`, `push_environment` and a redacted
`last_push_error` summary.

Home Assistant also exposes `djconnect.test_apns_push` as a developer diagnostic
service. By default it is a dry-run and does not contact APNs or the central
relay. With `send:true`, it attempts one privacy-safe test event through
`POST /v1/push/event`. Input fields are:

- `device_id`, optional; defaults to the paired runtime device id.
- `client_type`, optional; defaults to the paired runtime client type.
- `event_type`, optional; default `ask_dj_confirm`.
- `user_id`, optional; uses the service call context user id when omitted.
- `send`, optional boolean; default `false`.
- `explicit_user_request`, optional boolean; default `true`.

Diagnostic responses are intentionally redacted and must not include APNs tokens,
bearer tokens, bootstrap proofs, `djci_` token values, authorization headers,
raw prompts, raw audio, Ask DJ history or Music DNA dumps:

```json
{
  "success": false,
  "send_requested": true,
  "event_type": "ask_dj_confirm",
  "device_id": "djconnect-macos-ABCDEFGHIJKL",
  "client_type": "macos",
  "user_id_provided": true,
  "explicit_user_request": true,
  "central_api_configured": false,
  "ha_install_id_present": true,
  "install_token_present": false,
  "bootstrap_proof_present": false,
  "decision": {"send": true},
  "push_statuses": [
    {
      "device_id": "djconnect-macos-ABCDEFGHIJKL",
      "client_type": "macos",
      "push_registered": false,
      "push_environment": null,
      "last_push_error": "missing_bootstrap_proof"
    }
  ],
  "sent": 0,
  "error": "missing_bootstrap_proof"
}
```

Expected diagnostic error reasons include `missing_bootstrap_proof`,
`missing_install_token`, `push_relay_unavailable`, `rate_limited`,
`client_recently_active`, `event_not_pushable` and `not_explicit_user_request`.

The HACS integration only stores central API settings scoped to one Home
Assistant installation:

- `api_base_url`, default `https://api.djconnect.dev`
- `ha_install_id`, generated once and kept stable for the HA installation
- `djconnect_install_token`, a secret per-install token with prefix `djci_`

Home Assistant obtains the install token automatically by calling
`POST /v1/install/token` with the generated `ha_install_id`, non-sensitive
integration metadata and a short-lived pairing/bootstrap proof supplied by an
Apple push client (`ios`, `macos` or `watchos`). HACS never calls the token endpoint with a
global secret and no longer attempts blind/public token minting without a proof.
Users do not need to see, copy or enter the token. Push relay calls use
`Authorization: Bearer <djci_install_token>` and include the matching
`ha_install_id`. HACS must never contain a global relay secret, APNs provider
`.p8` key, APNs private key or Cloudflare secret. When no bootstrap proof is
available yet or the central API is temporarily unavailable, push stays disabled
and normal Ask DJ flows continue; the next central API use can retry token
bootstrap after an Apple client supplies a fresh proof. ESP32, Raspberry Pi, Windows and
Assist-agent-only entries do not require this proof because they do not use APNs
push. The central
`djconnect-api` service owns proof validation, APNs provider-token auth, topics,
sandbox/production selection, delivery retries and invalid-token handling. Token
rotation uses `POST /v1/install/rotate` with the current install token and Home
Assistant replaces the locally stored token only after a successful response.
Users should never paste install tokens or logs containing secrets into issues.

The central API also exposes operator-only endpoints for the website/admin
surface. These endpoints require server-side operator auth using
`DJCONNECT_RELAY_SECRET` and explicitly reject per-install `djci_...` tokens:

- `GET /v1/admin/registrations`: privacy-safe Apple device registration
  overview. It returns hashed/prefixed install and device identifiers plus
  operational metadata only; it never returns raw APNs tokens, ciphertext,
  nonces, relay secrets, prompts, responses or chat history.
- `POST /v1/operator/install-token/revoke`: disables one compromised
  per-install token by `ha_install_id` plus central API token ID. It never
  accepts raw `djci_...` token material from the browser and never issues a
  replacement token.

The DJConnect website operator UI must call central operator endpoints only via
server-side Pages Functions. `DJCONNECT_RELAY_SECRET` must never be present in
browser bundles, static HTML, logs, screenshots or public fixtures.

The central API stores APNs tokens encrypted at rest with
`APNS_TOKEN_ENCRYPTION_KEY`. Planned key rotation requires the operator runbook
in `pcvantol/djconnect-api/OPERATOR_RUNBOOK.md`; the current API runtime uses
one active encryption key, so zero-downtime rotation requires temporary
dual-key/backfill tooling before replacing the secret.

Push payloads are deliberately small and generic. They must not contain secrets,
Spotify tokens, Home Assistant tokens, raw prompts, raw LLM context, full memory,
full history or long/raw assistant responses. Default pushable events are only:

- `ask_dj_response`: after an explicit user Ask DJ request and after server-side
  history has advanced.
- `ask_dj_confirm`: when the Ask DJ response contains `confirmation_actions` and
  waits for a user choice.

DJConnect does not push for `track_change`, `playback_change`, `queue_change`,
`volume_change`, `mood_change`, `idle_suggestion`, ambient/system messages,
status refreshes, Spotify progress updates or ordinary current-track changes.
`playback_change` may exist as a future relay category but is default disabled
in the HACS integration.

If a client status payload reports usable foreground/recent-active state, HA
suppresses Ask DJ pushes back to that active client. HA rate-limits Ask DJ push
events per HA user and device/client to at most one push per 30 seconds and five
pushes per ten minutes. HA sends only the central API event payload below to
`POST /v1/push/event`; the central API is responsible for APNs payload
construction.

Central API event payload shape for `ask_dj_response`:

```json
{
  "ha_install_id": "ha_...",
  "ha_user_hash": "...",
  "event_type": "ask_dj_response",
  "open_target": "ask_dj",
  "history_revision": 123,
  "client_message_id": "client-1",
  "client_types": ["ios", "macos", "watchos"]
}
```

Central API event payload shape for `ask_dj_confirm`:

```json
{
  "ha_install_id": "ha_...",
  "ha_user_hash": "...",
  "event_type": "ask_dj_confirm",
  "open_target": "ask_dj",
  "history_revision": 124,
  "client_types": ["ios", "macos", "watchos"]
}
```

## Playback Confirmation

If Ask DJ proposes music from a contextual follow-up, playback must still start only
after confirmation via `playback_actions[]` / `confirmation_actions[]` and
`command:"ask_dj_followup_response"`.
