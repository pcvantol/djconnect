# Trusted Delivery Startup Failure Root Cause Analysis

Date: 2026-07-13  
Decision: `STARTUP_FAILURE_ROOT_CAUSE_NOT_YET_IDENTIFIED`

## Scope and safety state

This is a diagnosis-only investigation. No workflow or governance design was
changed. `sha_pinning_required` remains effectively `false` in every active
repository following the earlier safety rollback.

## Timeline and evidence

1. Recursive closure validation passed on the merged default branches.
2. SHA enforcement was enabled and live read back as `true` in all ten
   repositories.
3. Representative `workflow_dispatch` validation runs were started.
4. API `29232155802`, Apple `29232157161`, Pi `29232158794`, Windows
   `29232160264`, ESP32 `29232161943`, Website `29232163457`, and Firmware
   `29232165212` completed as `startup_failure` within one or two seconds.
5. The Actions jobs API reports `total_count: 0` for sampled API and Pi runs;
   timing reports only 1000 ms and 2000 ms respectively. No job logs exist.
6. SHA enforcement was rolled back and live read back as `false` everywhere.

## Live GitHub configuration

The affected repositories have Actions enabled, `allowed_actions: all`,
read-only default workflow permissions and pull-request review approval
disabled. The only configuration change between the preceding successful
state and the failed representative runs was
`sha_pinning_required: false` to `true`.

## Workflow graph result

GitHub's run metadata contains resolved `referenced_workflows`, not merely the
caller declaration. API resolved:

```text
ci-cd.yml
  -> pcvantol/djconnect/.github/workflows/software-assurance-governance.yml
     @ 4e57f1c8343b0eb863fdeb68f59b9b872f18b748
```

Pi resolved that governance workflow plus
`djconnect-python-ci.yml@4e57f1c8343b0eb863fdeb68f59b9b872f18b748` and its
nested governance source at `1ff14bcccce3921410c2d84dfb784d21a766edf7`.
The terminal `actions/checkout` reference in both resolved governance sources
is the full SHA `9c091bb21b7c1c1d1991bb908d89e4e9dddfe3e0`.

This matches the recursive validator's dependency graph. There is no observed
workflow-resolution, reusable-workflow-resolution or mutable-terminal-action
divergence.

## Classification

| Investigation point | Evidence-based result |
| --- | --- |
| Reusable workflow resolution | Passed: GitHub reports exact resolved workflow SHAs. |
| Terminal action pinning | Passed: recursive scan and registry checks passed. |
| Runner allocation | Excluded: zero jobs were created. |
| Action download | Excluded: no job exists to download an action. |
| Workflow graph construction | Passed far enough for GitHub to report referenced workflows. |
| GitHub Actions policy evaluation | Suspected stage: it is the only changed condition and failure precedes job creation. |
| Exact rejecting rule / platform defect | Not proven: GitHub supplied neither job log nor policy diagnostic. |

## Root cause and confidence

The objective root cause cannot yet be identified beyond a pre-job GitHub
Actions startup rejection associated with enabling SHA enforcement. The
evidence supports policy evaluation as the failure stage, but does not prove
which policy rule, workflow node, or GitHub platform behavior rejected the
run. No unsupported GitHub limitation is asserted.

Confidence: **high** for the pre-job boundary and successful reusable-workflow
resolution; **insufficient** for a more specific root-cause claim.

## Required remediation

No implementation remediation is authorized or proposed by this diagnosis.
Further progress requires a GitHub-provided startup diagnostic or a separately
authorized, bounded minimal-reproducer investigation. Prompt 3 remains
blocked and Prompt 4 remains blocked.
