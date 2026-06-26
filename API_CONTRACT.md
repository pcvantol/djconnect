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
The help list includes exact prompt examples that are covered by
`examples/ask_dj_e2e_cases.json`; for example `Analyseer dit nummer` maps to
the read-only `technical_track_analysis` intent.

Personal memory questions such as `wat weet je nu over mij?`, `wat staat er in
mijn DJ Memory?` and `what do you know about me?` return
`intent.intent:"personal_memory_summary"` and `action:"memory_summary"`. The
response is DJ Memory-only: `sources[]` contains `djconnect_memory`, `images`
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

## Ask DJ Technical Track Analysis

Ask DJ supports read-only live technical analysis questions for the currently
playing Spotify track. Examples:

- `geef een technische track analyse van dit nummer`
- `analyseer dit nummer`
- `wat is de bpm en opbouw van deze track?`
- `analyseer intro, coupletten en refrein`
- `give me a technical analysis of this song`

These responses use:

- `intent.category: "informational"`
- `intent.intent: "technical_track_analysis"`
- `intent.action: "track_analysis"`
- `action: "track_analysis"`
- `playback_actions: []`
- `sources[]` including `spotify_playback_context` and, when available,
  `spotify_audio_features` / `spotify_audio_analysis`

The response may include top-level `analysis{}` and display-ready `items[]`
with `kind:"technical_metric"` or `kind:"arrangement"` for values such as BPM,
key, energy, danceability and detected section count. If Spotify audio features
or deep audio analysis are unavailable, the backend must say so explicitly and
must not invent intro/couplet/refrein labels.

`analysis{}` uses a provider-neutral v2 shape. v2 keeps the v1
`measured`/`inferred`/`limitations` fields intact and adds client-ready
rendering sections:

```json
{
  "contract_version": 2,
  "mode": "knowledge_plus_metadata | measured_plus_knowledge | measured | unavailable",
  "confidence": "low | medium | high",
  "measured": {
    "bpm": 128,
    "key": "C minor",
    "time_signature": 4,
    "sections": [],
    "features": {
      "energy": 0.82,
      "danceability": 0.71
    }
  },
  "inferred": {
    "provider": "ha_conversation | local_fallback",
    "structure": "..."
  },
  "sections": [
    {
      "id": "rhythm_bpm | energy_curve | buildup | instrumentation | melody_harmony | limitations",
      "title": "Rhythm & BPM",
      "kind": "technical_metrics",
      "confidence": "low | medium | high",
      "source": "measured | inferred | ha_conversation | local_fallback | unavailable | system",
      "summary": "...",
      "items": [
        {"label": "BPM", "value": "128", "source": "measured"}
      ]
    }
  ],
  "timeline": [
    {
      "label": "Section 1",
      "kind": "section",
      "source": "measured",
      "start_ms": 0,
      "duration_ms": 18000,
      "end_ms": 18000,
      "confidence": 0.86
    }
  ],
  "dj_tips": [
    {
      "kind": "mixing | set_placement | watch_out | limitation",
      "title": "Tempo match",
      "text": "Use 128 BPM as the beatmatch anchor.",
      "confidence": "low | medium | high",
      "source": "measured | inferred | system"
    }
  ],
  "limitations": [
    "Exact intro, verse, chorus, drop or outro timestamps were not measured."
  ]
}
```

The canonical client display order is `sections[]`, optional `timeline[]`,
then `dj_tips[]`. Clients must treat timestamps and section labels as measured
only when `source:"measured"` is present, and should show low-confidence or
unavailable sections as caveats instead of pretending that intro, verse, chorus
or drop labels are known.

Canonical client fixtures:

- `examples/ask_dj_track_analysis_v2_response.json`
- `examples/ask_dj_track_analysis_v2_unavailable.json`

These fixtures are validated by `tests.test_track_analysis_fixtures` and should
be used as golden responses by iOS, macOS, watchOS, Raspberry Pi and Windows
clients.

v2 is local-first and self-installable: it must work without a DJConnect central
backend. Extra providers may be added later through user-supplied keys or a
local analyzer add-on, but clients should depend on `analysis.mode`,
`analysis.measured`, `analysis.inferred`, `analysis.sections`,
`analysis.timeline`, `analysis.dj_tips`, `analysis.limitations` and `items[]`,
not on a specific provider. Existing v1 clients can keep using
`measured`/`inferred`/`limitations`.

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
  "app_version": "3.1.93",
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
