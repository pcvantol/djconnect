# macOS Runner-Host Bootstrap Post-Merge Repin

**Prompt ID:** `G2-PLATFORM-EVOLUTION-MACOS-BOOTSTRAP-REPIN-001`
**Prompt Title:** Platform Evolution: repin macOS runner-host bootstrap workflow references to merged main
**Generation:** 2
**Engineering Program:** Platform Evolution
**Branch:** `codex/repin-macos-bootstrap-main`
**Commit SHA:** `dd65f70d3ce2632f8b4737daf3ed7b3c2e8a58cd`
**Pull Request:** Reviewable pull request created from this branch
**Decision:** `MACOS_RUNNER_BOOTSTRAP_MAIN_REPIN_REVIEWABLE`

## Validation Summary

PR #144 merge commit `452bed7655e579d3fb12b7b379f8fc0b70a8c342` is an ancestor
of the selected immutable current-`main` SHA
`3d7d24a84b3aaacb8f2fb229e09c33da85e0545d`. The selected commit contains the
reusable Software Assurance governance workflow and the canonical-policy
checkout fallback. All eight caller references and that checkout reference are
repinned to the same immutable merged-`main` SHA. Static workflow and runtime
validation confirms the changed callers remain valid.

## Created Artifacts

- This immutable Prompt History record.

## Updated Artifacts

- Eight reusable-governance workflow callers.
- Reusable governance workflow canonical-policy checkout pin.
- macOS runner-host bootstrap readiness record.
- Rolling engineering, repository, management and prompt records.

## Known Limitations

- The PR #144 feature branch remains retained until this repin PR is merged
  and its checks are green.

## Deferred Work

- Delete `codex/macos-runner-recovery-bootstrap` only after the merged repin
  and successful required checks.
- Continue Windows or Home Assistant Release 3.3 qualification only through
  their separate authorized increments.

## Recommended Next Prompt

Repository hygiene: after this repin PR is merged and green, remove the
retained PR #144 feature branch and reconcile the rolling records.
