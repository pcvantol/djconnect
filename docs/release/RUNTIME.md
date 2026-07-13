# Platform Release Orchestrator Runtime

Status: simulation-only implementation  
Scope owner: `pcvantol/djconnect`

## Purpose

`tools.release` implements the reusable Platform Release Orchestrator control
plane. It consumes an ownership document and caller-supplied candidate facts to
compose a canonical Release Manifest, execution plan, readiness result,
qualification plan, artifact plan and rollback plan.

It does not access sibling repositories by name, update versions, create tags,
publish artifacts, deploy, execute verification, or execute rollback.

## Inputs

- `REPOSITORY_OWNERSHIP.md` supplies repository records dynamically. Repository
  names are parsed from ownership headings; they are not embedded in runtime
  code.
- `--platform-version` supplies the required `Major.Minor` train.
- optional JSON string maps supply candidate repository versions, source SHAs,
  evidence states and plan-local role overrides.

The current ownership prose safely identifies distribution-only repositories.
An ownership record may later declare `Release role:` explicitly. Plan-local
role overrides are supported as immutable inputs until that canonical metadata
exists; they do not change Repository Ownership.

Mandatory source/release-source/distribution records enter the default plan.
Optional and future records are still discovered and preserved in the manifest,
but are marked `included: false` / `not in scope by default` until a later
scope-selection contract explicitly includes them. They never become mandatory
because of their repository name.

## CLI

Run from the repository root:

```bash
python -m tools.release --platform-version 3.3 plan
python -m tools.release --platform-version 3.3 readiness
python -m tools.release --platform-version 3.3 graph
python -m tools.release --platform-version 3.3 manifest
python -m tools.release --platform-version 3.3 simulate
python -m tools.release --platform-version 3.3 explain
```

All commands are simulations. They return JSON to standard output and do not
write a Release Manifest to the repository. With missing candidate facts, the
simulation succeeds but correctly reports `NOT_READY` or `BLOCKED` with every
condition explained.

Candidate facts can be passed with JSON maps:

```bash
python -m tools.release \
  --platform-version 3.3 \
  --versions-file versions.json \
  --shas-file shas.json \
  --evidence-file evidence.json \
  --mode dry_run \
  simulate
```

`versions.json` maps discovered repository IDs to `Major.Minor.Patch` values;
`shas.json` maps them to source identities; and `evidence.json` maps evidence
classes to `PASS`, `FAIL`, `MISSING` or another declared state. The runtime
also provides local, non-mutating `read_repository_version()` support for
common `manifest.json`, `package.json`, `pyproject.toml` and `VERSION` files.

## Runtime contracts

- [Release Manifest JSON Schema](../../schemas/release-manifest.schema.json)
  defines the machine-readable manifest baseline.
- `tools.release.manifest.validate_manifest()` validates required simulation
  fields without requiring an optional JSON Schema package.
- Supported modes are `development`, `nightly`, `candidate`, `dry_run`,
  `qualification`, `production`, `hotfix` and `maintenance`. Even modes that
  conceptually permit publication remain simulation-only in this runtime.
- Profiles are `fast`, `balanced`, `full_qualification` and `production` and
  select required evidence classes.

## Readiness states

| State | Meaning |
| --- | --- |
| `READY` | Required candidate versions, SHAs and profile evidence are present and aligned. |
| `NOT_READY` | Required information is missing. |
| `BLOCKED` | A version is invalid/misaligned or supplied evidence has failed. |

The result contains structured condition codes, subjects and explanations.
Verification, Software Assurance, Trusted Delivery, coverage and platform
qualification are consumed as supplied evidence references/states; this runtime
does not reimplement their systems.

## Safety boundary

The release runtime is intentionally not an executor. Prompt 3 owns the first
complete Platform Release Dry Run. Production publication, tags, deployments
and rollback execution remain unavailable from this CLI.
