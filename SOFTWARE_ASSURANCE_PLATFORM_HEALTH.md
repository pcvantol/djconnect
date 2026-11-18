# DJConnect Software Assurance Platform Health

Status: canonical Platform Health architecture  
Scope owner: `pcvantol/djconnect`  
Phase: architecture only; no implementation

## Purpose

Platform Health is the Software Assurance trend model for understanding how
DJConnect quality evolves.

Platform Health visualizes platform evolution. It never blocks releases
directly. Policies block releases.

## Data Flow

```text
Evidence
  -> Metrics
  -> Quality Indicators
  -> Health Trends
  -> Dashboards
  -> Engineering Decisions
```

Evidence comes first. Metrics are derived from evidence. Quality indicators
interpret metrics. Trends show movement over time. Dashboards present trends.
Engineering decisions use the information but remain governed by policies,
ownership and release rules.

## Health Categories

| Category | Meaning | Typical inputs | Owner |
| --- | --- | --- | --- |
| Functional | Behavioural verification posture and known functional risks. | Verification reports, scenario readiness, blocked/warning outcomes. | Verification Platform for source evidence; Software Assurance for trend view. |
| Engineering | Maintainability, static quality, documentation, CI reliability and delivery posture. | Static quality, drift, complexity, runner health and documentation evidence. | Software Assurance. |
| Security | Static security, secret safety, auth-sensitive findings and vulnerability posture. | CodeQL/Semgrep references, CVE findings, secret-safety evidence and policy classifications. | Software Assurance with repository owners for fixes. |
| Supply Chain | Dependency, SBOM, license, provenance and artifact integrity posture. | Dependency inventory, SBOM, license reports, checksums and provenance. | Software Assurance with repository/release owners for evidence. |
| Operational | Runtime diagnostics, recovery, release operations and support readiness. | Diagnostics evidence, recovery evidence, rollback posture and release operations metadata. | Software Assurance with runtime/release owners. |
| Repository | Per-repository hygiene, ownership alignment, bootstrap quality and drift. | Repository inventory, required docs, AGENTS/bootstrap alignment and ownership map. | Canonical Platform. |
| Execution Efficiency | Cost, runtime, runner health, artifact retention and scheduling posture. | Execution profiles, runner qualification, runtime summaries, artifact retention and budgets. | Software Assurance and Verification Runtime. |
| Developer Experience | Local feedback speed, clarity, reproducibility and author-side usefulness. | Developer profile evidence, dry-run usability, report readability and local setup posture. | Software Assurance with repository maintainers. |

No scoring formulas are defined in this phase.

## Health Semantics

Platform Health can report:

- improving;
- stable;
- degrading;
- unknown;
- stale;
- missing;
- externally blocked;
- policy-blocked.

Health does not decide whether a release may ship. Release policies and Release
Qualification decide that.

## Evidence To Health Ownership

Software Assurance may aggregate:

- Verification evidence references;
- Software Assurance evidence;
- repository metadata;
- runtime metadata;
- CI metadata;
- dependency metadata;
- build metadata;
- release metadata.

Software Assurance must not duplicate raw Verification evidence or rewrite
Verification readiness decisions.

## Dashboards

Dashboards are consumption surfaces.

They may show:

- health categories;
- trend direction;
- stale evidence;
- missing evidence;
- warnings;
- release-impacting findings;
- backlog recommendations;
- owner breakdown.

Dashboards must not:

- compute their own policy;
- create backlog items directly;
- override release gates;
- hide missing evidence behind aggregate scores.

## Backlog Recommendations

Health findings may feed backlog recommendations only through classification:

```text
Health Finding
  -> Evidence Reference
  -> Owner Classification
  -> Risk Assessment
  -> Backlog Recommendation
  -> Platform or Repository Backlog
```

This keeps scanners, dashboards and metrics from creating unreviewed backlog
items directly.

## Release Relationship

Release Qualification may consume Platform Health as context. It must still
make release decisions from policy, evidence and qualification rules.

Examples:

- improving repository health may support confidence, but it cannot override a
  release-blocking missing checksum;
- stale functional evidence may require release review even if security health
  is strong;
- supply chain health may identify release risk only when policy classifies the
  finding as warning or blocking.

## Principles

- Evidence before metrics.
- Metrics never replace policy.
- Trends explain direction, not truth.
- Missing evidence is visible.
- Stale evidence is visible.
- Health is cross-repository but owner-aware.
- Platform Health supports engineering decisions; it does not make them alone.
