# Client Connectivity & Resilience Architecture

**Status:** Qualification complete; no implementation authorization.

Connectivity determines only how a client reaches Home Assistant. It never owns a Session, Runtime, Planner, Knowledge Engine, DJMoment or Session Flow; those remain server-owned.

| Definition | Owner/maturity | Reconciliation |
| --- | --- | --- |
| HTTP and optional WebSocket | `CLIENT_SERVER_TRANSPORT.md`; confirmed code | Client reachability only; Broadcast remains Runtime-scoped. |
| Pairing and registration | `PAIRING.md`; confirmed code | Device lifecycle, never Session lifecycle. |
| Snapshot, delta and recovery | Broadcast and Session Flow recovery | Server-owned Flow and renderer-safe recovery. |
| Renderer Host | Renderer Host Classification | Consumes Broadcast, no Runtime authority. |
| Cache and client state | Cache/Storage; mixed confirmed/unknown | Reconstructable client state only. |
| Push | Push Notifications | Continuation only, not realtime transport. |

Pairing remains local installation trust bootstrap. It may return canonical local endpoint, optional remote endpoint, installation identity and transport capabilities. Remote discovery is configuration, never another trust bootstrap.

iOS, macOS, Windows and Linux may use configured remote HTTPS request/response; local rich clients prefer the existing WebSocket fast path with HTTP fallback. ESP32 and Raspberry Pi remain local-only. No remote WebSocket or cloud relay is authorized for them.

The single client state model is `UNPAIRED`, `PAIRING`, `DEMO`, `PAIRED`, `ONLINE_LOCAL`, `ONLINE_REMOTE`, `DEGRADED`, `OFFLINE`. Demo is unpaired onboarding, review, UI-validation or development installation state, never connection state. Offline is calm and reconnecting, never modal or Demo; it cannot create a local Runtime, Planner, DJ Intelligence or Session.

Every future cached projection must declare cache permission, encryption, freshness, TTL, privacy class and offline permission. Push contains only minimal continuation metadata for Session continuation or long-running Ask DJ completion; it is not DJMoment, Broadcast, Session Update or live commentary.

External HTTP qualification is future Public Release Readiness work: HA Dev Docker Lab → ngrok HTTPS → native client → DJConnect HTTP. It supplements, never replaces, Golden or Session Intelligence Qualification. No client, pairing, transport, push, Broadcast, Runtime or CI implementation is authorized.

## Client Connectivity & Resilience Qualification

**Decision:** `GO_CLIENT_CONNECTIVITY_PARTIALLY_QUALIFIED`

**Scope:** Existing repository architecture and confirmed implementation
evidence only. This qualification changes no Runtime, Renderer, API, pairing,
onboarding, Config Flow, transport or client behavior.

### Canonical connectivity architecture

| Connection | Owner | Delivery model | Scope and recovery evidence |
| --- | --- | --- | --- |
| Client-to-HA HTTP | Client transport and HA application services | Request/response | Canonical functional path for pairing, status, commands, Ask DJ and the owner Broadcast snapshot; bearer authorization applies after pairing. |
| HA WebSocket | Client transport and Runtime-owned Broadcast | Event-driven snapshot then incremental events | Optional live path for rich clients and Pi; a disconnect falls back to the owner-authorized HTTP snapshot, then a new subscription or bounded recovery cursor. |
| HA-to-local device API | HA integration and the local ESP32/Pi device API | Request/response | Local-only command, status, info, OTA and device-response paths; bearer authorization applies after pairing. |
| Apple push relay | Apple Renderer Host, HA push service and central API | Event notification | Continuation metadata only; it is not realtime Broadcast, Session, DJMoment or playback transport. |

The Session Runtime, Planner, Knowledge Engine, DJMoment Engine and Session
Flow remain server-owned and transport-independent. Broadcast is
Runtime-scoped; it is the sole renderer-safe live/recovery projection and is
not a client-owned Session replica.

### Concrete-host inventory

