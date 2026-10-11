# Active Session presence owner transport v1

Assignment `DJC-CORE-DJ-PRESENCE-V1-20261011`; implementation candidate, not
published/installed or native accepted. Policy: [Core policy](DJ_PRESENCE_CORE_POLICY_V1.md).

Discovery: GET `/api/djconnect/v1/capabilities`, `active_session_presence`
and matching boolean/version fields. Available/version 1; POST
`/api/djconnect/v1/session/presence`; authentication `paired_device_bearer`.
Capability grants no authority. Values, in order: `music_only`, `occasional`,
`balanced`, `talkative`, `presenter`. Default `balanced`, revision 0 for every
new Session; older consumers ignore additive fields. No persistent preference.

Request has exactly six fields:

```json
{"contract_version":1,"client_type":"ios","device_id":"djconnect-ios-ABCDEF123456","session_id":"exact-active-session-id","selected_presence":"music_only","expected_presence_revision":0}
```

Use the ordinary paired device bearer and matching device identity. Server
resolves its current enabled Profile and exact active Session. Read-only paired
live transport, Broadcast tokens and receiver end grants cannot write.

HTTP 200: `success`, `contract_version`, exact `session_id`, `selected_presence`,
`presence_revision`, `changed`. Same value/current revision is a no-op, no event.
Every change increments presence revision exactly once and emits
`presence_changed` with canonical `session` fields. Mood revision is independent.
GET `/api/djconnect/v1/session/active` and ordinary paired-live snapshot/recovery
read back the same additive fields; shared Broadcast exposes no owner identity.

400: strict schema/type/value/version failure (`invalid_request`,
`unsupported_contract_version`, `invalid_selected_presence`,
`invalid_presence_revision`). Integers reject bool/float. 401 `unauthorized`
after wrong/withdrawn bearer, owner binding or final authority fence. 404
`active_session_not_found` for wrong/ended/replaced Session. 409
`presence_revision_conflict` with authorized `current` containing exact
`session_id`, `selected_presence`, `presence_revision`. Stale same-value writes
also conflict. All rejected operations have zero setting/event/playback effects.

Clients show pending intent separately from confirmed server state. CAS uses
last confirmed revision for the exact Session ID. On conflict or response loss,
refresh snapshot and reconcile; never blind retry or invent a revision. Ignore
older replies; replies for previous Sessions must never affect replacement
Sessions. Reconnect restores server state and never resets contribution budgets.

Apple localization anchors (native consumer owns accessible implementation):

| Code | en | nl | de | fr | es |
| --- | --- | --- | --- | --- | --- |
| music_only | Music only | Alleen muziek | Nur Musik | Musique uniquement | Solo música |
| occasional | Occasionally | Af en toe | Gelegentlich | De temps en temps | De vez en cuando |
| balanced | Balanced | Gebalanceerd | Ausgewogen | Équilibré | Equilibrado |
| talkative | Talkative | Praatgraag | Gesprächig | Bavard | Conversador |
| presenter | Presenter | Presentator | Moderator | Présentateur | Presentador |

Real isolated HA proof: two ordinary pairing tokens minted and persisted, zero
HA-user credentials, production router/resolver/Runtime/Broadcast, CAS/no-op,
wrong inputs, readonly token refusal, six owner-withdrawal races, final-lock
withdrawal, late response/readback and ended/replacement fence. Synthetic configured
slots/Profile/provider inputs are declared fixtures; no installed qualification.
Actual transport fixtures and source hashes are retained under
`examples/client_contracts/session_presence_v1/`. Core pin is provisional until
final source review/regressions. Apple #87 requires its own admission; no Swift
or Watch work, no expansion of a frozen Apple candidate.
