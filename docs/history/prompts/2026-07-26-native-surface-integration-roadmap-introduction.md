# Prompt History: Native Surface Integration Roadmap Introduction

**Prompt ID:** Native Surface Integration Roadmap Introduction
**Generation and engineering program:** Generation 2, Phase 1 — DJ Intelligence
Evolution / Platform Evolution
**Engineering mode:** Product & Platform Architecture
**Branch:** `codex/native-surface-integration-roadmap`
**Decision:** `GO_NATIVE_SURFACE_ROADMAP_REGISTERED`
**Execution date:** 2026-07-26
**Scope:** roadmap and architecture registration only; no assessment,
implementation, Runtime, Renderer, API or product code.

## Archived prompt

Introduce the future **Native Surface Integration** capability family without
changing the current Execution Horizon, backlog priorities or any production
behavior. Record only these conceptual categories and constraints:

- **Session Control Surfaces:** App Shortcuts, App Icon Context Menu, Jump
  Lists, Spotlight and Siri App Intents may submit an explicit existing Session
  lifecycle request to start, continue, open or end a Session, or open Ask DJ.
  They must not execute DJ Intelligence, control playback or create automatic
  Session mutations.
- **Session Surfaces:** Live Activity, Dynamic Island and Lock Screen Live
  Activity are available only for an active DJ Session, consume renderer-safe
  projections and disappear when that Session ends.
- **Information Surfaces:** iOS/macOS Widgets and future watchOS complications
  are persistent renderer-safe information surfaces for Session Direction and
  current DJMoment, never a second music player.

Record the canonical boundaries:

```text
Session Control Surfaces -> Session Runtime -> Renderer
Session Surfaces -> Renderer-safe Projections -> Apple Renderer Host
Information Surfaces -> Renderer-safe Projections -> Widgets
```

Register **Apple Native Surface Capability Assessment** as a later,
repository-first inventory of Widgets, Live Activity, Dynamic Island, Lock
Screen Activity, App Shortcuts, App Icon Context Menu, Spotlight, Siri App
Intents, Notifications, Handoff and Universal Links. Do not perform that
assessment or implement Apple code. Record Small/Medium/Large Widgets, Live
Activity, Dynamic Island, Lock Screen Activity, App Shortcuts and Siri App
Intents only as separately bounded, future candidates.

Position the family after CMB-05, CMB-06 and CMB-07, outside the current
Execution Horizon. Update only the Capability Model Backlog, Renderer
Experience Roadmap, relevant roadmap navigation and this immutable Prompt
History. Validate roadmap consistency and `git diff --check`. End with exactly
one decision: `GO_NATIVE_SURFACE_ROADMAP_REGISTERED` or
`NO_GO_ROADMAP_INSUFFICIENT_CONTEXT`.

## Validation and limitations

- Repository synchronization, predecessor verification and current development
  host qualification completed before this record was created.
- Validation is documentation-only: roadmap consistency checks and
  `git diff --check` apply; no Runtime, Renderer, API, product or Apple-source
  validation is implied.
- The Apple capability inventory, architecture assessment and every candidate
  implementation remain future, separately authorized work.

## Recommended next prompt

Resume the canonical Execution Horizon; Native Surface Integration may be
considered only after CMB-05, CMB-06 and CMB-07 are complete or after an
objective canonical-roadmap change.