| Host | Confirmed connectivity | Explicit boundary | Qualification |
| --- | --- | --- | --- |
| Apple | HTTPS request/response, optional authenticated HA WebSocket, Apple-only push registration/continuation | No client Runtime or platform-native push ownership in DJ Intelligence; detailed local storage rotation and entitlement/background evidence remains unknown. | Partially qualified. |
| Windows | HTTPS request/response and optional HA WebSocket with HTTP fallback; credential-store evidence and stale-pairing cleanup policy | No Apple/APNs bootstrap; no local Runtime or server credential ownership. | Qualified at documented contract level. |
| Raspberry Pi | Local HTTP device API, status polling and optional HA WebSocket fast path with HTTP fallback | Local-only; remote URL is intentionally ignored. | Qualified at documented local contract level, not for remote public use. |
| ESP32 | Local HTTP status, command and voice paths; HA-to-device local API | Local-only; no remote WebSocket or cloud-relay path is authorized. | Qualified at documented local contract level, not for remote public use. |
| Conversation Agent | Home Assistant-local Assist/Conversation invocation and existing server-side DJConnect services | Not a separately paired Renderer Host, remote client or independent Session transport. | Qualified as a local integration boundary only. |

### Failure, recovery and offline qualification

| Condition | Existing evidence | Classification |
| --- | --- | --- |
| Temporary HA/API unavailability or timeout | HTTP remains the functional fallback; no client may create a local Runtime, Planner or DJ Intelligence result. | Partially qualified: boundary is explicit; cross-host timeout evidence is not yet collected. |
| WebSocket interruption or renderer restart | Fresh owner-authorized Broadcast snapshot is authoritative; bounded cursor recovery may replay or require a snapshot; a finished Runtime returns the renderer to idle. | Qualified for the documented owner Broadcast path. |
| Home Assistant restart, stale state or partial reconnect | Server-authoritative snapshot supersedes transport-local cache; pairing is device lifecycle, never Session lifecycle. | Partially qualified: architecture prevents client authority, but restart/reconnect qualification across concrete hosts is incomplete. |
| Expired pairing/device token | Existing structured unauthorized/stale-pairing behavior; HA repair/re-pair and ESP32/Pi forget/reboot/restart paths; Windows cleanup policy. | Partially qualified: Apple final persistence/rotation behavior is not fully reconstructed. |
| Offline state | `OFFLINE` is calm and reconnecting, not Demo; no offline Session, Planner, Knowledge or fallback DJ intelligence is permitted. Renderer-safe state is only usable where explicitly cache-qualified. | Qualified boundary; host-specific cache freshness, TTL and offline evidence remains incomplete. |
| Duplicate requests | Existing server authorization and canonical server state remain authoritative. | Insufficient cross-host idempotency/retry evidence; no retry policy is inferred or authorized. |

### Security qualification

Initial code-based pairing is the only unauthenticated trust bootstrap. After
pairing, bearer token plus canonical device/client identity authorizes HA and
local device calls. Owner Broadcast access additionally resolves the
server-side device-to-profile binding; a recovery cursor is never a credential.
Broadcast excludes Music DNA, Profile-private state, credentials, provider
payloads and conversation history. Push preserves status rather than raw APNs
tokens in HA and carries only minimal continuation metadata.

This is sufficient architectural evidence for the stated ownership and
privacy boundaries. It is not a new transport-security certification or a
claim that every public-network deployment condition has been qualified.

### Public Release Readiness disposition

The architecture is **partially sufficient** for Community Public Release:
the canonical local/remote division, HTTP fallback, server-authoritative
recovery, token boundaries and renderer-safe Broadcast recovery are established.
The missing evidence is bounded and explicit: a real external HTTPS path from
the HA Dev Docker Lab through ngrok to a native client, plus observed timeout,
restart, reconnect, stale-token and cache/offline behavior for the supported
host classes. Existing Apple entitlement/background and exact storage-rotation
unknowns remain qualifications, not evidence of a repository defect.

**Exactly one recommended next step:** perform the already-recorded bounded
external HTTP and resilience evidence qualification in Public Release
Readiness context. It must observe the existing paths only; it does not
authorize a retry, timeout, reconnect, offline, API, Runtime or client
implementation change.
