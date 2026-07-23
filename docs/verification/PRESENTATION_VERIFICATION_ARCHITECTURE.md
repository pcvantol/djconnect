# Presentation Verification Architecture

## Status

**Canonical architecture and governance only.** Presentation Verification is a
future verification capability. This document authorizes no capture,
validator, Golden Scenario execution, CI workflow, renderer implementation or
Runtime behavior change.

## Purpose

Presentation Verification proves that the server composes, projects and
publishes an immutable Presentation correctly. It ends at the renderer-safe
Broadcast projection. It never proves how a Renderer Host renders, speaks,
animates or otherwise experiences that projection.

The verified product path is exactly:

```text
approved immutable DJMoment
  -> Presentation Composer
  -> immutable Presentation
  -> renderer-safe Presentation Projection
  -> Broadcast publication
  -> renderer-safe Presentation available to Renderer Hosts
```

The last step is a safe distribution boundary, not a renderer test. Existing
renderer-safe visual Presentation remains authoritative, and Speech
Presentation remains additive; neither is remodelled by this verification
architecture.

## Separate verification domains

Session Intelligence Verification and Presentation Verification protect
different contracts on the same canonical Runtime execution. Neither creates a
second Runtime, Scenario Driver, Session Flow or Broadcast path.

| Domain | Proves | Does not prove |
| --- | --- | --- |
| Session Intelligence Verification | Planner, Knowledge Engine, DJ Moment Engine and Session Flow produce the approved semantic behavior. | Presentation composition policy, renderer behavior or audio output. |
| Presentation Verification | Presentation Composer, immutable Presentation structure and renderer-safe Broadcast projection preserve the approved Moment meaning. | Planner decisions, Knowledge resolution, Session Flow ownership, renderer visuals, generated audio or hardware behavior. |

Session Intelligence Golden Scenarios remain the canonical contracts for
semantic Session behavior. Presentation Golden Scenarios are a separate future
family for Presentation behavior. They may reuse the same approved immutable
DJMoment and production path, but they do not reinterpret or replace Session
Intelligence outcomes.

## Ownership and observation boundary

| Owner | Responsibility | Presentation Verification may observe | Does not become visible to Renderer Hosts |
| --- | --- | --- | --- |
| DJ Moment Engine | One approved immutable semantic DJMoment. | Stable source identity and approved content already frozen in the Moment. | Planner, Knowledge or realization internals. |
| Presentation Composer | Deterministically composes one immutable Presentation from the source Moment and bounded Runtime-derived Presentation Context. | Immutable structure, source linkage, mode, ordered roles, speech segments and fallback outcome. | `session_id` and `PresentationContext`. |
| Broadcast | Distributes the canonical renderer-safe Presentation Projection. | Projection identity, source linkage, visibility and safe supported content. | Runtime-only Context, raw Runtime objects and internal diagnostics. |
| Renderer Host | Consumes a safe projection and renders locally. | Nothing in this capability. | No server ownership moves to the browser or another host. |
| Presentation Verification | Read-only contract assessment of the composition and projection boundary. | Immutable inputs and outputs only. | Runtime control, renderer behavior, provider access or persistent state. |

Presentation Context is valid verification evidence only at the server-side
composition boundary. The projection integrity assertion must prove that this
Runtime-only Context is absent from Broadcast and unavailable to Renderer
Hosts.

## Presentation behavioral contract

For an approved immutable DJMoment, the Composer creates exactly one immutable
Presentation with a stable Presentation identity and source Moment identity.
The Presentation carries the bounded Context used for composition; Broadcast
projects only the renderer-safe subset. The projection must preserve the
identity and approved supported Presentation content required by a Renderer
Host without exposing Context or other Runtime internals.

Presentation Verification asserts only the following observable server-side
properties when the corresponding capability is present:

