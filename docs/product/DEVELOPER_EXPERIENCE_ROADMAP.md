# Developer Experience and Verification Roadmap

## Status

**Active workstream.** The single active next capability is **Developer Session
Bootstrap**. This document records product-development sequencing only; it does
not authorize implementation beyond that capability.

## Purpose

The Session Intelligence Runtime and Universal Receiver V1 foundation are
complete. The next work makes the existing server-owned pipeline practical to
start, inspect and verify during development without creating a second Runtime
or granting a Renderer Host authority.

The canonical pipeline remains:

```text
Playback Observation -> Session Runtime -> Planner -> Knowledge Engine
-> DJ Moment Engine -> Session Flow -> Broadcast -> Renderer Hosts
```

Developer tooling observes or invokes bounded server-owned lifecycle entry
points. It never reimplements Planner, Knowledge, DJ Moment, Flow or Broadcast
behaviour.

## Active next capability

### 1. Developer Session Bootstrap — active / next

The later implementation will establish one Home Assistant development or
service boundary that starts an ordinary server-owned Session and establishes a
Session identifier. It may establish bounded, ephemeral, session-scoped
Receiver access for manual development and CI, and it must provide a safe stop
or cleanup path.

It must preserve Runtime, Planner, Knowledge Engine, DJ Moment Engine, Session
Flow and Broadcast ownership. A browser must not create Sessions, own access
authority or acquire a new synchronization path. The capability is not
implemented by this roadmap update.

## Ordered sequence

The following order is intentional. Only item 1 is active; every later item
needs its predecessor evidence and a separate authorization.

| Order | Capability | Status | Boundary |
| --- | --- | --- | --- |
| 1 | Developer Session Bootstrap | Active / next | Starts and cleans up an ordinary server-owned Session with bounded developer access. |
| 2 | Receiver connection bootstrap and safe access exchange | Ready after 1 | Supplies an installation-owned, ephemeral access handoff; no browser authority. |
| 3 | Read-only Developer Overlay architecture | Deferred pending separate architecture review | A development-only, non-authoritative view, disabled in production by default and separate from the normal Receiver. |
| 4 | Accelerated Session Simulation architecture | Parked | Defines use of the real pipeline with simulated observation and an accelerated clock; no alternate production Runtime. |
| 5 | Scenario Runner | Deferred | Executes authorized scenarios through the established developer boundary. |
| 6 | DJMoment and Flow capture | Deferred | Captures only canonical immutable outcomes and Flow evidence. |
| 7 | Intelligence Evaluation Report | Deferred | Reports bounded evidence from captured scenarios. |
| 8 | Golden Session regression suite | Deferred | Uses approved scenarios and canonical captures for regression protection. |
| 9 | Optional TTS session replay | Deferred | Replays eligible existing presentation output without creating canonical audio persistence. |
| 10 | Side-by-side session comparison | Deferred | Compares captured canonical outcomes; it does not create a competing planner. |

## Simulation position

Session Simulation is parked, not active work. Its later architecture must run
the real Runtime pipeline from simulated playback observation, use an explicit
accelerated clock, capture canonical outcomes and produce a bounded report. It
must not add a parallel production Runtime, business-logic branch, Planner,
Knowledge Engine, DJ Moment Engine, Session Flow or Broadcast implementation.

## Product work kept separate

Normal product backlog remains distinct from Developer Experience: player
controls through server APIs, Session start and selection flow, Ask DJ,
Discover, responsive refinement, and local deployment/install UX need their
own product authorization. Universal Receiver V1 remains local-first and
installation-owned; Home Assistant delivery-mechanism selection is deferred.

## Deferred intelligence

Preferences, Music DNA expansion, Narrative Sequencing, Lyrics, Discover
Evolution, Audience Intelligence, Playback Observation Stage 2 and Continue
Stage 2 remain deferred. Audience Intelligence is a low-priority future
Planner-influence capability, not a prerequisite for Developer Experience or a
new execution path.

## Receiver duplicate-work guard

Before any new Universal Receiver capability is authorized, Pre-Flight must
inspect current `main` and the canonical Receiver architecture. Capability
proposals must not repeat completed Session Flow Timeline or Now Playing work,
and must identify an existing renderer-safe Broadcast projection rather than
introduce a duplicate contract.
