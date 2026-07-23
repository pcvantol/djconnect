# Golden Scenario Governance

## Status

Canonical governance policy for platform-scoped Golden Scenario families. This
policy governs planning and verification scope; it introduces no Runtime,
Planner, Knowledge Engine, DJ Moment Engine, renderer, Qualification or CI
behavior.

## Purpose

Golden Scenarios protect approved, user-visible product behavior. They are
product contracts, not tests of classes, methods, private state, fixtures,
adapters or CI wiring. Each architectural platform owns the catalogue entries
for its observable behavior; this policy is the canonical cross-platform
governance for those families.

Verification infrastructure exists only to execute, observe, validate or
protect approved Golden Scenario behavior. It is not independently valuable
scope and it may not become a second product architecture.

## Platform-scoped Golden Scenario families

Golden Scenarios are organized by architectural platform while remaining part
of one product-behavior contract system. A family verifies only its owning
platform's observable behavior; it must not absorb or redefine another
platform's contract.

| Platform family | Contract boundary | Status |
| --- | --- | --- |
| Session Intelligence | Semantic Session behavior. The six original scenarios, `SI-GOLDEN-001` through `SI-GOLDEN-006`, are the complete behavioral contract for the Session Intelligence Platform. | Approved and unchanged. New Session Intelligence scenarios require explicit product justification. |
| Presentation | Immutable Presentation composition and renderer-safe Broadcast projection. It does not test a Renderer Host, audio output, visuals or hardware. | Future family; its boundary is defined by the [Presentation Verification Architecture](PRESENTATION_VERIFICATION_ARCHITECTURE.md). |
| Audience Experience | Observable Audience behavior, including any approved audience projection, layer, energy or privacy contract. | Future family; no behavior or implementation is authorized by this policy. |

Additional platform-specific families may be introduced only when a distinct
architectural platform has approved user-visible behavior requiring its own
contract. A future platform family does not extend the original Session
Intelligence roadmap merely because it consumes, observes or follows a Session
Intelligence outcome.

Scenario identifiers are stable within their platform family, not one
continuously growing global sequence. Existing Session Intelligence identifiers
are never renumbered. The identifier prefixes are:

| Family | Identifier form | Examples |
| --- | --- | --- |
| Session Intelligence | `SI-GOLDEN-###` | `SI-GOLDEN-001`, `SI-GOLDEN-006` |
| Presentation | `PR-GOLDEN-###` | `PR-GOLDEN-001` |
| Audience Experience | `AUD-GOLDEN-###` | `AUD-GOLDEN-001` |

The Presentation and Audience examples reserve governance shapes only. They do
not create scenario IDs, fixtures, catalogue entries, execution authorization
or implementation work.

## Unified Golden Qualification

Golden Qualification remains one platform-independent behavioral qualification
pipeline. It selects and executes all approved Golden Scenario families through
their approved boundaries; it does not become a second scenario family or give
one family ownership of another.

```text
Session Intelligence Golden Scenarios
             +
Presentation Golden Scenarios
             +
Audience Golden Scenarios
             ↓
      Golden Qualification
```

This is governance direction only. It does not change the current
Qualification Foundation, Golden Smoke, Golden Regression, CI or execution
selection. New families enter Qualification only through separately approved
work.

## Governing rules

### 1. Observable product behavior

A Golden Scenario describes what a listener, Session surface or approved
renderer can observably experience. Internal implementation contracts belong in
unit or integration tests unless they directly prove an approved behavioral
assertion.

### 2. Verification capability relationship

Every Verification capability must identify the approved Golden Scenario or
Scenarios it will **enable**, **execute**, **capture**, **validate** or
**protect**. A capability with no such relationship requires an explicit,
accepted architectural justification before implementation.

### 3. Session Intelligence capability relationship

Every Session Intelligence capability must state whether it **preserves**,
**extends** or **introduces** an approved Golden Scenario. If no scenario
relationship exists, the prompt must explain why the capability has no
user-visible Golden Scenario effect and why its narrower evidence is
sufficient.

### 4. Preservation by default

Runtime, Planner, Knowledge Engine and DJ Moment Engine changes preserve
approved Golden Scenario behavior unless an explicitly governed product change
revises the relevant catalogue contract. Infrastructure may execute, observe or
validate a scenario, but must not reinterpret, repair or replace its behavior.

### 5. Proportional verification infrastructure

Bootstrap, Scenario Driver, verification Clock, Capture, Validator, CI and
developer tooling remain bounded to the behavior they serve. A capability may
not use Golden Scenario work to create a second Runtime, Planner, Knowledge
Engine, DJ Moment Engine, diagnostics framework, simulation engine or replay
path.

### 6. Developer tools are subordinate observers

