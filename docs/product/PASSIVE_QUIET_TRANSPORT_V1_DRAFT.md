# Passive quiet transport — integration proposal

Status: **DRAFT; no activated registration or relay capability**. Existing
`SURFACE::APPLE::QUIET-TRANSPORT`, selected best-effort follow-up to the
[passive projection](PASSIVE_SESSION_PROJECTION_V1.md). Core, API and Apple keep
their existing ownership. This is a reviewable dependency contract, not a new
push service, frozen cross-repository wire or consumer implementation claim.

## Observed implementation boundary

API contract readback: `pcvantol/djconnect-api` source
`734129ccd8859384c4e25e988861959eae14b669`; this is an inspected owning-repository
snapshot, not a frozen quiet contract or remote production qualification.

Core `push.py` sends existing `/v1/push/register`, `/unregister` and `/event`
requests. API's current `/v1/push/event` permits explicit Ask DJ reply/confirmation
alerts only. It does not admit unsolicited Session updates, background headers
or ActivityKit tokens. Do not pass a new event through that alert route, put
ActivityKit tokens in ordinary APNs registration, or relax `explicit_user_request`
to simulate completion. API remains token encryption, APNs delivery and relay
transaction owner; Core remains Session and source-purpose owner.

Projection v2 still advertises `background_delivery:false` and all contribution
and artwork payloads have `external_relay:false`. Native/foreground acceptance
does not override these fields. Apple40337 is a separate native v1 candidate;
no exact v2 adoption or suspended-app receipt has been obtained here.

## Proposed registration identity for owner review

The following is the required logical tuple, not a request to an invented URL.
API must publish its versioned route and exact request/receipt schema before
Core advertises it or Apple sends network registration.

| Field | Binding and validation |
| --- | --- |
| `transport_version` | Exact integer1, separate from passive `projection_version` |
| `token_purpose` | Closed `app_background_sync` or `live_activity_update`; never interchangeable |
| installation + paired recipient | Current API install token and existing registration, resolved by Core; client cannot choose another owner |
| `surface` | Exact granted widget or Live Activity purpose |
| `session_id`, `binding_id`, `generation` | Exact current surface grant; rotates with reauthorization and never revives on ABA |
| `projection_version` | Exact version of that grant |
| environment + topic | Exact APNs development/production environment and server-allowlisted bundle topic; ActivityKit adds its own topic suffix |
| token bytes | Separate ordinary app or existing ActivityKit update token, encrypted by API; never in logs, fixtures, App Group or broadcast |
| activity identity | Required only for an already started Activity; no push-to-start token or remote creation |
| `expires_at` | Original finite registration/source boundary, never sliding on read/hint |
| operation identity | Stable operation ID + monotonic revision for idempotent registration/rotation/revoke, exact receipt and safe retry |

The paired bearer and raw surface grant stay HA/app local; relay sees a scoped
opaque binding, not a Profile/account identity, history or arbitrary URL.
Registration is explicit separate consent and must survive neither pairing
revocation, Profile/source change, grant withdrawal nor HA install removal.
A lost registration reply is reconciled by operation identity before retry.
ActivityKit token rotation revokes the old token within the same binding;
ordinary device-token rotation cannot replace it. API owns encrypted token
storage and bounded cleanup, not this Core branch.

## Two distinct delivery paths

1. **Widget/app wake:** Core's existing accepted publication or invalidation
   produces a category-only, coalescible hint for the exact authorized binding.
   API uses APNs background priority5, `content-available:1`, no alert/sound/badge
   and bounded expiration/collapse scope. No title, artwork, DJ text, private
   history or session content travels in the hint. The app uses its existing
   secure grant to perform a pure read and reload WidgetKit only if the OS grants
   runtime. It clears stale data when learned; the hint renews no original TTL.
2. **Existing Live Activity:** API uses its separate activity token, ActivityKit
   topic and update/end push type. Core must first produce a separate
   **relay-qualified**, minimal content-state with original expiry, generation,
   attribution and bounded size. Current passive v2 is explicitly insufficient
   for this path. A generic no-content wake cannot directly update a suspended
   Activity. No fallback converts an unsupported field into permitted relay copy.

End/revoke invalidates pending updates before sending one idempotent end.
Out-of-order revisions and expired/generation-mismatched events are discarded.
An end cannot be followed by a late recreation. Foreground reread and APNs
receipt never republish a DJMoment or extend media/source validity. OS delivery
is best effort; no periodic wake or immediate remote pixel-erasure guarantee.

## Consumer work safe before API acceptance

Apple may prepare the closed token-purpose types, separate secure token slots,
versioned payload decoder, original-expiry/withdrawal handling and tests with
explicit fixtures. It can implement the category-only wake handler using the
existing pure-read API under its existing grant. Network registration, APNs
headers/topic use and new activity push activation remain disabled until the
exact API contract and Core capability are present. Existing foreground v1
continues; explicit v2 adoption requires its own pinned fixtures and attribution
layout. No watch or push-to-start work is implied.

## Acceptance and exact remaining dependency

Core/API/Apple must agree the route, tuple, source-purpose relay policy and
operation receipts above. Then prove real registration, rotation, offline retry,
wrong environment/topic/token-purpose rejection, Profile/source ABA and revoke,
publication/update/end ordering and nonrenewing expiry. Physical acceptance
covers foreground, background, suspension, termination and normal OS throttling;
forced quit or missing delivery remains neutral, never a guaranteed refresh.

Until that named API contract and separate relay permission exist, the exact
blocked effects are **consumer network registration and actual background APNs /
ActivityKit sends**. Pure projection v2, native foreground adoption and their
qualification are independently reviewable. No API source, deployment, Apple
signing or private user Session is changed by this proposal.

Apple platform references: [background updates](https://developer.apple.com/documentation/usernotifications/pushing-background-updates-to-your-app)
and [ActivityKit](https://developer.apple.com/documentation/activitykit).
