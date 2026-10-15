# HTTP API

The machine-readable route inventory is
[`inventory/http_routes.json`](inventory/http_routes.json).

## HA API

`CONFIRMED_CODE` HA route constants live in `custom_components/djconnect/const.py`.
View classes live in `custom_components/djconnect/http.py`.

`CONFIRMED_CODE` Route registration is idempotent and is performed during both
integration setup and config-entry setup. The config-entry registration keeps
the existing `/api/djconnect/v1/...` routes available when Home Assistant
restores an entry through an entry-first startup path.

`CONFIRMED_CODE` `GET /api/djconnect/v1/capabilities` exposes the implemented
DJ Session Broadcast transport contract. It is discovery only: it reports the
owner HTTP snapshot and authenticated WebSocket subscription as available,
snapshot recovery as supported, and replay, cursor, Flow delta and sequence as
unsupported. It shares its declaration with the WebSocket capability response;
it neither grants owner access nor changes transport behaviour.

`CONFIRMED_CODE` Most DJConnect HA views set `requires_auth = False` and perform
DJConnect bearer/device validation inside the handler. Voice debug is the
exception observed with `requires_auth = True`.

## Shared Ask DJ owner requests

The connected `ask_dj.service.async_exchange` owns application text, post-STT
voice, raw Ask DJ compatibility and Ask DJ command acceptance. General and
Session composers use the same `/ask_dj/message` contract; optional
`conversation_context` supplies an authorized Session, entry or live Moment,
never a second pipeline. The current request owns explicit topic changes.
Pairing/Profile authority is revalidated before private delivery, Store/Flow
acceptance and actual music-effect dispatch. Private responses use `no-store`.

The additive capability `ask_dj_contextual_dialogue` and contract version 1
describe bounded Profile/thread memory, immutable result-set/action identities,
clear/retry semantics and typed failures. A visible selection is not a play
grant. `action_outcome.readback_confirmed` distinguishes dispatch from qualified
playback confirmation. Existing unsupported consumer fields can be ignored;
there is no client-side conversation reconstruction requirement.

`track_insight_target` optionally carries the closed version 1 Session/Moment/
action reference advertised by `moment_track_insight_navigation_v1`. It resolves
an eligible published recording through the existing TrackInsightService; it
never substitutes current playback when the explicit target is stale. Ordinary
analysis discussion does not navigate. Receiving an offer performs no lookup,
analysis, model call or playback operation.

See the [canonical dialogue contract](../product/ASK_DJ_CONTEXTUAL_DIALOGUE_CONTRACT_V1.md)
and [exact navigation contract](../product/MOMENT_TRACK_INSIGHT_DRILLDOWN_V1.md).

## Local Device API

`CONFIRMED_CODE` ESP32 and Pi expose local `/api/device/*` endpoints. Pairing
info and pair are used before bearer auth; most device commands require bearer
auth once paired.

## Central API

`CONFIRMED_CODE` `djconnect-api` exposes `/health` plus `/v1/...` install,
pairing bootstrap, push and admin routes. It records D1 diagnostics and uses
bearer authorization for install/push/admin flows depending on route.

## Common Error Shapes

`CONFIRMED_CODE` HA returns JSON with `success:false`, `error` and often
`message`. Voice/STT failures use `stt_failed` with HTTP 422 for Ask DJ app
voice or 503/500 for other voice paths. Version mismatches use HTTP 426.

## Verification Mapping

`SETUP-*`, `ASKDJ-*`, `MUSICDNA-*`, `DISCOVER-*`, `TRACK-*`, `PLAYBACK-*`,
`BACKEND-*`, `PRIVACY-*`, `VOICE-*`.
