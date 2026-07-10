# HTTP API

The machine-readable route inventory is
[`inventory/http_routes.json`](inventory/http_routes.json).

## HA API

`CONFIRMED_CODE` HA route constants live in `custom_components/djconnect/const.py`.
View classes live in `custom_components/djconnect/http.py`.

`CONFIRMED_CODE` Most DJConnect HA views set `requires_auth = False` and perform
DJConnect bearer/device validation inside the handler. Voice debug is the
exception observed with `requires_auth = True`.

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
