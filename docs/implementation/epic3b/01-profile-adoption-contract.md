# Epic 3B Phase 1 — Profile Adoption Contract

Status: implemented in source, pending review/merge.

## Purpose

This document defines the canonical profile-aware contract for DJConnect
clients, Home Assistant services and voice endpoints.

The backend remains authoritative. Clients provide request context signals; they
must not implement their own Profile resolution order.

## Contract Versioning

Profile context contract version: `1`.

The contract is part of the existing `/api/djconnect/v1` API. Phase 1 does not
introduce a new REST API version.

Clients detect support through existing `djconnect/capabilities`:

```json
{
  "capabilities": {
    "profiles": true,
    "explicit_profile_selection": true,
    "private_sessions": true,
    "profile_export": true,
    "request_context": true
  },
  "contract_versions": {
    "profile_context": 1,
    "client_contract_fixtures": 1
  }
}
```

Compatibility policy:

- additive fields are allowed in `/v1`;
- clients must ignore unknown response fields;
- removals or semantic changes require an explicit future contract version;
- fixture schema version remains `1` until fixture format changes.

## Canonical Request Envelope

Profile-aware requests may include:

```json
{
  "profile_id": "optional-explicit-profile",
  "device_id": "optional-djconnect-device",
  "client_type": "ios|macos|watchos|windows|raspberry_pi|esp32|ha_voice",
  "session_id": "optional-session",
  "private_session": false,
  "request_source": "ask_dj|device_command|voice|track_insight|discover"
}
```

The backend translates the public envelope into internal
`ProfileResolutionContext`.

### Required Fields

Apple, Windows and Raspberry Pi clients normally send:

- `device_id`;
- `client_type`;
- paired device token/authorization where required by the endpoint.

ESP32 sends:

- `device_id`;
- `client_type: "esp32"`;
- device bearer token.

Voice Endpoint requests are derived by the Home Assistant integration. A generic
Home Assistant Voice Satellite does not need a DJConnect `device_id` unless it is
also registered as a DJConnect Device.

### Optional Fields

- `profile_id`: explicit profile selection, highest priority.
- `private_session`: suppresses persistence for the resolved request.
- `session_id`: temporary client/session correlation.
- `voice_endpoint_id`, `satellite_id`, `assist_pipeline_id`, `ha_device_id`,
  `area_id`, `room_id`, `player_id`, `playback_zone_id`: server-side
  request-context signals when available.

### Forbidden Fields

Clients must not send these as profile context:

- OAuth tokens;
- provider refresh tokens;
- Home Assistant tokens;
- APNs tokens;
- raw prompts;
- raw audio;
- Ask DJ history;
- Music DNA contents;
- provider credentials.

## Backend Resolution

The implemented backend resolution order is:

1. explicit `profile_id`;
2. DJConnect `device_id` mapping;
3. explicit Voice Endpoint / HA device mapping;
4. Home Assistant `ha_user_id` hint;
5. `area_id` / `room_id` mapping;
6. playback player / zone mapping;
7. configured fallback profile;
8. structured Profile error.

Future speaker identity hints must be added to the same `ProfileResolver`.

## Canonical Response Envelope

Profile-aware responses should remain minimal:

```json
{
  "success": true,
  "profile_id": "profile-peter",
  "music_dna_key": "profile:profile-peter",
  "resolved_profile": {
    "id": "profile-peter",
    "name": "Peter",
    "type": "personal",
    "privacy_mode": "normal"
  },
  "resolution": {
    "source": "device_mapping",
    "fallback_used": false
  }
}
```

Current runtime responses consistently expose `profile_id` and profile-scoped
`music_dna_key` where profile context is applied. The richer
`resolved_profile`/`resolution` envelope is the canonical target for client
adoption fixtures and should be added only where it does not expose private
state.

Do not expose:

- full Music DNA;
- private Ask DJ history;
- provider account identifiers unless explicitly required;
- OAuth/provider/Home Assistant/APNs/device tokens;
- internal authorization details.

## Canonical Errors

