# VibeCast Pi owner handoff — Core source Finalization

- **Assignment:** `DJC-VIBECAST-PI-OWNER-HANDOFF-V1-20261004`.
- **Decision:** Core source merged and exact-main qualified; integrated product
  acceptance `BLOCKED` pending physical Pi receipt.
- **Branch:** `codex/vibecast-pi-owner-handoff-finalization` from main
  `c46b41cb77354b57f3388ddde8e67a462b2ff919`.
- **Commit SHA:** Implementation merge
  `c46b41cb77354b57f3388ddde8e67a462b2ff919`, reviewed implementation
  head `db368a92b97f0e5bbd033baa877a65892c0a1138`.
- **Pull Request:** [Core #1104](https://github.com/pcvantol/djconnect/pull/1104);
  paired [Apple #89](https://github.com/pcvantol/djconnect-app/pull/89).
- **Validation:** 1,475 local Core tests passed and 7 skipped before merge;
  exact-main [Validate](https://github.com/pcvantol/djconnect/actions/runs/37192659840),
  [CodeQL](https://github.com/pcvantol/djconnect/actions/runs/37192659676),
  [artifact](https://github.com/pcvantol/djconnect/actions/runs/37192754992)
  and [evidence](https://github.com/pcvantol/djconnect/actions/runs/37192755106)
  succeeded. Independent review of both exact source heads found no remaining
  P1/P2 after corrections.
- **Created documents:** This immutable source Finalization record.
- **Updated documents:** `ENGINEERING_STATUS.md`, `REPOSITORY_STATUS.md`,
  `MANAGEMENT_SUMMARY.md`, `PROMPT_INDEX.md`, `PRODUCT_BACKLOG.md` and
  `docs/product/VIBECAST_REFERENCE_RENDERER_INCREMENT.md`; implementation had
  updated the latter product design and `SYNC_PROMPTS.md`.
- **Outstanding blocker:** The exact Core artifact now runs in HA-dev Docker;
  the renderer responds and the exact-main iPhone simulator is paired. Live
  session start exposed Apple `keyNotFound(current_direction)` at
  `session.planner`: HA provides direction in `broadcast.planner`. The Apple
  contract must be corrected, then approval, snapshot/updates, reconnect,
  Runtime end/privacy and token non-persistence must be proven on the physical
  portrait Pi. See the [live readback](https://github.com/pcvantol/djconnect/issues/1101#issuecomment-5980280006).
  Source CI and simulator pairing alone are not integrated acceptance.
- **Recommended next prompt:** Continue this same first-slice integrated
  acceptance and record its exact producer/consumer receipt in the owning
  [central register](https://github.com/pcvantol/djconnect/issues/1101).
  Do not start the later Google Cast slice.

The canonical five Planned Execution Horizon items are unchanged. No public
release, production deployment, deployment workflow, workflow change or new
product selection occurred; the authorized HA-dev test installation is recorded
above.
