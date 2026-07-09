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
`POST /api/djconnect/v1/pair`. Home Assistant generates the app pairing code. The
iPhone/iPad app pairs by scanning a QR/deep-link payload:

```text
djconnect://pair?ha_url=<local-ha-url>&pair_code=<code>&client_type=ios&pair_path=/api/djconnect/v1/pair
```

Apple Watch pairs through the iPhone/iPad proxy: the iPhone/iPad scans the Watch
QR/deep-link payload and forwards the pairing material to the paired Watch, which then uses
`client_type=watchos` and its own `djconnect-watchos-*` device id. The Watch must
not require manual HA URL entry:

```text
djconnect://pair?ha_url=<local-ha-url>&pair_code=<code>&client_type=watchos&pair_path=/api/djconnect/v1/pair
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

Client contract fixtures are exported from `examples/client_contracts/` for
Apple, Raspberry Pi and Windows client tests. Use
`python3 tools/export_client_contracts.py --output <client-fixture-dir>` to copy
the current golden payloads. The source manifest is named
`contract_manifest.json` so Home Assistant hassfest does not confuse it with an
integration manifest; the export tool still writes it to client repos as
`manifest.json`.

```json
{
  "id": 1,
  "type": "djconnect/capabilities"
}
```

A supporting server returns a successful result with
`websocket_supported:true`, `transports.websocket:true` and
`commands[]` containing supported DJConnect websocket message types. The same
response also includes coarse `features{}` flags and `fallbacks{}` hints. Clients
must feature-detect these fields rather than parse Home Assistant integration
versions, and must fall back to HTTP or hide optional controls if a needed
websocket command is missing, errors, times out or reports unsupported
capabilities.

Example capability fallback block:

```json
{
  "features": {
    "music_dna": true,
    "music_discovery": true,
    "music_discovery_feedback": true
  },
  "fallbacks": {
    "music_discovery": {
      "available": true,
      "preferred_transport": "websocket",
      "http_paths": {
        "feed": "/api/djconnect/v1/music_discovery",
        "refresh": "/api/djconnect/v1/music_discovery/refresh",
        "play": "/api/djconnect/v1/music_discovery/play"
      },
      "missing_behavior": "use_http_or_hide_feature"
    },
    "music_discovery_feedback": {
      "available": true,
      "preferred_transport": "websocket",
      "http_path": "/api/djconnect/v1/music_discovery/feedback",
      "missing_behavior": "hide_negative_feedback_controls"
    }
  }
}
```

Send commands with the same semantic payload used for
`POST /api/djconnect/v1/command`:

```json
{
  "id": 2,
  "type": "djconnect/command",
  "device_id": "djconnect-ios-XXXXXXXXXXXX",
  "client_type": "ios",
  "client_id": "djconnect-ios-XXXXXXXXXXXX",
  "device_name": "Peter's iPhone/iPad",
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
`/api/djconnect/v1/command`. Chat clients should still prefer
`POST /api/djconnect/v1/ask_dj/message` for normal text chat because that endpoint
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
`POST /api/djconnect/v1/ask_dj/message`: it appends server-side history, returns
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
`POST /api/djconnect/v1/ask_dj/idle_suggestion`: it appends the server-generated
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
`POST /api/djconnect/v1/track_insight`. If `title`/`artist` are omitted, the
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

The response shapes match `POST /api/djconnect/v1/music_dna/profile`,
`/settings` and `/clear`. HTTP remains the canonical fallback.
Music DNA import/export is intentionally HTTP-only; clients should not expect
`djconnect/music_dna/export` or `djconnect/music_dna/import` websocket commands
in capabilities.

Clients should treat websocket failures as transport failures, not pairing
failures. On disconnect, auth error, HA websocket error, DJConnect websocket
capability miss, timeout or protocol mismatch, immediately retry the user action
through HTTP and reconnect the websocket later with backoff. Suggested client
timeouts are about 2 seconds for short playback controls, 5 seconds for
status/list requests and the existing longer Ask DJ/action timeout for commands
that already wait on backend work. Never log HA auth tokens, DJConnect device
tokens, authorization headers, raw prompts, raw audio, Ask DJ history or Music
DNA while diagnosing websocket transport state.

## VibeCast Feed

Apple clients can poll `GET /api/djconnect/v1/vibecast` for a small live feed of
track, artist, album, genre, trivia, listening-tip, mood, production, history or
system bubbles around the current backend playback context. The route uses the
same paired DJConnect device token and canonical identity fields as other app
client routes. Supported client types are `ios`, `macos` and `watchos`.

VibeCast is a premium-ready first-class DJConnect platform feature for both
macOS and iOS, with the same backend contract and functionally equivalent
experience on both platforms. `client_type:"macos"` and `client_type:"ios"` use
the same endpoint, response contract, item kinds, structured text segment types,
disabled reasons and polling/cache semantics. The backend must not treat macOS
and iOS differently for content quality, entitlement, fact generation, cache,
TTL, revision or current-track resolution. Platform differences should be
presentation- or capability-driven only, such as screen space, hover/focus,
compact layout or reported render capabilities. If a render capability such as
`magnify` is unavailable, clients should gracefully degrade that segment type or
the backend can return equivalent safe fallback segments without changing the
meaning of the item.

Clients should send identity and rendering metadata through query parameters or
existing headers where available: `device_id`, `device_name`, `client_id`,
`client_type`, app version/build, locale/language, timezone and supported
render capabilities such as `bold`, `emphasis`, `magnify`, `accent` and
`emoji_safe`.

Successful responses include `enabled:true`, `revision`, `ttl_seconds`,
`poll_after_seconds`, a backend-neutral `context` and `items[]`. Polling is the
current transport; future websocket or push delivery can reuse the same response
shape without changing client rendering.

When genre metadata is known, `context.genre_badge` contains the first
backend-provided genre as a compact badge hint. Clients should render
`genre_badge.label` as a small badge in the top-right/top-trailing corner of the
VibeCast surface and may keep `genre_badge.genre` as the canonical genre value.
If `genre_badge` is omitted, clients should simply hide the badge.

When the selected backend can provide artist artwork, VibeCast includes a
proxied `context.artist_image_url` and mirrors it on the `artist_fact` item as
`image_url`/`thumbnail_url` with `image_alt` and `image_source`. The URL always
uses DJConnect's image proxy path, so clients should load the proxied
`/api/djconnect/v1/image_proxy/...` URL rather than a direct Spotify, Wikipedia
or catalog URL. If no artist image is available, those fields are omitted.

Canonical item kinds are `track_fact`, `artist_fact`, `album_fact`,
`genre_context`, `trivia`, `listening_tip`, `mood_context`,
`production_note`, `history_note` and `system`. Clients should render unknown
future kinds with the same safe text renderer and no provider-specific behavior.

VibeCast text is structured rich text, never HTML or Markdown:

```json
[
  { "type": "emoji", "value": "♪ ♫ " },
  { "type": "text", "value": "This track rides on " },
  { "type": "strong", "value": "space and pulse" },
  { "type": "text", "value": "." }
]
```

Allowed segment types are `text`, `strong`, `emphasis`, `magnify`, `accent` and
`emoji`, and `line_break`. When clients advertise `emoji_safe`, VibeCast bubbles
may include one short `emoji` segment with 1-3 decorative music/vibe symbols;
clients that do not advertise `emoji_safe` receive text-only structured
segments. Clients must ignore unknown fields and must not display raw
provider, decoding or generative errors. Disabled responses always remain JSON,
for example `enabled:false`, `reason:"no_active_playback"` and empty `items[]`.
Known reasons include `feature_disabled`, `premium_unavailable`,
`no_active_playback`, `playback_inactive`, `unknown_track`,
`unsupported_backend`, `provider_unavailable`,
`generative_provider_unavailable`, `rate_limited`, `cache_failure`,
`unauthorized`, `invalid_client_type`, `client_type_mismatch` and
`privacy_disabled`.

Generated VibeCast copy is deliberately cautious. The backend may ask the
configured Home Assistant conversation agent for three short bubbles using the
current track title, artist, album and genres: one trivia/fact, one concrete
listening tip and one mood/texture line. When that succeeds, items use
`source.kind:"conversation"`; when the backend falls back to local
metadata-shaped copy, `source.kind:"generated"`. `source.confidence` is usually
`medium`; clients should present those bubbles as playful context, not as
verified biographies, chart claims, rights/sample claims or personal artist
details.

Example success:

```json
{
  "enabled": true,
  "revision": 12,
  "ttl_seconds": 45,
  "poll_after_seconds": 20,
  "context": {
    "track_id": "provider-or-stable-track-id",
    "title": "Song Title",
    "artist": "Artist Name",
    "album": "Album Name",
    "genres": ["melodic techno"],
    "genre_badge": {
      "label": "melodic techno",
      "genre": "melodic techno",
      "placement": "top_trailing"
    },
    "artist_image_url": "/api/djconnect/v1/image_proxy/...",
    "music_backend": "music_assistant",
    "music_backend_name": "Music Assistant",
    "music_backend_revision": 2
  },
  "items": [
    {
      "id": "stable-or-generated-id",
      "kind": "track_fact",
      "tone": "playful",
      "priority": 50,
      "display_seconds": 8,
      "placement_hint": "side",
      "text": [
        { "type": "text", "value": "This track rides on " },
        { "type": "strong", "value": "space and pulse" },
        { "type": "text", "value": "." }
      ],
      "source": {
        "kind": "generated",
        "confidence": "medium"
      }
    },
    {
      "id": "stable-or-generated-id",
      "kind": "artist_fact",
      "image_url": "/api/djconnect/v1/image_proxy/...",
      "thumbnail_url": "/api/djconnect/v1/image_proxy/...",
      "image_alt": "Artist Name artist image",
      "image_source": "spotify",
      "text": [
        { "type": "text", "value": "Artist Name keeps the mix expressive." }
      ],
      "source": {
        "kind": "generated",
        "confidence": "medium"
      }
    }
  ],
  "cache": {
    "hit": false
  }
}
```

Example disabled response:

```json
{
  "enabled": false,
  "reason": "no_active_playback",
  "ttl_seconds": 30,
  "poll_after_seconds": 30,
  "items": []
}
```

## Ask DJ Mood Zones

iOS, macOS and watchOS clients send `mood` as an optional integer-like value from
`0` to `100`. The Home Assistant integration accepts the value on:

- `POST /api/djconnect/v1/ask_dj/message`
- `POST /api/djconnect/v1/ask_dj/idle_suggestion`
- `POST /api/djconnect/v1/voice`
- `POST /api/djconnect/v1/status`

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
status/debug context. When runtime mood is available, the mood zone chooses the
effective DJ voice profile: `chill -> late_night`, `groove -> classic_radio`,
`energy -> energy` and `party -> clean_host`. The configured backend
`voice_profile` is fallback only when a request has no valid mood. Responses do
not need to echo mood fields.

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
- `POST /api/djconnect/v1/track_insight` with Home Assistant auth.
- Home Assistant service `djconnect.track_insight`, which fires
  `djconnect_track_insight` with the normalized result.

Request fields may include `title`, `artist`, `album`, `entity_id`,
`player_id`, `music_backend`, `force_refresh`, `locale`, `language`, `mood`,
`music_dna_key`, `include_visual_profile` and `include_raw_response`. Clients
may also send nested `track`, `playback` or `media` objects with aliases such as
`track_name`, `artist_name`, `album_name`, `media_title`, `media_artist`,
`album_image_url`, `image_url` and optional `genres[]`. If `title` and `artist`
are present, the backend analyzes that explicit track; otherwise it resolves
Now Playing through the music backend/status context.

Responses use normalized TrackInsight JSON with `id`, `created_at`, `source`,
`language`, optional `mood_context`, `track`, `analysis`, `visual_profile` and
`cache`. `track` may include deterministic `genres[]` from playback or Spotify
artist metadata. `analysis.genre` and `analysis.subgenre` are the primary genre
display fields; clients can fall back to `track.genres[]`. Numeric analysis and
visual values are normalized from `0.0` to `1.0`. Track Insight does not include
measured timing or pitch-key cards and does not include a Music DNA per-track
match score, label or reason; Music DNA remains a separate opt-in
profile/context feature. `visual_profile` is deterministic and is only a
rendering hint; clients remain responsible for final visualization and must not
expect server-generated images or video. Structured errors use `error`/`message`,
for example `no_track_playing`.

## Music DNA Profile Contract

Music DNA is a first-class opt-in feature. Clients must not assume it is
enabled. Home Assistant only builds Music DNA knowledge after the resolved
user/client context has explicitly opted in, and disabling Music DNA clears
learned knowledge and stops future collection. Clearing Music DNA is always
available and preserves the current opt-in setting; if it remains enabled, new
knowledge starts building again from an empty profile.

HTTP endpoints use the regular DJConnect bearer token, `device_id` and
canonical `client_type` identity contract:

- `POST /api/djconnect/v1/music_dna/profile`
- `POST /api/djconnect/v1/music_dna/settings`
- `POST /api/djconnect/v1/music_dna/clear`
- `POST /api/djconnect/v1/music_dna/export`
- `POST /api/djconnect/v1/music_dna/import`

`/music_dna/settings` accepts:

```json
{
  "device_id": "djconnect-ios-...",
  "client_type": "ios",
  "enabled": true
}
```

`/music_dna/profile` and `/music_dna/clear` accept the same identity fields and
optional `music_dna_key`, `language`, `locale` and realtime `mood`. Profile
responses are structured for the Music DNA screen:

`/music_dna/export` accepts the same identity/auth fields and returns a stable
export envelope built by Home Assistant. Clients should use this route for JSON
downloads instead of constructing the envelope locally from `/profile`.
Export is HTTP-only and is not advertised through
`djconnect/capabilities.commands[]`.

```json
{
  "success": true,
  "format": "djconnect.music_dna.export",
  "schema_version": 1,
  "exported_at": "2026-07-04T19:30:00Z",
  "exported_by_client_type": "ios",
  "app_version": "3.2.x",
  "profile": {
    "success": true,
    "music_dna_key": "user:abc123",
    "enabled": true,
    "generation": 12,
    "updated_at": "2026-07-04T19:30:00Z",
    "profile": {"favorite_artists": [{"name": "The xx"}]},
    "sources": []
  }
}
```

`/music_dna/import` accepts the same identity/auth fields plus a previously
exported Music DNA profile response. It is an overwrite, not a merge, and it
only succeeds when Music DNA is already enabled on the resolved server-side
scope. Import must not create consent or opt-in by itself. If the scope is not
enabled, Home Assistant returns HTTP `409` with
`error:"music_dna_not_enabled"`. On success, Home Assistant increments
`generation`, sets `updated_at`/`imported_at` internally to the import time and
returns the normal profile response shape.
Import is HTTP-only and is not advertised through
`djconnect/capabilities.commands[]`.

```json
{
  "identity": {
    "device_id": "djconnect-ios-...",
    "client_type": "ios",
    "device_name": "iPhone"
  },
  "music_dna_key": "user:abc123",
  "language": "nl",
  "profile": {
    "success": true,
    "music_dna_key": "user:abc123",
    "enabled": true,
    "generation": 12,
    "updated_at": "2026-07-04T19:30:00Z",
    "profile": {"favorite_artists": [{"name": "The xx"}]},
    "sources": []
  }
}
```

Clients may also wrap the profile response in an export envelope:

```json
{
  "format": "djconnect.music_dna.export",
  "schema_version": 1,
  "exported_at": "2026-07-04T19:30:00Z",
  "exported_by_client_type": "ios",
  "app_version": "3.2.x",
  "profile": {
    "success": true,
    "music_dna_key": "user:abc123",
    "enabled": true,
    "generation": 12,
    "updated_at": "2026-07-04T19:30:00Z",
    "profile": {"favorite_artists": [{"name": "The xx"}]},
    "sources": []
  }
}
```

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
    "playtime": {
      "total_seconds": 5400,
      "total_hours": 1.5,
      "formatted_total": "1u 30m",
      "top_artists": [
        {"name": "The xx", "seconds": 3600, "hours": 1.0, "formatted": "1u"},
        {"name": "Bon Iver", "seconds": 1200, "hours": 0.33, "formatted": "20m"},
        {"name": "Radiohead", "seconds": 600, "hours": 0.17, "formatted": "10m"}
      ],
      "top_albums": [
        {"name": "xx", "seconds": 2400, "hours": 0.67, "formatted": "40m"}
      ]
    },
    "listening_rhythm": {
      "sample_count": 6,
      "top_daypart": "avond",
      "top_weekday": "vrijdag",
      "dayparts": [{"daypart": "avond", "count": 4, "percent": 66.7}],
      "weekdays": [{"weekday": "vrijdag", "count": 3, "percent": 50.0}]
    },
    "mood_mix": {
      "sample_count": 3,
      "average": 57,
      "top_zone": "groove",
      "zones": [{"zone": "groove", "count": 2, "percent": 66.7}]
    },
    "repeat_magnets": {
      "eligible": true,
      "items": [
        {"kind": "artist", "name": "The xx", "count": 3},
        {"kind": "album", "name": "xx", "seconds": 2400, "formatted": "40m"}
      ]
    },
    "explicit_positives": {
      "eligible": true,
      "signal_count": 2,
      "favorite_tracks": [{"kind": "favorite_track", "title": "Far Behind", "artist": "Candlebox"}],
      "accepted_recommendations": [{"kind": "accepted_recommendation", "title": "Intro", "subtitle": "The xx"}]
    },
    "taste_anchors": {
      "eligible": true,
      "items": [
        {"kind": "artist", "name": "The xx", "play_count": 3, "seconds": 3600, "formatted": "1u"},
        {"kind": "genre", "name": "ambient"}
      ]
    },
    "recent_tracks": [{"title": "Intro", "artist": "The xx"}],
    "recent_favorite_tracks": [{"title": "Far Behind", "artist": "Candlebox"}],
    "top_tracks_by_range": {},
    "top_artists_by_range": {},
    "snapshot_history": [
      {
        "captured_at": "2026-06-29T12:00:00+00:00",
        "source": "spotify",
        "sources": ["spotify_recently_played", "spotify_top_tracks_short_term"],
        "recent_artists": ["The xx"],
        "top_artists": [{"name": "The xx", "uri": "spotify:artist:..."}],
        "top_tracks": [{"title": "Intro", "artist": "The xx", "uri": "spotify:track:..."}],
        "inferred_genres": ["ambient"],
        "recent_track_count": 20
      }
    ],
    "mood": {"value": 65, "zone": "energy", "prompt_hint": "..."},
    "time_patterns": [],
    "recommendation_signals": [],
    "blocked_artists": [],
    "blocked_items": [],
    "discovery_feedback": {
      "eligible": true,
      "accepted_count": 1,
      "negative_count": 1,
      "accepted_items": [
        {
          "kind": "track",
          "title": "Midnight City",
          "subtitle": "M83",
          "uri": "spotify:track:...",
          "reason": "Past bij je recente synthpop.",
          "source": "music_discovery_play",
          "section_id": "new_for_you",
          "quality_score": 91,
          "quality_band": "high"
        }
      ],
      "blocked_artists": [{"kind": "artist", "name": "Coldplay", "reason": "hide_artist"}],
      "blocked_items": []
    },
    "privacy_dashboard": {
      "enabled": true,
      "scope": "ha_user_or_client",
      "stores_raw_audio": false,
      "stores_oauth_tokens": false,
      "stores_full_prompts": false,
      "active_source_count": 3,
      "data_sources": [
        {"id": "recent_tracks", "label": "Recent DJConnect tracks", "enabled": true, "count": 3},
        {"id": "spotify_listening_profile", "label": "Spotify recent/top profile snapshots", "enabled": true, "count": 1, "last_updated": "2026-06-29T12:00:00+00:00"},
        {"id": "recommendation_feedback", "label": "Recommendation feedback", "enabled": true, "count": 2}
      ],
      "retention": {"recent_tracks_max": 20, "chat_facts_max": 20, "snapshot_history_max": 12},
      "controls": {
        "clear_supported": true,
        "export_supported": true,
        "import_supported": true,
        "opt_out_preserves_clear": true
      }
    },
    "last_profile_refresh": "2026-06-29T12:00:00+00:00",
    "consent_updated_at": "2026-06-29T11:50:00+00:00"
  },
  "sources": [{"source": "djconnect_music_dna", "kind": "source", "title": "Music DNA"}]
}
```

When Music DNA is disabled, `enabled:false` and `profile:{}` are returned.
Clients should show an opt-in state instead of deriving a fake profile from
local Track Insight history.

Music DNA is server-authoritative. Clients should render backend-provided
summary, favorite genres, favorite artists, total play time, top artists/albums
by play time, listening rhythm, mood mix, recent tracks, energy/mood profile,
repeat magnets, explicit positives, taste anchors, recent favorite tracks, taste
direction, compact snapshot history, based-on values and update timestamps where present. Clients must not
calculate favorite artists, favorite genres, play time, listening rhythm, mood
mix, repeat magnets, explicit positives, taste anchors, favorite history,
snapshot trends or taste direction locally from Ask DJ history or local playback
cache.

`privacy_dashboard` is a compact transparency block for Music DNA settings and
dashboard screens. It lists which backend signal sources currently contribute,
rough counts, retention limits and supported controls. It must never include
OAuth tokens, bearer tokens, raw audio, full prompts or full playback history.

`snapshot_history` is a bounded backend summary of recent Spotify listening
profile refreshes, not raw playback history. It keeps only compact timestamped
top artists, top tracks, recent artist names, inferred genres, source labels and
counts, currently capped to the most recent 12 snapshots.

`discovery_feedback` is the compact bridge from Music Discovery back into Ask
DJ. It summarizes accepted Discovery/Ask DJ recommendations and negative
Discovery feedback so future Ask DJ recommendations can respect what the user
played, hid or marked as not fitting. Clients must send feedback through the
backend endpoints and must not build separate local taste rules.

Music DNA dashboard fields are optional. Empty legacy placeholders such as empty
arrays or empty objects are omitted; clients should hide absent blocks without a
separate empty state. Conditional insight blocks expose `eligible:false` and a
stable `reason` when there are not enough reliable compact signals. Clients
should hide those blocks instead of showing empty charts. Current reasons include
`insufficient_repeat_signals`, `no_explicit_positive_signals` and
`insufficient_anchor_signals`.

Home Assistant developer actions mirror the HTTP contract:

- `djconnect.music_dna_profile`
- `djconnect.set_music_dna_enabled`
- `djconnect.clear_music_dna`

The conversation/AI tool allowlist also exposes read-only
`djconnect_music_dna_profile` so the DJConnect conversation agent can inspect
the same structured profile without mutating playback or consent.

## Music Discovery Contract

Music Discovery is a first-class client surface for iOS, macOS and watchOS. It
uses Music DNA as its primary recommendation input and is disabled until Music
DNA is enabled for the resolved user/client context. Clients must not generate
recommendations or reasons locally.

HTTP endpoints:

- `GET /api/djconnect/v1/music_discovery`
- `POST /api/djconnect/v1/music_discovery/refresh`
- `POST /api/djconnect/v1/music_discovery/play`
- `POST /api/djconnect/v1/music_discovery/feedback`

WebSocket equivalents, when advertised by `djconnect/capabilities.commands[]`:

- `djconnect/music_discovery/feed`
- `djconnect/music_discovery/refresh`
- `djconnect/music_discovery/play`
- `djconnect/music_discovery/feedback`

When Apple push is registered and Music DNA is enabled, Home Assistant may send
one daily `music_discovery_ready` wake/sync hint around 08:00 local HA time. The
push deep-links to the Ontdek/Music Discovery surface and tells clients to
refresh the Music Discovery backend feed; the APNs payload never contains
recommendation contents. Clients should open the Ontdek page and call
`POST /api/djconnect/v1/music_discovery/refresh` or the equivalent websocket
refresh command, falling back to the regular feed endpoint if refresh is
rate-limited or unavailable.

Home Assistant also refreshes Music Discovery server-side about once per hour
for eligible runtimes. When Music DNA is enabled, this refresh updates compact
Music DNA listening-profile data from Spotify recently-played/top tracks/top
artists, then rebuilds the Music Discovery cache. Recently played tracks are
used as seeds/context only; they must not be surfaced as raw Discovery cards.
The feed cache is also context-aware: when compact Music DNA signals change
between requests, for example new recent-track identities, changed top
artist/track profile data, mood changes, accepted recommendations, blocked
items/artists or Discovery play/feedback signals, Home Assistant can rebuild the
feed even while the normal TTL is still valid. Clients should simply refetch the
feed after meaningful user actions and render the returned revision.

When Home Assistant debug logging is enabled for `custom_components.djconnect`,
the HTTP handlers emit redacted diagnostics prefixed with
`DJConnect Music Discovery`. These lines identify feed/refresh/play requests,
auth failures, `music_dna_disabled`, cache hits, refresh rate limits and
generated section/item counts. They include client type and device id but never
tokens, raw prompts or full request payloads.

Disabled response:

```json
{
  "success": true,
  "enabled": false,
  "reason": "music_dna_disabled",
  "sections": []
}
```

Feed responses are cached per Music DNA key for about one day. User-triggered
refresh may be rate-limited and returns the current cached feed when limited.
Contextual server refreshes are automatic and do not require clients to decide
which Music DNA fields changed:

```json
{
  "success": true,
  "enabled": true,
  "revision": 12,
  "generated_at": "2026-07-04T12:00:00+00:00",
  "ttl_seconds": 86400,
  "source": "music_dna",
  "music_dna_key": "user:abc123",
  "sections": [
    {
      "id": "new_for_you",
      "title": "Nieuw voor jou",
      "items": [
        {
          "id": "disc-123",
          "kind": "track",
          "title": "Fresh Discovery",
          "subtitle": "New Artist",
          "uri": "spotify:track:...",
          "image_url": "/api/djconnect/v1/image_proxy/...",
          "reason": "Omdat je vaak naar The xx luistert en ambient in je Music DNA zit.",
          "reason_sources": ["spotify_recommendations", "djconnect_music_dna", "music_dna_artists", "music_dna_genres"],
          "confidence": "medium",
          "quality_score": 88,
          "quality_band": "high",
          "quality_factors": ["spotify_recommendation", "fresh_candidate", "favorite_artist_match"]
        }
      ]
    },
    {
      "id": "rediscover",
      "title": "Opnieuw ontdekken",
      "items": [
        {
          "id": "disc-456",
          "kind": "track",
          "title": "Top Track",
          "subtitle": "The xx",
          "uri": "spotify:track:...",
          "reason": "Een bekende favoriet uit je Music DNA om opnieuw op te pakken.",
          "reason_sources": ["djconnect_music_dna", "spotify_top_tracks"],
          "confidence": "medium",
          "quality_score": 70,
          "quality_band": "medium",
          "quality_factors": ["known_favorite", "rediscover"]
        }
      ]
    },
    {
      "id": "artist_spotlight",
      "title": "Artiesten om verder te verkennen",
      "items": [
        {
          "id": "disc-789",
          "kind": "artist",
          "title": "The xx",
          "subtitle": "Artist",
          "uri": "spotify:artist:...",
          "reason": "Artiest die sterk terugkomt in je Music DNA.",
          "reason_sources": ["djconnect_music_dna", "spotify_top_artists"],
          "confidence": "medium",
          "quality_score": 74,
          "quality_band": "medium",
          "quality_factors": ["artist_anchor", "spotify_top_artists"]
        }
      ]
    }
  ]
}
```

Displayed items must have `id`, `kind`, `title`, playable `uri` and a backend
`reason`. If a good backend reason cannot be generated, the backend should not
return the item. Reasons are based on compact Music DNA signals, Spotify profile
seeds and backend recommendation provenance. Prefer specific explanations such
as a favorite artist, genre or recent listening context over generic copy.
`new_for_you` items are generated recommendations; `rediscover` may contain
known favorite tracks from compact Music DNA/top-track profile data; and
`artist_spotlight` may contain artist anchors for further exploration. Raw
Spotify recently-played entries are not a Discovery section unless the backend
explicitly returns such a section in the future. Clients should render one
row/card per unique backend-provided `id` or `uri` and should not hardcode
section ids.

Items may include backend-owned quality metadata: `quality_score` from 0-100,
`quality_band` (`low`, `medium`, `high`) and compact `quality_factors[]`.
The backend uses these values to order items within a section; clients may show
subtle confidence/fit hints but must not calculate or override quality locally.

The backend applies freshness and dedupe filters before returning sections:
known/recent/top/blocked track URIs are excluded from generated new-music rows,
common title variants such as live, remix, radio edit and remaster are collapsed
per artist, album/title overlap is treated as duplicate context, and a section
should avoid overloading the user with too many items from the same artist.
Clients must not attempt to recreate or loosen these filters locally.

Play requests must use the discovery play endpoint instead of generic playback
commands so the backend can record the click as positive Music DNA feedback:

```json
{
  "device_id": "djconnect-ios-...",
  "client_type": "ios",
  "discovery_item_id": "disc-123",
  "section_id": "new_for_you",
  "music_dna_key": "user:abc123"
}
```

Successful play responses include `played:true` and
`music_dna_feedback_recorded:true` when the feedback was stored. The feedback
record keeps the discovery item id, section id, kind, URI, title, reason,
reason sources, optional quality metadata and source `music_discovery_play`; it
does not store raw prompts, tokens or unlimited listening history. Stored
Discovery play feedback is also exposed to Ask DJ through compact Music DNA
context so later recommendations can lean into accepted discoveries.

Negative feedback must use the discovery feedback endpoint, never local client
filtering only. Supported `feedback` values are `not_for_me`, `less_like_this`
and `hide_artist`:

```json
{
  "device_id": "djconnect-ios-...",
  "client_type": "ios",
  "discovery_item_id": "disc-123",
  "section_id": "new_for_you",
  "feedback": "hide_artist",
  "music_dna_key": "user:abc123"
}
```

Successful feedback responses include `music_dna_feedback_recorded:true` when
the compact negative signal was stored. The backend may remove the item from
the cached feed immediately and filters future generated recommendations
against blocked item and artist signals. Ask DJ also receives those compact
negative signals through Music DNA context and should avoid repeating the same
item or artist unless the user explicitly asks for it. Clients may show controls
such as `Niet voor mij`, `Minder hiervan` and `Verberg artiest`, but must send
the backend action and must not maintain their own long-lived blocklist.

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
- `djconnect_music_discovery_feed`
- `djconnect_vibecast_feed`
- `djconnect_music_backend_status`
- `djconnect_recently_played`
- `djconnect_search_music`
- `djconnect_list_outputs`
- `djconnect_build_recommendations`
- `djconnect_prepare_playback_action`
- `djconnect_execute_confirmed_action`

`djconnect_music_discovery_feed` reads the backend-built Music Discovery feed
for the resolved Music DNA context and must not call discovery play, force
refresh or mutate playback. `djconnect_vibecast_feed` reads the same
privacy/premium-gated VibeCast feed exposed to supported app clients and must
not bypass VibeCast feature, privacy, entitlement or client-type gates.
`djconnect_music_backend_status` returns safe selected-backend availability,
capability and target-player metadata without secrets. `djconnect_prepare_playback_action` stores a bounded pending confirmation in
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

`POST /api/djconnect/v1/ask_dj/message` responses may include
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

Assistant messages may include `text_source:"generated"` and
`is_generated_text:true` when Home Assistant's configured conversation agent
created the answer text. Clients should show the generative-answer indicator
from these fields even when the response is text-only. When `audio_url` is
present on `assistant_message`, render the replay/play affordance for that exact
assistant bubble; generated current-track answers such as `wat speelt er` can
include both generated text metadata and a replayable TTS URL.

DJ announcement audio routing is explicit. App clients may send or store
`dj_announcement_output` as one of `client_device`, `both`, `ha_speaker` or
`text_only`; the Home Assistant config/options flow owns the optional
`dj_announcement_speaker_entity_id` and clients must not set the HA entity id.
When no HA speaker is configured, app clients support only `client_device` and
`text_only`. Raspberry Pi supports `text_only` and, when a backend speaker is
configured, `ha_speaker`; it does not expose local client audio. ESP32 keeps the
existing `/api/device/dj_response` device-speaker path and does not use these app
announcement modes.

Responses include an `announcement{}` object when Ask DJ evaluates announcement
delivery:

```json
{
  "announcement": {
    "output": "both",
    "delivery": "both",
    "audio_response_effective": "always",
    "audio_url": "/api/djconnect/v1/tts/token.mp3",
    "audio_type": "mp3",
    "target": {
      "kind": "ha_media_player",
      "entity_id": "media_player.voice_preview",
      "name": "Voice Preview"
    },
    "warnings": []
  }
}
```

For `ha_speaker`, Home Assistant plays the generated TTS server-side on the
configured `media_player` and does not return client-playback `audio_url`. For
`both`, HA plays server-side and also returns `audio_url` for clients that allow
autoplay/replay. For `text_only`, HA skips TTS entirely. Spotify Direct never
pauses, resumes or changes Spotify volume for DJ announcements; the HA speaker
plays separately from Spotify playback.

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
  `POST /api/djconnect/v1/command`. Current-track Ask DJ responses such as
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

Artist track-list questions such as `welke nummers heb je`,
`welke nummers heb je van <artist>` and `more tracks by <artist>` are handled
server-side. If the artist is omitted, the backend may resolve it from the
current playback context or recent Ask DJ history. Successful responses return
`playback_actions[]`/`items[]` rows with `kind:"track"` and Play Now labels; the
client must render those backend rows and must not reinterpret the question as a
style recommendation. Artist matching is tolerant of common textual differences
such as `and` versus `&`.

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
    "image_url": "/api/djconnect/v1/image_proxy/token"
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
    "image_url": "/api/djconnect/v1/image_proxy/token",
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

Discover and Music DNA explanation questions such as `Hoe werkt Discover met
feedback?`, `Refresh my Discover recommendations`, `Wat zegt mijn Music DNA?`
and `welke gegevens bewaart Music DNA over mij?` are read-only. They return
text plus source metadata, never start playback and never mutate Discover or
Music DNA state directly.

Same-title track variant searches such as
`Geef me 10 uitvoeringen van [nummer] door verschillende artiesten`,
`Doe me 10 uitvoeringen door verschillende artiesten van "[nummer]"`,
`Zoek versies van "[nummer]"`, `Toon covers van "[nummer]"`,
`Find versions of "[song]"` and `Give me versions titled [song]` return
`intent.intent:"track_versions_search"`. Ask DJ searches Spotify tracks with
limit 10, keeps only results whose title contains all meaningful words from the
requested title, returns rows plus `kind:"track"` `Play Now` actions, and does
not start playback automatically. Title extraction supports quoted titles or
titles after `van`, `voor`, `of`, `called`, `named` or `titled`.

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

The live runner posts each case to `/api/djconnect/v1/ask_dj/message` with a
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
  "image_url": "/api/djconnect/v1/image_proxy/...",
  "thumbnail_url": "/api/djconnect/v1/image_proxy/...",
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
  `visual_profile` and `cache`

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
can post it unchanged to `/api/djconnect/v1/command`. The command handler first
sets the selected Spotify output and then replays the original Ask DJ playback
request server-side. Clients must not reconstruct the original prompt locally.

## Ask DJ History

Ask DJ history is server-side and HA-user scoped. App clients synchronize through
`GET /api/djconnect/v1/ask_dj/history?since_revision=<number>` and clear through
`POST /api/djconnect/v1/ask_dj/history/clear`. Clients can export the current
bounded server-side history through HTTP-only
`POST /api/djconnect/v1/ask_dj/history/export`; this route is intentionally not a
Home Assistant websocket command.

`clear_revision` is the authoritative full-clear marker. When a history or clear
response contains a higher `clear_revision` than the client has locally, the
client must wipe its local Ask DJ cache for that HA user/context before merging
new server messages.

Clear responses also include `cleared:true`, `ask_dj_clear_required:true` and
`messages:[]`. Clients should clear their local visible chat immediately after a
successful clear response; do not wait for a later history fetch to empty the
UI.

Current retention limit: `1000` messages per HA user.

History responses include `history_limit`, `history_trimmed_before` and
`history_trimmed_count`. When trimming occurs, clients should delete local
messages older than `history_trimmed_before` and must not parse retention message
text.

History export uses the same DJConnect bearer token and identity contract as
history sync. The response is a backend-built envelope:

```json
{
  "success": true,
  "format": "djconnect.ask_dj.history.export",
  "schema_version": 1,
  "exported_at": "2026-07-04T19:30:00Z",
  "exported_by_client_type": "ios",
  "app_version": "3.2.x",
  "user_id": "ha-user",
  "history_revision": 12,
  "clear_revision": 2,
  "history_limit": 1000,
  "history_trimmed_before": null,
  "history_trimmed_count": 0,
  "messages": []
}
```

Export is read-only. It must not include bearer tokens, OAuth tokens,
bootstrap proofs, raw prompts beyond the already persisted bounded chat
messages, raw audio or Music DNA data. Ask DJ history import is not supported.

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
APIs when opened, especially `GET /api/djconnect/v1/ask_dj/history`.

Endpoints:

- `POST /api/djconnect/v1/push/bootstrap`
- `POST /api/djconnect/v1/push/register`
- `POST /api/djconnect/v1/push/unregister`

All endpoints require the existing DJConnect bearer token and support only
`ios`, `macos` and `watchos` clients. Home Assistant validates the client
request, hashes the HA user id, and relays registration/unregistration to the
central `djconnect-api` push relay. Home Assistant does not persist APNs tokens
and never requires the APNs provider `.p8` key.

Bootstrap payload:

```json
{
  "device_id": "djconnect-macos-ABCDEFGHIJKL",
  "client_type": "macos",
  "push_environment": "sandbox",
  "app_bundle_id": "dev.djconnect.mac",
  "app_version": "3.2.36",
  "locale": "nl-NL"
}
```

The legacy `/push/bootstrap` endpoint does not mint local proofs and normally
responds:

```json
{
  "success": false,
  "push_supported": true,
  "push_registered": false,
  "push_environment": "sandbox",
  "error": "bootstrap_proof_unavailable",
  "last_push_error": "bootstrap_proof_unavailable"
}
```

Clients should treat `bootstrap_proof_unavailable` as an instruction to use the
trusted Apple issuer flow. When `/push/register` reports
`missing_bootstrap_proof`, request a central-issued proof from that issuer and
retry registration with `bootstrap_proof` before it expires. Home Assistant does
not locally mint, request or store bootstrap proofs for `/v1/install/token`.
HA/HACS never calls central bootstrap-proof issuer routes and never has relay,
pairing-issuer or APNs provider secrets.

Register payload:

```json
{
  "device_id": "djconnect-ios-...",
  "client_type": "ios",
  "push_token": "...",
  "push_environment": "sandbox",
  "app_bundle_id": "dev.djconnect.app",
  "app_version": "3.2.18",
  "locale": "nl-NL",
  "notification_categories": ["ask_dj_response", "ask_dj_confirm", "playback_change"],
  "bootstrap_proof": "djcboot_..."
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
Clients may send `push_environment: "development"` for Apple development APNs
entitlements; Home Assistant normalizes that to canonical `sandbox` for relay
calls, stored status and registration responses. Production builds must keep
using `push_environment: "production"`.

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

Central API error responses keep the language-neutral `error` code stable.
Clients may send `Accept-Language` or `lang`; the API may include an optional
localized `message` in `en`, `nl`, `de`, `fr` or `es`. `Accept-Language`
quality values are honored across supported languages. Unsupported locales fall
back to the best supported language in the header, or English when none is
present. Clients must make decisions from `error`, not localized message text.

Push payloads are deliberately small and generic. They must not contain secrets,
Spotify tokens, Home Assistant tokens, raw prompts, raw LLM context, full memory,
full history or long/raw assistant responses. Default pushable events are only:

- `ask_dj_response`: after an explicit user Ask DJ request and after server-side
  history has advanced.
- `ask_dj_confirm`: when the Ask DJ response contains `confirmation_actions` and
  waits for a user choice.
- `music_discovery_ready`: once daily around 08:00 local HA time, only when
  Music DNA is enabled, as a generic Ontdek/Music Discovery refresh hint.

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
construction. APNs alert text is selected from the registered client locale when
available. Supported central relay languages are `en`, `nl`, `de`, `fr` and
`es`; unsupported locales fall back to English. APNs payload keys, event values
and `open_target` values are protocol fields and are never localized.

Central API event payload shape for `ask_dj_response`:

```json
{
  "ha_install_id": "ha_...",
  "ha_user_hash": "...",
  "event_type": "ask_dj_response",
  "open_target": "ask_dj",
  "history_revision": 123,
  "client_message_id": "client-1",
  "announcement": {
    "delivery": "both",
    "audio_available": true,
    "speaker_delivery": "attempted"
  },
  "client_types": ["ios", "macos", "watchos"]
}
```

Central API event payload shape for `music_discovery_ready`:

```json
{
  "ha_install_id": "ha_...",
  "event_type": "music_discovery_ready",
  "open_target": "music_discovery",
  "refresh_target": "music_discovery",
  "deeplink": "djconnect://music-discovery",
  "title": "DJConnect",
  "body": "Je nieuwe aanbevelingen staan klaar!",
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
