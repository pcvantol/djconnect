# Developer Session Bootstrap

## Purpose

`djconnect.developer_session_bootstrap` is the narrow, machine-invokable Home
Assistant developer-service boundary that enables the first Session
Intelligence Golden Scenario, `SI-GOLDEN-001` (the requested GS-001 flow).
It creates and terminates an isolated ordinary server-owned Runtime Session.

It is an enabling boundary only. It does not execute a Golden Scenario,
provide a Scenario Driver, collect E2E evidence, evaluate assertions, or
introduce CI orchestration.

## Contract

The service accepts one optional field:

| Field | Values | Default |
| --- | --- | --- |
| `action` | `start`, `stop` | `start` |

`start` creates the deterministic fixture Session through the existing
integration-wide `SessionRuntimeManager`. It returns only the machine-readable
bootstrap result:

```json
{
  "success": true,
  "status": "ready",
  "scenario_id": "SI-GOLDEN-001",
  "session_id": "session-...",
  "lifecycle_state": "active"
}
```

`stop` uses the same Runtime Manager to end and dispose of that fixture Session.
It returns the ended lifecycle state and the matching ephemeral Session ID.
An already active start, absent stop, or unsupported action returns a bounded
failure status without changing the Runtime.

## Ownership and lifecycle

The service owns no Runtime state and keeps no Session reference. The existing
`SessionRuntimeManager` remains the exclusive owner of the Runtime, Planner,
Knowledge Engine, DJ Moment Engine, Session Flow, Broadcast and all scoped
state. Runtime disposal follows the ordinary production lifecycle and removes
the fixture Session from the manager.

The fixture uses a dedicated profile identifier, a deterministic room, mood,
locale and manual start strategy. It is provider-neutral and has no provider
credentials, queue reads or user-profile mutation.

## Explicit exclusions

Bootstrap does not submit Track Started observations, resolve knowledge,
realize a DJMoment, publish a scenario outcome, obtain a Broadcast token, or
expose Planner, Knowledge, Performance Memory or Runtime internals. It adds no
browser surface, transport, persistence mechanism, time acceleration or Runtime
business logic.

## Relationship to E2E verification

This is only the first enabling capability in the [Session Intelligence E2E
Verification Architecture](../verification/SESSION_INTELLIGENCE_E2E_ARCHITECTURE.md).
Future independently approved work may add the deterministic Scenario Driver,
immutable capture, structural validation and CI execution around this existing
production-lifecycle boundary.
