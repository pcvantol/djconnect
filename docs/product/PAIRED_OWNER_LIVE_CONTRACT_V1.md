# Paired owner live Broadcast contract v1

Assignment: `DJC-CORE-PAIRED-LIVE-AUTH-V1-20261010`.

Ordinary Apple pairing returns the existing per-device `device_token` from
`POST /api/djconnect/v1/pair`. That token is not an HA access token. The native
HA `/api/websocket` endpoint continues to require HA authentication. Core does
not implement an HA credential issuer at `/api/djconnect/v1/websocket/session`.

## Discovery and connection

Read `session_broadcast.paired_owner_websocket` in the existing public discovery
response from `GET /api/djconnect/v1/capabilities`. Discovery metadata is not
an access grant. Version 1 advertises path
`/api/djconnect/v1/session/broadcast/paired`, audience `active_owner_broadcast`,
client types `ios`, `macos`, `watchos`, and only these commands:

- `djconnect/session/broadcast/subscribe`
- `djconnect/session/broadcast/recover`

Connect to the advertised relative path on the same trusted HA origin using
`wss` for HTTPS, `ws` for HTTP. Preserve the client's existing TLS policy.
Never put credentials or identity in the URL. All query parameters are rejected
with HTTP 400 `query_not_allowed`. No redirect, external issuer, HA account,
HA refresh/access token, shared VibeCast token or broader service grant is needed.

The server sends `{"type":"auth_required","protocol_version":1}`.
Within five seconds send exactly these fields:

```json
{"type":"auth","protocol_version":1,"device_id":"djconnect-ios-ABCDEFGHIJKL","client_type":"ios","device_token":"<existing paired token>"}
```

Success is `auth_ok` with `protocol_version:1`, `lease_seconds:300`,
`audience:"active_owner_broadcast"` and `commands` as above. No secret is
returned. Device identity and Profile are resolved from existing HA pairing and
Profile Store; the caller cannot choose an owner. A fresh connection has a
five-minute lease; incoming messages cannot extend it. Reconnect with the same
current pairing, then subscribe or recover. No reset or new pairing is needed.

## Commands and envelopes

After `auth_ok`, send a positive integer `id`, `type` and current `session_id`:

```json
{"id":1,"type":"djconnect/session/broadcast/subscribe","session_id":"<active Session>"}
```

Success uses `{"id":1,"type":"result","success":true,"result":{...}}`.
The result is the existing owner Broadcast handler's canonical snapshot,
`session_id`, `subscription_id` and opaque `recovery_cursor`. Snapshot is sent
before subscription activation. Existing `native_delivery` and rich Moment,
Persona, source and transition semantics are unchanged.

Updates use `{"type":"event","event_type":"djconnect/session/broadcast","data":{...}}`.
`data` is the existing Broadcast Engine event, including its `event_type`,
`session_id`, sequence and payload. This adapter does not synthesize events,
chat history, private question content, archives or playback actions.

On reconnect, send:

```json
{"id":1,"type":"djconnect/session/broadcast/recover","session_id":"<same active Session>","recovery_cursor":"<opaque cursor>"}
```

The result and replay come from the existing recovery handler. Cursor validity
and active owner Session are rechecked. A connection permits one successful
subscription; close before replacing it. Transport close always unregisters.

## Denial and withdrawal

Command errors use `{"id":1,"type":"result","success":false,"error":{"code":"..."}}`.
Unsupported commands return `unsupported_command`; extra identity/Profile or
authorization fields return `invalid_command`; a second successful subscription
returns `already_subscribed`. Invalid Session/cursor errors retain the existing
handler's codes (`active_session_not_found`, `invalid_recovery_cursor`, etc.).
Invalid ids/non-object/non-JSON commands close the connection without executing.

Auth denial uses `{"type":"auth_invalid","code":"..."}`, then closes.
Codes include `invalid_auth`, `invalid_identity`, `unauthorized`,
`profile_unavailable`, `pairing_revoked`, `profile_changed`, `auth_expired`,
`slow_consumer`. Clients must immediately withdraw the old live view on any auth
failure or close. Pairing revocation follows existing HTTP stale-pairing policy;
lease expiry alone permits reconnect with the current pairing.

Authority is checked before results/events and at most every one second while
idle. Token rotation, runtime unload/generation revocation, missing Profile or
Profile switch withdraw the old stream. They do not end/restart any Session or
change playback. Session end is the existing terminal Broadcast event. No
old Session becomes readable merely because a connection remains authenticated.
The event queue is bounded to 64 and inbound frames to 16 KiB.

## Apple consumer delta and evidence boundary

Apple owns Swift changes. Its current session auth provider's issuer request
and hardcoded native `/api/websocket` address cannot consume this route without
an explicit change. Discover v1, select its path, send the paired auth frame,
then use existing snapshot/update/recovery parsing. Do not fall back to HA user
credentials or shared receiver tokens if the capability is absent.

`scripts/verification/verify_paired_live_auth.py` runs against an isolated real
HA SDK/router/AuthManager/ConfigEntries/Store and real DJConnect pairing,
Profile Store, persistence, Session and Broadcast handlers. Configured slots
and music are synthetic; the device token is minted by actual pairing. No HA
user credential is created or used by the test. `--baseline` proves ordinary
pairing succeeds while the old issuer is 404 and native HA auth rejects the
device token; `--expiry` additionally measures the real 300-second lease.
Receipts retain status/codes and structural event names only, never secrets,
private content, session identifiers or recovery cursors.

This qualifies producer software and ordinary paired live transport in the
isolated lab. Installed HA and native Apple acceptance require their separate
owners and specific installation/native test authority. Cast/Pi/player and
HTTP questions, voice, history and search retain their existing contracts.
