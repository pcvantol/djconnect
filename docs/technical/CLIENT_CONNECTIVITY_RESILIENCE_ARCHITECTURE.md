# Client Connectivity & Resilience Architecture

**Status:** Canonical reconciliation; no implementation authorization.

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
