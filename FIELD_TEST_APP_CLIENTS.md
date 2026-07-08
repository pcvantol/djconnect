# DJConnect app client field test checklist

Use this checklist for real iOS, macOS and Windows validation before a public release.
The automated tests cover the Home Assistant contract; these steps verify the native
client, network and remote-access behavior.

## Preconditions

- Home Assistant has DJConnect installed and configured.
- The entry uses Spotify Direct or Music Assistant and shows backend availability.
- Home Assistant has a local URL and, for remote tests, a HTTPS external/Nabu Casa URL.
- The target client is on the local network for initial pairing.
- No Spotify refresh token, Home Assistant token, device token or raw audio is copied
  into notes, screenshots or logs.

## Inbound Pairing

Run once per client type: `ios`, `macos`, `windows`.

1. Start Add Integration and choose DJConnect app pairing.
2. Confirm the pairing form hides Client address.
3. Pair from the app with:
   - `device_id`: `djconnect-ios-XXXXXXXXXXXX`, `djconnect-macos-XXXXXXXXXXXX` or
     `djconnect-windows-XXXXXXXXXXXX`
   - matching `client_type`
   - current `pair_code`
4. Confirm the Home Assistant response contains:
   - `success: true`
   - `device_token`
   - `api_base: /api/djconnect/v1`
   - `status_path`, `voice_path` and `event_path`
   - `ha_local_url`
   - `ha_remote_url` for iOS, macOS and Windows when a HTTPS external URL is configured
5. Confirm the response does not contain Spotify OAuth credentials, refresh tokens,
   Home Assistant long-lived access tokens, `device_language` or `language`.
6. Confirm the HA device stores the stable app `device_id`, matching `client_type` and
   pairing status `pending` until the app posts status.

## Remote Playback

Run once per paired client type.

1. On LAN, send `/api/djconnect/v1/status` with the returned bearer token.
2. Send `/api/djconnect/v1/command` with `command: status`.
3. Send `/api/djconnect/v1/command` with a playback command such as `play`,
   `set_shuffle`, `set_repeat`, `devices`, `queue` and `playlists`.
4. Leave the LAN and repeat the same command set via `ha_remote_url`.
5. Confirm playback commands return HTTP 200 for successful backend calls and do not
   trigger re-pairing or Spotify reauthorization repairs.
6. Confirm firmware channel, firmware update, reboot and ESP-only settings entities
   are not active for iOS, macOS or Windows.

## Apple Push Registration

Run for iOS and macOS development builds, and for watchOS when push is enabled.

1. Confirm the app APNs entitlement matches the registration environment:
   - development entitlement: client sends `push_environment: development` or `sandbox`
   - production entitlement: client sends `push_environment: production`
2. Pair the app fresh with Home Assistant, then call
   `POST /api/djconnect/v1/push/bootstrap` if the client does not already have a
   current bootstrap proof.
3. Fully quit and restart the app, then let it retry APNs registration once the
   device token and Home Assistant bearer token are available.
4. Confirm Home Assistant accepts the registration and returns either
   `push_registered: true` or a client log such as
   `registered with Home Assistant env=sandbox`.
5. Confirm a development build is reported as canonical `push_environment: sandbox`
   by Home Assistant, not `production`.
6. If the response contains `missing_bootstrap_proof`, request a fresh proof
   through `/push/bootstrap` and retry registration. If it contains
   `invalid_bootstrap_proof`, request a fresh proof or re-pair before debugging
   APNs entitlements; stale bootstrap proof is the first blocker.
7. Confirm no APNs token, bearer token, bootstrap proof or `djci_` install token is
   copied into notes, screenshots or logs.

## Evidence To Record

- Client type and app build.
- Home Assistant version.
- DJConnect integration version.
- Backend: Spotify Direct or Music Assistant.
- Local pairing result.
- Remote command result.
- APNs environment and registration result for Apple clients.
- Any HA Repair issue created during the test.
