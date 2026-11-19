# GitHub Support Case: SHA Enforcement Pre-Job Startup Failure

With `sha_pinning_required: true`, private repository
`pcvantol/djconnect-sha-enforcement-reproducer` runs shell-only
(`29233827686`) and direct full-SHA checkout (`29233857176`) workflows, but
the full-SHA canonical reusable-workflow caller `29233882040` ends as
`startup_failure` with zero jobs.

The caller uses:

```yaml
uses: pcvantol/djconnect/.github/workflows/software-assurance-governance.yml@4e57f1c8343b0eb863fdeb68f59b9b872f18b748
```

GitHub reports the same SHA in `referenced_workflows`; the called workflow
uses only pinned `actions/checkout@9c091bb21b7c1c1d1991bb908d89e4e9dddfe3e0`.
The failing run lasted two seconds, produced no job log, and disabling
enforcement restores execution. No secrets, self-hosted runners, deployment
or publication behavior is involved.