| Category | Wire code | HTTP status | Retryable | Expected client behavior |
| --- | --- | ---: | --- | --- |
| `profile_required` | `profile_required` | 428 | No | Ask user/admin to configure or select a profile. |
| `profile_not_found` | `invalid_profile` | 404 | No | Clear stale explicit selection and refresh profile state. |
| `device_not_mapped` | `device_not_mapped` | 409 | No | Keep pairing; ask user/admin to map device to profile. |
| `unknown_device` | `not_configured` / `unauthorized` | 401/503 | Maybe | Recheck pairing/configuration. |
| `backend_not_configured` | `profile_backend_missing` | 400 | No | Show backend setup/repair guidance. |
| `music_account_not_configured` | `profile_music_account_missing` | 400 | No | Show account setup/repair guidance. |
| `backend_account_mismatch` | `profile_backend_account_mismatch` | 400 | No | Show backend/account repair guidance. |
| `profile_access_denied` | `profile_access_denied` | 403 | No | Do not retry automatically. |
| `private_session_restriction` | `private_session_restriction` | 409 | No | Hide persistence-only actions in private mode. |
| `invalid_client_type` | `invalid_client_type` | 400 | No | Stop request and fix client identity. |
| `invalid_request_context` | `invalid_request_context` | 400 | No | Correct malformed request fields. |

Endpoints must not invent endpoint-specific profile error strings.

## Client-Class Requirements

| Client class | Identity fields sent | Profile switching | Shared behavior | Personal history | Private session | Forbidden responsibilities |
| --- | --- | --- | --- | --- | --- | --- |
| Apple Intelligence Client | `device_id`, `client_type`; may send `profile_id` | Required for adoption | Explicit selected/shared profile | Visible for resolved personal profile only | Required | No local Music DNA or resolver order |
| Windows Intelligence Client | `device_id`, `client_type`; may send `profile_id` | Required for adoption | Explicit selected/shared profile | Visible for resolved personal profile only | Required | No local Music DNA or resolver order |
| Raspberry Pi Ambient Client | `device_id`, `client_type` | Optional/admin | Defaults to shared/room profile | Read-only/limited | Optional | No personal profile guessing |
| ESP32 Voice/Control Client | `device_id`, `client_type:"esp32"` | Future only | Device mapping/fallback | None | Not required | No profile UI unless future scoped feature |
| Voice Endpoint / Home Assistant Voice Satellite | Server-derived Voice Endpoint/area context | HA-owned mappings | Defaults to shared/room/household profile | No automatic access | Supported resolver signals | No speaker identity guessing |
| Future Web/Android | `device_id`, `client_type`; may send `profile_id` | Required | Explicit selected/shared profile | Visible for resolved personal profile only | Required | No local resolver order |
| Presentation Client | Session/controller-derived context | Controller-owned | Shared/guest-safe by default | None | Optional | No durable intelligence state |

## Endpoint Inventory

