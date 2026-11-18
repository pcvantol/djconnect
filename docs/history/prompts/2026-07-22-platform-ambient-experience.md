# Prompt History: Platform Ambient Experience

**Prompt ID:** Platform Ambient Experience
**Generation:** V4
**Engineering program:** DJConnect Product Development
**Branch:** `codex/document-platform-ambient-experience`
**Pull Request:** [#384](https://github.com/pcvantol/djconnect/pull/384)
**Merge Commit:** `e07b259e41a37f4bb937f2b772a4aff6754462d2`
**Decision:** `MERGED_RECONCILED` after dedicated Finalization
**Execution date:** 2026-07-22

## Outcome

PR #384 records Platform Ambient Experience as deferred architecture. It keeps
Universal Receiver platform-neutral and defines a future local Platform Adapter
boundary for wall-panel hardware concerns only. The document preserves deferred
Display Policy vocabulary, Ambient Audio, optional renderer output of
server-generated speech and a passive Development Replay workflow.

The Raspberry Pi Reference Renderer remains local-first, installation-owned,
stateless and Renderer-only. It may eventually observe the existing Golden
Scenario execution through Broadcast for visual verification, UX validation and
engineering debugging, but it does not execute or control verification.

No production code, Runtime behavior, Universal Receiver implementation,
transport, TTS, hardware integration or Raspberry Pi-specific code changed.

## Validation

- `python -m unittest discover -s tests` — 1,345 passed, 7 skipped
- `python -m ruff check custom_components/djconnect tests` — passed
- `git diff --check` — passed
- development-host verification — MATCH
- PR #384 merge and current-main containment — verified

## Deferred work

Implementation remains blocked until reference hardware is available, Universal
Receiver maturity supports real-world evaluation and the Golden Scenario
infrastructure can attach a passive Renderer Host without weakening its one
canonical execution path.
