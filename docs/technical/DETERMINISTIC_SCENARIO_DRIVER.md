# Deterministic Scenario Driver

## Purpose

`djconnect.developer_session_scenario_driver` executes only
`SI-GOLDEN-001` through the existing production Session Runtime. It is a
machine-invokable, headless CI boundary, not a simulation engine or a second
Runtime.

The service requires the isolated Session created by
`djconnect.developer_session_bootstrap`. If that Session is absent, it returns
the bounded `bootstrap_required` status and performs no work.

## Fixture and event

The sole fixture is the approved normalized track `Harbor Lights` by
`Northline`, with bounded safe Track Insight input. It has no provider
identifier, credentials, queue data, wall-clock value or random value.

The driver invokes exactly one existing Runtime boundary:

```text
fixture Track Insight -> SessionRuntimeManager.async_process_track_started
  -> Planner -> Knowledge Engine -> DJ Moment Engine -> Session Flow -> Broadcast
```

The fixture is raw Track Insight input, not a fabricated Knowledge result. The
Runtime remains responsible for planning, knowledge resolution, realization,
Flow publication and Broadcast distribution.

## Result and boundaries

On success the service returns only execution status, scenario identifier,
ephemeral Session identifier and realized Moment identifier. It does not return
Planner, Knowledge, Performance Memory, Flow, Broadcast token or Runtime
internals.

The driver does not start or stop Sessions, call Planner, Knowledge Engine or
DJ Moment Engine methods, validate outcomes, record a capture artifact, compare
Golden Sessions, accelerate time or interact with a browser. Bootstrap and
Runtime cleanup remain separate existing responsibilities.
