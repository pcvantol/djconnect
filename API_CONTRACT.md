# DJConnect API Contract

This document summarizes the client-facing DJConnect Home Assistant API contract.
It is intentionally compact; `README.md` remains the full user/developer guide.

## Client Identity

Pairing, status, command, Ask DJ and voice requests use canonical
`client_type` values to distinguish runtimes. Current values are `esp32`, `ios`,
`macos`, `watchos`, `raspberry_pi` and `windows`.

App-like client ids must match their client type prefix and use the first 12
alphanumeric characters of the stable client install id:

- `ios`: `djconnect-ios-XXXXXXXXXXXX`
- `macos`: `djconnect-macos-XXXXXXXXXXXX`
- `watchos`: `djconnect-watchos-XXXXXXXXXXXX`
- `raspberry_pi`: `djconnect-raspberry-pi-XXXXXXXXXXXX`
- `windows`: `djconnect-windows-XXXXXXXXXXXX`

App-like clients may advertise `_djconnect._tcp` mDNS with TXT records including
`device_id`, `client_type`, `device_name`, `local_url`, `version`/`app_version`
and pairing code aliases. Home Assistant treats
`GET /api/device/pairing-info` as authoritative when reachable.

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
suggestions, DJ Memory prompt context, spoken DJ announcement style and
status/debug context. DJ announcement style is not a client or config option:
when runtime mood is available, the mood zone drives the final announcement
tone; otherwise DJConnect uses its hardcoded default announcement style.
Responses do not need to echo mood fields.

Spoken DJ announcements may include one short personal intro line when compact
DJ Memory or explicitly shared smart-home context makes that natural. Temperature
or weather wording is allowed only from entities configured in
`smart_home_context_entities`, for example a shared outdoor temperature sensor.
Clients must not send arbitrary Home Assistant state or local memory for this.

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

- `album`: direct Play Now action for a Spotify album. The action includes a
  Spotify `uri`/`context_uri`, `title`, optional `subtitle`/artist and optional
  proxied `image_url`.
- `output`: Spotify Connect output selection. Render the action as an output row
  or button. Use `label`/`button_label` such as `Activeer`; an already active
  output may use `Actief`.
- `control`: immediate playback control action. Pause/stop responses can return
  `command:"play"` with `label:"Resume"` / `button_label:"Resume"` so clients
  show a Resume button.
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

Speaker/output questions such as `welke speakers zijn er?` or
`wissel van uitvoer` return a short text intro plus one `output` action per
available Spotify Connect device. They must not include stale album art from an
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

Unknown, unsupported or low-confidence informational answers are text-only and
return `images: []`. Clients must not reuse current-track album art for these
fallback responses.

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

## Ask DJ History

Ask DJ history is server-side and HA-user scoped. App clients synchronize through
`GET /api/djconnect/ask_dj/history?since_revision=<number>` and clear through
`POST /api/djconnect/ask_dj/history/clear`.

Current retention limit: `1000` messages per HA user.

History responses include `history_limit`, `history_trimmed_before` and
`history_trimmed_count`. When trimming occurs, clients should delete local
messages older than `history_trimmed_before` and must not parse retention message
text.

When the last DJConnect Home Assistant config entry is unloaded or removed, HA
clears server-side DJ Memory and Ask DJ history. A deleted app/device entry must
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
  "app_version": "3.1.84",
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
bearer tokens, bootstrap proofs or `djci_` token values:

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

## Smart-Home Context

Ask DJ may use selected Home Assistant entity state as read-only context for
future smart-home aware system messages, such as weather, room temperature,
appliance-ready or scene-changed prompts.

Only entities explicitly configured in `smart_home_context_entities` are exposed
to Ask DJ. DJConnect must not expose arbitrary HA states and must not mutate
smart-home devices from this context.

If Ask DJ proposes music after a smart-home event, playback must still start only
after confirmation via `playback_actions[]` / `confirmation_actions[]` and
`command:"ask_dj_followup_response"`.
