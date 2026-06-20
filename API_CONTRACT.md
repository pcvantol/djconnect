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
`ios`, `macos` and `watchos` clients. Registrations are scoped to the Home
Assistant user/account, `device_id`, `client_type` and APNs token.

Register payload:

```json
{
  "device_id": "djconnect-ios-...",
  "client_type": "ios",
  "push_token": "...",
  "push_environment": "sandbox",
  "app_bundle_id": "dev.djconnect.app",
  "app_version": "3.1.66",
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

APNs provider-token auth uses these environment variables/config values:

- `APNS_TEAM_ID`
- `APNS_KEY_ID`
- `APNS_PRIVATE_KEY` or `APNS_PRIVATE_KEY_PATH`
- `APNS_TOPIC_IOS`
- `APNS_TOPIC_MACOS`
- `APNS_TOPIC_WATCHOS`
- `APNS_ENVIRONMENT` (`sandbox` by default, `production` for release)

When APNs credentials are missing, push stays disabled and normal Ask DJ flows
continue. Sandbox uses `https://api.sandbox.push.apple.com`; production uses
`https://api.push.apple.com`.

Push payloads are deliberately small and generic. They must not contain secrets,
Spotify tokens, Home Assistant tokens, raw prompts, raw LLM context, full memory,
full history or long/raw assistant responses. Ask DJ responses trigger
`ask_dj_response` or `ask_dj_confirm` after server-side history has advanced, and
payloads include only sync hints such as `event_type`, `open_target`,
`client_message_id` when available and `history_revision` when available. APNs
`BadDeviceToken`, `Unregistered` and related invalid-token responses mark a
registration disabled/invalid.

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
