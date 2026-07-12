# Software Assurance CI Governance Foundation

This directory is the reusable implementation foundation created by Software
Assurance Generation 1, Prompt 1. It is deliberately separate from
`.github/workflows/`: it defines policy, templates and validation without
rolling any policy into a repository workflow.

## Contents

- `policy/governance-policy.json` is the sole canonical machine-readable
  policy source.
- `schema/governance-policy.schema.json` describes the portable policy shape.
- `templates/workflow-governance.json` is a shared metadata template for a
  future repository rollout.

`tools/software_assurance` loads this policy and exposes reusable validators.
Run the canonical policy self-check with:

```text
python -m tools.software_assurance.validate
```

The command validates the policy and template only. It does not inspect,
modify, enable or dispatch any GitHub workflow.

## Override Model

Future repositories may provide a narrow override mapping to the validator.
Overrides are rejected when they relax protected policy constraints, including
permissions, required metadata, retry bounds and retention minima. Repository
rollout and any workflow consumption remain owned by Prompt 2.
