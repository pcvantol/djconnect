# DJConnect Software Assurance Quality Gates

Status: canonical gate architecture  
Scope owner: `pcvantol/djconnect`  
Phase: architecture frozen; no gates enabled

## Purpose

This document defines canonical Software Assurance quality gates.

It does not enable gates. It defines the future architecture so gates can be
introduced only through explicit policy and implementation work.

## Gate Principles

- Policies own gates.
- Workflows execute gates.
- Evidence supports gates.
- Metrics never replace gates.
- Platform Health never blocks releases directly.
- Gate promotion requires explicit implementation approval.

## Canonical Gates

| Gate | Purpose | Inputs | Outputs | Blocking conditions | Evidence | Owner |
| --- | --- | --- | --- | --- | --- | --- |
| Developer Gate | Give fast local feedback before review. | Local source, advisory policies, schemas, repo metadata. | Local findings and evidence previews. | None by default. | Local report or dry-run evidence. | Repository owner. |
| Repository Gate | Establish repository quality posture. | Static quality, dependency, docs and repository metadata. | Repository health input. | Only after explicit repository policy promotion. | Repository quality report. | Repository owner with canonical policy. |
| Verification Gate | Protect behavioural correctness. | Verification scenarios, plans, execution evidence and readiness reports. | Behavioural qualified/warn/blocked status. | Verification policy failure. | Verification evidence and reports. | Verification Platform. |
| Security Gate | Classify security and privacy risk. | Static security, CVE/advisory, secret-safety and auth-sensitive evidence. | Security finding status and release impact. | Policy-defined severe or release-impacting findings. | Security evidence report. | Software Assurance with repository owner. |
| Nightly Gate | Maintain broad recurring health visibility. | Nightly policy, broad evidence, runner health and trend data. | Trend findings and backlog recommendations. | None by default; future policy may block specific nightly promotion. | Nightly assurance report. | Software Assurance. |
| Release Candidate Gate | Determine release candidate evidence completeness. | Verification evidence, release evidence, supply chain, compatibility and runtime metadata. | RC qualified/warn/blocked input. | Missing required RC evidence or policy-blocking finding. | Release candidate evidence bundle. | Release Qualification owner. |
| Release Gate | Decide whether a release may be promoted. | RC gate output, waivers, release notes, artifacts, provenance and baseline impact. | Release go/no-go input. | Release-blocking policy failure without formal waiver. | Release qualification report. | Release governance owner. |

## Gate Lifecycle

```text
Proposed Gate
  -> Policy Definition
  -> Evidence Contract
  -> Advisory Dry Run
  -> Report Review
  -> Explicit Promotion
  -> Blocking Gate
```

No gate may skip advisory dry-run and report review unless an emergency
release governance decision explicitly records the exception.

## Waivers

Waivers must include:

- affected gate;
- finding ID or evidence reference;
- owner;
- reason;
- risk;
- expiration or review condition;
- release impact;
- maintainer approval.

Waivers do not delete evidence.

## Relationship To Platform Health

Platform Health may show that a gate is healthy, stale, missing or failing.
It does not decide gate outcomes.

Gate outcomes come from policy and evidence.
