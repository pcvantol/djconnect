# Developer Session Bootstrap

## Purpose

`djconnect.developer_session_bootstrap` is the narrow, machine-invokable Home
Assistant developer-service boundary that enables the first Session
Intelligence Golden Scenarios `SI-GOLDEN-001`, `SI-GOLDEN-002` and
`SI-GOLDEN-003`. It creates
and terminates an isolated ordinary server-owned Runtime Session.

It is an enabling boundary only. It does not execute a Golden Scenario,
provide a Scenario Driver, collect E2E evidence, evaluate assertions, or
introduce CI orchestration.

## Contract

The service accepts two optional fields:

| Field | Values | Default |
| --- | --- | --- |
| `action` | `start`, `stop` | `start` |
| `scenario_id` | `SI-GOLDEN-001`, `SI-GOLDEN-002`, `SI-GOLDEN-003` | `SI-GOLDEN-001` |

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

The fixtures use dedicated profile identifiers, a deterministic room, mood,
locale and manual start strategy. It is provider-neutral and has no provider
credentials, queue reads or user-profile mutation.

`SI-GOLDEN-002` additionally composes one ephemeral Verification Clock at the
approved Runtime construction boundary. The Clock supplies only the ordinary
monotonic elapsed-time value used by that Runtime's Planner. It is not created
for production Sessions, cannot cross the fixture Session boundary, and is
removed with the fixture Runtime. It is not exposed through Runtime transport,
Broadcast, persistence or renderer state.

`SI-GOLDEN-003` requires no additional Runtime composition. It uses its own
isolated Session and the ordinary Runtime lifecycle, so the fixed unavailable
Knowledge input can degrade through the existing Planner, Knowledge, Moment,
Session Flow and Broadcast boundaries.

## Explicit exclusions

Bootstrap does not submit Track Started observations, resolve knowledge,
realize a DJMoment, publish a scenario outcome, obtain a Broadcast token, or
expose Planner, Knowledge, Performance Memory or Runtime internals. It adds no
browser surface, transport, persistence mechanism or Runtime business logic.

## Relationship to E2E verification

This is only the first enabling capability in the [Session Intelligence E2E
Verification Architecture](../verification/SESSION_INTELLIGENCE_E2E_ARCHITECTURE.md).
Future independently approved work may add the deterministic Scenario Driver,
immutable capture, structural validation and CI execution around this existing
production-lifecycle boundary.
