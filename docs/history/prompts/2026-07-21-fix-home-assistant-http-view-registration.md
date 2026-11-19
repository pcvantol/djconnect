# Prompt History: Fix Home Assistant HTTP View Registration

**Prompt ID:** Home Assistant HTTP View Registration Repair
**Generation:** V4
**Engineering program:** DJConnect Product Development
**Branch:** `codex/fix-ha-dev-view-registration`
**Pull Request:** [#356](https://github.com/pcvantol/djconnect/pull/356)
**Merge Commit:** `d62fd2d41b8a2896cc1b6fe4f12cf3fdaacec8f7`
**Decision:** `MERGED_UNRECONCILED` pending dedicated Finalization
**Execution date:** 2026-07-21
**Created:** 2026-07-21
**Updated:** 2026-07-21

## Outcome

The HA development deployment exposed an existing startup defect: the
parameterless Transport Capabilities HTTP view was constructed with a Home
Assistant argument. This prevented the DJConnect integration from completing
setup and therefore prevented all registered routes, including the Universal
Receiver, from becoming available.

The repair constructs the view according to its parameterless contract and
adds a focused registration regression test covering both parameterless views.
No Runtime, Broadcast, Receiver, API or ownership behaviour changed.

## Validation

- `python -m unittest discover -s tests` — 1315 passed, 7 skipped
- `ruff check custom_components tests` — passed
- `git diff --check` — passed
- `python -m unittest tests.test_capability_completion_lifecycle` — passed
- `./scripts/runner/bootstrap_djconnect_macos_host.sh --verify` — MATCH
- HA development deployment — `/djconnect/receiver` returned HTTP 200

## Known limitations

This is a startup-registration repair only. It does not change the Receiver's
connection contract, introduce new data transport or add browser authority.

## Deferred work

Universal Receiver experience capabilities remain separately authorized. The
existing Broadcast and Runtime ownership boundaries remain unchanged.

## Recommended next prompt

After this dedicated Finalization and Workspace Cleanup restore
`MERGED_RECONCILED` and `WORKSPACE_READY`, select the next bounded Universal
Receiver experience capability from current repository evidence.
