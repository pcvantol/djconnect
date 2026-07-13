# Platform Release Orchestrator Runtime

Status: controlled internal-execution implementation
Scope owner: `pcvantol/djconnect`

## Purpose

`tools.release` implements the reusable Platform Release Orchestrator control
plane. It consumes an ownership document and caller-supplied candidate facts to
compose a canonical Release Manifest, execution plan, readiness result,
qualification plan, artifact plan and rollback plan. It also provides a
fail-closed `INTERNAL_RELEASE` executor over that approved plan.

It never builds software directly or selects sibling repositories by name.
Build, tagging, release creation, artifact publication, deployment and rollback
remain explicit GitHub Actions workflow responsibilities. The runtime has no
direct mutation capability.

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

Planning commands are simulations and return JSON without writing a Release
Manifest to the repository. With missing candidate facts, the simulation
correctly reports `NOT_READY` or `BLOCKED` with every condition explained.

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
  `qualification`, `production`, `hotfix` and `maintenance`. Operational
  execution is additionally constrained to `production` or `hotfix` mode with
  the `INTERNAL_RELEASE` profile.
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

## Controlled execution

`rehearse` exercises the complete action ordering through an evidence-only
client. It never contacts GitHub, creates a tag, publishes an artifact or
deploys a target. It is the required representative non-production validation.

```bash
python -m tools.release \
  --ownership tests/release/fixtures/operational-ownership.md \
  --platform-version 3.3 --mode production \
  --versions-file tests/release/fixtures/operational-versions.json \
  --shas-file tests/release/fixtures/operational-shas.json \
  --evidence-file tests/release/fixtures/operational-evidence.json \
  --execution-file tests/release/fixtures/operational-request.json \
  --output-dir /tmp/djconnect-release-rehearsal rehearse
```

`execute` requires the additional `--execute` acknowledgement plus an approved
execution request and evidence output directory. It dispatches and monitors
only the workflows named by that request through the authenticated GitHub CLI,
then reads their canonical evidence artifact. Each request action is generic
and must identify a discovered repository, category, workflow/ref and the
bounded immutable candidate inputs. This preserves dynamic repository discovery
while keeping every mutation inside GitHub Actions.

Execution fails closed unless all of the following are true:

- release mode is `production` or `hotfix`;
- readiness is `READY` with aligned versions and candidate SHAs;
- the production/hotfix manifest marks the candidate `QUALIFIED`;
- Verification, Software Assurance, Trusted Delivery, coverage and platform
  qualification evidence are all `PASS`;
- every action belongs to the immutable discovered release scope; and
- the request is explicitly `INTERNAL_RELEASE`.

On the first action failure the executor stops, preserves already completed
operation receipts and writes rollback-preparation evidence. It never
continues downstream actions or silently falls back to another channel.

The executor emits `release-execution-report.json`, deployment evidence and
publication evidence. Their machine-readable contract is
`schemas/release-execution.schema.json`.

## Safety boundary

The runtime does not compile software, create tags or releases, upload
artifacts itself, publish, deploy, or execute rollback. Apple and Windows builds remain
on their qualified native runners; all other source builds remain on
GitHub-hosted Linux according to the frozen runner policy.
