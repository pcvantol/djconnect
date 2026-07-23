# Prompt History: Speech Rendering contract

**Prompt ID:** Renderer-neutral Speech Rendering contract
**Generation:** V4
**Engineering program:** DJConnect Product Development
**Branch:** `codex/define-speech-rendering-contract`
**Pull Request:** [#408](https://github.com/pcvantol/djconnect/pull/408)
**Merge Commit:** `2eb658b66aa2a366183a4114218a7f0138210744`
**Decision:** `MERGED_RECONCILED` after dedicated Finalization
**Execution date:** 2026-07-23
**Created:** 2026-07-23

## Outcome

PR #408 establishes one canonical renderer-neutral Speech Rendering Contract.
Speech Presentation is consumed only after Broadcast. Every Renderer Host sees
the same immutable renderer-safe Presentation Projection and preserves ordered
segments and semantic Speaker Roles. A host never generates, alters, reorders,
splits or infers Presentation content.

Role-to-Voice mapping is local to an Audio Renderer Host:

```text
Speaker Role -> configured local voice -> configured local TTS provider
```

The server receives and selects none of those values. Broadcast remains
text-only: it excludes TTS provider, voice, provider payload, audio asset,
locale, room-routing instruction and renderer configuration. Speech Audio and
Speech Text are alternative local interpretations. If audio is unavailable,
text may render; if neither capability exists, the Presentation remains valid.

The Universal Receiver, VibeCast, Apple and Home Assistant are documented as
future consumers only. This work adds no Renderer, TTS, transport, Runtime,
Planner, Knowledge Engine or Session Flow implementation.

## Validation

- `python3.11 -m unittest discover -s tests` — 1,389 passed, 7 skipped
- `python3.11 -m ruff check custom_components/djconnect tests` — passed
- `python3.11 -m tools.software_assurance.validate` — passed
- `git diff --check` — passed
- development-host verification — MATCH
- PR #408 merge, current-main containment and removed remote implementation
  branch — verified

## Deferred work

Home Assistant, Apple, Google TV and VibeCast renderer implementations; voice
configuration UI; synchronized speech highlighting; Presentation Memory and
Presentation Cast; multi-audio-renderer policy; speech asset generation; and
cloud speech remain separate future capabilities.

## Recommended next prompt

Follow the active, separately authorized capability in the canonical planning
records. This contract does not authorize a renderer implementation.
