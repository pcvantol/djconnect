# Prompt History: Knowledge Source Qualification & Knowledge Object Contract

**Prompt ID:** Canonical Knowledge Source Qualification & Knowledge Object
Contract

**Generation and engineering program:** Generation 2 — Product Engineering

**Branch:** `codex/knowledge-source-qualification-contract`

**Decision:** `GO_PROVIDER_INDEPENDENT_KNOWLEDGE_OBJECT_ARCHITECTURE`

**Execution date:** 2026-07-30

## Objective

Make the existing V4 Knowledge Engine explicitly provider-independent through
one canonical Source Contract, Knowledge Qualification model, internal
Knowledge Resolver boundary and canonical Knowledge Object contract.

## Repository truth and pre-flight

The canonical repository was synchronized on `main` with a clean working tree.
The required macOS host verification initially found unavailable Docker/Home
Assistant and expired ignored verification artifacts. After explicit maintainer
authorization, the existing maintenance task was run and Docker/Home Assistant
were restarted; the final desired-state verification reported `MATCH`.

Existing V4 evidence confirms unchanged ownership: the Planner owns Knowledge
Intent and timing; the Knowledge Engine retrieves and assembles context; the
DJ Moment Engine owns storytelling; Broadcast distributes immutable Moments;
and Renderer Hosts never resolve knowledge independently.

## Implemented bounded documentation contract

- separate Source Contract eligibility from per-resolution Knowledge
  Qualification;
- define the Knowledge Resolver as an internal Knowledge Engine responsibility
  and terminate raw provider payloads at that boundary;
- define provider-independent Knowledge Object, Knowledge Type, Knowledge
  Domain, Storytelling Value and Knowledge Context semantics;
- make rights, attribution, processing, retention and presentation scope
  mandatory qualification inputs;
- assign all source-cache layers to the Resolver without changing cache
  behaviour; and
- confirm that only DJMoments, never Knowledge Objects, enter Broadcast.

## Validation

- repository synchronization and clean-tree verification;
- macOS desired-state verification returned `MATCH` before content mutation;
- architecture ownership, source-boundary and terminology inspection;
- Markdown link validation and `git diff --check`.

## Explicitly deferred

No source provider, external integration, Runtime capability, Planner policy,
cache implementation, Lyrics Knowledge, API, Broadcast schema, renderer
behaviour or Golden Scenario semantic change is introduced.

## Required finalization

After the refinement PR merges, a dedicated governance-only Finalization must
reconcile the rolling records, preserve this immutable history and complete
Workspace Cleanup before another implementation increment.
