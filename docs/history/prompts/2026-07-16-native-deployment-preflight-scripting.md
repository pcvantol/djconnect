# Native Deployment Preflight Scripting

**Prompt ID:** `G2-RELEASE-NATIVE-PREFLIGHT-SCRIPTING-001`
**Prompt Title:** Platform Release Engineering: use native runner scripting for deployment readiness
**Generation:** 2
**Engineering Program:** Platform Release Engineering
**Branch:** `codex/native-deployment-preflight-scripting`
**Commit SHA:** `5704905e5f39e266ac07b34e20391a14e1519fe9`
**Pull Request:** reviewable pull request created from this branch
**Decision:** `NATIVE_DEPLOYMENT_PREFLIGHT_SCRIPTING_REVIEWABLE`

## Validation summary

Windows deployment run `29483901468` reached the shared readiness preflight
after its workflow-local service-shell repairs. The preflight resolved Bash to
the Windows WSL shim and failed because WSL required an update. The failure
occurred before manifest validation, artifact download, target mutation or
evidence publication.

The shared composite action now runs the same fail-closed contract in
PowerShell 7 on Windows and Bash elsewhere. YAML parsing and a static review
verify that each platform has exactly one native preflight step. Live Windows
execution remains deferred until the Windows consumer pins this merged
immutable action SHA and the service exposes PowerShell 7 machine-wide.

## Created artifacts

- This immutable Prompt History record.

## Updated artifacts

- Shared deployment readiness action.
- Deployment input contract.
- Rolling engineering, repository, management and prompt records.

## Known limitations

- The existing Windows consumer still pins the prior immutable shared action
  revision and retains its local Bash prerequisite.
- The Windows `NETWORK SERVICE` account must have a machine-level PowerShell
  7 installation before a consumer using the new action can execute.

## Deferred work

- Pin the Windows consumer to the merged action SHA and remove its redundant
  Bash prerequisite.
- Rerun the already authorized Windows manifest-bound deployment and dispatch
  smoke only on deployment success.

## Recommended next prompt

Platform Release Engineering: adopt the merged native preflight in the Windows
consumer, then qualify the already authorized Windows deployment and smoke.