Developer overlays, browser tools, diagnostics and reference renderers are
optional passive observers. They consume the same canonical projections and
never execute scenarios, own verification outcomes, alter Runtime behavior or
become a prerequisite for headless Golden Scenario verification.

### 7. Quality metrics stay advisory

Quality metrics are advisory observations by default. A metric may block a
workflow only after repository governance approves its stable definition,
baseline, expected variance, false-positive handling and promotion decision.
Measurement alone is not authorization to gate a scenario.

### 8. Product-driven scenario growth

Before new infrastructure or engineering work is planned, answer: **what
user-visible behavior needs protection?** Add or revise a Golden Scenario only
for an approved product behavior. Infrastructure follows that contract; it
does not generate a scenario merely to justify itself.

### 9. Scope-creep prevention

Golden Scenario work must not create an alternate execution pipeline or special
business behavior. In particular, it must not add verification-only Planner or
Knowledge decisions, Runtime shortcuts, browser authority, mutable capture
state or a competing simulation/replay system.

### 10. Canonical execution reuse

Interactive development reuses the same approved Golden Scenario execution:

```text
Golden Scenario
  -> Developer Session Bootstrap
  -> Deterministic Scenario Driver
  -> Production Runtime
  -> Immutable Session Capture
  -> Structural Validation
  -> PASS / FAIL
```

A Renderer Host may attach through Broadcast as a passive observer. This does
not create a second Runtime, Scenario Driver or verification path.

### 11. Platform-preserving roadmap order

The original Session Intelligence roadmap completes before a new platform
family is considered. The intended order is:

1. retain the complete original Session Intelligence behavioral contract;
2. define and approve Presentation Golden Scenarios when Presentation behavior
   needs protection;
3. define additional platform-specific families only when justified; and
4. have the one Golden Qualification pipeline execute every approved family.

This ordering does not change current implementation priorities or authorize a
future family.

## Mandatory capability declaration

Every capability prompt in this area records the following before the GO/NO-GO
decision:

| Capability type | Required declaration |
| --- | --- |
| Verification | Approved scenario ID(s), relationship (`enable`, `execute`, `capture`, `validate` or `protect`), and why the proposed boundary is the smallest sufficient one. |
| Session Intelligence | Approved scenario ID(s), relationship (`preserve`, `extend` or `introduce`), and the behavioral contract that must remain true. |
| Presentation | Presentation scenario family or accepted architectural precursor, relationship (`preserve`, `compose`, `project` or `protect`), and proof that the boundary ends at the renderer-safe projection. |
| Audience Experience | Audience scenario family or accepted architectural precursor, relationship and proof that it preserves the Audience platform boundary, including privacy where applicable. |
| No direct scenario relationship | Explicit architectural justification, the reason no user-visible behavior changes, and the narrower validation evidence that replaces a Golden Scenario assertion. |

The declaration must identify no duplicate execution path and no unapproved
behavioral reinterpretation. Missing evidence is a Pre-Flight `NO-GO` for a
new capability proposal.

## Pre-Flight requirements

The canonical prompt template and initialization contract require future
capability reviews to verify:

1. the Golden Scenario relationship or accepted architectural justification;
2. the required Verification role or Session Intelligence behavior relation;
3. the existing behavioral contract that must be preserved or the approved
   catalogue change that authorizes a different result; and
4. that the proposal creates no duplicate Runtime, Scenario Driver, validation
   path or browser-owned verification authority.

These checks supplement, rather than replace, repository synchronization,
state, ownership and validation gates.

## Deferred work and non-goals

This policy does not add a scenario, make any scenario executable, change the
Qualification pyramid, implement CI, modify Golden Smoke or Golden Regression,
promote a quality metric, add a browser tool or alter production ownership. The
[Session Intelligence Qualification Policy](SESSION_INTELLIGENCE_QUALIFICATION_POLICY.md)
continues to define qualification layers and metric-promotion conditions.

## References

- [Session Intelligence Golden Scenario Catalogue](SESSION_INTELLIGENCE_GOLDEN_SCENARIOS.md)
- [DJConnect Scenario Catalog](03_SCENARIO_CATALOG.md)
- [Session Intelligence Qualification Policy](SESSION_INTELLIGENCE_QUALIFICATION_POLICY.md)
- [Session Intelligence E2E Verification Architecture](SESSION_INTELLIGENCE_E2E_ARCHITECTURE.md)
- [Presentation Verification Architecture](PRESENTATION_VERIFICATION_ARCHITECTURE.md)
- [Developer Experience Roadmap](../product/DEVELOPER_EXPERIENCE_ROADMAP.md)
- [Canonical Engineering Prompt Template](../governance/PROMPT_TEMPLATE.md)
- [Prompt Initialization](../../PROMPT_INITIALIZATION.md)
