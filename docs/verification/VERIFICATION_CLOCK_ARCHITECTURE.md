# Verification Clock Architecture

## Decision

**YES, WITH RESTRICTIONS.** DJConnect should introduce one canonical
Verification Clock only as an infrastructure-owned elapsed-time source for an
isolated verification Runtime. It resolves the `SI-GOLDEN-002` blocker without
changing production behavior or making business rules aware of verification.

## Repository evidence

The Planner deliberately enforces its minimum speaking interval using monotonic
elapsed time. A second immediate Track Started evaluation therefore correctly
chooses Silence before Performance Memory becomes eligible to influence a new
knowledge-backed decision. Real waiting is deterministic only in the weak
sense that it eventually completes; it is unsuitable for a small, stable CI
scenario and introduces wall-clock dependence.

## Alternatives considered

| Option | Architectural consistency | Determinism and CI suitability | Runtime purity and maintenance | Decision |
| --- | --- | --- | --- | --- |
| A. Real wall-clock waiting | Preserves current implementation shape | Slow, timing-sensitive and unsuitable for routine Golden Smoke | No new abstraction, but recurring verification delays | Reject |
| B. Verification Clock abstraction | Preserves owners when bound at Runtime composition | Deterministic, fast and suitable for bounded verification | Production retains its monotonic time source; one small infrastructure contract | Accept with restrictions |
| C. Scenario redesign without time abstraction | Avoids a new time source | Cannot prove the approved immediate-repetition behavior after the speaking interval without waiting | Would weaken or misrepresent `SI-GOLDEN-002` | Reject |

## Ownership and lifecycle

The Verification Clock is owned by Verification infrastructure. It is created
only for one isolated verification Runtime, is scoped to that Runtime's
lifecycle, is non-persistent, is disposed when the Runtime ends and never
crosses Profile, Session or scenario boundaries.

The Session Runtime remains the composition boundary and owner of execution.
The Planner remains owner of the minimum-interval and Performance Memory
decisions. Knowledge Engine, DJ Moment Engine, Session Flow and Broadcast keep
their existing ownership and behavior. They do not own, select, advance or
inspect the Verification Clock.

## Allowed injection boundary

Only the Runtime composition boundary may bind an elapsed-time source while
constructing an isolated verification Runtime. Production Runtime construction
must always bind the existing monotonic elapsed-time source. The binding is not
a public Renderer, transport, provider or Profile contract.

The Planner may receive elapsed-time values through its ordinary Runtime-owned
timing boundary, but it must not know their origin. It must have no developer,
simulation, accelerated or CI mode branch, and no capability to advance time.
The same restriction applies to Knowledge, DJ Moment realization, Session Flow
and Broadcast.

## Prohibited usage

The Verification Clock must not:

- change Planner rules, intervals, priorities or Performance Memory;
- be selected by a Scenario Driver or exposed as a Scenario input;
- affect provider playback, Playback Observation, renderer progress or
  external wall-clock behavior;
- persist, cross Sessions, alter historical projections or enter Broadcast;
- create a second Runtime pipeline, test-only Planner behavior or a generic
  simulation engine.

## Relationship to future capabilities

`SI-GOLDEN-002` may use the Clock only after a separately authorized
implementation binds it at the approved Runtime boundary. Its Scenario Driver
continues to supply observable inputs only and never advances time or changes
Planner state.

This decision is not accelerated execution. A future accelerated-execution
capability may propose controlled advancement only through this same
infrastructure boundary, with its own Pre-Flight, ownership review and product
scope. It may not reinterpret this architecture as authorization for replay,
simulation, Runtime shortcuts or CI workflow changes.

## Consequences

The next verification implementation may introduce the smallest bounded Clock
contract needed to execute `SI-GOLDEN-002`; it must prove unchanged production
monotonic behavior and no business-mode branching. Until that separate
capability is accepted, no Scenario Driver, Planner, Runtime or CI change is
authorized by this architecture record.

## References

- [Session Intelligence E2E Verification Architecture](SESSION_INTELLIGENCE_E2E_ARCHITECTURE.md)
- [Golden Scenario Catalogue](SESSION_INTELLIGENCE_GOLDEN_SCENARIOS.md)
- [Session Intelligence Qualification Policy](SESSION_INTELLIGENCE_QUALIFICATION_POLICY.md)
- [Developer Experience Roadmap](../product/DEVELOPER_EXPERIENCE_ROADMAP.md)
