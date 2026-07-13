# SHA Enforcement Minimal Reproducer

Date: 2026-07-13  
Decision: `STARTUP_FAILURE_MINIMAL_REPRODUCER_IDENTIFIED`

## Isolated scope

Repository: `pcvantol/djconnect-sha-enforcement-reproducer` (private and
temporary). No production workflow, secret, self-hosted runner, publication or
deployment was used. All ten active repositories, and the test repository,
are currently effective `sha_pinning_required: false`.

## Matrix

| Case | Graph | Enforcement | Run ID | Jobs | Result |
| --- | --- | --- | --- | ---: | --- |
| 1a | `workflow_dispatch -> shell` | false | `29233817532` | 1 | PASS |
| 1b | `workflow_dispatch -> shell` | true | `29233827686` | 1 | PASS |
| 2 | `workflow_dispatch -> actions/checkout@9c091bb…` | true | `29233857176` | 1 | PASS |
| 10 | `workflow_dispatch -> canonical cross-repository governance reusable workflow@4e57f1c… -> checkout@9c091bb…` | true | `29233882040` | 0 | `startup_failure` |

## Smallest observed failing graph

The last passing graph has one direct terminal action. The first failing graph
adds the tested cross-repository reusable-workflow characteristic:

```text
caller
  -> pcvantol/djconnect/.github/workflows/software-assurance-governance.yml
     @4e57f1c8343b0eb863fdeb68f59b9b872f18b748
       -> actions/checkout@9c091bb21b7c1c1d1991bb908d89e4e9dddfe3e0
```

Every remote reference is a full SHA. GitHub resolves and reports the called
workflow in `referenced_workflows`, but creates zero jobs and returns
`startup_failure` after two seconds.

## Conclusion

The reproducer identifies an observed compatibility boundary: under this
account's SHA-enforcement setting, the tested cross-repository reusable
workflow graph fails before job creation, while shell-only and direct pinned
actions execute. Confidence is high for this boundary, but insufficient to
claim an undocumented internal GitHub cause.

Cases 3–9 and 11 were not run because they add graph complexity after the
earliest observed failing characteristic. A second isolated producer
repository would be needed to independently test a shell-only cross-repository
reusable workflow; this task permits exactly one test repository.

## Supported next steps (not implemented)

1. Open GitHub Support with the documented runs and API evidence.
2. Separately authorize a two-repository reproducer.
3. Evaluate local workflow generation or vendoring only after remediation is
   explicitly authorized.