| Surface | Request/path | Profile fields | Resolver used | Response profile fields | Error behavior | Consumers | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Services | `djconnect.ask_dj`, `ask_dj_message`, `track_insight`, Music DNA, Discovery, export/import/clear | `profile_id`, `device_id`, HA user from service context | Yes via `api_handlers` where personal/backend state applies | `profile_id`, `music_dna_key`, privacy metadata where relevant | Structured profile errors where routed through `api_handlers` | HA users/dev tools | Service schema remains public-HA style. |
| REST command | `POST /api/djconnect/v1/command` | `profile_id`, `device_id`, `client_type`, private/session fields | Yes | Backend command response plus profile-enriched payload where applied | `profile_required`, `invalid_profile`, `device_not_mapped`, auth errors | Apple, Windows, Pi, ESP32 | Device auth still required. |
| REST Ask DJ | `POST /api/djconnect/v1/ask_dj/message`, `/idle_suggestion`, history/state/clear/export | Same envelope | Yes | `profile_id`, `music_dna_key`, history/privacy metadata | Structured profile/auth errors | Apple, Windows, Pi | ESP32 does not use chat history UI. |
| REST Music DNA | `/music_dna/profile`, `/settings`, `/clear`, `/export`, `/import` | Same envelope | Yes | Profile-scoped Music DNA response/export | Structured profile errors plus `music_dna_not_enabled` | Apple, Windows, future clients | No raw Music DNA in profile context envelope. |
| REST Discovery | `/music_discovery`, `/refresh`, `/play`, `/feedback` | Same envelope | Yes | Feed/play/feedback response scoped to profile | Structured profile errors plus feature errors | Apple, Windows, Pi future | Discovery remains backend-owned. |
| REST Track Insight | `/track_insight` | Same envelope plus track fields | Yes | Track Insight response scoped to profile/privacy | Structured profile/auth errors | Apple, Windows, Pi | Client must not compute insight locally. |
| WebSocket capabilities | `djconnect/capabilities` | None | No resolution needed | `capabilities`, `contract_versions` | HA websocket errors | Apple, Windows local fast path | Detect `profile_context:1`. |
| WebSocket commands | `djconnect/command`, Ask DJ, Music DNA, Discovery, Track Insight | `profile_id`, `private_session`, `privacy_mode` top-level or payload; `device_id`, `client_type` | Yes via equivalent handlers | Same as REST equivalents | Same as REST equivalents surfaced as websocket errors | Apple, Windows local fast path | HTTP remains fallback. |
| Device status/pairing | `/api/djconnect/v1/status`, `/pair`, `/api/device/*` | `device_id`, `client_type`; config flow maps device to profile | Partially; status/pairing creates/mirrors device state | Pair/status capability metadata | Auth/version/pairing errors | ESP32, Pi, app pairing | Not all status payloads are personal. |
| Voice/PTT | `POST /api/djconnect/v1/voice` | `device_id`, `client_type`; optional voice headers for profile/Voice Endpoint/area context | Ask DJ voice path uses same Ask DJ handler | Ask DJ voice response | STT/Ask DJ/profile errors | Apple voice, ESP32/Pi voice paths | Voice Endpoint metadata is resolver input only. |
| Pair/bootstrap/config | Config flow, app pairing, push bootstrap | `client_type`, pairing code, device identity | Creates profile/device mappings indirectly | Device token/capability response | Pair/auth/config errors | All clients | Does not expose profile resolver output directly. |

## Known Gaps

| Gap | Classification | Notes |
| --- | --- | --- |
| Rich `resolved_profile` response envelope is fixture-defined but not universally emitted. | Non-blocking cleanup before Apple | Current `profile_id` and `music_dna_key` are enough for initial adoption; add richer metadata only after privacy review. |
| End-user mapping UI is not implemented. | Follow-up UX work | Resolver/storage support exists; polished HA config/options UI is deferred. |
| Speaker recognition is not implemented. | Future enhancement | Voice Endpoint adoption keeps this as a future hint only. |
| Service schemas are not yet fully documented as profile-context schemas. | Non-blocking cleanup | Services route through same handlers where applicable. |
| Existing wire code for missing explicit profile is `invalid_profile`, while category is `profile_not_found`. | Non-blocking cleanup | Preserve current wire code; docs define category mapping. |
| Unknown device can surface as auth/config errors before profile resolution. | Non-blocking cleanup | Correct because device auth happens before profile resolution. |

## Readiness Verdict By Client

| Client | Verdict | Reason |
| --- | --- | --- |
| Apple Intelligence Client | GO for adoption planning | Device/explicit profile/private-session contract exists; fixtures available. |
| Windows Intelligence Client | GO for adoption planning | Same contract as Apple; no Windows repo changes in this phase. |
| Raspberry Pi Ambient Client | GO for contract validation, CAUTION for UI | Shared profile behavior documented; Pi UX adoption still future. |
| ESP32 Voice/Control Client | GO, no adoption required now | Existing device-id path remains compatible. |
| HA Voice Assist Satellite | NO-GO for rollout | Mapping/config and HA-derived metadata are not implemented yet. |
| Future Web/Android | GO for planning only | Contract is generic but clients do not exist yet. |

Apple adoption may begin after this phase once PR checks pass.
