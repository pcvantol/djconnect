# DJConnect Software Assurance Repository Model

Status: canonical repository integration model  
Scope owner: `pcvantol/djconnect`  
Phase: architecture only; no implementation

## Purpose

This document defines how DJConnect repositories consume Software Assurance
without redefining it.

The canonical Software Assurance Platform lives in `pcvantol/djconnect`.
Sibling repositories may add repository-specific extensions, but they must not
copy, fork or redefine canonical Software Assurance capability, policy,
execution or health models.

## Repository Integration Layers

```text
Canonical Platform
  -> Verification Runtime
  -> Repository-specific Extension
  -> Repository Evidence
  -> Software Assurance Reports
  -> Platform Health
```

Canonical Platform owns shared definitions. Verification Runtime owns shared
planning and execution plumbing. Repositories own local evidence production
for their source, artifacts and release surfaces.

## Cross-Repository Responsibilities

| Repository | Consumes | May extend | Must not own |
| --- | --- | --- | --- |
| `pcvantol/djconnect` | All canonical Software Assurance docs. | Canonical contracts, Verification Runtime integration and HA-specific evidence. | Native client code, firmware source or release artifact publication for sibling repos. |
| `pcvantol/djconnect-app` | Capability, evidence, execution and health models. | Apple analyzer/build/signing/test evidence. | Canonical Software Assurance policy or backend behaviour. |
| `pcvantol/djconnect-windows` | Capability, evidence, execution and health models. | Windows analyzer/build/package evidence. | Canonical policy or platform health definitions. |
| `pcvantol/djconnect-pi` | Capability, evidence, execution and health models. | Pi runtime, packaging, service and device evidence. | Canonical assurance governance. |
| `pcvantol/djconnect-esp32` | Capability, evidence, execution and health models. | Firmware build, PlatformIO, serial, OTA and hardware evidence. | Backend playback or canonical release policy. |
| `pcvantol/djconnect-api` | Capability, evidence, execution and health models. | API security, relay, token and deployment evidence. | Local-first HA runtime behaviour. |
| `pcvantol/djconnect-website` | Capability, evidence, execution and health models. | Website build, link, SEO, docs and localization evidence. | Runtime contracts or release artifact truth. |
| `pcvantol/djconnect-firmware` | Release assurance and supply-chain models. | Public firmware artifact metadata and distribution evidence. | ESP32 source implementation. |
| `pcvantol/djconnect-app-releases` | Release assurance and supply-chain models. | App release artifact metadata and distribution evidence. | Apple client source or entitlement policy. |
| `pcvantol/djconnect-pi-releases` | Release assurance and supply-chain models. | Pi release artifact metadata and distribution evidence. | Pi source implementation. |

## Repository Consumption Rules

Each repository should:

- point to canonical Software Assurance docs;
- produce repo-local evidence through canonical contracts;
- classify findings with canonical owner/severity/release-impact semantics;
- keep repo-specific tool details local;
- avoid copying platform-wide Software Assurance models;
- route behavioural questions back to Verification;
- route product or ownership changes back to Foundation/ADR docs.

Each repository must not:

- redefine Software Assurance themes;
- create local capability IDs that conflict with canonical IDs;
- invent release gates in scripts;
- allow scanners to create backlog items directly;
- hide evidence behind repo-local dashboards;
- treat GitHub Actions as the quality owner.

## Repository Bootstrap

Repository sessions should read:

```text
BOOTSTRAP_CODEX_SESSION.md
  -> repository AGENTS.md
  -> CANONICAL_REFERENCES.md or canonical repository pointer
  -> Platform Foundation
  -> Verification Foundation when behavioural evidence is relevant
  -> Software Assurance Foundation when engineering quality is relevant
  -> repository-local phase or prompt
```

This keeps clean sessions from relying on chat history or duplicated
repository-local copies of canonical Software Assurance.

## Repository Evidence Lifecycle

```text
Repository check or artifact
  -> Local evidence
  -> Canonical evidence contract
  -> Owner/severity classification
  -> Repository health input
  -> Platform Health input
  -> Backlog or release review when policy requires
```

Repository evidence should include:

- repository name;
- branch and SHA where applicable;
- tool or workflow identity where applicable;
- runtime or build version where applicable;
- evidence type;
- owner;
- redaction status;
- release impact;
- links or paths to raw evidence.

## Release Repository Model

Release repositories own distribution state only.

They may produce:

- artifact metadata;
- checksums;
- release notes;
- compatibility notes;
- manifest evidence;
- signing/provenance references;
- publication evidence.

They must not become product logic, source architecture or canonical Software
Assurance owners.

## Repository Drift

Repository drift findings may include:

- missing canonical pointers;
- stale AGENTS/bootstrap guidance;
- missing license or third-party notice material;
- duplicated platform foundation files;
- local quality gates that conflict with canonical policy;
- release artifacts without expected metadata;
- prompts that contradict current phase state.

Drift findings require owner classification before they become backlog work.

## Cross-platform Interaction

Cross-platform Software Assurance evidence should preserve boundaries:

- Apple, Windows and Pi own client evidence;
- ESP32 owns firmware evidence;
- website owns documentation and public presentation evidence;
- API owns central relay evidence;
- release repositories own artifact distribution evidence;
- `pcvantol/djconnect` owns canonical aggregation and platform health.

Cross-platform findings should identify the producing repository, consuming
repository, affected contract and canonical owner.
