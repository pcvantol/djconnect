# DJConnect Engineering Program Model

**Status:** Established
**Decision:** `DJCONNECT_GENERATION_2_STRATEGY_ESTABLISHED`

## Purpose

Generation 2 has exactly three long-term engineering programs. An initiative
belongs to one program only; it may depend on work in another program but may
not be duplicated there.

| Program | Purpose | Owns | Does not own |
| --- | --- | --- | --- |
| DJConnect Product Development | Deliver user-facing value. | Validated product roadmap, product discovery, implementation and release sequencing. | Engineering-platform redesign or unvalidated ideas. |
| Platform Evolution | Improve the frozen Engineering Platform in support of product delivery. | Proven platform constraints, bounded capability extensions and platform technical debt. | The primary product roadmap or production features. |
| Innovation Lab | Research future possibilities. | Ideas, research, architecture review, justified prototypes and Innovation Review evaluation. | Production delivery or release commitments. |

## Shared rules

- Every active initiative records its owner, priority, dependencies, status and
  promotion path in its canonical program register.
- Status is exactly one of: Completed, Current execution, Planned, Deferred,
  Historical or Retired. Innovation Lab records use the same vocabulary and
  identify their owning program separately.
- Operational release work is temporary work outside the three programs. It is
  recorded in `MANAGEMENT_SUMMARY.md` and release evidence, never promoted into
  a permanent program merely because it is urgent.
- Product Development is primary. Platform Evolution work requires objective
  evidence that it removes a product-delivery constraint.

## Product Development assessment workflow

Product Development is the single delivery discipline. Its assessment-first
workflow is:

```text
Capability Assessment
        ↓
Product Assessment
        ↓
Experience Assessment
        ↓
If the slice modifies DJ Intelligence:
        ↓
DJ Intelligence Assessment
        ↓
Golden Scenario Assessment
        ↓
Implementation
        ↓
Verification
        ↓
Experience Validation
```

For a slice that does not modify DJ Intelligence, the conditional DJ
Intelligence Assessment and Golden Scenario Assessment are omitted entirely;
the slice proceeds from Experience Assessment to Implementation. This is one
Product Development workflow, not a separate Intelligence Engineering
discipline or governance track.

### DJ Intelligence applicability

A Product Development slice requires the conditional assessment when it
changes one or more of:

- Session Planner, Planner inputs or Planner outputs;
- Knowledge Engine, knowledge sources, selection or ranking;
- DJMoment generation or existing DJMoment types;
- narrative planning or planning horizon;
- audience adaptation or interpretation of Audience Signals;
- Lyric Intelligence or music-aware timing;
- music understanding or recommendation reasoning;
- performance learning; or
- other Session decision logic.

### DJ Intelligence Assessment checklist

Each applicable slice records explicit answers to:

| Area | Required assessment |
| --- | --- |
| Planner | Whether Planner behaviour changes. |
| Planner inputs | Whether inputs are introduced or changed. |
| Knowledge | Whether sources, selection or prioritization change. |
| DJMoment | Whether types are introduced or changed. |
| Narrative | Whether Session narrative or planning horizon changes. |
| Audience | Whether runtime Audience Signals become Planner inputs or are interpreted differently. |
| Lyrics | Whether lyric awareness or music-aware timing is introduced. |
| Performance | Whether the DJ learns from prior Session behaviour. |
| Capability ownership | Whether ownership remains consistent with the Capability Architecture. |

### Golden Scenario Assessment and traceability

Every applicable DJ Intelligence slice also determines, as review evidence,
whether existing Golden coverage is sufficient, an existing Golden Scenario
must be extended, or a new Golden Scenario is required. This consumes
`docs/verification/GOLDEN_SCENARIO_GOVERNANCE.md`; it does not create a
parallel scenario process.

The slice records this traceability:

```text
Capability
  ↓
Planner Input
  ↓
Planner Decision
  ↓
Knowledge
  ↓
DJMoment
  ↓
Golden Scenario
  ↓
Experience Validation
```

## Frozen baseline

The following remain frozen under Generation 1 decisions: Platform Engineering,
Verification Runtime 1.1.0, Software Assurance, Trusted Delivery and Platform
Release Engineering architecture. Platform Evolution may extend these only
without redesigning them; an architectural change still requires Architecture
Review.

## Relationship to engineering modes

The Innovation Lab uses Innovation Engineering for bounded learning work.
This does not add a fourth program or authorize production delivery. The
execution rules, Innovation Review outcomes and promotion transition are
canonical in `docs/meta/INNOVATION_ENGINEERING.md`; Product Engineering owns
delivery work only after Promote.

## Canonical registers

- Product Development: `PRODUCT_ROADMAP.md`
- Platform Evolution: `PLATFORM_EVOLUTION_BACKLOG.md`
- Innovation Lab: `INNOVATION_LAB.md` and `INNOVATION_BACKLOG.md`
- Navigation: `ROADMAP_INDEX.md`
