# Deterministic Scenario Driver

## Purpose

`djconnect.developer_session_scenario_driver` executes only the approved
`SI-GOLDEN-001`, `SI-GOLDEN-002` and `SI-GOLDEN-003` scenarios through the
existing production Session Runtime. It is a machine-invokable, headless
verification boundary, not a simulation engine or a second Runtime.

The service requires the isolated Session created by
`djconnect.developer_session_bootstrap`. If that Session is absent, it returns
the bounded `bootstrap_required` status and performs no work.

## Fixture and event

`SI-GOLDEN-001` uses the approved normalized track `Harbor Lights` by
`Northline`, with bounded safe Track Insight input. `SI-GOLDEN-002` uses that
first input followed by fixed `Afterimage` evidence for the same artist with a
valid `ambient electronic` genre alternative. Neither fixture has a provider
identifier, credentials, queue data, wall-clock value or random value.

`SI-GOLDEN-003` supplies one fixed unavailable-Knowledge input by raising at
the existing Runtime insight-provider boundary. It returns no partial insight,
fabricated knowledge result or provider payload. The Runtime's normal failure
handling owns the resulting approved Silence behavior.

The driver invokes the existing Runtime boundary for every fixed Track Started
event:

```text
fixture Track Insight -> SessionRuntimeManager.async_process_track_started
  -> Planner -> Knowledge Engine -> DJ Moment Engine -> Session Flow -> Broadcast
```

The fixture is raw Track Insight input, not a fabricated Knowledge result. For
`SI-GOLDEN-002`, verification infrastructure advances that Session's already
composed Clock by the fixed approved interval between the two Runtime events.
The Runtime remains responsible for planning, knowledge resolution,
realization, Flow publication and Broadcast distribution.

## Result and boundaries

On success the service returns only execution status, scenario identifier,
ephemeral Session identifier and the realized Moment identifier or identifiers
for the fixed scenario. It does not return Planner, Knowledge, Performance
Memory, Flow, Broadcast token or Runtime internals.

The driver does not start or stop Sessions, call Planner, Knowledge Engine or
DJ Moment Engine methods, validate outcomes, record a capture artifact, compare
Golden Sessions or interact with a browser. It never selects a clock, changes
Planner state or derives a Planner decision; the approved `SI-GOLDEN-002`
sequence only requests its isolated verification infrastructure to advance the
already composed Clock. Bootstrap and Runtime cleanup remain separate existing
responsibilities.

For `SI-GOLDEN-003`, the Driver does not catch, translate or recover the
unavailable input. It supplies the fixed failure at the same boundary as every
other input; Planner selection, Knowledge resolution, Silence realization,
Flow and Broadcast remain Runtime-owned.
