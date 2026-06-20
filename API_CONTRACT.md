# DJConnect API Contract

This document summarizes the client-facing DJConnect Home Assistant API contract.
It is intentionally compact; `README.md` remains the full user/developer guide.

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

## Ask DJ History

Ask DJ history is server-side and HA-user scoped. App clients synchronize through
`GET /api/djconnect/ask_dj/history?since_revision=<number>` and clear through
`POST /api/djconnect/ask_dj/history/clear`.

Current retention limit: `1000` messages per HA user.

History responses include `history_limit`, `history_trimmed_before` and
`history_trimmed_count`. When trimming occurs, clients should delete local
messages older than `history_trimmed_before` and must not parse retention message
text.

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
  "app_version": "3.1.69",
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
bootstrap after an Apple client supplies a fresh proof. ESP32, Raspberry Pi and
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
