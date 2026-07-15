# DJConnect Repository Governance Rollout

**Status:** blocked pending canonical-governance correction  
**Decision:** `DJCONNECT_REPOSITORY_GOVERNANCE_ROLLOUT_BLOCKED`  
**Assessment date:** 2026-07-15

## Decision and blocker

Repository adoption cannot be planned safely yet. The canonical Platform
Architect instructions identify themselves as **AI-Native Engineering Operating
System Version 2.2**, while their required decision value remains
`AI_NATIVE_ENGINEERING_OPERATING_SYSTEM_V2_1_ESTABLISHED`. This is an internal
version contradiction in the source that every repository would otherwise
adopt. No separate adoption version can be assigned objectively.

The canonical source is centralized in `pcvantol/djconnect`, not duplicated in
the assessed repositories. `ENGINEERING_METHOD.md` is version 2.4 and is an
operational contract within that source; it does not resolve the contradictory
Operating System version above. Per the requested fail-closed rule, no
repository-adoption prompt, queue, or implementation PR is generated until one
central correction establishes a single adoption contract.

## Evidence

- Current central `main` was synchronized at
  `d26a6068cd9d0a6ae01e633eba82606b18e30606`, tracking `origin/main` with zero
  divergence and a clean working tree.
- GitHub records central PR [#125](https://github.com/pcvantol/djconnect/pull/125)
  as merged on 2026-07-15. Its squash merge is current `main`; the next
  increment reconciles the expected `MERGED_UNRECONCILED` records.
- `docs/governance/PLATFORM_ARCHITECT_SYSTEM_INSTRUCTIONS.md` names Version 2.2
  and later prescribes the V2.1 decision value.
- The canonical source also contains the required Platform Architect
  instructions, Engineering Method, prompt governance, initialization,
  finalization, synchronization and post-merge rules. The problem is version
  identity, not missing ownership.

## Repository inventory

GitHub account inventory and current default-branch inspection identify these
repositories. All listed active repositories use `main` as their default
branch.

| Repository | Classification | Evidence-based current state | Governance assessment |
| --- | --- | --- | --- |
| `pcvantol/djconnect` | `CENTRAL_GOVERNANCE_REPOSITORY` | Canonical platform and HA integration; PR #125 merged. | Source correction required before rollout. |
| `pcvantol/djconnect-app` | `ACTIVE_ENGINEERING_REPOSITORY` | Apple source; PR [#23](https://github.com/pcvantol/djconnect-app/pull/23) merged 2026-07-15. | `APPLE_GOVERNANCE_ADOPTION_PARTIAL`; see below. |
| `pcvantol/djconnect-windows` | `ACTIVE_ENGINEERING_REPOSITORY` | Windows source; latest merged PR #15. | No canonical local bootstrap/status/roadmap set discovered at root. |
| `pcvantol/djconnect-pi` | `ACTIVE_ENGINEERING_REPOSITORY` | Raspberry Pi source; latest merged PR #46. | No canonical local bootstrap/status/roadmap set discovered at root. |
| `pcvantol/djconnect-esp32` | `ACTIVE_ENGINEERING_REPOSITORY` | ESP32 source; latest merged PR #23. | No canonical local bootstrap/status/roadmap set discovered at root. |
| `pcvantol/djconnect-api` | `ACTIVE_ENGINEERING_REPOSITORY` | Cloudflare Worker API; latest merged PR #45. | No canonical local bootstrap/status/roadmap set discovered at root. |
| `pcvantol/djconnect-website` | `ACTIVE_ENGINEERING_REPOSITORY` | Website source; latest merged PR #23. | No canonical local bootstrap/status/roadmap set discovered at root. |
| `pcvantol/djconnect-firmware` | `ACTIVE_DISTRIBUTION_REPOSITORY` | Public OTA firmware artifacts; latest merged PR #7. | No canonical local bootstrap/status/roadmap set discovered at root. |
| `pcvantol/djconnect-app-releases` | `ACTIVE_DISTRIBUTION_REPOSITORY` | Apple artifact handoff; latest merged PR #8. | No canonical local bootstrap/status/roadmap set discovered at root. |
| `pcvantol/djconnect-pi-releases` | `ACTIVE_DISTRIBUTION_REPOSITORY` | Pi release artifacts; latest merged PR #7. | No canonical local bootstrap/status/roadmap set discovered at root. |
| `pcvantol/djconnect-verification-platform` | `NOT_FOUND` | GitHub repository lookup returned 404; current canonical documents reference a container runtime name. | Do not create an adoption prompt without a repository. |
| `pcvantol/djconnect-releases` | `NOT_FOUND` | GitHub repository lookup returned 404. | No adoption prompt. |
| `pcvantol/djconnect-sha-enforcement-reproducer` | `OUT_OF_SCOPE` | Private isolated reproducer, explicitly non-production. | No adoption prompt. |

The source/distribution split is retained: source repositories own native
implementation and validation; distribution repositories own artifacts,
manifests, checksums and release evidence. Docker remains specific to the
verification-runtime distribution and is not a universal release target.

## Apple verification

**Result:** `APPLE_GOVERNANCE_ADOPTION_PARTIAL`

Apple correctly references the central foundation and retains local rather than
copied governance. It has `BOOTSTRAP.md`, all five local rolling records,
`CANONICAL_REFERENCES.md`, and an immutable record at
`docs/history/prompts/2026-07-15-generation-2-governance-bootstrap.md`.

It is not verified because its current `main` already contains merged PR #23,
but its rolling records still say that PR is pending review and its prompt index
uses `REVIEWABLE_PENDING_MERGE` rather than the canonical lifecycle state.
The adoption declaration also does not state one adopted governance version or
repository-specific exceptions, and the inspected bootstrap does not define a
repository-specific Definition of Done, validation profile, release/deployment
profile, or fail-closed branch-cleanup contract. Those gaps must be assessed
against the corrected central contract; no Apple correction prompt is produced
while that contract is ambiguous.

## Deferred rollout and risk

The default rollout order remains appropriate after unblocking: central
baseline, Apple correction, Windows, Raspberry Pi, ESP32, firmware
distribution, API, verification runtime if it gains a repository, website,
distribution repositories, then a cross-repository audit. This is a
provisional order only, not an executable queue.

| Risk | Priority | Treatment |
| --- | --- | --- |
| Contradictory canonical adoption version | P0 | Correct centrally before any repository prompt. |
| Apple post-merge records are stale | P0 after central correction | Reconcile in the focused Apple adoption PR. |
| Other active repositories lack the discovered local governance record set | P0 after central correction | Verify each separately and adopt through one PR each. |
| Verification-platform/release repository names are not found | P1 | Resolve ownership or repository identity during final audit. |

## Required central correction prompt

```text
Title: Governance: establish a single AI-Native Engineering Operating System adoption contract
Repository: pcvantol/djconnect
Mission: Correct the canonical governance-version contradiction and publish one unambiguous, referenceable adoption contract. Do not adopt governance in sibling repositories.

Synchronization:
1. Run `git switch main` and `git pull --ff-only`.
2. Verify branch, HEAD, upstream, zero divergence and a clean worktree; stop on failure.
3. Verify the latest merged central PR, its current-main containment and immutable Prompt History; classify and reconcile any `MERGED_UNRECONCILED` rolling state before substantive work.

Current-state verification:
1. Inspect the Platform Architect instructions, Engineering Method, Prompt Governance, Prompt Initialization, Prompt Finalization, Repository Synchronization and current rollout report.
2. Prove the exact version/decision contradiction and identify every canonical reference that states an Operating System or adoption version.
3. Perform the implementation-reality check: reuse an existing unambiguous contract if one already exists; otherwise make only the smallest central correction.

Scope:
- Establish exactly one named AI-Native Engineering Operating System version and matching decision value.
- Add or correct one concise canonical adoption contract that names the source repository, canonical document path, adopted version, local-exception rule and reference-not-copy rule.
- Align only directly contradictory central governance documents and this blocked rollout record.
- Do not change Platform Architecture, product implementation, sibling repositories, release execution or repository-local adoption.

Validation and release profile:
- Verify every adoption-contract reference resolves locally.
- Search canonical governance documents for contradictory Operating System versions/decision values.
- Confirm the contract requires repository-specific native validation and release profiles rather than Docker by default.
- Run `git diff --check`.

Finalization:
- Update ENGINEERING_STATUS.md, REPOSITORY_STATUS.md, MANAGEMENT_SUMMARY.md, ROADMAP_INDEX.md where required and PROMPT_INDEX.md.
- Create one immutable Prompt History record.
- Produce exactly one reviewable, mergeable central-governance PR; do not merge it.

Decision: AI_NATIVE_ENGINEERING_ADOPTION_CONTRACT_ESTABLISHED or AI_NATIVE_ENGINEERING_ADOPTION_CONTRACT_BLOCKED.
Required execution report: decision, branch, final commit SHA, PR, resolved canonical version, corrected documents, validation, limitations, deferred work and exactly one recommended next prompt: the evidence-based first repository adoption prompt.
```

## Completion criteria for this planning increment

This blocked planning increment is complete when the contradiction, repository
inventory, Apple result, stop condition and one central correction prompt are
recorded. It deliberately does not satisfy the conditions for
`DJCONNECT_REPOSITORY_GOVERNANCE_ROLLOUT_PLANNED`: the canonical adoption
source is not yet unambiguous, so a deterministic repository prompt queue and
per-repository prompt specifications would be unsafe.