- Presentation identity and source DJMoment identity are present and linked;
- Presentation mode, bounded Context and supported Speech structure are valid;
- Speech segment order and semantic speaker roles are preserved;
- repeated composition with equivalent source Moment, Context and policy yields
  an equivalent immutable Presentation;
- Primary Only is retained as the safe fallback when Sidekick enrichment is
  disabled, ineligible or fails;
- the Broadcast projection preserves safe identity and supported content;
- the Broadcast projection exposes neither Presentation Context nor Planner,
  Knowledge, Session Runtime or Session Flow internals; and
- composition and publication introduce no Planner decision, Flow item,
  Session Flow ordering change or renderer authority.

The contract must not assert rendered pixels, DOM structure, animation,
generated audio, voice quality, TTS provider behavior, device output, room
routing hardware or a Renderer Host's local capability selection.

## Determinism

Presentation composition is deterministic at the architectural contract level:

```text
equivalent immutable DJMoment + equivalent Presentation Context + equivalent policy
  -> equivalent immutable Presentation
  -> equivalent renderer-safe Presentation Projection
```

Equivalent means the same immutable source identity and approved source fields,
the same bounded Context and the same versioned composition policy. It does not
require a renderer to reproduce the same voice, audio waveform or visual
implementation. Any nondeterministic renderer concern remains outside this
boundary.

## Future Presentation Golden Scenarios

The following are candidate architecture-only contracts. They do not create
scenario IDs, fixtures, test code or implementation authorization yet.

| Candidate | Contract to protect | Boundary |
| --- | --- | --- |
| Presentation Primary Only | An eligible source Moment composes one ordered DJ-role primary segment, or no Speech when the Moment has no approved content. | Immutable Presentation and safe projection. |
| Presentation Sidekick | An eligible approved summary adds one ordered Sidekick segment without creating facts or changing the source Moment. | Immutable Presentation and safe projection. |
| Presentation Fallback | Disabled, ineligible or failed Sidekick enrichment remains deterministic Primary Only and never invalidates its source Moment. | Composer fallback and safe projection. |
| Presentation Projection | Source linkage and supported Presentation content reach Broadcast while Runtime-only Context remains absent. | Broadcast projection only. |
| Presentation Determinism | Equivalent Moment, Context and policy compose equivalent immutable Presentation and projection. | Composer and projection boundary. |

These scenarios are deliberately not renderer scenarios. A future Receiver E2E
or hardware qualification may independently verify a Renderer Host, but it is
not Presentation Verification and cannot become a prerequisite for it.

## Qualification direction

The intended future sequence is:

```text
Presentation Verification
  -> Presentation Golden Scenarios
  -> Golden Smoke
  -> Qualification
```

Once separately implemented and governed, Golden Regression may validate both
Session Intelligence and Presentation Golden Scenario families. This is a
future qualification direction only; it does not change the current Golden
Smoke, Golden Regression, CI or capture implementation.

## Scope exclusions

This architecture does not authorize renderer tests, browser tests, visual
assertions, audio assertions, TTS provider tests, generated-audio validation,
hardware qualification, Presentation capture implementation, CI changes,
Golden Smoke changes, Golden Regression changes, Session Intelligence changes,
new Broadcast transport, persistence, new Runtime state or renderer
implementations.

## Canonical references

- [Presentation Composer Architecture](../product/PRESENTATION_COMPOSER_ARCHITECTURE.md)
- [Presentation Capability Architecture](../product/PRESENTATION_CAPABILITY_ARCHITECTURE.md)
- [Speech Rendering Contract](../technical/SPEECH_RENDERING_CONTRACT.md)
- [Session Intelligence E2E Verification Architecture](SESSION_INTELLIGENCE_E2E_ARCHITECTURE.md)
- [Golden Scenario Governance](GOLDEN_SCENARIO_GOVERNANCE.md)
- [Session Intelligence Qualification Policy](SESSION_INTELLIGENCE_QUALIFICATION_POLICY.md)
