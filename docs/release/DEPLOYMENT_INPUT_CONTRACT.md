# Deployment Input Contract

Every operational deployment workflow accepts and validates these required
`workflow_dispatch` inputs:

| Input | Required value/format |
|---|---|
| `action` | exactly `deployment` |
| `candidate_sha` | full lowercase 40-character Git SHA on approved `main` lineage |
| `execution_mode` | exactly `execute` |
| `manifest_id` | canonical manifest identifier bound to the candidate SHA |
| `artifact_id` | immutable qualified artifact identifier referenced by the manifest |
| `artifact_sha256` | lowercase SHA-256 digest referenced by the manifest |
| `target` | allowlisted manifest deployment target identifier |
| `platform_version` | `Major.Minor` platform version matching the manifest |
| `release_profile` | an allowlisted supported profile, currently `INTERNAL_RELEASE` |

Target-specific inputs are permitted only when schema-bound, allowlisted,
validated, documented and necessary for the canonical target. They cannot
replace or weaken any required input.

## Mandatory deployment-readiness preflight

Before any target mutation, every deployment consumer must run the canonical
`deployment-readiness-preflight` action. The preflight is a separate,
fail-closed workflow step and records no secrets. It validates:

- the manifest-bound identity and artifact checksum;
- the actual runner OS and architecture against the target requirement;
- non-empty presence of every target-specific configuration value required by
  the consumer, without printing a value;
- a concrete smoke-contract identifier, rejecting `NOT_IMPLEMENTED` and other
  placeholders.

The preflight always uses the runner's native scripting runtime: PowerShell 7
(`pwsh`) on Windows and Bash on non-Windows runners. A Windows self-hosted
runner must therefore expose a machine-level PowerShell 7 installation to its
service account. Windows deployment consumers must not depend on WSL or a
user-profile-only shell merely to execute this preflight.

Artifact publication and manifest approval never satisfy this preflight. A
failed preflight blocks only its target, produces `TARGET_NOT_READY`, and does
not block deployment or smoke of other independently authorized targets. A
retry uses the same manifest-bound artifact and reruns the preflight first.

## Canonical target identifiers

The canonical Raspberry Pi runtime deployment target is exactly
`rbpi-djconnect`. Any Raspberry Pi deployment or post-deployment smoke
consumer and any approved manifest must use this value; aliases and inferred
hostnames are not valid target identifiers.

## Manifest-bound artifact selection

The deployment workflow does not select an artifact or version. It consumes an
approved release manifest and rejects `PRIVATE_NETWORK_DEPLOYMENT_NOT_AUTHORIZED`
before mutation when the manifest is missing, unknown, not qualified, stale or
superseded; when candidate SHA, platform version or release profile differs;
when the artifact ID or SHA-256 is not referenced; or when the target is not
allowlisted by that manifest. Arbitrary local paths and mutable selectors such
as `latest` are never valid deployment inputs.

The manifest binds `candidate_sha`, `platform_version`, `manifest_id`,
`artifact_id`, `artifact_sha256`, `target`, `release_profile`, `action` and
`execution_mode`. The only mutation values are `action=deployment` and
`execution_mode=execute`.


## Bounded Pi multi-instance extension

The canonical target remains `rbpi-djconnect`. The existing rc.5 two-instance
producer dependency is specified by [Pi two-host contract v1](PI_TWO_HOST_DEPLOYMENT_CONTRACT_V1.md),
its closed request/manifest schemas and immutable identity-only inventory.
Its required instance/profile/inventory qualifiers supplement every existing
required input. They do not authorize dispatch or widen historical manifests.
Only a matching qualified consumer and a new exact approved operational binding
may use this extension; old single-host consumers fail closed.


### Distinct rc.6 producer contract

The separately versioned [Pi two-host contract v2](PI_TWO_HOST_DEPLOYMENT_CONTRACT_V2.md)
defines rc.6-only request V3 and operational manifest V3 structure. Existing
rc.5 contract v1/V2 schemas and operative history remain unchanged. Both use the
same closed identity inventory and canonical target; no fallback, new target,
dispatch authority or artifact approval follows from this additive contract.
An operational rc.6 binding is a later protected delivery after actual qualified
Pi source/Finalization, matching consumer, publication hashes and human authority.
