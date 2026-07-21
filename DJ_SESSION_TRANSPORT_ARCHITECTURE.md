# DJ Session Transport Architecture

**Status:** Accepted architecture contract  
**Owner:** DJConnect Product Development  
**Scope:** Transport independence for server-owned DJ Sessions; no API or Runtime implementation

## Purpose

This document defines how existing server-side DJ Session capabilities may be delivered to clients with different connectivity characteristics. It preserves one server-owned Session Runtime and one intelligence architecture whether a client uses HTTP, a persistent WebSocket or a future delivery adapter.

It does not create an endpoint, event schema, persistence model, renderer, WebSocket implementation or Runtime behaviour. Current route and command inventories remain authoritative in [`docs/technical/HTTP_API.md`](docs/technical/HTTP_API.md) and [`docs/technical/WEBSOCKET_API.md`](docs/technical/WEBSOCKET_API.md).

## Principle: Transport Independence

DJ Intelligence is transport-independent. Business behaviour must never depend on a particular transport. Every server-side DJ Session capability has a functionally equivalent HTTP request/response path; WebSocket is a preferred low-latency delivery path, never the only supported path.

```text
Transport
  ↓
Application Services
  ↓
DJ Intelligence
  ↓
Session Flow
  ↓
Broadcast
  ↓
Transport adapter / client delivery
```

The diagram describes responsibility, not a second execution pipeline. The Session Runtime orchestrates the existing Planner, Knowledge Engine and DJ Moment Engine. Those components never know whether their result will reach a client through HTTP, WebSocket or another adapter.

## Ownership

| Owner | Responsibility | Does not own |
| --- | --- | --- |
| Transport | Request, response, connection and delivery mechanics. | Session meaning, intelligence or history. |
| Application services | Authentication, authorization and transport-neutral invocation of server capabilities. | Planner decisions or renderer behaviour. |
| Session Runtime | Active Session state and orchestration. | A client connection or transport-specific state. |
| Planner | Decisions and ordering. | Delivery. |
| Knowledge Engine | Safe knowledge selection. | Delivery. |
| DJ Moment Engine | Immutable Moment realization. | Delivery. |
| Session Flow | Authoritative ordered Session history. | Transport cursors or connections. |
| Broadcast | Scoped distribution of immutable state and events. | A specific protocol or socket lifecycle. |
| Clients and renderers | Presentation and recovery behaviour. | Server business logic. |

Broadcast may be projected through multiple adapters. It remains transport-agnostic: an adapter may use an HTTP snapshot, an HTTP delta or a WebSocket event stream without changing Broadcast, Session Flow or any intelligence owner.

## HTTP: Canonical Functional Transport

HTTP is the canonical request/response transport and the guaranteed fallback for a client that cannot establish or retain a WebSocket. The architectural contract requires functional HTTP access to:

- Session start and stop;
- Session status and the current Runtime snapshot;
- the current DJ Moment;
- Session Flow snapshot and Session Flow changes after a known sequence;
- Ask DJ and Track Insight;
- capability discovery; and
- diagnostics authorized for the caller.

The current implementation already exposes HTTP lifecycle operations and an active Session response. It also exposes existing HTTP feature routes described by the route inventory. Granular current-Moment, Flow-snapshot and Flow-delta HTTP resources are architectural requirements for a later bounded HTTP contract; this document does not claim that such endpoints already exist or authorize their implementation.

HTTP preserves the same server authorization and privacy rules as every other transport. It does not expose Planner internals, raw Profile data, Music DNA, provider credentials or raw provider payloads.

## WebSocket: Preferred Live Delivery

WebSocket is the preferred low-latency transport for live updates. It may deliver Session updates, immutable DJ Moments, Session Flow changes, Runtime state updates and Broadcast events after the client has authorized a subscription.

Its only additional value is efficient live delivery. A WebSocket neither owns business logic nor becomes a source of Session truth. It must invoke the same application services and receive the same scoped server result as HTTP.

The current authenticated Home Assistant WebSocket Broadcast subscription returns a complete initial Broadcast snapshot followed by incremental Broadcast events. Its current command, event and authorization details remain defined by [`docs/technical/BROADCAST_TRANSPORT.md`](docs/technical/BROADCAST_TRANSPORT.md).

## Snapshots, Deltas and Authoritative Ordering

A **snapshot** is the current authorized state of one Session at one point in time. A **delta** is an authorized set of changes after a client-known Session Flow sequence. A client must be able to recover with a current snapshot or a delta; it must not reconstruct Session state from transport-local assumptions or replay an entire Session merely because a connection dropped.

Session Flow ordering is authoritative. Future HTTP delta retrieval and WebSocket recovery must use that canonical ordering rather than a socket event identifier, local timestamp or client-managed history. This establishes a recovery contract, not a sequence field, cursor format or endpoint design.

## Recovery

The canonical recovery flow is:

```text
WebSocket disconnects
  ↓
Client requests an authorized HTTP snapshot or Flow delta after its known sequence
  ↓
Client applies the canonical current state and ordered Flow changes
  ↓
Client reconnects WebSocket when available
  ↓
New live delivery continues from server-authoritative state
```

The server must never require a permanently connected WebSocket for a Session to remain valid. A client remains functionally usable through HTTP alone. After reconnecting, a returned server snapshot is authoritative over any local transport cache.

## Client Expectations

Clients should discover capabilities, then prefer WebSocket when it is available and authorized. If it is unavailable, disabled, unauthorized or disconnected, they use the equivalent HTTP capability. On disconnection they recover with HTTP and may subsequently reconnect WebSocket.

Clients render only authorized immutable Broadcast projections and canonical Session Flow state. They do not compensate for a missing live connection by reimplementing Planner, Knowledge Engine, Moment Engine or Runtime behaviour.

## Future Adapters

Push notifications, MQTT, Voice and future transports may become delivery adapters. They may notify, request a snapshot, carry a scoped event or trigger an authorized application-service call. They must not create an alternative business-logic path, a second Session Flow, a renderer-owned Runtime or a transport-specific DJ Intelligence model.

## Relationship to Existing Documents

- [`DJ_SESSION_RUNTIME_CONTRACTS.md`](DJ_SESSION_RUNTIME_CONTRACTS.md) owns Runtime lifecycle and ownership.
- [`docs/product/DJ_INTELLIGENCE_ARCHITECTURE.md`](docs/product/DJ_INTELLIGENCE_ARCHITECTURE.md) owns the intelligence pipeline.
- [`docs/technical/BROADCAST_TRANSPORT.md`](docs/technical/BROADCAST_TRANSPORT.md) records the current Broadcast transport implementation.
- [`docs/technical/HTTP_API.md`](docs/technical/HTTP_API.md) and [`docs/technical/WEBSOCKET_API.md`](docs/technical/WEBSOCKET_API.md) record current transport inventories.

When implementation and this contract differ, current implementation facts belong in the technical references; a proposed implementation change must be introduced through its own bounded capability or API-contract work.
