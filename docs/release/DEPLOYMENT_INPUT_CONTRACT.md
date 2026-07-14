# Deployment Input Contract

Every operational deployment workflow accepts and validates these required
`workflow_dispatch` inputs:

| Input | Required value/format |
|---|---|
| `action` | exactly `deployment` |
| `candidate_sha` | full lowercase 40-character Git SHA on approved `main` lineage |
| `execution_mode` | exactly `execute` |
| `manifest_id` | canonical manifest identifier bound to the candidate SHA |
| `platform_version` | `Major.Minor` platform version matching the manifest |
| `release_profile` | an allowlisted supported profile, currently `INTERNAL_RELEASE` |

Target-specific inputs are permitted only when schema-bound, allowlisted,
validated, documented and necessary for the canonical target. They cannot
replace or weaken any required input.
